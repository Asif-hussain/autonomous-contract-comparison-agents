"""
Enhanced Contract Comparison System with Guardrails and Evaluation

This enhanced version includes:
1. Input validation with guardrails
2. Output quality evaluation
3. Safety checks
4. Comprehensive metrics tracking

Usage:
    python src/main_enhanced.py --original <path> --amendment <path> [options]

Options:
    --skip-guardrails: Skip input validation (not recommended)
    --skip-evaluation: Skip output evaluation
    --enable-llm-eval: Enable LLM-based evaluation (slower, more comprehensive)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from openai import OpenAI
from langfuse.decorators import observe, langfuse_context
from langfuse import Langfuse

import logging

from src.image_parser import parse_contract_image, get_llm_client
from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
from src.models import ContractChangeOutput, ParsedContract, AgentContext
from src.guardrails import ContractGuardrails, SafetyGuardrails
from src.evaluator import ContractEvaluator, MetricsTracker

# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def validate_environment() -> bool:
    """Validate required environment variables."""
    has_llm_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")

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
        return False

    return True


def initialize_clients() -> tuple[OpenAI, Langfuse]:
    """Initialize LLM and Langfuse clients."""
    try:
        openai_client = get_llm_client()
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


@observe(name="enhanced_workflow", capture_input=False, capture_output=False)
def process_contract_comparison_enhanced(
    original_image_path: str,
    amendment_image_path: str,
    openai_client: OpenAI,
    enable_guardrails: bool = True,
    enable_evaluation: bool = True,
    enable_llm_eval: bool = False
) -> tuple[ContractChangeOutput, Optional[str], Dict[str, Any]]:
    """
    Execute the enhanced contract comparison workflow with guardrails and evaluation.

    Args:
        original_image_path: Path to original contract image
        amendment_image_path: Path to amendment contract image
        openai_client: Initialized OpenAI client
        enable_guardrails: Whether to apply input validation
        enable_evaluation: Whether to evaluate output quality
        enable_llm_eval: Whether to use LLM-based evaluation

    Returns:
        Tuple of (changes, trace_id, metadata) where metadata includes
        guardrails and evaluation results
    """
    session_id = f"contract_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    metadata = {
        'guardrails_enabled': enable_guardrails,
        'evaluation_enabled': enable_evaluation,
        'llm_eval_enabled': enable_llm_eval,
        'guardrails_results': {},
        'evaluation_results': {},
        'warnings': [],
        'errors': []
    }

    # Update trace
    langfuse_context.update_current_trace(
        session_id=session_id,
        input={
            "original_image_path": original_image_path,
            "amendment_image_path": amendment_image_path
        },
        metadata={
            "workflow": "enhanced_contract_comparison",
            "original_image": original_image_path,
            "amendment_image": amendment_image_path,
            "timestamp": datetime.now().isoformat()
        },
        tags=["contract_comparison", "multi_agent", "guardrails", "evaluation"]
    )

    logger.info("="*70)
    logger.info("ENHANCED CONTRACT COMPARISON SYSTEM")
    logger.info("="*70)

    # Initialize guardrails and evaluator
    guardrails = ContractGuardrails() if enable_guardrails else None
    safety_guardrails = SafetyGuardrails() if enable_guardrails else None
    evaluator = ContractEvaluator(client=openai_client) if enable_evaluation else None

    # STEP 1: Parse and Validate Original Contract
    logger.info("STEP 1: Parsing original contract...")
    logger.info(f"  Image: {original_image_path}")

    try:
        original_contract = parse_contract_image(
            image_path=original_image_path,
            document_type="original",
            client=openai_client
        )
        logger.info(f"  ✓ Extracted {len(original_contract.raw_text)} characters")

        # Apply guardrails
        if guardrails:
            logger.info("  Running input validation...")
            validation = guardrails.validate_input(
                contract=original_contract,
                file_path=original_image_path
            )
            metadata['guardrails_results']['original'] = validation

            if not validation['is_valid']:
                error_msg = f"Original contract failed validation: {validation['errors']}"
                logger.error(f"  ✗ {error_msg}")
                metadata['errors'].append(error_msg)
                raise ValueError(error_msg)

            if validation['warnings']:
                for warning in validation['warnings']:
                    logger.warning(f"  ⚠ {warning}")
                    metadata['warnings'].append(f"Original: {warning}")

            logger.info(f"  ✓ Validation passed ({validation['checks_passed']}/{validation['total_checks']})")

            # Safety check
            safety = safety_guardrails.check_content_safety(original_contract.raw_text)
            if not safety['is_safe']:
                error_msg = f"Safety check failed: {safety['threats_detected']}"
                logger.error(f"  ✗ {error_msg}")
                raise ValueError(error_msg)

    except Exception as e:
        error_msg = f"Failed to parse original contract: {str(e)}"
        langfuse_context.update_current_observation(level="ERROR", status_message=error_msg)
        raise Exception(error_msg)

    # STEP 2: Parse and Validate Amendment Contract
    logger.info("STEP 2: Parsing amendment contract...")
    logger.info(f"  Image: {amendment_image_path}")

    try:
        amendment_contract = parse_contract_image(
            image_path=amendment_image_path,
            document_type="amendment",
            client=openai_client
        )
        logger.info(f"  ✓ Extracted {len(amendment_contract.raw_text)} characters")

        # Apply guardrails
        if guardrails:
            logger.info("  Running input validation...")
            validation = guardrails.validate_input(
                contract=amendment_contract,
                file_path=amendment_image_path
            )
            metadata['guardrails_results']['amendment'] = validation

            if not validation['is_valid']:
                error_msg = f"Amendment contract failed validation: {validation['errors']}"
                logger.error(f"  ✗ {error_msg}")
                metadata['errors'].append(error_msg)
                raise ValueError(error_msg)

            if validation['warnings']:
                for warning in validation['warnings']:
                    logger.warning(f"  ⚠ {warning}")
                    metadata['warnings'].append(f"Amendment: {warning}")

            logger.info(f"  ✓ Validation passed ({validation['checks_passed']}/{validation['total_checks']})")

            # Safety check
            safety = safety_guardrails.check_content_safety(amendment_contract.raw_text)
            if not safety['is_safe']:
                error_msg = f"Safety check failed: {safety['threats_detected']}"
                logger.error(f"  ✗ {error_msg}")
                raise ValueError(error_msg)

    except Exception as e:
        error_msg = f"Failed to parse amendment contract: {str(e)}"
        langfuse_context.update_current_observation(level="ERROR", status_message=error_msg)
        raise Exception(error_msg)

    # STEP 3: Execute Agent 1 (Contextualization)
    logger.info("STEP 3: Executing Agent 1 (Contextualization)...")

    try:
        agent1 = ContextualizationAgent(client=openai_client)
        context = agent1.analyze(
            original_contract=original_contract,
            amendment_contract=amendment_contract
        )
        logger.info(f"  ✓ Identified {len(context.identified_change_areas)} change areas")
    except Exception as e:
        error_msg = f"Agent 1 failed: {str(e)}"
        langfuse_context.update_current_observation(level="ERROR", status_message=error_msg)
        raise Exception(error_msg)

    # STEP 4: Execute Agent 2 (Change Extraction)
    logger.info("STEP 4: Executing Agent 2 (Change Extraction)...")

    try:
        agent2 = ExtractionAgent(client=openai_client)
        changes = agent2.extract_changes(
            original_contract=original_contract,
            amendment_contract=amendment_contract,
            context=context
        )
        logger.info(f"  ✓ Found changes in {len(changes.sections_changed)} sections")
    except Exception as e:
        error_msg = f"Agent 2 failed: {str(e)}"
        langfuse_context.update_current_observation(level="ERROR", status_message=error_msg)
        raise Exception(error_msg)

    # STEP 5: Validate Output
    logger.info("STEP 5: Validating output...")

    if guardrails:
        output_validation = guardrails.validate_output(
            output=changes,
            original_contract=original_contract,
            amendment_contract=amendment_contract
        )
        metadata['guardrails_results']['output'] = output_validation

        if not output_validation['is_valid']:
            for error in output_validation['errors']:
                logger.error(f"  ✗ {error}")
                metadata['errors'].append(f"Output: {error}")

        if output_validation['warnings']:
            for warning in output_validation['warnings']:
                logger.warning(f"  ⚠ {warning}")
                metadata['warnings'].append(f"Output: {warning}")

        logger.info(f"  ✓ Output validation complete ({output_validation['checks_passed']}/{output_validation['total_checks']})")

    # STEP 6: Evaluate Quality
    if evaluator:
        logger.info("STEP 6: Evaluating output quality...")

        try:
            evaluation = evaluator.evaluate_output(
                changes=changes,
                original_contract=original_contract,
                amendment_contract=amendment_contract,
                context=context
            )
            metadata['evaluation_results']['rule_based'] = evaluation

            logger.info(f"  ✓ Quality Score: {evaluation['overall_score']:.2f}/100 (Grade: {evaluation['grade']})")
            logger.info(f"    Completeness: {evaluation['dimension_scores']['completeness']:.1f}")
            logger.info(f"    Accuracy: {evaluation['dimension_scores']['accuracy']:.1f}")
            logger.info(f"    Clarity: {evaluation['dimension_scores']['clarity']:.1f}")
            logger.info(f"    Relevance: {evaluation['dimension_scores']['relevance']:.1f}")
            logger.info(f"    Consistency: {evaluation['dimension_scores']['consistency']:.1f}")

            if evaluation['recommendations']:
                logger.info("  Recommendations:")
                for rec in evaluation['recommendations'][:3]:
                    logger.info(f"    - {rec}")

            # Optional LLM-based evaluation
            if enable_llm_eval:
                logger.info("  Running LLM-based evaluation...")
                llm_eval = evaluator.evaluate_with_llm(
                    changes=changes,
                    original_contract=original_contract,
                    amendment_contract=amendment_contract
                )
                metadata['evaluation_results']['llm_based'] = llm_eval

                if 'error' not in llm_eval:
                    logger.info(f"    Legal Accuracy: {llm_eval.get('legal_accuracy', 'N/A')}/10")
                    logger.info(f"    Business Relevance: {llm_eval.get('business_relevance', 'N/A')}/10")
                    logger.info(f"    Summary Quality: {llm_eval.get('summary_quality', 'N/A')}/10")

        except Exception as e:
            logger.warning(f"  ⚠ Evaluation failed: {str(e)}")
            metadata['warnings'].append(f"Evaluation: {str(e)}")

    logger.info("="*70)
    logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
    logger.info("="*70)

    # Update trace with results
    langfuse_context.update_current_trace(
        output={
            "sections_changed": changes.sections_changed,
            "topics_touched": changes.topics_touched,
            "summary_of_the_change": changes.summary_of_the_change,
            "metadata": metadata
        }
    )

    return changes, langfuse_context.get_current_trace_id(), metadata


def save_enhanced_output(
    changes: ContractChangeOutput,
    metadata: Dict[str, Any],
    output_path: str
) -> None:
    """Save enhanced output with metadata."""
    output_data = changes.model_dump()
    output_data["_metadata"] = {
        "generated_at": datetime.now().isoformat(),
        "system": "Enhanced Contract Comparison System",
        "version": "2.0.0",
        "guardrails_enabled": metadata['guardrails_enabled'],
        "evaluation_enabled": metadata['evaluation_enabled']
    }
    output_data["_guardrails"] = metadata['guardrails_results']
    output_data["_evaluation"] = metadata['evaluation_results']
    output_data["_warnings"] = metadata['warnings']

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Enhanced results saved to: {output_path}")


def print_enhanced_results(changes: ContractChangeOutput, metadata: Dict[str, Any]) -> None:
    """Print enhanced results with quality metrics."""
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
    print(changes.summary_of_the_change)
    print("-" * 70)

    # Print quality metrics
    if 'rule_based' in metadata['evaluation_results']:
        eval_result = metadata['evaluation_results']['rule_based']
        print("\nQUALITY METRICS:")
        print(f"  Overall Score: {eval_result['overall_score']:.2f}/100 (Grade: {eval_result['grade']})")
        print("  Dimension Scores:")
        for dim, score in eval_result['dimension_scores'].items():
            print(f"    {dim.capitalize()}: {score:.1f}/100")

    # Print warnings if any
    if metadata['warnings']:
        print("\nWARNINGS:")
        for warning in metadata['warnings']:
            print(f"  ⚠ {warning}")

    print("="*70)


def main():
    """Main entry point for enhanced execution."""
    parser = argparse.ArgumentParser(
        description="Enhanced Contract Comparison System with Guardrails and Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--original", type=str, required=True, help="Path to original contract")
    parser.add_argument("--amendment", type=str, required=True, help="Path to amendment contract")
    parser.add_argument("--output", type=str, default=None, help="Path to save output")
    parser.add_argument("--skip-guardrails", action="store_true", help="Skip input validation")
    parser.add_argument("--skip-evaluation", action="store_true", help="Skip output evaluation")
    parser.add_argument("--enable-llm-eval", action="store_true", help="Enable LLM-based evaluation")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Validate environment
    if not validate_environment():
        sys.exit(1)

    # Validate input files
    if not os.path.exists(args.original):
        print(f"ERROR: Original contract not found: {args.original}")
        sys.exit(1)

    if not os.path.exists(args.amendment):
        print(f"ERROR: Amendment contract not found: {args.amendment}")
        sys.exit(1)

    try:
        # Initialize clients
        openai_client, langfuse_client = initialize_clients()

        # Execute enhanced workflow
        changes, trace_id, metadata = process_contract_comparison_enhanced(
            original_image_path=args.original,
            amendment_image_path=args.amendment,
            openai_client=openai_client,
            enable_guardrails=not args.skip_guardrails,
            enable_evaluation=not args.skip_evaluation,
            enable_llm_eval=args.enable_llm_eval
        )

        if trace_id:
            logger.info(f"Langfuse Trace ID: {trace_id}")

        # Print results
        print_enhanced_results(changes, metadata)

        # Save to file if specified
        if args.output:
            save_enhanced_output(changes, metadata, args.output)
        else:
            print("\nJSON OUTPUT:")
            print("-" * 70)
            print(json.dumps(changes.model_dump(), indent=2))

        # Flush traces
        langfuse_client.flush()

        print(f"\n✓ Check Langfuse dashboard: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
        sys.exit(1)

    except Exception as e:
        print(f"\n\nERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
