"""
Image Parser for Contract Documents using Multimodal LLMs

This module handles the conversion of scanned contract images into structured text
using vision-capable language models (GPT-4o, Gemini Vision, or Claude Vision).

The parser validates image formats, encodes images for API transmission, and
constructs specialized prompts for accurate contract text extraction while
preserving document hierarchy.

Key Functions:
    - parse_contract_image: Main entry point for parsing a contract image
    - validate_image: Ensures image format and size requirements are met
    - encode_image_to_base64: Converts image files to base64 for API transmission
    - create_vision_prompt: Constructs the prompt for contract extraction
"""

import base64
import os
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import io

from openai import OpenAI
from langfuse.decorators import observe, langfuse_context

from src.models import ParsedContract


import logging

# Configure logger
logger = logging.getLogger(__name__)

def get_llm_client() -> OpenAI:
    """
    Create and return an OpenAI-compatible client.
    
    Tried to use OPENAI_API_KEY first (standard OpenAI), then falls back
    to OPENROUTER_API_KEY (OpenRouter).

    Returns:
        OpenAI client instance
    """
    # 1. Try standard OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        logger.debug("Using standard OpenAI API key")
        return OpenAI(api_key=openai_key)

    # 2. Try OpenRouter
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        logger.debug("Using OpenRouter API key")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        return OpenAI(
            api_key=openrouter_key,
            base_url=base_url
        )

    raise ValueError("Missing API Key: Set either OPENAI_API_KEY or OPENROUTER_API_KEY in environment.")


# Maximum file size for images (10 MB)
MAX_IMAGE_SIZE_MB = 10
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf'}


