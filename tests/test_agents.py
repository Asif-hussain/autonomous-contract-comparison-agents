"""
Agent Tests for Contract Comparison System

This module tests the multi-agent collaboration pattern, including agent handoff
mechanisms and integration between Agent 1 and Agent 2.

Test Coverage:
    - Agent 1 context generation
    - Agent 2 receiving Agent 1's output
    - Agent handoff mechanism verification
    - End-to-end agent collaboration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.models import ParsedContract, AgentContext, ContractChangeOutput
from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client for testing."""
    return Mock()


@pytest.fixture
def sample_original_contract():
    """Create a sample parsed original contract for testing."""
    return ParsedContract(
        raw_text="""
SERVICE AGREEMENT

This Service Agreement ("Agreement") is entered into as of January 1, 2024.

SECTION 1.0 - DEFINITIONS
1.1 "Services" means the professional services described in Exhibit A.
1.2 "Term" means the period specified in Section 3.0.

SECTION 2.0 - PAYMENT TERMS
2.1 Payment Schedule: Client shall pay Vendor within 30 days of invoice.
2.2 Payment Method: All payments shall be made via wire transfer.

SECTION 3.0 - TERM AND TERMINATION
3.1 Initial Term: This Agreement shall commence on the Effective Date and
    continue for a period of 12 months.
3.2 Renewal: This Agreement may be renewed for successive 12-month periods.

SECTION 4.0 - CONFIDENTIALITY
4.1 Confidential Information: Both parties shall maintain confidentiality.
4.2 Duration: Confidentiality obligations shall survive for 2 years after
    termination.

EXHIBIT A - SERVICE DESCRIPTION
Professional consulting services shall be provided on a time and materials basis.
        """,
        document_type="original",
        sections_identified=[
            "SECTION 1.0 - DEFINITIONS",
            "SECTION 2.0 - PAYMENT TERMS",
            "SECTION 3.0 - TERM AND TERMINATION",
            "SECTION 4.0 - CONFIDENTIALITY",
            "EXHIBIT A - SERVICE DESCRIPTION"
        ]
    )


@pytest.fixture
def sample_amendment_contract():
    """Create a sample parsed amendment contract for testing."""
    return ParsedContract(
        raw_text="""
AMENDMENT TO SERVICE AGREEMENT

This Amendment is entered into as of June 1, 2024.

SECTION 1.0 - DEFINITIONS
(No changes)

SECTION 2.0 - PAYMENT TERMS
2.1 Payment Schedule: Client shall pay Vendor within 45 days of invoice.
    Early payment discount: 2% discount for payments within 15 days.
2.2 Payment Method: All payments shall be made via wire transfer.

SECTION 3.0 - TERM AND TERMINATION
(No changes)

SECTION 4.0 - CONFIDENTIALITY
4.1 Confidential Information: Both parties shall maintain confidentiality.
4.2 Duration: Confidentiality obligations shall survive for 5 years after
    termination.

EXHIBIT A - SERVICE DESCRIPTION
Professional consulting services shall be provided on a time and materials basis.
Service Level: 99.9% uptime guarantee.
        """,
        document_type="amendment",
        sections_identified=[
            "SECTION 1.0 - DEFINITIONS",
            "SECTION 2.0 - PAYMENT TERMS",
            "SECTION 3.0 - TERM AND TERMINATION",
            "SECTION 4.0 - CONFIDENTIALITY",
            "EXHIBIT A - SERVICE DESCRIPTION"
        ]
    )


