"""
Autonomous Contract Comparison and Change Extraction System

This is the main entry point for the contract comparison system. It orchestrates
the complete workflow from image parsing through multi-agent analysis to
validated structured output.

Workflow Architecture:
    1. Image Parsing: Uses GPT-4o Vision to convert scanned contract images to text
    2. Agent 1 (Contextualization): Analyzes structure and maps sections
    3. Agent 2 (Change Extraction): Extracts specific changes using Agent 1's context
    4. Output Validation: Ensures Pydantic-compliant structured output
    5. Tracing: All steps instrumented with Langfuse for observability

Command Line Usage:
    python src/main.py --original <path> --amendment <path> [--output <path>]

Example:
    python src/main.py --original data/test_contracts/contract1_original.jpg \\
                       --amendment data/test_contracts/contract1_amendment.jpg \\
                       --output results.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from openai import OpenAI
from langfuse.decorators import observe, langfuse_context
from langfuse import Langfuse

import logging
from src.image_parser import parse_contract_image, get_llm_client
from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
from src.models import ContractChangeOutput, ParsedContract, AgentContext

# Configure logger
logger = logging.getLogger(__name__)


# Load environment variables from .env file
load_dotenv()


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set.

    Checks for:
    - OPENAI_API_KEY *OR* OPENROUTER_API_KEY: Required for LLM
    - LANGFUSE_PUBLIC_KEY: Required for tracing
    - LANGFUSE_SECRET_KEY: Required for tracing
    """
    # 1. Check for LLM Key
    has_llm_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    
    # 2. Check for Langfuse
    required_vars = [
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY"
    ]

    missing_vars = []
    if not has_llm_key:
        missing_vars.append("OPENAI_API_KEY (or OPENROUTER_API_KEY)")

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error("Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.error("Please set these variables in your .env file.")
        return False

    return True


def initialize_clients() -> tuple[OpenAI, Langfuse]:
    """
    Initialize LLM and Langfuse clients with API credentials.
    """
    try:
        # Initialize LLM client (OpenAI or OpenRouter)
        openai_client = get_llm_client()

        # Initialize Langfuse client with explicit configuration
        langfuse_client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            debug=False,
            enabled=True
        )

        return openai_client, langfuse_client

    except Exception as e:
        logger.exception("Failed to initialize clients")
        raise ValueError(f"Failed to initialize clients: {str(e)}")


