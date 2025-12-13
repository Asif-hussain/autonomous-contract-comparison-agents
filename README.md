# Contract Comparison Agent

An AI-powered system that automatically compares contract documents (images or PDFs) and extracts changes using a collaborative two-agent architecture with GPT-4o Vision.

![UI Screenshot](data/traces/main-page.png)


## Features

- **Multimodal Input**: Processes scanned images and PDFs
- **Two-Agent Architecture**: Specialized agents for contextualization and extraction
- **Structured Output**: Pydantic-validated JSON with sections changed, topics, and summaries
- **Web UI**: Streamlit interface with drag-and-drop upload
- **Complete Tracing**: Langfuse integration for observability
- **Production Ready**: Comprehensive tests and error handling

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key with GPT-4o access
- Langfuse account (free tier available)

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd autonomous-contract-comparison

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys
```

### Running the Application

**Web UI (Recommended):**
```bash
streamlit run src/app.py
```
Then open http://localhost:8501 and upload your contracts.

**Command Line:**
```bash
python src/main.py --original data/test_contracts/original.jpg --amendment data/test_contracts/amendment.jpg
```

## How It Works

```
Input (Images/PDFs)
    ↓
GPT-4o Vision (Parse documents)
    ↓
Agent 1 (Contextualization) → Maps structure and sections
    ↓
Agent 2 (Extraction) → Extracts specific changes
    ↓
Pydantic Validation
    ↓
Structured JSON Output
```

## Output Format

```json
{
  "sections_changed": ["Section 2.1 - Payment Terms", "Section 4.3 - Confidentiality"],
  "topics_touched": ["Payment Terms", "Confidentiality", "Service Levels"],
  "summary_of_the_change": "The amendment extends payment terms from 30 to 45 days..."
}
```

## Environment Variables

Required in `.env`:
```bash
OPENAI_API_KEY=your_key_here
LANGFUSE_PUBLIC_KEY=your_key_here
LANGFUSE_SECRET_KEY=your_key_here
LANGFUSE_HOST=https://cloud.langfuse.com  # Optional
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/
```

## Project Structure

```
autonomous-contract-comparison/
├── src/
│   ├── main.py              # Main workflow orchestration
│   ├── app.py               # Streamlit web UI
│   ├── image_parser.py      # Image/PDF to text conversion
│   ├── models.py            # Pydantic data models
│   └── agents/
│       ├── contextualization_agent.py  # Agent 1
│       └── extraction_agent.py         # Agent 2
├── tests/                   # Test suite
├── data/test_contracts/     # Sample contracts
└── requirements.txt         # Dependencies
```

## Key Technologies

- **GPT-4o Vision**: Multimodal document parsing
- **Pydantic v2**: Data validation and structured outputs
- **Langfuse**: Tracing and observability
- **Streamlit**: Web interface
- **PyMuPDF**: PDF processing (no system dependencies)

## Troubleshooting

**"No module named 'src'"**
- Ensure you're running from the project root directory

**"Missing API key"**
- Check `.env` file has all required keys
- Verify keys are valid and have GPT-4o access

**PDF upload fails**
- Ensure PyMuPDF is installed: `pip install PyMuPDF`

## License

MIT License - See LICENSE file for details

## Contact

For questions or issues, please open a GitHub issue.