@pytest.fixture
def sample_agent1_context():
    """Create a sample Agent 1 context output for testing."""
    return AgentContext(
        document_structure=(
            "Both documents follow a standard contract structure with numbered "
            "sections (1.0-4.0) and an exhibit. The amendment maintains the same "
            "structural organization as the original, with modifications to "
            "specific clauses within existing sections."
        ),
        corresponding_sections={
            "SECTION 1.0 - DEFINITIONS": "SECTION 1.0 - DEFINITIONS",
            "SECTION 2.0 - PAYMENT TERMS": "SECTION 2.0 - PAYMENT TERMS",
            "SECTION 3.0 - TERM AND TERMINATION": "SECTION 3.0 - TERM AND TERMINATION",
            "SECTION 4.0 - CONFIDENTIALITY": "SECTION 4.0 - CONFIDENTIALITY",
            "EXHIBIT A - SERVICE DESCRIPTION": "EXHIBIT A - SERVICE DESCRIPTION"
        },
        identified_change_areas=[
            "SECTION 2.0 - PAYMENT TERMS",
            "SECTION 4.0 - CONFIDENTIALITY",
            "EXHIBIT A - SERVICE DESCRIPTION"
        ],
        context_summary=(
            "This amendment modifies payment terms, confidentiality duration, "
            "and service level guarantees while maintaining the overall contract "
            "structure."
        )
    )


class TestContextualizationAgent:
    """Tests for Agent 1 (Contextualization Agent)."""

    @patch('src.agents.contextualization_agent.OpenAI')
    def test_agent1_produces_valid_context(
        self,
        mock_openai_class,
        sample_original_contract,
        sample_amendment_contract
    ):
        """Test that Agent 1 produces valid AgentContext output."""
        # Mock the API response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "document_structure": "Both contracts have standard structure with sections 1.0 through 4.0 and an exhibit. The amendment preserves the organizational hierarchy.",
            "corresponding_sections": {
                "SECTION 2.0": "SECTION 2.0",
                "SECTION 4.0": "SECTION 4.0"
            },
            "identified_change_areas": [
                "SECTION 2.0 - PAYMENT TERMS"
            ],
            "context_summary": "The amendment modifies payment terms and confidentiality period."
        })
        mock_response.usage.prompt_tokens = 1000
        mock_response.usage.completion_tokens = 200
        mock_response.usage.total_tokens = 1200
        mock_client.chat.completions.create.return_value = mock_response

        # Create agent and run analysis
        agent = ContextualizationAgent(client=mock_client)
        context = agent.analyze(sample_original_contract, sample_amendment_contract)

        # Verify output is valid AgentContext
        assert isinstance(context, AgentContext)
        assert len(context.document_structure) >= 100
        assert len(context.corresponding_sections) > 0
        assert len(context.identified_change_areas) >= 1
        assert len(context.context_summary) >= 50

    def test_agent1_context_structure(self, sample_agent1_context):
        """Test that Agent 1's context has all required fields."""
        # Verify all required fields are present
        assert hasattr(sample_agent1_context, 'document_structure')
        assert hasattr(sample_agent1_context, 'corresponding_sections')
        assert hasattr(sample_agent1_context, 'identified_change_areas')
        assert hasattr(sample_agent1_context, 'context_summary')

        # Verify types
        assert isinstance(sample_agent1_context.document_structure, str)
        assert isinstance(sample_agent1_context.corresponding_sections, dict)
        assert isinstance(sample_agent1_context.identified_change_areas, list)
        assert isinstance(sample_agent1_context.context_summary, str)