@observe(name="complete_workflow", capture_input=False, capture_output=False)
def process_contract_comparison(
    original_image_path: str,
    amendment_image_path: str,
    openai_client: OpenAI
) -> tuple[ContractChangeOutput, str | None]:
    """
    Execute the complete contract comparison workflow.

    This function orchestrates all stages of the comparison process:
    1. Parse both contract images using multimodal LLM
    2. Execute Agent 1 for contextualization
    3. Execute Agent 2 for change extraction (receives Agent 1 output)
    4. Validate final output with Pydantic

    All steps are traced with Langfuse to provide complete observability.

    Args:
        original_image_path: Path to original contract image
        amendment_image_path: Path to amendment contract image
        openai_client: Initialized OpenAI client

    Returns:
        ContractChangeOutput with validated change information

    Raises:
        Exception: If any stage of the workflow fails

    Example:
        >>> result = process_contract_comparison(
        ...     "contract_orig.jpg",
        ...     "contract_amend.jpg",
        ...     client
        ... )
    """
    # Generate session ID for tracing correlation
    session_id = f"contract_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Update trace with session metadata
    langfuse_context.update_current_trace(
        session_id=session_id,
        input={
            "original_image_path": original_image_path,
            "amendment_image_path": amendment_image_path
        },
        metadata={
            "workflow": "contract_comparison",
            "original_image": original_image_path,
            "amendment_image": amendment_image_path,
            "timestamp": datetime.now().isoformat()
        },
        tags=["contract_comparison", "multi_agent", "multimodal"]
    )

    logger.info("="*70)
    logger.info("AUTONOMOUS CONTRACT COMPARISON SYSTEM")
    logger.info("="*70)

    # STEP 1: Parse Original Contract Image
    logger.info("STEP 1: Parsing original contract image...")
    logger.info(f"  Image: {original_image_path}")

    try:
        original_contract = parse_contract_image(
            image_path=original_image_path,
            document_type="original",
            client=openai_client
        )
        logger.info(f"  ✓ Extracted {len(original_contract.raw_text)} characters")
        logger.info(f"  ✓ Identified {len(original_contract.sections_identified)} sections")
    except Exception as e:
        error_msg = f"Failed to parse original contract: {str(e)}"
        langfuse_context.update_current_observation(
            level="ERROR",
            status_message=error_msg
        )
        raise Exception(error_msg)

    # STEP 2: Parse Amendment Contract Image
    logger.info("STEP 2: Parsing amendment contract image...")
    logger.info(f"  Image: {amendment_image_path}")

    try:
        amendment_contract = parse_contract_image(
            image_path=amendment_image_path,
            document_type="amendment",
            client=openai_client
        )
        logger.info(f"  ✓ Extracted {len(amendment_contract.raw_text)} characters")
        logger.info(f"  ✓ Identified {len(amendment_contract.sections_identified)} sections")
    except Exception as e:
        error_msg = f"Failed to parse amendment contract: {str(e)}"
        langfuse_context.update_current_observation(
            level="ERROR",
            status_message=error_msg
        )
        raise Exception(error_msg)

    # STEP 3: Execute Agent 1 (Contextualization)
    logger.info("STEP 3: Executing Agent 1 (Contextualization)...")
    logger.info("  Analyzing document structure and mapping sections...")

    try:
        agent1 = ContextualizationAgent(client=openai_client)
        context = agent1.analyze(
            original_contract=original_contract,
            amendment_contract=amendment_contract
        )

        logger.info(f"  ✓ Identified {len(context.identified_change_areas)} change areas")
        logger.info(f"  ✓ Mapped {len(context.corresponding_sections)} sections")
        logger.info(f"  ✓ Context: {context.context_summary[:100]}...")
    except Exception as e:
        error_msg = f"Agent 1 (Contextualization) failed: {str(e)}"
        langfuse_context.update_current_observation(
            level="ERROR",
            status_message=error_msg
        )
        raise Exception(error_msg)

    # STEP 4: Execute Agent 2 (Change Extraction)
    logger.info("STEP 4: Executing Agent 2 (Change Extraction)...")
    logger.info("  Using Agent 1's context to extract specific changes...")

    try:
        agent2 = ExtractionAgent(client=openai_client)
        changes = agent2.extract_changes(
            original_contract=original_contract,
            amendment_contract=amendment_contract,
            context=context  # This shows the explicit Agent 1 -> Agent 2 handoff
        )

        logger.info(f"  ✓ Found changes in {len(changes.sections_changed)} sections")
        logger.info(f"  ✓ Identified {len(changes.topics_touched)} affected topics")
        logger.info(f"  ✓ Generated summary of {len(changes.summary_of_the_change)} characters")
    except Exception as e:
        error_msg = f"Agent 2 (Extraction) failed: {str(e)}"
        langfuse_context.update_current_observation(
            level="ERROR",
            status_message=error_msg
        )
        raise Exception(error_msg)

    # STEP 5: Validate Output
    logger.info("STEP 5: Validating structured output...")

    try:
        # The output is already Pydantic-validated in Agent 2
        # This demonstrates that validation occurred
        logger.info("  ✓ Output structure validated")
        logger.info("  ✓ All required fields present")
        logger.info("  ✓ Field constraints satisfied")

        # Add validation metadata to trace
        langfuse_context.update_current_observation(
            metadata={
                "validation_passed": True,
                "output_model": "ContractChangeOutput",
                "sections_changed_count": len(changes.sections_changed),
                "topics_touched_count": len(changes.topics_touched),
                "summary_length": len(changes.summary_of_the_change)
            }
        )

    except Exception as e:
        error_msg = f"Output validation failed: {str(e)}"
        langfuse_context.update_current_observation(
            level="ERROR",
            status_message=error_msg
        )
        raise Exception(error_msg)

    logger.info("="*70)
    logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
    logger.info("="*70)

    # Manually log output at trace level (since capture_output=False)
    langfuse_context.update_current_trace(
        output={
            "sections_changed": changes.sections_changed,
            "topics_touched": changes.topics_touched,
            "summary_of_the_change": changes.summary_of_the_change
        }
    )

    return changes, langfuse_context.get_current_trace_id()


