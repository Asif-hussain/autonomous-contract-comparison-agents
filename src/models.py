"""
Pydantic Models for Contract Comparison System

This module defines the data validation models used throughout the contract
comparison workflow. These models ensure type safety and data consistency
for the structured outputs returned by the multi-agent system.

Key Models:
    - ContractChangeOutput: Main output model containing all extracted changes
    - ParsedContract: Intermediate model for parsed contract text
    - AgentContext: Model for Agent 1's contextualization output
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ParsedContract(BaseModel):
    """
    Represents a contract document parsed from an image.

    This intermediate model stores the extracted text and metadata
    from the multimodal LLM's image parsing step.

    Attributes:
        raw_text: The complete extracted text from the contract image
        document_type: Type of document (e.g., "original", "amendment")
        sections_identified: List of section headers found in the document
    """
    raw_text: str = Field(
        ...,
        min_length=50,
        description="Complete text extracted from contract image"
    )
    document_type: str = Field(
        ...,
        description="Type of contract document: 'original' or 'amendment'"
    )
    sections_identified: List[str] = Field(
        default_factory=list,
        description="Section headers identified in the document"
    )

    @field_validator('document_type')
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        """Ensure document type is either 'original' or 'amendment'."""
        if v.lower() not in ['original', 'amendment']:
            raise ValueError("document_type must be 'original' or 'amendment'")
        return v.lower()


class AgentContext(BaseModel):
    """
    Output from Agent 1 (Contextualization Agent).

    This model captures Agent 1's analysis of both contract documents,
    identifying structure and corresponding sections for change extraction.

    Attributes:
        document_structure: Description of the contract's organizational structure
        corresponding_sections: Mapping of sections between original and amendment
        identified_change_areas: Preliminary identification of areas with changes
        context_summary: High-level summary of both documents' relationship
    """
    document_structure: str = Field(
        ...,
        min_length=100,
        description="Detailed analysis of contract document structure"
    )
    corresponding_sections: dict = Field(
        ...,
        description="Mapping between original and amendment sections"
    )
    identified_change_areas: List[str] = Field(
        ...,
        min_length=1,
        description="Areas where changes are likely present"
    )
    context_summary: str = Field(
        ...,
        min_length=50,
        description="Summary of the relationship between both documents"
    )

    @field_validator('corresponding_sections')
    @classmethod
    def validate_section_mapping(cls, v: dict) -> dict:
        """Ensure section mapping is not empty."""
        if not v:
            raise ValueError("corresponding_sections cannot be empty")
        return v


class ContractChangeOutput(BaseModel):
    """
    Final validated output from the contract comparison system.

    This is the primary deliverable model that satisfies the assignment
    requirements. It contains structured information about all changes
    detected between the original contract and its amendment.

    Attributes:
        sections_changed: List of specific section identifiers that were modified
        topics_touched: List of business/legal topics affected by the changes
        summary_of_the_change: Detailed narrative description of all changes

    Example:
        {
            "sections_changed": ["Section 3.2", "Section 5.1", "Exhibit A"],
            "topics_touched": ["Payment Terms", "Confidentiality", "Termination"],
            "summary_of_the_change": "The amendment modifies payment terms in
                Section 3.2 by extending the payment period from 30 to 45 days..."
        }
    """
    sections_changed: List[str] = Field(
        ...,
        min_length=1,
        description="List of section identifiers that were modified in the amendment"
    )
    topics_touched: List[str] = Field(
        ...,
        min_length=1,
        description="Business or legal topics affected by the changes"
    )
    summary_of_the_change: str = Field(
        ...,
        min_length=100,
        description="Detailed narrative description of all changes made"
    )

    @field_validator('sections_changed')
    @classmethod
    def validate_sections(cls, v: List[str]) -> List[str]:
        """
        Validate that section identifiers are meaningful.

        Ensures each section identifier is a non-empty string and removes
        any duplicate entries.
        """
        if not all(isinstance(s, str) and len(s.strip()) > 0 for s in v):
            raise ValueError("All section identifiers must be non-empty strings")
        # Remove duplicates while preserving order
        seen = set()
        unique_sections = []
        for section in v:
            if section not in seen:
                seen.add(section)
                unique_sections.append(section)
        return unique_sections

    @field_validator('topics_touched')
    @classmethod
    def validate_topics(cls, v: List[str]) -> List[str]:
        """
        Validate that topics are meaningful and non-empty.

        Ensures each topic is a descriptive string and removes duplicates.
        """
        if not all(isinstance(t, str) and len(t.strip()) > 0 for t in v):
            raise ValueError("All topics must be non-empty strings")
        # Remove duplicates while preserving order
        seen = set()
        unique_topics = []
        for topic in v:
            if topic not in seen:
                seen.add(topic)
                unique_topics.append(topic)
        return unique_topics

    @field_validator('summary_of_the_change')
    @classmethod
    def validate_summary(cls, v: str) -> str:
        """
        Validate that summary is comprehensive and meaningful.

        Ensures the summary is sufficiently detailed to be useful for
        legal review and downstream processing.
        """
        if len(v.strip()) < 100:
            raise ValueError(
                "Summary must be at least 100 characters to provide adequate detail"
            )
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sections_changed": [
                    "Section 2.1 - Payment Terms",
                    "Section 4.3 - Confidentiality Period",
                    "Exhibit B - Service Level Agreement"
                ],
                "topics_touched": [
                    "Payment Terms",
                    "Confidentiality",
                    "Service Levels",
                    "Termination Rights"
                ],
                "summary_of_the_change": (
                    "This amendment introduces three significant changes to the "
                    "original agreement. First, Section 2.1 modifies the payment "
                    "terms by extending the net payment period from 30 to 45 days "
                    "and adding a 2% early payment discount for payments within "
                    "15 days. Second, Section 4.3 extends the confidentiality "
                    "obligation period from 2 years to 5 years post-termination. "
                    "Third, Exhibit B updates the Service Level Agreement to "
                    "include 99.9% uptime guarantee and new penalties for downtime."
                )
            }
        }
    )


class ValidationError(BaseModel):
    """
    Model for capturing validation errors during processing.

    Used for error handling and debugging when Pydantic validation fails.

    Attributes:
        field: The field that failed validation
        error_message: Description of the validation error
        invalid_value: The value that caused the validation to fail
    """
    field: str = Field(..., description="Field name that failed validation")
    error_message: str = Field(..., description="Error message from validator")
    invalid_value: Optional[str] = Field(
        None,
        description="The value that caused validation to fail"
    )
