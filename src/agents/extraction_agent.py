"""
Change Extraction Agent (Agent 2)

This agent receives the contextual analysis from Agent 1 and uses it to perform
targeted extraction of specific changes between the original contract and amendment.

Agent 2's Role in the Workflow:
    1. Receives Agent 1's context and section mappings
    2. Uses the context to focus on identified change areas
    3. Extracts specific modifications, additions, and deletions
    4. Categorizes changes by topics and sections
    5. Generates comprehensive change summary
    6. Returns Pydantic-validated structured output

This implements the second half of the collaborative agent pattern, where
Agent 2 builds upon Agent 1's contextual understanding to extract precise changes.
"""

import json
import os
from typing import Dict, List
from openai import OpenAI
from langfuse.decorators import observe, langfuse_context

from src.models import ParsedContract, AgentContext, ContractChangeOutput


class ExtractionAgent:
    """
    Agent 2: Extracts specific changes using Agent 1's contextual analysis.

    This agent performs targeted change extraction by leveraging the structural
    understanding and section mappings provided by Agent 1. It identifies exactly
    what changed, where it changed, and what topics are affected.

    Attributes:
        client: OpenAI-compatible client for LLM API calls via OpenRouter
        model: LLM model to use (default: from MODEL_NAME env var)
        system_prompt: Specialized prompt defining agent's role and behavior
    """

    def __init__(self, client: OpenAI, model: str = None):
        """
        Initialize the Change Extraction Agent.

        Args:
            client: OpenAI-compatible client configured for OpenRouter
            model: Model name to use for extraction (defaults to MODEL_NAME env var)
        """
        self.client = client
        self.model = model if model else os.getenv("MODEL_NAME", "openai/gpt-4o")
        self.system_prompt = self._create_system_prompt()

    def _create_system_prompt(self) -> str:
        """
        Create the specialized system prompt for Agent 2.

        This prompt defines the agent's role as the change extraction specialist
        who builds upon Agent 1's context to identify specific modifications.

        Returns:
            Formatted system prompt string
        """
        return """You are Agent 2: The Change Extraction Specialist.

You receive contextual analysis from Agent 1 (the Contextualization Agent) and use it to extract SPECIFIC changes between the original contract and its amendment. Agent 1 has already analyzed the structure and mapped sections - your job is to identify exactly what changed.

YOUR RESPONSIBILITIES:

1. PRECISE CHANGE EXTRACTION:
   - Using Agent 1's section mappings, identify exact modifications in each section
   - Extract specific text that was added, deleted, or modified
   - Capture the nature of each change (word changes, new clauses, deleted provisions)
   - Focus on the change areas identified by Agent 1

2. SECTION IDENTIFICATION:
   - List all section identifiers that contain changes
   - Use the exact section names/numbers from the documents
   - Include subsections if they contain modifications
   - Reference exhibits, schedules, or attachments that changed

3. TOPIC CATEGORIZATION:
   - Identify the business or legal topics affected by changes
   - Common topics include: Payment Terms, Confidentiality, Term/Duration,
     Termination Rights, Liability, Indemnification, Service Levels, Pricing,
     Intellectual Property, Data Protection, Warranties, etc.
   - Be specific about topics (e.g., "Payment Timeline" not just "Payments")
   - Each change may touch multiple topics

4. COMPREHENSIVE SUMMARY:
   - Write a detailed narrative describing ALL changes
   - For each change area, explain: what section, what changed, and the impact
   - Use clear language that legal teams can understand
   - Minimum 100 characters (typically 200-500 words for real contracts)
   - Structure: "This amendment introduces X changes. First, [section] modifies [topic] by [specific change]. Second..."

OUTPUT FORMAT (you must return valid JSON):
{
    "sections_changed": [
        "Section 2.1 - Payment Terms",
        "Section 4.3 - Confidentiality",
        "Exhibit A - Service Level Agreement"
    ],
    "topics_touched": [
        "Payment Timeline",
        "Confidentiality Period",
        "Service Level Commitments",
        "Penalty Clauses"
    ],
    "summary_of_the_change": "This amendment introduces three significant modifications to the original agreement. First, Section 2.1 modifies the payment terms by extending the net payment period from 30 days to 45 days and introducing a 2% early payment discount for payments received within 15 days of invoice. Second, Section 4.3 extends the confidentiality obligation period from 2 years to 5 years post-termination, affecting both parties' data protection responsibilities. Third, Exhibit A updates the Service Level Agreement to guarantee 99.9% uptime (previously 99.5%) and introduces new financial penalties of $1,000 per hour for downtime exceeding the threshold."
}

IMPORTANT GUIDELINES:
- Use Agent 1's context and mappings to guide your analysis
- Be SPECIFIC about what changed (not just "Section 2 changed")
- Extract actual changes, don't infer or assume
- If a section appears in the change areas but has no substantive change, don't include it
- Focus on legally or commercially significant changes
- Always return valid JSON matching the exact output format
- Ensure summary is detailed and comprehensive (minimum 100 characters)
- List section identifiers exactly as they appear in the documents"""

    @observe(name="agent_2_extract_changes", capture_input=False, capture_output=False)
    def extract_changes(
        self,
        original_contract: ParsedContract,
        amendment_contract: ParsedContract,
        context: AgentContext
    ) -> ContractChangeOutput:
        """
        Extract specific changes using Agent 1's contextual analysis.

        This is Agent 2's main execution method. It receives both parsed contracts
        and Agent 1's context, then performs targeted extraction of specific changes.
        This demonstrates the agent handoff mechanism in the collaborative pattern.

        The method is instrumented with Langfuse tracing to capture:
        - Input from Agent 1 (context and mappings)
        - Both contract documents
        - LLM extraction process
        - Token usage and costs
        - Final structured output

        Args:
            original_contract: Parsed original contract document
            amendment_contract: Parsed amendment contract document
            context: AgentContext from Agent 1's analysis

        Returns:
            ContractChangeOutput with validated changes, sections, and topics

        Raises:
            Exception: If extraction fails or output validation fails

        Example:
            >>> agent2 = ExtractionAgent(client)
            >>> changes = agent2.extract_changes(original, amendment, context)
            >>> print(f"Found changes in {len(changes.sections_changed)} sections")
        """
        # Update trace with metadata showing Agent 1 -> Agent 2 handoff
        langfuse_context.update_current_trace(
            metadata={
                "agent": "extraction_agent",
                "agent_number": 2,
                "receives_input_from": "agent_1_contextualization",
                "context_change_areas": len(context.identified_change_areas),
                "context_section_mappings": len(context.corresponding_sections),
                "original_text_length": len(original_contract.raw_text),
                "amendment_text_length": len(amendment_contract.raw_text)
            },
            tags=["agent_2", "change_extraction", "agent_handoff"]
        )

        # Construct user prompt with both contracts AND Agent 1's context
        # This shows the explicit handoff: Agent 2 uses Agent 1's output
        user_prompt = f"""You are receiving input from Agent 1 (Contextualization Agent). Use their analysis to extract specific changes.

AGENT 1'S CONTEXTUAL ANALYSIS:
{json.dumps({
    "document_structure": context.document_structure,
    "corresponding_sections": context.corresponding_sections,
    "identified_change_areas": context.identified_change_areas,
    "context_summary": context.context_summary
}, indent=2)}

ORIGINAL CONTRACT:
{original_contract.raw_text}

AMENDMENT CONTRACT:
{amendment_contract.raw_text}

Using Agent 1's analysis above, extract the specific changes and return them in the specified JSON format."""

        try:
            # Manually log input
            langfuse_context.update_current_observation(
                input={
                    "context_summary": context.context_summary,
                    "change_areas": context.identified_change_areas
                }
            )

            # Use environment variable for model to support both OpenAI and OpenRouter
            model_name = os.getenv("MODEL_NAME", "gpt-4o")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            # Extract response content
            response_content = response.choices[0].message.content
            if not response_content:
                raise ValueError("Empty response from Agent 2")

            # Parse JSON response
            extraction_result = json.loads(response_content)

            # Add token usage to trace
            langfuse_context.update_current_observation(
                metadata={
                    "tokens_used": {
                        "prompt": response.usage.prompt_tokens,
                        "completion": response.usage.completion_tokens,
                        "total": response.usage.total_tokens
                    },
                    "sections_changed_count": len(
                        extraction_result.get("sections_changed", [])
                    ),
                    "topics_touched_count": len(
                        extraction_result.get("topics_touched", [])
                    ),
                    "summary_length": len(
                        extraction_result.get("summary_of_the_change", "")
                    )
                }
            )

            # Validate and create ContractChangeOutput model
            # This Pydantic validation ensures output meets all requirements
            change_output = ContractChangeOutput(
                sections_changed=extraction_result["sections_changed"],
                topics_touched=extraction_result["topics_touched"],
                summary_of_the_change=extraction_result["summary_of_the_change"]
            )

            # Manually log output
            langfuse_context.update_current_observation(
                output=change_output.model_dump()
            )

            # Log successful completion
            langfuse_context.update_current_observation(
                level="DEFAULT",
                status_message="Change extraction completed successfully"
            )

            return change_output

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse LLM response as JSON: {str(e)}"
            langfuse_context.update_current_observation(
                level="ERROR",
                status_message=error_msg
            )
            raise Exception(error_msg)

        except KeyError as e:
            error_msg = f"LLM response missing required field: {str(e)}"
            langfuse_context.update_current_observation(
                level="ERROR",
                status_message=error_msg
            )
            raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Agent 2 extraction failed: {str(e)}"
            langfuse_context.update_current_observation(
                level="ERROR",
                status_message=error_msg
            )
            raise Exception(error_msg)

    def format_output(self, changes: ContractChangeOutput) -> str:
        """
        Format the change output as a human-readable report.

        Utility method for creating readable reports from the structured output.

        Args:
            changes: ContractChangeOutput object from extract_changes()

        Returns:
            Formatted string report of all changes

        Example:
            >>> report = agent.format_output(changes)
            >>> print(report)
        """
        report_parts = [
            "=" * 70,
            "CONTRACT AMENDMENT ANALYSIS REPORT",
            "=" * 70,
            "",
            f"SECTIONS CHANGED ({len(changes.sections_changed)}):",
            ""
        ]

        for i, section in enumerate(changes.sections_changed, 1):
            report_parts.append(f"  {i}. {section}")

        report_parts.extend([
            "",
            f"TOPICS AFFECTED ({len(changes.topics_touched)}):",
            ""
        ])

        for i, topic in enumerate(changes.topics_touched, 1):
            report_parts.append(f"  {i}. {topic}")

        report_parts.extend([
            "",
            "DETAILED SUMMARY OF CHANGES:",
            "-" * 70,
            changes.summary_of_the_change,
            "",
            "=" * 70
        ])

        return "\n".join(report_parts)

    def validate_against_context(
        self,
        changes: ContractChangeOutput,
        context: AgentContext
    ) -> Dict[str, bool]:
        """
        Validate that Agent 2's output aligns with Agent 1's context.

        Quality check to ensure Agent 2 properly used Agent 1's analysis.
        Checks if the extracted changes align with the identified change areas.

        Args:
            changes: Extracted changes from Agent 2
            context: Context from Agent 1

        Returns:
            Dictionary with validation results:
            - all_areas_covered: All change areas from Agent 1 were addressed
            - no_extra_sections: No sections outside Agent 1's scope
            - alignment_score: Percentage of Agent 1's areas covered

        Example:
            >>> validation = agent.validate_against_context(changes, context)
            >>> if not validation['all_areas_covered']:
            ...     print("Warning: Some change areas not addressed")
        """
        # Extract section identifiers from Agent 1's change areas
        agent1_sections = set()
        for area in context.identified_change_areas:
            # Extract section identifier (e.g., "Section 2.1" from "Section 2.1 - Payment Terms")
            if ' - ' in area:
                section_id = area.split(' - ')[0]
                agent1_sections.add(section_id)
            else:
                agent1_sections.add(area)

        # Extract section identifiers from Agent 2's output
        agent2_sections = set()
        for section in changes.sections_changed:
            if ' - ' in section:
                section_id = section.split(' - ')[0]
                agent2_sections.add(section_id)
            else:
                agent2_sections.add(section)

        # Calculate coverage
        covered_sections = agent1_sections.intersection(agent2_sections)
        coverage_ratio = (
            len(covered_sections) / len(agent1_sections)
            if agent1_sections else 0
        )

        return {
            "all_areas_covered": coverage_ratio >= 0.8,  # 80% threshold
            "no_extra_sections": agent2_sections.issubset(
                agent1_sections.union({"[NEW]"})
            ),
            "alignment_score": round(coverage_ratio * 100, 2),
            "covered_sections": list(covered_sections),
            "missed_sections": list(agent1_sections - agent2_sections),
            "extra_sections": list(agent2_sections - agent1_sections)
        }