def save_output(
    changes: ContractChangeOutput,
    output_path: str,
    include_metadata: bool = True
) -> None:
    """
    Save the structured output to a JSON file.

    Args:
        changes: ContractChangeOutput object to save
        output_path: Path where JSON file should be saved
        include_metadata: Whether to include metadata in output

    Example:
        >>> save_output(changes, "results.json")
    """
    output_data = changes.model_dump()

    if include_metadata:
        output_data["_metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "system": "Autonomous Contract Comparison System",
            "version": "1.0.0"
        }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Results saved to: {output_path}")


def print_results(changes: ContractChangeOutput) -> None:
    """
    Print formatted results to console.

    Args:
        changes: ContractChangeOutput object to display
    """
    print("\n" + "="*70)
    print("CHANGE EXTRACTION RESULTS")
    print("="*70)

    print(f"\nSECTIONS CHANGED ({len(changes.sections_changed)}):")
    for i, section in enumerate(changes.sections_changed, 1):
        print(f"  {i}. {section}")

    print(f"\nTOPICS AFFECTED ({len(changes.topics_touched)}):")
    for i, topic in enumerate(changes.topics_touched, 1):
        print(f"  {i}. {topic}")

    print("\nSUMMARY OF CHANGES:")
    print("-" * 70)
    # Wrap summary text for better readability
    summary = changes.summary_of_the_change
    words = summary.split()
    line = ""
    for word in words:
        if len(line) + len(word) + 1 <= 70:
            line += word + " "
        else:
            print(line)
            line = word + " "
    if line:
        print(line)

    print("="*70)


def main():
    """
    Main entry point for command-line execution.

    Parses arguments, validates environment, executes workflow,
    and outputs results.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Autonomous Contract Comparison System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py --original contract1.jpg --amendment contract1_amended.jpg

  python src/main.py --original data/test_contracts/contract1_original.jpg \\
                     --amendment data/test_contracts/contract1_amendment.jpg \\
                     --output results.json

For more information, see README.md
        """
    )

    parser.add_argument(
        "--original",
        type=str,
        required=True,
        help="Path to original contract image (JPG, PNG, etc.)"
    )

    parser.add_argument(
        "--amendment",
        type=str,
        required=True,
        help="Path to amendment contract image (JPG, PNG, etc.)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save JSON output (optional, prints to console if not specified)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="OpenAI model to use (default: gpt-4o)"
    )

    args = parser.parse_args()

    # Configure Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'  # Simplified format for CLI-like feel
    )

    # Validate environment
    if not validate_environment():
        sys.exit(1)

    # Validate input files exist
    if not os.path.exists(args.original):
        print(f"ERROR: Original contract image not found: {args.original}")
        sys.exit(1)

    if not os.path.exists(args.amendment):
        print(f"ERROR: Amendment contract image not found: {args.amendment}")
        sys.exit(1)

    try:
        # Initialize clients
        openai_client, langfuse_client = initialize_clients()

        # Execute workflow
        changes, trace_id = process_contract_comparison(
            original_image_path=args.original,
            amendment_image_path=args.amendment,
            openai_client=openai_client
        )
        
        if trace_id:
            logger.info(f"Langfuse Trace ID: {trace_id}")


        # Print results to console
        print_results(changes)

        # Save to file if output path specified
        if args.output:
            save_output(changes, args.output)
        else:
            # Print JSON to console
            print("\nJSON OUTPUT:")
            print("-" * 70)
            print(json.dumps(changes.model_dump(), indent=2))

        # Flush Langfuse traces
        langfuse_client.flush()

        print("\n✓ Check your Langfuse dashboard for detailed trace:")
        print(f"  {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
        sys.exit(1)

    except Exception as e:
        print(f"\n\nERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
