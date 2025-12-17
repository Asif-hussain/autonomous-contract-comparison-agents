# Guardrails and Evaluation Guide

This document explains the guardrails and evaluation systems added to the contract comparison project.

## Overview

The enhanced system provides:
1. **Input Guardrails**: Validate and sanitize inputs before processing
2. **Output Guardrails**: Verify output quality and consistency
3. **Quality Evaluation**: Multi-dimensional assessment of extraction quality
4. **Safety Checks**: Detect malicious content and sensitive data

## Guardrails System

### Input Validation

The `ContractGuardrails` class validates inputs across multiple dimensions:

#### 1. Text Length Checks
- **Minimum**: 50 characters (configurable)
- **Maximum**: 50,000 characters (configurable)
- **Purpose**: Prevent empty or excessively large inputs

#### 2. Text Quality Checks
- **Minimum word count**: 20 words
- **Average word length**: 2-20 characters (detects gibberish)
- **Alphabetic ratio**: >50% (detects parsing errors)
- **Purpose**: Ensure OCR/parsing produced usable text

#### 3. File Integrity Checks
- **Allowed extensions**: .jpg, .jpeg, .png, .pdf
- **File size limit**: 10MB (configurable)
- **Image validation**: Verifies images can be opened
- **Purpose**: Prevent file corruption and unsupported formats

#### 4. Sensitive Data Detection
- **Patterns detected**:
  - Social Security Numbers (SSN)
  - Credit card numbers
  - Email addresses
  - Phone numbers
- **Action**: Warning only (contracts may legitimately contain contact info)
- **Purpose**: Alert users to sensitive data presence

#### 5. Safety Checks
- **Malicious content detection**:
  - Script injection patterns
  - JavaScript execution attempts
  - Eval() function calls
- **Action**: Blocks processing if threats detected
- **Purpose**: Prevent security vulnerabilities

### Output Validation

Validates the final `ContractChangeOutput`:

- **Completeness**: Ensures sections and topics are identified
- **Summary quality**: Minimum 100 characters
- **Cross-reference**: Verifies topics appear in source documents
- **Hallucination detection**: Flags topics not present in inputs

### Usage Example

```python
from src.guardrails import ContractGuardrails, SafetyGuardrails

# Initialize guardrails
guardrails = ContractGuardrails(
    min_text_length=50,
    max_text_length=50000,
    max_file_size_mb=10.0
)

# Validate input
validation = guardrails.validate_input(
    contract=parsed_contract,
    file_path="/path/to/contract.jpg"
)

print(f"Valid: {validation['is_valid']}")
print(f"Checks passed: {validation['checks_passed']}/{validation['total_checks']}")
print(f"Warnings: {validation['warnings']}")
print(f"Errors: {validation['errors']}")

# Validate output
output_validation = guardrails.validate_output(
    output=changes,
    original_contract=original_contract,
    amendment_contract=amendment_contract
)
```

## Evaluation System

### Quality Dimensions

The `ContractEvaluator` assesses output across 5 dimensions:

#### 1. Completeness (0-100)
**What it measures**: Are all changes captured?

**Evaluation criteria**:
- Coverage of Agent 1's identified change areas
- Presence of sections and topics
- Summary comprehensiveness (length)

**Scoring**:
- 100: All change areas covered, comprehensive output
- 70-99: Most changes captured, minor gaps
- 0-69: Significant missing information

#### 2. Accuracy (0-100)
**What it measures**: Is the information correct?

**Evaluation criteria**:
- Section references exist in documents (60% weight)
- Topics relate to document content (40% weight)
- Claims are verifiable in source text

**Scoring**:
- 100: All sections and topics verified in source
- 70-99: Most references accurate, minor discrepancies
- 0-69: Significant inaccuracies or hallucinations

#### 3. Clarity (0-100)
**What it measures**: Is the summary clear and understandable?

**Evaluation criteria**:
- Sentence structure (multi-sentence preferred)
- Average sentence length (15-30 words optimal)
- Use of structure indicators (First, Second, Additionally, etc.)

**Scoring**:
- 100: Well-structured, clear, appropriate length
- 70-99: Generally clear, minor issues
- 0-69: Unclear, poor structure, or awkward phrasing

#### 4. Relevance (0-100)
**What it measures**: Are identified changes substantive?

**Evaluation criteria**:
- Avoidance of generic topics ("general", "miscellaneous")
- Specific section references (not "all sections")
- Appropriate topic-to-section ratio

**Scoring**:
- 100: All changes specific and substantive
- 70-99: Mostly relevant, some generic elements
- 0-69: Too generic or overly broad

#### 5. Consistency (0-100)
**What it measures**: Is the output internally consistent?

**Evaluation criteria**:
- Sections mentioned in summary (40% weight)
- Topics discussed in summary (30% weight)
- Alignment with Agent 1's context (30% weight)

**Scoring**:
- 100: Perfect internal consistency
- 70-99: Minor inconsistencies
- 0-69: Significant contradictions or omissions

### Overall Grading

**Overall Score**: Average of all 5 dimension scores

**Letter Grades**:
- **A** (90-100): Excellent quality
- **B** (80-89): Good quality
- **C** (70-79): Acceptable quality
- **D** (60-69): Below expectations
- **F** (0-59): Unacceptable quality

### Usage Example

```python
from src.evaluator import ContractEvaluator

# Initialize evaluator
evaluator = ContractEvaluator(client=openai_client)

# Evaluate output
evaluation = evaluator.evaluate_output(
    changes=changes,
    original_contract=original_contract,
    amendment_contract=amendment_contract,
    context=context
)

print(f"Overall Score: {evaluation['overall_score']:.2f}/100")
print(f"Grade: {evaluation['grade']}")

print("\nDimension Scores:")
for dimension, score in evaluation['dimension_scores'].items():
    print(f"  {dimension.capitalize()}: {score:.1f}/100")

print("\nRecommendations:")
for rec in evaluation['recommendations']:
    print(f"  - {rec}")
```

