"""
Evaluator Module for Contract Comparison System

This module provides comprehensive evaluation of the contract comparison
output quality across multiple dimensions:

1. Completeness: Are all changes captured?
2. Accuracy: Is the information correct?
3. Clarity: Is the summary clear and understandable?
4. Relevance: Are identified changes actually relevant?
5. Consistency: Is the output internally consistent?

The evaluator uses both rule-based and LLM-based evaluation methods.
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from openai import OpenAI
from langfuse.decorators import observe

from src.models import ContractChangeOutput, ParsedContract, AgentContext


class ContractEvaluator:
    """
    Evaluates the quality of contract comparison outputs.

    Provides multi-dimensional scoring and actionable recommendations
    for improving extraction quality.
    """

    def __init__(self, client: Optional[OpenAI] = None):
        """
        Initialize evaluator.

        Args:
            client: Optional OpenAI client for LLM-based evaluation
        """
        self.client = client

    def evaluate_output(
        self,
        changes: ContractChangeOutput,
        original_contract: ParsedContract,
        amendment_contract: ParsedContract,
        context: AgentContext
    ) -> Dict[str, Any]:
        """
        Comprehensive evaluation of contract comparison output.

        Args:
            changes: The extracted changes to evaluate
            original_contract: Original contract for reference
            amendment_contract: Amendment contract for reference
            context: Agent 1's contextualization output

        Returns:
            Evaluation results with scores and recommendations
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'dimension_scores': {},
            'overall_score': 0.0,
            'grade': '',
            'recommendations': [],
            'details': {}
        }

        # Run all evaluation dimensions
        self._evaluate_completeness(changes, context, results)
        self._evaluate_accuracy(changes, original_contract, amendment_contract, results)
        self._evaluate_clarity(changes, results)
        self._evaluate_relevance(changes, original_contract, amendment_contract, results)
        self._evaluate_consistency(changes, context, results)

        # Calculate overall score
        dimension_scores = results['dimension_scores']
        results['overall_score'] = sum(dimension_scores.values()) / len(dimension_scores)

        # Assign grade
        results['grade'] = self._assign_grade(results['overall_score'])

        # Generate recommendations
        self._generate_recommendations(results)

        return results

    def _evaluate_completeness(
        self,
        changes: ContractChangeOutput,
        context: AgentContext,
        results: Dict[str, Any]
    ) -> None:
        """
        Evaluate completeness of the extraction.

        Checks:
        - Are all identified change areas covered?
        - Is the output comprehensive?
        """
        score = 100.0

        # Check if sections_changed covers identified_change_areas
        identified_areas = len(context.identified_change_areas)
        sections_changed = len(changes.sections_changed)

        results['details']['identified_change_areas'] = identified_areas
        results['details']['sections_changed'] = sections_changed

        # Penalize if fewer sections than identified areas
        if sections_changed < identified_areas:
            coverage_ratio = sections_changed / identified_areas
            score *= coverage_ratio
            results['details']['coverage_ratio'] = coverage_ratio
        else:
            results['details']['coverage_ratio'] = 1.0

        # Check for empty outputs
        if sections_changed == 0:
            score = 0.0

        if len(changes.topics_touched) == 0:
            score *= 0.5

        # Check summary length (should be comprehensive)
        summary_length = len(changes.summary_of_the_change)
        if summary_length < 200:
            score *= 0.7
        elif summary_length < 100:
            score *= 0.3

        results['dimension_scores']['completeness'] = max(0.0, min(100.0, score))

    def _evaluate_accuracy(
        self,
        changes: ContractChangeOutput,
        original_contract: ParsedContract,
        amendment_contract: ParsedContract,
        results: Dict[str, Any]
    ) -> None:
        """
        Evaluate accuracy of the extraction.

        Checks:
        - Do mentioned sections exist in documents?
        - Do topics relate to document content?
        - Are claims in summary verifiable?
        """
        score = 100.0

        combined_text = (
            original_contract.raw_text.lower() +
            " " +
            amendment_contract.raw_text.lower()
        )

        # Check section references
        section_found_count = 0
        for section in changes.sections_changed:
            # Extract section number/identifier
            section_key = re.sub(r'[^\w\s.-]', '', section.lower())
            if section_key in combined_text:
                section_found_count += 1

        section_accuracy = (
            section_found_count / len(changes.sections_changed)
            if changes.sections_changed else 0
        )
        results['details']['section_accuracy'] = section_accuracy

        # Check topic relevance
        topic_found_count = 0
        for topic in changes.topics_touched:
            # Check if topic keywords appear in documents
            topic_words = topic.lower().split()
            if any(word in combined_text for word in topic_words if len(word) > 3):
                topic_found_count += 1

        topic_relevance = (
            topic_found_count / len(changes.topics_touched)
            if changes.topics_touched else 0
        )
        results['details']['topic_relevance'] = topic_relevance

        # Calculate accuracy score
        score = (section_accuracy * 0.6 + topic_relevance * 0.4) * 100

        results['dimension_scores']['accuracy'] = max(0.0, min(100.0, score))

    def _evaluate_clarity(
        self,
        changes: ContractChangeOutput,
        results: Dict[str, Any]
    ) -> None:
        """
        Evaluate clarity of the summary.

        Checks:
        - Is the summary well-structured?
        - Are sentences clear and concise?
        - Is legal terminology used appropriately?
        """
        score = 100.0
        summary = changes.summary_of_the_change

        # Check sentence structure
        sentences = re.split(r'[.!?]+', summary)
        sentences = [s.strip() for s in sentences if s.strip()]

        results['details']['sentence_count'] = len(sentences)

        if len(sentences) == 1:
            score *= 0.7  # Prefer multi-sentence summaries

        # Check average sentence length
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            results['details']['avg_sentence_length'] = avg_sentence_length

            # Optimal: 15-30 words per sentence
            if avg_sentence_length < 10 or avg_sentence_length > 50:
                score *= 0.8

        # Check for clear structure indicators
        structure_indicators = [
            'first', 'second', 'third', 'finally',
            'additionally', 'furthermore', 'moreover',
            'however', 'therefore', 'consequently'
        ]

        has_structure = any(
            indicator in summary.lower()
            for indicator in structure_indicators
        )
        results['details']['has_structure_indicators'] = has_structure

        if not has_structure and len(sentences) > 2:
            score *= 0.9

        results['dimension_scores']['clarity'] = max(0.0, min(100.0, score))

    def _evaluate_relevance(
        self,
        changes: ContractChangeOutput,
        original_contract: ParsedContract,
        amendment_contract: ParsedContract,
        results: Dict[str, Any]
    ) -> None:
        """
        Evaluate relevance of identified changes.

        Checks:
        - Are the changes actually substantive?
        - Are trivial changes excluded?
        """
        score = 100.0

        # Check for overly generic topics
        generic_topics = [
            'general', 'miscellaneous', 'other', 'various',
            'changes', 'updates', 'modifications'
        ]

        generic_count = sum(
            1 for topic in changes.topics_touched
            if any(gen in topic.lower() for gen in generic_topics)
        )

        if generic_count > 0:
            generic_ratio = generic_count / len(changes.topics_touched)
            score *= (1 - generic_ratio * 0.3)

        results['details']['generic_topics_count'] = generic_count

        # Check for overly generic sections
        if any(
            section.lower() in ['all sections', 'entire document', 'whole contract']
            for section in changes.sections_changed
        ):
            score *= 0.5
            results['details']['overly_broad_sections'] = True
        else:
            results['details']['overly_broad_sections'] = False

        # Check topic-section alignment
        if len(changes.topics_touched) > len(changes.sections_changed) * 2:
            score *= 0.8  # Too many topics for sections identified
        elif len(changes.topics_touched) < len(changes.sections_changed) * 0.5:
            score *= 0.9  # Too few topics for sections identified

        results['dimension_scores']['relevance'] = max(0.0, min(100.0, score))

    def _evaluate_consistency(
        self,
        changes: ContractChangeOutput,
        context: AgentContext,
        results: Dict[str, Any]
    ) -> None:
        """
        Evaluate internal consistency of the output.

        Checks:
        - Do sections and topics align?
        - Does summary match sections/topics?
        - Is there consistency with Agent 1's context?
        """
        score = 100.0

        summary_lower = changes.summary_of_the_change.lower()

        # Check if sections are mentioned in summary
        sections_in_summary = sum(
            1 for section in changes.sections_changed
            if any(
                word.lower() in summary_lower
                for word in section.split()
                if len(word) > 3
            )
        )

        section_summary_consistency = (
            sections_in_summary / len(changes.sections_changed)
            if changes.sections_changed else 0
        )
        results['details']['section_summary_consistency'] = section_summary_consistency

        # Check if topics are mentioned in summary
        topics_in_summary = sum(
            1 for topic in changes.topics_touched
            if any(
                word.lower() in summary_lower
                for word in topic.split()
                if len(word) > 3
            )
        )

        topic_summary_consistency = (
            topics_in_summary / len(changes.topics_touched)
            if changes.topics_touched else 0
        )
        results['details']['topic_summary_consistency'] = topic_summary_consistency

        # Check consistency with Agent 1's identified change areas
        context_lower = context.context_summary.lower()
        changes_align_with_context = sum(
            1 for section in changes.sections_changed
            if any(
                word.lower() in context_lower
                for word in section.split()
                if len(word) > 3
            )
        )

        context_consistency = (
            changes_align_with_context / len(changes.sections_changed)
            if changes.sections_changed else 0
        )
        results['details']['context_consistency'] = context_consistency

        # Calculate consistency score
        score = (
            section_summary_consistency * 0.4 +
            topic_summary_consistency * 0.3 +
            context_consistency * 0.3
        ) * 100

        results['dimension_scores']['consistency'] = max(0.0, min(100.0, score))

    def _assign_grade(self, score: float) -> str:
        """Assign letter grade based on overall score."""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

    def _generate_recommendations(self, results: Dict[str, Any]) -> None:
        """
        Generate actionable recommendations based on evaluation.

        Args:
            results: Evaluation results dictionary (modified in-place)
        """
        recommendations = []
        scores = results['dimension_scores']
        details = results['details']

        # Completeness recommendations
        if scores['completeness'] < 70:
            if details.get('coverage_ratio', 1.0) < 1.0:
                recommendations.append(
                    "Ensure all identified change areas are covered in the extraction"
                )
            if len(details.get('sections_changed', [])) == 0:
                recommendations.append(
                    "No sections identified - review the extraction logic"
                )

        # Accuracy recommendations
        if scores['accuracy'] < 70:
            if details.get('section_accuracy', 1.0) < 0.7:
                recommendations.append(
                    "Some sections do not appear in source documents - verify section references"
                )
            if details.get('topic_relevance', 1.0) < 0.7:
                recommendations.append(
                    "Topics may not be well-grounded in document content - improve topic extraction"
                )

        # Clarity recommendations
        if scores['clarity'] < 70:
            if not details.get('has_structure_indicators', False):
                recommendations.append(
                    "Add structure indicators (First, Second, Additionally) to improve summary clarity"
                )
            avg_len = details.get('avg_sentence_length', 20)
            if avg_len > 50:
                recommendations.append(
                    "Break long sentences into shorter, clearer statements"
                )

        # Relevance recommendations
        if scores['relevance'] < 70:
            if details.get('generic_topics_count', 0) > 0:
                recommendations.append(
                    "Replace generic topics with more specific business/legal concepts"
                )
            if details.get('overly_broad_sections', False):
                recommendations.append(
                    "Identify specific sections rather than broad references"
                )

        # Consistency recommendations
        if scores['consistency'] < 70:
            if details.get('section_summary_consistency', 1.0) < 0.5:
                recommendations.append(
                    "Ensure all sections are explicitly mentioned in the summary"
                )
            if details.get('topic_summary_consistency', 1.0) < 0.5:
                recommendations.append(
                    "Ensure all topics are discussed in the summary"
                )

        results['recommendations'] = recommendations

    @observe(name="llm_based_evaluation")
    def evaluate_with_llm(
        self,
        changes: ContractChangeOutput,
        original_contract: ParsedContract,
        amendment_contract: ParsedContract
    ) -> Dict[str, Any]:
        """
        LLM-based evaluation for subjective quality metrics.

        Uses the LLM to evaluate aspects that are difficult to assess
        with rules, such as:
        - Legal accuracy
        - Business impact assessment
        - Summary coherence

        Args:
            changes: Extracted changes
            original_contract: Original contract
            amendment_contract: Amendment contract

        Returns:
            LLM evaluation results
        """
        if not self.client:
            return {
                'error': 'LLM client not initialized',
                'score': None
            }

        prompt = f"""You are a contract law expert evaluating the quality of a contract change extraction.

ORIGINAL CONTRACT (excerpt):
{original_contract.raw_text[:1000]}...

AMENDMENT CONTRACT (excerpt):
{amendment_contract.raw_text[:1000]}...

EXTRACTED CHANGES:
Sections Changed: {', '.join(changes.sections_changed)}
Topics Touched: {', '.join(changes.topics_touched)}
Summary: {changes.summary_of_the_change}

Please evaluate this extraction on a scale of 1-10 for:
1. Legal Accuracy: Are the changes correctly identified from a legal perspective?
2. Business Relevance: Are the identified changes materially significant?
3. Summary Quality: Is the summary clear, accurate, and comprehensive?

Respond in JSON format:
{{
    "legal_accuracy": <1-10>,
    "business_relevance": <1-10>,
    "summary_quality": <1-10>,
    "overall_assessment": "<brief assessment>",
    "key_strengths": ["strength1", "strength2"],
    "key_weaknesses": ["weakness1", "weakness2"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a contract law evaluation expert."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            import json
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            return {
                'error': f'LLM evaluation failed: {str(e)}',
                'score': None
            }


class MetricsTracker:
    """
    Track evaluation metrics over time for system improvement.
    """

    def __init__(self):
        self.evaluations: List[Dict[str, Any]] = []

    def add_evaluation(self, evaluation: Dict[str, Any]) -> None:
        """Add an evaluation result to the tracker."""
        self.evaluations.append(evaluation)

    def get_average_scores(self) -> Dict[str, float]:
        """Calculate average scores across all evaluations."""
        if not self.evaluations:
            return {}

        dimensions = self.evaluations[0]['dimension_scores'].keys()
        averages = {}

        for dimension in dimensions:
            scores = [
                eval_result['dimension_scores'][dimension]
                for eval_result in self.evaluations
                if dimension in eval_result['dimension_scores']
            ]
            averages[dimension] = sum(scores) / len(scores) if scores else 0.0

        overall_scores = [
            eval_result['overall_score']
            for eval_result in self.evaluations
        ]
        averages['overall'] = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0

        return averages

    def get_common_recommendations(self) -> List[tuple[str, int]]:
        """Get most common recommendations across evaluations."""
        from collections import Counter

        all_recommendations = []
        for evaluation in self.evaluations:
            all_recommendations.extend(evaluation.get('recommendations', []))

        return Counter(all_recommendations).most_common(10)