class TestExtractionAgent:
    """Tests for Agent 2 (Change Extraction Agent)."""

    @patch('src.agents.extraction_agent.OpenAI')
    def test_agent2_receives_agent1_output(
        self,
        mock_openai_class,
        sample_original_contract,
        sample_amendment_contract,
        sample_agent1_context
    ):
        """
        Test that Agent 2 receives and uses Agent 1's output.

        This is the critical agent handoff test.
        """
        # Mock the API response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "sections_changed": [
                "SECTION 2.0 - PAYMENT TERMS",
                "SECTION 4.0 - CONFIDENTIALITY"
            ],
            "topics_touched": [
                "Payment Timeline",
                "Confidentiality Period"
            ],
            "summary_of_the_change": (
                "This amendment introduces two main changes. First, Section 2.0 "
                "extends the payment period from 30 to 45 days and adds a 2% "
                "early payment discount. Second, Section 4.0 extends confidentiality "
                "obligations from 2 years to 5 years post-termination."
            )
        })
        mock_response.usage.prompt_tokens = 1500
        mock_response.usage.completion_tokens = 300
        mock_response.usage.total_tokens = 1800
        mock_client.chat.completions.create.return_value = mock_response

        # Create agent and extract changes
        agent2 = ExtractionAgent(client=mock_client)
        changes = agent2.extract_changes(
            original_contract=sample_original_contract,
            amendment_contract=sample_amendment_contract,
            context=sample_agent1_context  # Agent 1's output passed to Agent 2
        )

        # Verify that Agent 2 was called with API
        assert mock_client.chat.completions.create.called

        # Get the actual prompt sent to the LLM
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        user_message = messages[1]['content']

        # CRITICAL TEST: Verify that Agent 1's context was included in the prompt
        assert "AGENT 1'S CONTEXTUAL ANALYSIS" in user_message
        assert sample_agent1_context.context_summary in user_message
        assert "identified_change_areas" in user_message

        # Verify output is valid ContractChangeOutput
        assert isinstance(changes, ContractChangeOutput)
        assert len(changes.sections_changed) >= 1
        assert len(changes.topics_touched) >= 1
        assert len(changes.summary_of_the_change) >= 100

    def test_agent2_output_structure(self):
        """Test that Agent 2's output has correct structure."""
        # Create a sample output
        changes = ContractChangeOutput(
            sections_changed=["SECTION 2.0 - PAYMENT TERMS"],
            topics_touched=["Payment Timeline"],
            summary_of_the_change=(
                "The amendment modifies Section 2.0 to extend payment terms "
                "from 30 days to 45 days and introduces a 2% early payment "
                "discount for invoices paid within 15 days."
            )
        )

        # Verify structure
        assert hasattr(changes, 'sections_changed')
        assert hasattr(changes, 'topics_touched')
        assert hasattr(changes, 'summary_of_the_change')


