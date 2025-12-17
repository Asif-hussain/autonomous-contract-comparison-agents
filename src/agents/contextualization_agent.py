"""
Contextualization Agent (Agent 1)

This agent is responsible for analyzing both the original contract and its amendment
to understand the overall document structure, identify corresponding sections,
and provide contextual analysis that guides the change extraction process.

Agent 1's Role in the Workflow:
    1. Receives parsed text from both contract documents
    2. Analyzes document structure and organization
    3. Maps corresponding sections between original and amendment
    4. Identifies areas where changes are likely present
    5. Provides contextual summary for Agent 2

The output from this agent serves as critical input for Agent 2's targeted
change extraction, implementing the collaborative multi-agent pattern.
"""

import json
import os
from typing import Dict, List
from openai import OpenAI
from langfuse.decorators import observe, langfuse_context

from src.models import ParsedContract, AgentContext


class ContextualizationAgent:
    """
    Agent 1: Contextualizes both contract documents and identifies structure.

    This agent performs deep analysis of the original contract and amendment
    to understand their relationship, structure, and areas of modification.
    It mimics how a legal analyst would first understand both documents
    before identifying specific changes.

    Attributes:
        client: OpenAI-compatible client for LLM API calls via OpenRouter
        model: LLM model to use (default: from MODEL_NAME env var)
        system_prompt: Specialized prompt defining agent's role and behavior
    """

    def __init__(self, client: OpenAI, model: str = None):
        """
        Initialize the Contextualization Agent.

        Args:
            client: OpenAI-compatible client configured for OpenRouter
            model: Model name to use for analysis (defaults to MODEL_NAME env var)
        """
        self.client = client
        self.model = model if model else os.getenv("MODEL_NAME", "openai/gpt-4o")
        self.system_prompt = self._create_system_prompt()

    def _create_system_prompt(self) -> str:
        """
        Create the specialized system prompt for Agent 1.

        This prompt defines the agent's role, responsibilities, and output format.
        It emphasizes structural analysis and section correspondence mapping.

        Returns:
            Formatted system prompt string
        """
        return """You are Agent 1: The Contract Contextualization Specialist.

Your role is to analyze BOTH the original contract and its amendment to understand their structure, organization, and relationship. You are NOT extracting specific changes yet - that is Agent 2's job. Your task is to provide context and mapping that enables Agent 2 to accurately extract changes.

YOUR RESPONSIBILITIES:

1. DOCUMENT STRUCTURE ANALYSIS:
   - Identify the organizational structure of both documents (sections, articles, clauses)
   - Recognize the hierarchy and numbering systems used
   - Note the overall length and complexity of each document
   - Identify key structural elements (definitions, exhibits, schedules)

2. SECTION CORRESPONDENCE MAPPING:
   - Map which sections in the original correspond to which sections in the amendment
   - Identify sections that exist in one document but not the other (additions/deletions)
   - Note sections that appear to be renumbered or reorganized
   - Create a clear mapping structure that Agent 2 can use

3. PRELIMINARY CHANGE IDENTIFICATION:
   - Identify AREAS where changes are likely present (without extracting specifics)
   - Note sections that appear modified based on length or structure differences
   - Flag sections that are completely new or removed
   - Prioritize areas for Agent 2's detailed analysis

4. CONTEXTUAL SUMMARY:
   - Provide a high-level summary of the relationship between documents
   - Describe the type of amendment (minor modifications, major restructuring, etc.)
   - Note any patterns in changes (e.g., all financial terms, all dates, etc.)
   - Give Agent 2 context about what to expect

OUTPUT FORMAT (you must return valid JSON):
{
    "document_structure": "Detailed description of how both documents are organized...",
    "corresponding_sections": {
        "Section 1.0 (Original)": "Section 1.0 (Amendment)",
        "Section 2.1 (Original)": "Section 2.1 (Amendment)",
        "Section 3.0 (Original)": "[DELETED]",
        "[NEW]": "Section 4.0 (Amendment)"
    },
    "identified_change_areas": [
        "Section 2.1 - Payment Terms",
        "Section 5.3 - Confidentiality Period",
        "Exhibit A - Service Levels"
    ],
    "context_summary": "This amendment appears to be a moderate modification focusing primarily on..."
}

IMPORTANT GUIDELINES:
- Be thorough in your structural analysis
- Create clear, unambiguous section mappings
- Focus on CONTEXT and STRUCTURE, not specific word-by-word changes
- Your output will be directly consumed by Agent 2, so be precise
- If you're unsure about a mapping, note it explicitly
- Always return valid JSON that matches the output format exactly"""

    @observe(name="agent_1_contextualize", capture_input=False, capture_output=False)
    def analyze(
        self,
        original_contract: ParsedContract,
        amendment_contract: ParsedContract
    ) -> AgentContext:
        """
        Analyze both contracts to provide structural context and section mapping.

        This is Agent 1's main execution method. It takes both parsed contracts,
        analyzes their structure and relationship, and returns contextual
        information that Agent 2 will use for change extraction.

        The method is instrumented with Langfuse tracing to capture:
        - Input documents and their metadata
        - LLM analysis process
        - Token usage and costs
        - Output context structure

        Args:
            original_contract: Parsed original contract document
            amendment_contract: Parsed amendment contract document

        Returns:
            AgentContext object containing structural analysis and mappings

        Raises:
            Exception: If analysis fails or LLM returns invalid format

        Example:
            >>> agent = ContextualizationAgent(client)
            >>> context = agent.analyze(original_parsed, amendment_parsed)
            >>> print(f"Found {len(context.identified_change_areas)} change areas")
        """
        # Update trace with metadata
        langfuse_context.update_current_trace(
            metadata={
                "agent": "contextualization_agent",
                "agent_number": 1,
                "original_text_length": len(original_contract.raw_text),
                "amendment_text_length": len(amendment_contract.raw_text),
                "original_sections": len(original_contract.sections_identified),
                "amendment_sections": len(amendment_contract.sections_identified)
            },
            tags=["agent_1", "contextualization"]
        )

        # Construct the user prompt with both contract texts
        user_prompt = f"""Analyze these two contract documents:

ORIGINAL CONTRACT:
{original_contract.raw_text}

AMENDMENT CONTRACT:
{amendment_contract.raw_text}

Provide your structural analysis and section mapping in the specified JSON format."""

        try:
            # Manually log input to avoid serialization crash
            langfuse_context.update_current_observation(
                input={
                    "original_sections": original_contract.sections_identified,
                    "amendment_sections": amendment_contract.sections_identified
                }
            )

            # Call LLM for analysis
            # Using json_object response format to ensure valid JSON output
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
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from Agent 1")
            
            data = json.loads(content)
            context = AgentContext(**data)
            
            # Manually log output
            langfuse_context.update_current_observation(
                output=context.model_dump()
            )

            # Add token usage to trace
            langfuse_context.update_current_observation(
                metadata={
                    "tokens_used": {
                        "prompt": response.usage.prompt_tokens,
                        "completion": response.usage.completion_tokens,
                        "total": response.usage.total_tokens
                    },
                    "change_areas_identified": len(context.identified_change_areas),
                    "section_mappings": len(context.corresponding_sections)
                }
            )

            # Log successful completion
            langfuse_context.update_current_observation(
                level="DEFAULT",
                status_message="Contextualization completed successfully"
            )

            return context

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
            error_msg = f"Agent 1 analysis failed: {str(e)}"
            langfuse_context.update_current_observation(
                level="ERROR",
                status_message=error_msg
            )
            raise Exception(error_msg)

    def get_section_summary(self, context: AgentContext) -> str:
        """
        Generate a human-readable summary of the contextualization results.

        Utility method for debugging and logging Agent 1's analysis.

        Args:
            context: AgentContext object from analyze() method

        Returns:
            Formatted string summarizing the context analysis

        Example:
            >>> summary = agent.get_section_summary(context)
            >>> print(summary)
        """
        summary_parts = [
            "=" * 60,
            "AGENT 1: CONTEXTUALIZATION RESULTS",
            "=" * 60,
            "",
            "CONTEXT SUMMARY:",
            context.context_summary,
            "",
            f"IDENTIFIED CHANGE AREAS ({len(context.identified_change_areas)}):",
        ]

        for area in context.identified_change_areas:
            summary_parts.append(f"  - {area}")

        summary_parts.extend([
            "",
            f"SECTION MAPPINGS ({len(context.corresponding_sections)}):",
        ])

        for original, amendment in context.corresponding_sections.items():
            summary_parts.append(f"  {original} -> {amendment}")

        summary_parts.append("=" * 60)

        return "\n".join(summary_parts)
