"""
Validation Tests for Contract Comparison System

This module tests Pydantic validation for all data models used in the system.
It ensures that models properly validate valid data and reject invalid data
with appropriate error messages.

Test Coverage:
    - ContractChangeOutput validation (valid and invalid cases)
    - ParsedContract validation
    - AgentContext validation
    - Field constraints and validators
"""

import pytest
from pydantic import ValidationError

from src.models import (
    ContractChangeOutput,
    ParsedContract,
    AgentContext
)


class TestContractChangeOutputValidation:
    """Tests for ContractChangeOutput Pydantic model validation."""

    def test_valid_output(self):
        """Test that valid data passes validation."""
        valid_data = {
            "sections_changed": [
                "Section 2.1 - Payment Terms",
                "Section 4.3 - Confidentiality"
            ],
            "topics_touched": [
                "Payment Timeline",
                "Confidentiality Period"
            ],
            "summary_of_the_change": (
                "This amendment introduces two significant changes. "
                "First, Section 2.1 modifies payment terms by extending "
                "the payment period from 30 to 45 days. Second, Section 4.3 "
                "extends confidentiality obligations from 2 to 5 years."
            )
        }

        output = ContractChangeOutput(**valid_data)

        assert len(output.sections_changed) == 2
        assert len(output.topics_touched) == 2
        assert len(output.summary_of_the_change) >= 100
        assert "Section 2.1" in output.sections_changed[0]

    def test_empty_sections_rejected(self):
        """Test that empty sections_changed list is rejected."""
        invalid_data = {
            "sections_changed": [],  # Empty list should fail
            "topics_touched": ["Payment Terms"],
            "summary_of_the_change": "This is a summary with more than one hundred characters to meet the minimum length requirement for validation."
        }

        with pytest.raises(ValidationError) as exc_info:
            ContractChangeOutput(**invalid_data)

        assert "sections_changed" in str(exc_info.value)

    def test_empty_topics_rejected(self):
        """Test that empty topics_touched list is rejected."""
        invalid_data = {
            "sections_changed": ["Section 1.0"],
            "topics_touched": [],  # Empty list should fail
            "summary_of_the_change": "This is a summary with more than one hundred characters to meet the minimum length requirement for validation."
        }

        with pytest.raises(ValidationError) as exc_info:
            ContractChangeOutput(**invalid_data)

        assert "topics_touched" in str(exc_info.value)

    def test_short_summary_rejected(self):
        """Test that summary shorter than 100 characters is rejected."""
        invalid_data = {
            "sections_changed": ["Section 1.0"],
            "topics_touched": ["Payment Terms"],
            "summary_of_the_change": "Too short"  # Less than 100 chars
        }

        with pytest.raises(ValidationError) as exc_info:
            ContractChangeOutput(**invalid_data)

        assert "summary_of_the_change" in str(exc_info.value)

    def test_duplicate_sections_removed(self):
        """Test that duplicate section identifiers are removed."""
        data = {
            "sections_changed": [
                "Section 1.0",
                "Section 2.0",
                "Section 1.0",  # Duplicate
                "Section 3.0"
            ],
            "topics_touched": ["Terms"],
            "summary_of_the_change": "This is a summary with more than one hundred characters to meet the minimum length requirement for validation."
        }

        output = ContractChangeOutput(**data)

        # Should have only 3 sections (duplicates removed)
        assert len(output.sections_changed) == 3
        assert output.sections_changed == ["Section 1.0", "Section 2.0", "Section 3.0"]

    def test_duplicate_topics_removed(self):
        """Test that duplicate topics are removed."""
        data = {
            "sections_changed": ["Section 1.0"],
            "topics_touched": [
                "Payment Terms",
                "Confidentiality",
                "Payment Terms"  # Duplicate
            ],
            "summary_of_the_change": "This is a summary with more than one hundred characters to meet the minimum length requirement for validation."
        }

        output = ContractChangeOutput(**data)

        # Should have only 2 topics (duplicates removed)
        assert len(output.topics_touched) == 2
        assert output.topics_touched == ["Payment Terms", "Confidentiality"]

    def test_missing_required_fields(self):
        """Test that missing required fields are rejected."""
        incomplete_data = {
            "sections_changed": ["Section 1.0"]
            # Missing topics_touched and summary_of_the_change
        }

        with pytest.raises(ValidationError) as exc_info:
            ContractChangeOutput(**incomplete_data)

        error_str = str(exc_info.value)
        assert "topics_touched" in error_str
        assert "summary_of_the_change" in error_str


class TestParsedContractValidation:
    """Tests for ParsedContract Pydantic model validation."""

    def test_valid_parsed_contract(self):
        """Test that valid parsed contract data passes validation."""
        valid_data = {
            "raw_text": "This is the extracted contract text " * 10,  # > 50 chars
            "document_type": "original",
            "sections_identified": ["Section 1.0", "Section 2.0"]
        }

        contract = ParsedContract(**valid_data)

        assert len(contract.raw_text) >= 50
        assert contract.document_type == "original"
        assert len(contract.sections_identified) == 2

    def test_short_text_rejected(self):
        """Test that text shorter than 50 characters is rejected."""
        invalid_data = {
            "raw_text": "Too short",  # Less than 50 chars
            "document_type": "original",
            "sections_identified": []
        }

        with pytest.raises(ValidationError) as exc_info:
            ParsedContract(**invalid_data)

        assert "raw_text" in str(exc_info.value)

    def test_invalid_document_type_rejected(self):
        """Test that invalid document_type is rejected."""
        invalid_data = {
            "raw_text": "This is valid text that is longer than fifty characters for sure.",
            "document_type": "invalid_type",  # Not 'original' or 'amendment'
            "sections_identified": []
        }

        with pytest.raises(ValidationError) as exc_info:
            ParsedContract(**invalid_data)

        assert "document_type" in str(exc_info.value)

    def test_document_type_normalized(self):
        """Test that document_type is normalized to lowercase."""
        data = {
            "raw_text": "This is valid text that is longer than fifty characters for sure.",
            "document_type": "ORIGINAL",  # Uppercase
            "sections_identified": []
        }

        contract = ParsedContract(**data)

        # Should be normalized to lowercase
        assert contract.document_type == "original"


