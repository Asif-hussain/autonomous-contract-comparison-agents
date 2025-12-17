# Quick Start: Testing with Jupyter Notebook

This guide will help you quickly get started with testing the contract comparison system using the Jupyter notebook.

## Prerequisites

1. **Python 3.10+** installed
2. **API Keys** configured in `.env` file:
   ```bash
   OPENAI_API_KEY=your_key_here
   LANGFUSE_PUBLIC_KEY=your_key_here
   LANGFUSE_SECRET_KEY=your_key_here
   ```

## Step 1: Install Dependencies

```bash
# Navigate to project root
cd /path/to/autonomous-contract-comparison-agents

# Install all dependencies (includes Jupyter)
pip install -r requirements.txt
```

This installs:

- Core dependencies (OpenAI, Langfuse, Pydantic)
- Jupyter notebook and kernel
- Pandas for data visualization
- All other required packages

## Step 2: Start Jupyter

Choose one of these methods:

### Method A: Jupyter Notebook (Classic)

```bash
jupyter notebook
```

- Browser opens automatically
- Navigate to `notebooks/test_contract_flow.ipynb`
- Click to open

### Method B: Jupyter Lab (Modern)

```bash
jupyter lab
```

- Browser opens automatically
- Click `notebooks/test_contract_flow.ipynb` in file browser

### Method C: VS Code

```bash
code .
```

- Open `notebooks/test_contract_flow.ipynb`
- VS Code will prompt to select kernel
- Choose Python 3.10+ kernel

## Step 3: Run the Notebook

### Quick Run (All Cells)

1. Open the notebook
2. Click **Kernel** → **Restart & Run All**
3. Wait for all cells to complete (2-5 minutes)

### Step-by-Step Run

1. Click first cell
2. Press **Shift+Enter** to run and move to next cell
3. Review output before proceeding
4. Repeat for each cell

## What the Notebook Does

### Section 1: Setup

- Imports required modules
- Loads environment variables
- Validates API keys

**Expected Output**: ✓ Imports successful

### Section 2: Environment Validation

- Checks all required environment variables
- Confirms API key presence

**Expected Output**:

```
✓ Environment validated
  OPENAI_API_KEY: ✓
  LANGFUSE_PUBLIC_KEY: ✓
  LANGFUSE_SECRET_KEY: ✓
```

### Section 3: Initialize Clients

- Creates OpenAI client
- Creates Langfuse client
- Initializes guardrails and evaluator

**Expected Output**: ✓ Clients initialized

### Section 4: Discover Test Contracts

- Scans `data/test_contracts/` folder
- Finds pairs of original + amendment contracts
- Lists all available test contracts

**Expected Output**:

```
✓ Found 2 contract pair(s):

  1. contract1
     Original:  contract1_original.jpg
     Amendment: contract1_amendment.jpg

  2. contract2
     Original:  contract2_original.jpg
     Amendment: contract2_amendment.jpg
```

### Section 5: Test Image Parsing

- Parses one contract pair
- Extracts text using GPT-4o Vision
- Shows character counts and sections

**Expected Output**:

```
✓ Original parsed:
  Text length: 1234 characters
  Sections: 5
  First 200 chars: [contract text preview]
```

### Section 6: Test Guardrails

- Validates parsed contracts
- Runs safety checks
- Reports validation results

**Expected Output**:

```
Original Contract Validation:
  Valid: True
  Checks passed: 5/6
  Warnings: []
```

### Section 7: Test Two-Agent Workflow

- Runs Agent 1 (Contextualization)
- Runs Agent 2 (Change Extraction)
- Shows extracted changes

**Expected Output**:

```
✓ Changes extracted:
  Sections changed: 3
  Topics touched: 5
  Summary length: 456 chars
```

### Section 8: Test Output Evaluation

- Evaluates output quality
- Scores across 5 dimensions
- Provides recommendations

**Expected Output**:

```
Quality Evaluation:
  Overall Score: 87.50/100
  Grade: B

Dimension Scores:
  Completeness: 90.00/100
  Accuracy: 85.00/100
  Clarity: 88.00/100
  Relevance: 92.00/100
  Consistency: 82.50/100
```

### Section 9: Process All Contracts

