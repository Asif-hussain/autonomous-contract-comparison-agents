"""
Guardrails Module for Contract Comparison System

This module implements input validation and safety checks to ensure:
1. Input quality and completeness
2. File integrity and format validation
3. Content safety and appropriateness
4. Resource usage limits
5. Data privacy protection

Guardrails are applied BEFORE processing to prevent:
- Malformed inputs reaching the LLM
- Excessive API costs from invalid data
- Processing of inappropriate content
- Privacy violations
"""

import os
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from pydantic import ValidationError
from PIL import Image

from src.models import ParsedContract


class ContractGuardrails:
    """
    Implements comprehensive guardrails for contract comparison system.

    Validates inputs across multiple dimensions:
    - File format and integrity
    - Content quality and completeness
    - Size and resource constraints
    - Privacy and sensitive data detection
    """

    def __init__(
        self,
        min_text_length: int = 50,
        max_text_length: int = 50000,
        max_file_size_mb: float = 10.0,
        allowed_extensions: List[str] = None
    ):
        """
        Initialize guardrails with configurable constraints.

        Args:
            min_text_length: Minimum acceptable text length
            max_text_length: Maximum acceptable text length
            max_file_size_mb: Maximum file size in megabytes
            allowed_extensions: List of allowed file extensions
        """
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length
        self.max_file_size_mb = max_file_size_mb
        self.allowed_extensions = allowed_extensions or ['.jpg', '.jpeg', '.png', '.pdf']

        # Patterns for sensitive data detection
        self.sensitive_patterns = {
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b(\+\d{1,2}\s?)?(\()?\d{3}(\))?[\s.-]?\d{3}[\s.-]?\d{4}\b')
        }

    def validate_input(
        self,
        contract: ParsedContract,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a parsed contract input.

        Args:
            contract: ParsedContract object to validate
            file_path: Optional path to original file

        Returns:
            Dictionary with validation results:
            {
                'is_valid': bool,
                'checks_passed': int,
                'total_checks': int,
                'warnings': List[str],
                'errors': List[str],
                'details': Dict[str, Any]
            }
        """
        results = {
            'is_valid': True,
            'checks_passed': 0,
            'total_checks': 0,
            'warnings': [],
            'errors': [],
            'details': {}
        }

        # Run all validation checks
        self._check_text_length(contract, results)
        self._check_text_quality(contract, results)
        self._check_sections(contract, results)
        self._check_pydantic_model(contract, results)

        if file_path:
            self._check_file_integrity(file_path, results)
            self._check_file_size(file_path, results)

        # Check for sensitive data (warning only)
        self._check_sensitive_data(contract, results)

        # Final validation status
        results['is_valid'] = len(results['errors']) == 0

        return results

    def _check_text_length(
        self,
        contract: ParsedContract,
        results: Dict[str, Any]
    ) -> None:
        """Validate text length constraints."""
        results['total_checks'] += 1

        text_length = len(contract.raw_text)
        results['details']['text_length'] = text_length

        if text_length < self.min_text_length:
            results['errors'].append(
                f"Text too short ({text_length} chars, minimum {self.min_text_length})"
            )
        elif text_length > self.max_text_length:
            results['errors'].append(
                f"Text too long ({text_length} chars, maximum {self.max_text_length})"
            )
        else:
            results['checks_passed'] += 1

    def _check_text_quality(
        self,
        contract: ParsedContract,
        results: Dict[str, Any]
    ) -> None:
        """Check text quality indicators."""
        results['total_checks'] += 1

        text = contract.raw_text

        # Check for minimum word count
        words = text.split()
        word_count = len(words)
        results['details']['word_count'] = word_count

        if word_count < 20:
            results['errors'].append(
                f"Too few words ({word_count}, expected at least 20)"
            )
            return

        # Check average word length (detect gibberish)
        avg_word_length = sum(len(w) for w in words) / len(words)
        results['details']['avg_word_length'] = avg_word_length

        if avg_word_length < 2 or avg_word_length > 20:
            results['warnings'].append(
                f"Unusual average word length ({avg_word_length:.1f}), possible OCR errors"
            )

        # Check for reasonable character distribution
        alpha_chars = sum(c.isalpha() for c in text)
        alpha_ratio = alpha_chars / len(text) if text else 0
        results['details']['alpha_ratio'] = alpha_ratio

        if alpha_ratio < 0.5:
            results['warnings'].append(
                f"Low alphabetic character ratio ({alpha_ratio:.2%}), possible parsing issues"
            )

        results['checks_passed'] += 1

    def _check_sections(
        self,
        contract: ParsedContract,
        results: Dict[str, Any]
    ) -> None:
        """Validate section identification."""
        results['total_checks'] += 1

        sections = contract.sections_identified
        results['details']['sections_count'] = len(sections)

        if len(sections) == 0:
            results['warnings'].append(
                "No sections identified - contract structure may be unclear"
            )

        # Check for duplicate sections
        if len(sections) != len(set(sections)):
            results['warnings'].append(
                "Duplicate sections detected"
            )

        results['checks_passed'] += 1

    def _check_pydantic_model(
        self,
        contract: ParsedContract,
        results: Dict[str, Any]
    ) -> None:
        """Validate Pydantic model integrity."""
        results['total_checks'] += 1

        try:
            # Attempt to re-validate the model
            contract.model_validate(contract.model_dump())
            results['checks_passed'] += 1
        except ValidationError as e:
            results['errors'].append(
                f"Pydantic validation failed: {str(e)}"
            )

    def _check_file_integrity(
        self,
        file_path: str,
        results: Dict[str, Any]
    ) -> None:
        """Check file exists and has valid extension."""
        results['total_checks'] += 1

        path = Path(file_path)

        if not path.exists():
            results['errors'].append(f"File not found: {file_path}")
            return

        extension = path.suffix.lower()
        results['details']['file_extension'] = extension

        if extension not in self.allowed_extensions:
            results['errors'].append(
                f"Invalid file extension {extension}, allowed: {self.allowed_extensions}"
            )
            return

        # Try to open image files
        if extension in ['.jpg', '.jpeg', '.png']:
            try:
                with Image.open(file_path) as img:
                    results['details']['image_size'] = img.size
                    results['details']['image_mode'] = img.mode
            except Exception as e:
                results['errors'].append(f"Cannot open image: {str(e)}")
                return

        results['checks_passed'] += 1

    def _check_file_size(
        self,
        file_path: str,
        results: Dict[str, Any]
    ) -> None:
        """Validate file size constraints."""
        results['total_checks'] += 1

        try:
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)
            results['details']['file_size_mb'] = file_size_mb

            if file_size_mb > self.max_file_size_mb:
                results['errors'].append(
                    f"File too large ({file_size_mb:.2f}MB, maximum {self.max_file_size_mb}MB)"
                )
            else:
                results['checks_passed'] += 1
        except Exception as e:
            results['warnings'].append(f"Could not check file size: {str(e)}")

    def _check_sensitive_data(
        self,
        contract: ParsedContract,
        results: Dict[str, Any]
    ) -> None:
        """
        Detect potentially sensitive data (PII).

        Note: This generates warnings, not errors, as contracts
        may legitimately contain contact information.
        """
        text = contract.raw_text
        sensitive_found = {}

        for data_type, pattern in self.sensitive_patterns.items():
            matches = pattern.findall(text)
            if matches:
                # Anonymize the matches for reporting
                sensitive_found[data_type] = len(matches)

        if sensitive_found:
            results['details']['sensitive_data_detected'] = sensitive_found
            results['warnings'].append(
                f"Sensitive data detected: {', '.join(sensitive_found.keys())}. "
                "Ensure proper data handling procedures."
            )

    def validate_output(
        self,
        output: 'ContractChangeOutput',
        original_contract: ParsedContract,
        amendment_contract: ParsedContract
    ) -> Dict[str, Any]:
        """
        Validate the final output against input contracts.

        Args:
            output: ContractChangeOutput to validate
            original_contract: Original contract for cross-reference
            amendment_contract: Amendment contract for cross-reference

        Returns:
            Validation results dictionary
        """
        results = {
            'is_valid': True,
            'checks_passed': 0,
            'total_checks': 0,
            'warnings': [],
            'errors': []
        }

        # Check output completeness
        results['total_checks'] += 1
        if len(output.sections_changed) == 0:
            results['warnings'].append("No sections changed identified")
        else:
            results['checks_passed'] += 1

        results['total_checks'] += 1
        if len(output.topics_touched) == 0:
            results['warnings'].append("No topics identified")
        else:
            results['checks_passed'] += 1

        # Check summary quality
        results['total_checks'] += 1
        if len(output.summary_of_the_change) < 100:
            results['errors'].append("Summary too short")
        else:
            results['checks_passed'] += 1

        # Cross-reference with input
        results['total_checks'] += 1
        combined_text = original_contract.raw_text + amendment_contract.raw_text

        # Check if topics appear in source documents
        topics_found = 0
        for topic in output.topics_touched:
            if topic.lower() in combined_text.lower():
                topics_found += 1

        if topics_found == 0 and len(output.topics_touched) > 0:
            results['warnings'].append(
                "Topics do not appear in source documents - possible hallucination"
            )
        else:
            results['checks_passed'] += 1

        results['is_valid'] = len(results['errors']) == 0

        return results


class SafetyGuardrails:
    """
    Content safety guardrails for contract processing.

    Prevents processing of inappropriate or malicious content.
    """

    def __init__(self):
        # Patterns for potentially malicious content
        self.malicious_patterns = [
            re.compile(r'<script', re.IGNORECASE),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'eval\s*\(', re.IGNORECASE),
        ]

    def check_content_safety(self, text: str) -> Dict[str, Any]:
        """
        Check text for potentially malicious content.

        Args:
            text: Text to analyze

        Returns:
            Safety check results
        """
        results = {
            'is_safe': True,
            'threats_detected': [],
            'warnings': []
        }

        # Check for malicious patterns
        for pattern in self.malicious_patterns:
            if pattern.search(text):
                results['threats_detected'].append(
                    f"Potential injection attack detected: {pattern.pattern}"
                )
                results['is_safe'] = False

        return results