### LLM-Based Evaluation (Optional)

For subjective quality metrics:

```python
# Enable LLM evaluation
llm_eval = evaluator.evaluate_with_llm(
    changes=changes,
    original_contract=original_contract,
    amendment_contract=amendment_contract
)

print(f"Legal Accuracy: {llm_eval['legal_accuracy']}/10")
print(f"Business Relevance: {llm_eval['business_relevance']}/10")
print(f"Summary Quality: {llm_eval['summary_quality']}/10")
print(f"Assessment: {llm_eval['overall_assessment']}")
```

## Running Enhanced Workflow

### Command Line

```bash
# With guardrails and evaluation
python src/main_enhanced.py \
    --original data/test_contracts/contract1_original.jpg \
    --amendment data/test_contracts/contract1_amendment.jpg \
    --output results.json

# Skip guardrails (not recommended)
python src/main_enhanced.py \
    --original contract1.jpg \
    --amendment contract1_amend.jpg \
    --skip-guardrails

# Enable LLM-based evaluation
python src/main_enhanced.py \
    --original contract1.jpg \
    --amendment contract1_amend.jpg \
    --enable-llm-eval
```

### Jupyter Notebook

Open [notebooks/test_contract_flow.ipynb](notebooks/test_contract_flow.ipynb) and run all cells.

The notebook automatically:
1. Discovers all contract pairs in `data/test_contracts/`
2. Applies guardrails validation
3. Runs the two-agent workflow
4. Evaluates output quality
5. Generates comprehensive reports

## Output Format (Enhanced)

```json
{
  "sections_changed": ["Section 2.1", "Section 4.3"],
  "topics_touched": ["Payment Terms", "Confidentiality"],
  "summary_of_the_change": "The amendment modifies...",

  "_metadata": {
    "generated_at": "2025-12-13T10:30:00",
    "system": "Enhanced Contract Comparison System",
    "version": "2.0.0",
    "guardrails_enabled": true,
    "evaluation_enabled": true
  },

  "_guardrails": {
    "original": {
      "is_valid": true,
      "checks_passed": 5,
      "total_checks": 6,
      "warnings": []
    },
    "amendment": {
      "is_valid": true,
      "checks_passed": 5,
      "total_checks": 6,
      "warnings": ["Low alphabetic ratio"]
    },
    "output": {
      "is_valid": true,
      "checks_passed": 4,
      "total_checks": 4
    }
  },

  "_evaluation": {
    "rule_based": {
      "overall_score": 87.5,
      "grade": "B",
      "dimension_scores": {
        "completeness": 90.0,
        "accuracy": 85.0,
        "clarity": 88.0,
        "relevance": 92.0,
        "consistency": 82.5
      },
      "recommendations": [
        "Ensure all sections are explicitly mentioned in the summary"
      ]
    }
  },

  "_warnings": []
}
```

## Metrics Tracking

Track evaluation metrics over time:

```python
from src.evaluator import MetricsTracker

tracker = MetricsTracker()

# Add evaluation results
tracker.add_evaluation(evaluation1)
tracker.add_evaluation(evaluation2)
tracker.add_evaluation(evaluation3)

# Get average scores
averages = tracker.get_average_scores()
print(f"Average overall score: {averages['overall']:.2f}")

# Get common recommendations
common_recs = tracker.get_common_recommendations()
for rec, count in common_recs[:5]:
    print(f"{count}x: {rec}")
```

## Best Practices

### 1. Always Enable Guardrails
- Prevents processing of invalid inputs
- Saves API costs on bad data
- Detects security threats

### 2. Review Warnings
- Warnings don't stop processing but indicate potential issues
- Address warnings to improve input quality

### 3. Use Evaluation for Improvement
- Review dimension scores to identify weaknesses
- Follow recommendations to enhance extraction
- Track metrics over time to measure improvements

### 4. Handle Validation Failures
- Log validation failures for debugging
- Provide clear error messages to users
- Consider retry logic for transient issues

### 5. Customize Thresholds
```python
# Adjust guardrails for your use case
guardrails = ContractGuardrails(
    min_text_length=100,      # Stricter minimum
    max_text_length=100000,   # Allow larger docs
    max_file_size_mb=20.0     # Larger files
)
```

## Integration with Langfuse

All guardrails and evaluation results are traced in Langfuse:

```python
langfuse_context.update_current_trace(
    metadata={
        "guardrails_results": validation,
        "evaluation_results": evaluation
    }
)
```

View in Langfuse dashboard:
- Input validation results
- Quality scores
- Recommendations
- Warnings and errors

## Troubleshooting

### Guardrails Blocking Valid Input

**Issue**: Contract fails validation but appears valid

**Solutions**:
1. Check validation details: `print(validation['details'])`
2. Adjust thresholds if needed
3. Review warnings vs errors
4. Use `--skip-guardrails` temporarily for testing

### Low Evaluation Scores

**Issue**: Consistent low scores in certain dimensions

**Solutions**:
1. Review specific recommendations
2. Check Agent 1 context quality
3. Adjust prompts if needed
4. Validate input document quality

### False Positive Sensitive Data Detection

**Issue**: Warnings for legitimate contract information

**Solutions**:
- This is expected behavior (warnings, not errors)
- Ensure proper data handling procedures
- Consider disabling specific patterns if needed

## Future Enhancements

Potential improvements:
- Custom evaluation criteria per contract type
- Automated prompt tuning based on evaluation scores
- Threshold-based auto-retry with prompt adjustments
- Integration with external compliance APIs
- Real-time monitoring dashboards