def convert_pdf_to_image(pdf_path: str) -> str:
    """
    Convert the first page of a PDF to a PNG image using PyMuPDF.
    
    This function uses PyMuPDF (fitz) which is a pure-Python library
    with no system dependencies required (unlike pdf2image which needs poppler).
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Path to the converted PNG image (temporary file)
        
    Raises:
        ImportError: If PyMuPDF is not installed
        Exception: If PDF conversion fails
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF is required for PDF support. "
            "Install it with: pip install PyMuPDF"
        )
    
    try:
        # Open PDF
        pdf_document = fitz.open(pdf_path)
        
        if len(pdf_document) == 0:
            raise ValueError("PDF has no pages")
        
        # Get first page
        page = pdf_document[0]
        
        # Render page to image at 300 DPI
        # mat = fitz.Matrix(300/72, 300/72) creates 300 DPI (72 is default)
        mat = fitz.Matrix(300/72, 300/72)
        pix = page.get_pixmap(matrix=mat)
        
        # Save to temporary PNG file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        pix.save(temp_file.name)
        temp_file.close()
        
        pdf_document.close()
        
        logger.info(f"Converted PDF to image: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        raise Exception(f"Failed to convert PDF to image: {str(e)}")



def validate_image(image_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that the image file meets requirements for processing.

    This function checks:
    1. File exists and is accessible
    2. File extension is in supported formats
    3. File size is within acceptable limits
    4. Image can be opened and read by PIL (for images only, not PDFs)

    Args:
        image_path: Path to the image file to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if image passes all validation checks
        - error_message: None if valid, otherwise description of validation failure

    Example:
        >>> is_valid, error = validate_image("contract.jpg")
        >>> if not is_valid:
        ...     print(f"Invalid image: {error}")
    """
    # Check if file exists
    if not os.path.exists(image_path):
        return False, f"File not found: {image_path}"

    # Check file extension
    file_extension = Path(image_path).suffix.lower()
    if file_extension not in SUPPORTED_FORMATS:
        return False, (
            f"Unsupported format: {file_extension}. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    # Check file size
    file_size = os.path.getsize(image_path)
    if file_size > MAX_IMAGE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return False, (
            f"File too large: {size_mb:.2f}MB. "
            f"Maximum allowed: {MAX_IMAGE_SIZE_MB}MB"
        )

    if file_size == 0:
        return False, "File is empty"

    # For PDFs, skip PIL validation (will be converted to image later)
    if file_extension == '.pdf':
        return True, None

    # Try to open and verify it's a valid image (for non-PDF files)
    try:
        with Image.open(image_path) as img:
            img.verify()
        # Re-open to check if image data is readable (verify() closes the file)
        with Image.open(image_path) as img:
            img.load()
    except Exception as e:
        return False, f"Invalid or corrupted image file: {str(e)}"

    return True, None


def encode_image_to_base64(image_path: str) -> str:
    """
    Encode an image file to base64 string for API transmission.

    Reads the image file in binary mode and converts it to a base64-encoded
    string suitable for inclusion in API requests to multimodal LLMs.

    Args:
        image_path: Path to the image file to encode

    Returns:
        Base64-encoded string representation of the image

    Raises:
        FileNotFoundError: If image file does not exist
        IOError: If file cannot be read

    Example:
        >>> base64_image = encode_image_to_base64("contract.jpg")
        >>> print(f"Encoded {len(base64_image)} characters")
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def create_vision_prompt(document_type: str) -> str:
    """
    Create a specialized prompt for contract text extraction.

    Constructs a detailed prompt that instructs the vision model to extract
    all text from the contract image while preserving document structure,
    section hierarchy, and formatting.

    Args:
        document_type: Type of document being parsed ("original" or "amendment")

    Returns:
        Formatted prompt string for the vision model

    Example:
        >>> prompt = create_vision_prompt("original")
        >>> assert "Extract all text" in prompt
    """
    return f"""You are a legal document analysis expert. Extract ALL text from this {document_type} contract image with the following requirements:

1. PRESERVE DOCUMENT STRUCTURE:
   - Maintain all section headers (e.g., "Section 1.0", "Article III", "Clause 2.1")
   - Keep subsection hierarchy intact (e.g., 1.1, 1.1.1, 1.1.2)
   - Preserve paragraph breaks and formatting
   - Maintain numbered and bulleted lists

2. TEXT EXTRACTION:
   - Extract every word, including headers, footers, and page numbers
   - Include all legal clauses, definitions, and terms
   - Capture exhibit labels and references (e.g., "See Exhibit A")
   - Include signatures, dates, and party names if visible
   - Extract table contents if present

3. QUALITY REQUIREMENTS:
   - Ensure high accuracy (aim for 95%+ correctness)
   - If text is unclear or partially visible, note it as [UNCLEAR: approximate text]
   - For completely illegible sections, note as [ILLEGIBLE SECTION]
   - Maintain original capitalization and punctuation

4. OUTPUT FORMAT:
   - Start with document title if present
   - Then party names and effective date
   - Then full document body with all sections in order
   - End with signature blocks and exhibits

Extract the complete text now, maintaining all structure and hierarchy:"""


@observe(name="parse_contract_image", capture_input=False, capture_output=False)
def parse_contract_image(
    image_path: str,
    document_type: str,
    client: OpenAI,
    model: str = None
) -> ParsedContract:
    """
    Parse a contract image using a multimodal LLM via OpenRouter.

    This is the main entry point for converting a scanned contract image
    into structured text. It handles validation, encoding, API communication,
    and result parsing using OpenRouter's API.

    The function is instrumented with Langfuse tracing to capture:
    - Input parameters (image path, document type, model)
    - Image validation results
    - API call details (tokens, latency, cost)
    - Extracted text output

    Args:
        image_path: Path to the contract image file
        document_type: Type of document ("original" or "amendment")
        client: OpenAI-compatible client configured for OpenRouter
        model: Model to use for vision parsing (default: from MODEL_NAME env var)

    Returns:
        ParsedContract object containing extracted text and metadata

    Raises:
        ValueError: If image validation fails
        Exception: If API call fails or parsing errors occur

    Example:
        >>> client = get_openrouter_client()
        >>> parsed = parse_contract_image("contract.jpg", "original", client)
        >>> print(f"Extracted {len(parsed.raw_text)} characters")
    """
    # Get model from environment if not specified
    if model is None:
        model = os.getenv("MODEL_NAME", "openai/gpt-4o")

    # Add metadata to trace
    langfuse_context.update_current_trace(
        metadata={
            "image_path": image_path,
            "document_type": document_type,
            "model": model
        },
        tags=["image_parsing", document_type]
    )

    # Validate image before processing
    is_valid, error_message = validate_image(image_path)
    if not is_valid:
        langfuse_context.update_current_observation(
            level="ERROR",
            status_message=f"Image validation failed: {error_message}"
        )
        raise ValueError(f"Image validation failed: {error_message}")

    # Log successful validation
    langfuse_context.update_current_observation(
        metadata={"validation": "passed"}
    )

    # Handle PDF conversion
    pdf_converted = False
    original_path = image_path
    file_extension = Path(image_path).suffix.lower()
    
    if file_extension == '.pdf':
        logger.info(f"PDF detected, converting to image...")
        try:
            image_path = convert_pdf_to_image(image_path)
            pdf_converted = True
            logger.info(f"PDF converted successfully")
        except Exception as e:
            raise ValueError(f"PDF conversion failed: {str(e)}")

    try:
        # Encode image to base64
        base64_image = encode_image_to_base64(image_path)

        # Get file extension for MIME type
        file_extension = Path(image_path).suffix.lower()
        mime_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.gif': 'image/gif'
        }
        mime_type = mime_type_map.get(file_extension, 'image/jpeg')

        # Create vision prompt
        vision_prompt = create_vision_prompt(document_type)

        # Get model parameters from environment
        max_tokens = int(os.getenv("MAX_TOKENS", "4096"))
        temperature = float(os.getenv("TEMPERATURE", "0.1"))

        # Make API call to multimodal LLM via OpenRouter
        # This is the core multimodal integration using GPT-4o vision capabilities
        # Manually log input
        langfuse_context.update_current_observation(
            input={
                "image_path": image_path,
                "document_type": document_type
            }
        )

        messages = [
            {
                "type": "text",
                "text": vision_prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_image}",
                    "detail": "high"  # Request high-detail analysis
                }
            }
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": messages
                }
            ],
            max_tokens=max_tokens,  # Allow for long contract extraction
            temperature=temperature   # Low temperature for consistent, accurate extraction
        )

        # Extract the response text
        extracted_text = response.choices[0].message.content

        # Extract section headers using simple heuristics
        # Look for common section patterns like "Section X", "Article X", "Clause X"
        sections_identified = []
        for line in extracted_text.split('\n'):
            line_stripped = line.strip()
            # Common section header patterns
            if any(line_stripped.startswith(prefix) for prefix in [
                'Section', 'SECTION', 'Article', 'ARTICLE',
                'Clause', 'CLAUSE', 'Exhibit', 'EXHIBIT'
            ]):
                sections_identified.append(line_stripped)

        # Add token usage to trace metadata
        langfuse_context.update_current_observation(
            metadata={
                "tokens_used": {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                },
                "extracted_text_length": len(extracted_text),
                "sections_found": len(sections_identified)
            }
        )

        # Create and return ParsedContract model
        parsed_contract = ParsedContract(
            raw_text=extracted_text,
            document_type=document_type,
            sections_identified=sections_identified
        )

        return parsed_contract

    except Exception as e:
        # Log error to trace
        langfuse_context.update_current_observation(
            level="ERROR",
            status_message=f"Parsing failed: {str(e)}"
        )
        raise Exception(f"Failed to parse contract image: {str(e)}")


def get_image_info(image_path: str) -> dict:
    """
    Get metadata about an image file.

    Utility function to retrieve image dimensions, format, and size
    for debugging and logging purposes.

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary containing image metadata:
        - width: Image width in pixels
        - height: Image height in pixels
        - format: Image format (JPEG, PNG, etc.)
        - size_mb: File size in megabytes
        - mode: Color mode (RGB, RGBA, etc.)

    Example:
        >>> info = get_image_info("contract.jpg")
        >>> print(f"Image: {info['width']}x{info['height']}, {info['size_mb']:.2f}MB")
    """
    with Image.open(image_path) as img:
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "size_mb": round(file_size_mb, 2),
            "mode": img.mode
        }
