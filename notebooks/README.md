# Contract Comparison Testing Notebooks

This directory contains Jupyter notebooks for testing and demonstrating the contract comparison system.

## Notebooks

### test_contract_flow.ipynb

Comprehensive testing notebook that demonstrates:

1. **Image Parsing**: Converting contract images to text using GPT-4o Vision
2. **Two-Agent System**: Contextualization and extraction agents
3. **Guardrails**: Input validation and safety checks
4. **Evaluation**: Output quality assessment across 5 dimensions
5. **Complete Workflow**: Processing all test contracts

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Ensure your `.env` file contains:

```bash
OPENAI_API_KEY=your_key_here
LANGFUSE_PUBLIC_KEY=your_key_here
LANGFUSE_SECRET_KEY=your_key_here
```

### 3. Start Jupyter

```bash
# Option 1: Jupyter Notebook
jupyter notebook

# Option 2: Jupyter Lab
jupyter lab

# Option 3: VS Code (open .ipynb file)
```

## Usage

Open [test_contract_flow.ipynb](test_contract_flow.ipynb) and run all cells to:

- Test image parsing with all contracts in `data/test_contracts/`
- Validate inputs with guardrails
- Execute the two-agent workflow
- Evaluate output quality
- Generate comprehensive test results

## Output

The notebook generates:

- Console output showing progress and results
- Summary tables with pandas DataFrames
- JSON files in `notebooks/outputs/` with detailed results
- Quality metrics and recommendations

## Test Contracts

The notebook automatically discovers contract pairs from `data/test_contracts/`:

- `contract1_original.jpg` + `contract1_amendment.jpg`
- `contract2_original.jpg` + `contract2_amendment.jpg`
- etc.

## Guardrails

Input validation includes:

- Text length and quality checks
- File integrity validation
- Content safety screening
- Sensitive data detection (PII warnings)

## Evaluation Dimensions

Output quality is evaluated on:

1. **Completeness** (0-100): Are all changes captured?
2. **Accuracy** (0-100): Is the information correct?
3. **Clarity** (0-100): Is the summary clear?
4. **Relevance** (0-100): Are changes substantive?
5. **Consistency** (0-100): Is output internally consistent?

Overall score and letter grade (A-F) are calculated.

## Tips

- Run cells sequentially for best results
- Check the console for detailed logging
- Review evaluation recommendations to improve extraction quality
- Export results to JSON for further analysis

## Troubleshooting

**"Module not found" errors:**

```bash
# Ensure you're in the project root when starting Jupyter
cd /path/to/autonomous-contract-comparison-agents
jupyter notebook
```

**"Environment validation failed":**

- Check your `.env` file exists and has all required keys
- Verify API keys are valid

**Guardrails/Evaluator not found:**

- The notebook will run in basic mode without these modules
- Ensure `src/guardrails.py` and `src/evaluator.py` exist