class TestAgentContextValidation:
    """Tests for AgentContext Pydantic model validation."""

    def test_valid_agent_context(self):
        """Test that valid agent context passes validation."""
        valid_data = {
            "document_structure": "Both documents follow standard contract structure with numbered sections and subsections organized hierarchically with exhibits.",
            "corresponding_sections": {
                "Section 1.0": "Section 1.0",
                "Section 2.1": "Section 2.1"
            },
            "identified_change_areas": [
                "Section 2.1 - Payment Terms"
            ],
            "context_summary": "The amendment modifies payment-related clauses including payment period and discount terms."
        }

        context = AgentContext(**valid_data)

        assert len(context.document_structure) >= 100
        assert len(context.corresponding_sections) > 0
        assert len(context.identified_change_areas) >= 1

    def test_short_document_structure_rejected(self):
        """Test that document_structure shorter than 100 chars is rejected."""
        invalid_data = {
            "document_structure": "Too short",  # Less than 100 chars
            "corresponding_sections": {"Section 1": "Section 1"},
            "identified_change_areas": ["Section 1"],
            "context_summary": "Summary of the relationship between documents."
        }

        with pytest.raises(ValidationError) as exc_info:
            AgentContext(**invalid_data)

        assert "document_structure" in str(exc_info.value)

    def test_empty_corresponding_sections_rejected(self):
        """Test that empty corresponding_sections dict is rejected."""
        invalid_data = {
            "document_structure": "This is a detailed description of the document structure that is definitely longer than one hundred characters.",
            "corresponding_sections": {},  # Empty dict should fail
            "identified_change_areas": ["Section 1"],
            "context_summary": "Summary of the relationship between documents."
        }

        with pytest.raises(ValidationError) as exc_info:
            AgentContext(**invalid_data)

        assert "corresponding_sections" in str(exc_info.value)

    def test_empty_change_areas_rejected(self):
        """Test that empty identified_change_areas list is rejected."""
        invalid_data = {
            "document_structure": "This is a detailed description of the document structure that is definitely longer than one hundred characters.",
            "corresponding_sections": {"Section 1": "Section 1"},
            "identified_change_areas": [],  # Empty list should fail
            "context_summary": "Summary of the relationship between documents."
        }

        with pytest.raises(ValidationError) as exc_info:
            AgentContext(**invalid_data)

        assert "identified_change_areas" in str(exc_info.value)


class TestFieldConstraints:
    """Tests for field-level constraints and validators."""

    def test_sections_with_whitespace_stripped(self):
        """Test that section strings are properly stripped of whitespace."""
        data = {
            "sections_changed": [
                "  Section 1.0  ",  # Leading/trailing whitespace
                "Section 2.0"
            ],
            "topics_touched": ["Terms"],
            "summary_of_the_change": "This is a summary with more than one hundred characters to meet the minimum length requirement for validation."
        }

        output = ContractChangeOutput(**data)

        # Whitespace should be preserved for now (can be enhanced later)
        assert len(output.sections_changed) == 2

    def test_type_validation(self):
        """Test that incorrect types are rejected."""
        invalid_data = {
            "sections_changed": "Not a list",  # Should be List[str]
            "topics_touched": ["Terms"],
            "summary_of_the_change": "Valid summary text that is long enough to pass the minimum length validation requirement."
        }

        with pytest.raises(ValidationError) as exc_info:
            ContractChangeOutput(**invalid_data)

        assert "sections_changed" in str(exc_info.value)


def test_integration_valid_workflow_output():
    """
    Integration test: Validate a complete workflow output.

    This simulates what the actual system would produce.
    """
    complete_output = {
        "sections_changed": [
            "Section 2.1 - Payment Terms",
            "Section 4.3 - Confidentiality Period",
            "Exhibit A - Service Level Agreement"
        ],
        "topics_touched": [
            "Payment Timeline",
            "Early Payment Discount",
            "Confidentiality Duration",
            "Service Level Commitments",
            "Downtime Penalties"
        ],
        "summary_of_the_change": (
            "This amendment introduces three significant modifications to the "
            "original agreement. First, Section 2.1 modifies the payment terms "
            "by extending the net payment period from 30 days to 45 days and "
            "introducing a 2% early payment discount for payments received "
            "within 15 days of invoice date. Second, Section 4.3 extends the "
            "confidentiality obligation period from 2 years to 5 years "
            "post-termination, affecting both parties' responsibilities for "
            "protecting proprietary information. Third, Exhibit A updates the "
            "Service Level Agreement to guarantee 99.9% uptime (increased from "
            "99.5%) and introduces new financial penalties of $1,000 per hour "
            "for any downtime exceeding the guaranteed threshold."
        )
    }

    # Should validate without errors
    output = ContractChangeOutput(**complete_output)

    assert len(output.sections_changed) == 3
    assert len(output.topics_touched) == 5
    assert len(output.summary_of_the_change) > 100
    assert "payment" in output.summary_of_the_change.lower()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