class TestAgentHandoffMechanism:
    """Tests for the agent handoff mechanism (Agent 1 -> Agent 2)."""

    @patch('src.agents.extraction_agent.OpenAI')
    @patch('src.agents.contextualization_agent.OpenAI')
    def test_complete_agent_handoff_flow(
        self,
        mock_contextualization_openai,
        mock_extraction_openai,
        sample_original_contract,
        sample_amendment_contract
    ):
        """
        End-to-end test: Verify Agent 1 output is correctly passed to Agent 2.

        This test simulates the complete workflow:
        1. Agent 1 analyzes both contracts
        2. Agent 1 produces context
        3. Agent 2 receives Agent 1's context
        4. Agent 2 extracts changes using that context
        """
        # Mock Agent 1's response
        mock_client1 = MagicMock()
        agent1_response = {
            "document_structure": "Standard contract structure with sections 1.0-4.0 and exhibit. Amendment preserves the original organizational hierarchy and maintains all section numbering conventions.",
            "corresponding_sections": {
                "SECTION 2.0": "SECTION 2.0",
                "SECTION 4.0": "SECTION 4.0"
            },
            "identified_change_areas": [
                "SECTION 2.0 - PAYMENT TERMS",
                "SECTION 4.0 - CONFIDENTIALITY"
            ],
            "context_summary": "Amendment modifies payment terms by extending payment period and confidentiality duration obligations."
        }
        mock_response1 = MagicMock()
        mock_response1.choices[0].message.content = json.dumps(agent1_response)
        mock_response1.usage.prompt_tokens = 1000
        mock_response1.usage.completion_tokens = 200
        mock_response1.usage.total_tokens = 1200
        mock_client1.chat.completions.create.return_value = mock_response1

        # Step 1: Execute Agent 1
        agent1 = ContextualizationAgent(client=mock_client1)
        context = agent1.analyze(sample_original_contract, sample_amendment_contract)

        # Verify Agent 1 produced valid context
        assert isinstance(context, AgentContext)
        assert "SECTION 2.0 - PAYMENT TERMS" in context.identified_change_areas

        # Mock Agent 2's response
        mock_client2 = MagicMock()
        agent2_response = {
            "sections_changed": [
                "SECTION 2.0 - PAYMENT TERMS",
                "SECTION 4.0 - CONFIDENTIALITY"
            ],
            "topics_touched": [
                "Payment Timeline",
                "Confidentiality Period"
            ],
            "summary_of_the_change": (
                "The amendment extends payment terms from 30 to 45 days with "
                "a 2% early payment discount, and extends confidentiality "
                "obligations from 2 to 5 years post-termination."
            )
        }
        mock_response2 = MagicMock()
        mock_response2.choices[0].message.content = json.dumps(agent2_response)
        mock_response2.usage.prompt_tokens = 1500
        mock_response2.usage.completion_tokens = 300
        mock_response2.usage.total_tokens = 1800
        mock_client2.chat.completions.create.return_value = mock_response2

        # Step 2: Execute Agent 2 with Agent 1's context
        agent2 = ExtractionAgent(client=mock_client2)
        changes = agent2.extract_changes(
            original_contract=sample_original_contract,
            amendment_contract=sample_amendment_contract,
            context=context  # HANDOFF: Agent 1's output -> Agent 2's input
        )

        # Verify Agent 2 received Agent 1's context
        call_args = mock_client2.chat.completions.create.call_args
        user_prompt = call_args.kwargs['messages'][1]['content']

        # CRITICAL ASSERTION: Agent 1's context is in Agent 2's prompt
        assert context.context_summary in user_prompt
        assert "AGENT 1'S CONTEXTUAL ANALYSIS" in user_prompt

        # Verify Agent 2 produced valid output
        assert isinstance(changes, ContractChangeOutput)
        assert len(changes.sections_changed) >= 1

    def test_agent2_uses_agent1_change_areas(self):
        """Test that Agent 2 focuses on Agent 1's identified change areas."""
        # Create context with specific change areas
        context = AgentContext(
            document_structure="Standard structure with numbered sections and subsections following hierarchical organization with exhibits.",
            corresponding_sections={"Section 2": "Section 2"},
            identified_change_areas=[
                "SECTION 2.0 - PAYMENT TERMS",
                "SECTION 4.0 - CONFIDENTIALITY"
            ],
            context_summary="Amendment focuses on payment terms extension and confidentiality period modifications."
        )

        # Create changes that align with Agent 1's identified areas
        changes = ContractChangeOutput(
            sections_changed=[
                "SECTION 2.0 - PAYMENT TERMS",
                "SECTION 4.0 - CONFIDENTIALITY"
            ],
            topics_touched=["Payment", "Confidentiality"],
            summary_of_the_change=(
                "The amendment modifies payment terms and confidentiality "
                "obligations as identified in the change areas analysis."
            )
        )

        # Verify alignment
        for section in changes.sections_changed:
            # Each changed section should correspond to an identified change area
            assert any(area in section for area in context.identified_change_areas)


class TestAgentCollaboration:
    """Tests for agent collaboration quality."""

    def test_validation_alignment(self):
        """Test the validation alignment helper method."""
        context = AgentContext(
            document_structure="Standard contract structure with hierarchical sections and subsections organized into multiple parts with exhibits.",
            corresponding_sections={"Section 2": "Section 2"},
            identified_change_areas=[
                "Section 2.1 - Payment Terms",
                "Section 4.3 - Confidentiality"
            ],
            context_summary="Payment and confidentiality changes including extended payment period and confidentiality duration."
        )

        changes = ContractChangeOutput(
            sections_changed=[
                "Section 2.1 - Payment Terms",
                "Section 4.3 - Confidentiality"
            ],
            topics_touched=["Payment", "Confidentiality"],
            summary_of_the_change=(
                "Amendment modifies payment timeline by extending payment period from 30 to 45 days and confidentiality duration from 2 to 5 years."
            )
        )

        # Create extraction agent to test validation method
        mock_client = MagicMock()
        agent = ExtractionAgent(client=mock_client)

        # Test validation alignment
        validation = agent.validate_against_context(changes, context)

        assert validation['all_areas_covered'] is True
        assert validation['alignment_score'] == 100.0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
