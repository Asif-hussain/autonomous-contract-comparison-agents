# Contract Comparison Testing Notebooks

This directory contains the complete validation notebook for the autonomous contract comparison system.

## 📓 Main Notebook

### [test_contract_flow.ipynb](test_contract_flow.ipynb)

**Complete testing and validation notebook** that demonstrates all system requirements:

✅ Multimodal input processing (GPT-4o Vision)
✅ Two-agent collaborative architecture
✅ Structured Pydantic output
✅ Input/output guardrails
✅ 5-dimensional quality evaluation
✅ Complete Langfuse tracing
✅ Production testing with real contracts

## 🚀 Quick Start

```bash
# 1. Activate virtual environment
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# 2. Start Jupyter
jupyter notebook

# 3. Open test_contract_flow.ipynb and run all cells
```

## 📊 What You'll See

The notebook will:
- Process 2 contract pairs from `data/test_contracts/`
- Parse images using GPT-4o Vision
- Run contextualization and extraction agents
- Validate inputs and outputs with guardrails
- Score quality across 5 dimensions
- Generate Langfuse traces
- Save results to `notebooks/outputs/`
- Display comprehensive validation summary

## 📁 Output Files

Results are saved to `notebooks/outputs/`:
- `test_results_YYYYMMDD_HHMMSS.json` - Complete results with evaluation scores
- Each run generates a new timestamped file

## 📝 Prerequisites

Ensure your `.env` file contains:
```bash
OPENAI_API_KEY=your_key_here
LANGFUSE_PUBLIC_KEY=your_key_here
LANGFUSE_SECRET_KEY=your_key_here
```

## 💡 For Evaluators

This notebook provides **complete validation** of all project requirements. Simply run all cells to see:
- All core features in action
- Quality metrics and scores
- Langfuse trace IDs
- Comprehensive validation checklist

For detailed documentation, see the main [README.md](../README.md) and [data/test_contracts/README.md](../data/test_contracts/README.md)