- Runs complete workflow on all contract pairs
- Collects results
- Shows progress for each contract

**Expected Output**:

```
======================================================================
Processing Contract 1/2: contract1
======================================================================

[Full workflow logs]

✓ Success!
  Sections changed: 3
  Topics touched: 5
  Quality score: 87.50/100
```

### Section 10: Display Summary

- Creates pandas DataFrame
- Shows tabular summary of all results

**Expected Output**:

```
Results Summary:
Contract  Sections Changed  Topics Touched  Summary Length  Quality Score  Trace ID
contract1                3               5             456          87.5  abc123...
contract2                4               6             523          91.2  def456...
```

### Section 11: Detailed View

- Shows full results for first contract
- Displays sections, topics, summary
- Shows quality evaluation

### Section 12: Save Results

- Saves all results to JSON
- Creates timestamped file in `notebooks/outputs/`

**Expected Output**:

```
✓ Results saved to: notebooks/outputs/test_results_20251213_103045.json
```

### Section 13: Cleanup

- Flushes Langfuse traces
- Provides dashboard link

**Expected Output**:

```
✓ Langfuse traces flushed
View traces at: https://cloud.langfuse.com
```

## Expected Runtime

- **Setup & Discovery**: ~5 seconds
- **Single Contract**: ~30-60 seconds
- **Two Contracts**: ~1-2 minutes
- **Complete Notebook**: ~2-5 minutes

## Viewing Results

### In Notebook

- See real-time output in each cell
- Review pandas DataFrames for summaries
- Check detailed results sections

### JSON Files

```bash
# View saved results
cat notebooks/outputs/test_results_*.json | python -m json.tool
```

### Langfuse Dashboard

1. Open the URL shown in final cell
2. Navigate to your project
3. View traces with tag `contract_comparison`
4. Inspect detailed execution logs

## Troubleshooting

### "Kernel not found"

```bash
# Install IPython kernel
python -m ipykernel install --user --name=python3
```

### "Module not found" errors

```bash
# Ensure running from project root
cd /path/to/autonomous-contract-comparison-agents

# Reinstall dependencies
pip install -r requirements.txt

# Restart Jupyter kernel
# In notebook: Kernel → Restart
```

### "Environment validation failed"

1. Check `.env` file exists in project root
2. Verify all required keys are present
3. Ensure no extra quotes or spaces in `.env`

### No contracts found

```bash
# Verify test contracts exist
ls -la data/test_contracts/

# Should show:
# contract1_original.jpg
# contract1_amendment.jpg
# contract2_original.jpg
# contract2_amendment.jpg
```

### API errors

- **Rate limit**: Wait a few seconds, re-run cell
- **Invalid key**: Check `.env` file API keys
- **Quota exceeded**: Check OpenAI billing

## Tips for Best Results

### 1. Run Cells Sequentially

- Don't skip cells
- Each cell depends on previous ones
- Review output before proceeding

### 2. Monitor API Usage

- Each contract pair makes ~5-8 API calls
- Total cost per pair: ~$0.10-$0.30
- Watch for rate limits with many contracts

### 3. Explore the Code

- Click cells to see implementation
- Modify parameters to experiment
- Add your own analysis cells

### 4. Export Results

- Save interesting results to JSON
- Use pandas to analyze trends
- Create visualizations if desired

### 5. Customize Testing

```python
# Add your own contract pairs
test_pairs = [
    {
        'name': 'my_contract',
        'original': 'path/to/original.jpg',
        'amendment': 'path/to/amendment.jpg'
    }
]
```

## Next Steps

After running the notebook:

1. **Review Quality Scores**: Check evaluation recommendations
2. **Examine Langfuse Traces**: Deep dive into execution details
3. **Test Enhanced CLI**: Try `main_enhanced.py` with your contracts
4. **Integrate in Workflow**: Use the code in your applications

## Additional Resources

- [Guardrails and Evaluation Guide](../GUARDRAILS_AND_EVALUATION.md)
- [Main README](../README.md)
- [Notebook README](README.md)

## Questions?

If you encounter issues:

1. Check troubleshooting section above
2. Review cell outputs for specific errors
3. Verify environment setup
4. Check API key validity
