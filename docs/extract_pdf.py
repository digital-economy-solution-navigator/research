"""
Script to extract text from PDF files, including scanned PDFs using OCR.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Dict
import re

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


def extract_text_with_pdfplumber(pdf_path: Path) -> Optional[str]:
    """
    Extract text from PDF using pdfplumber (works for text-based PDFs).
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Extracted text or None if failed
    """
    if not PDFPLUMBER_AVAILABLE:
        return None
    
    try:
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return '\n\n'.join(text_parts) if text_parts else None
    except Exception as e:
        print(f"  Error with pdfplumber: {e}")
        return None


def extract_text_with_pypdf2(pdf_path: Path) -> Optional[str]:
    """
    Extract text from PDF using PyPDF2 (works for text-based PDFs).
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Extracted text or None if failed
    """
    if not PYPDF2_AVAILABLE:
        return None
    
    try:
        text_parts = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return '\n\n'.join(text_parts) if text_parts else None
    except Exception as e:
        print(f"  Error with PyPDF2: {e}")
        return None


def extract_text_with_ocr(pdf_path: Path) -> Optional[str]:
    """
    Extract text from scanned PDF using OCR (Tesseract).
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Extracted text or None if failed
    """
    if not OCR_AVAILABLE:
        return None
    
    try:
        print("  Converting PDF to images for OCR...")
        # Convert PDF pages to images
        # Try to find poppler path on Windows
        poppler_path = None
        if sys.platform == 'win32':
            # Common poppler installation paths on Windows
            possible_paths = [
                r'C:\poppler\bin',
                r'C:\Program Files\poppler\bin',
                r'C:\Program Files (x86)\poppler\bin',
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'poppler', 'bin'),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    poppler_path = path
                    break
        
        try:
            if poppler_path:
                images = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)
            else:
                images = convert_from_path(pdf_path, dpi=300)
        except Exception as e:
            if 'poppler' in str(e).lower() or 'page count' in str(e).lower():
                print(f"  ⚠ Poppler not found. Please install poppler:")
                print(f"     Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/")
                print(f"     Extract and add 'bin' folder to PATH, or place in C:\\poppler\\bin")
                print(f"     macOS: brew install poppler")
                print(f"     Linux: sudo apt-get install poppler-utils")
                return None
            raise
        
        print(f"  Processing {len(images)} page(s) with OCR...")
        text_parts = []
        
        for i, image in enumerate(images, 1):
            print(f"    Processing page {i}/{len(images)}...", end='\r')
            # Extract text using Tesseract OCR
            page_text = pytesseract.image_to_string(image, lang='eng')
            if page_text.strip():
                text_parts.append(page_text)
        
        print()  # New line after progress
        return '\n\n'.join(text_parts) if text_parts else None
    except Exception as e:
        print(f"  Error with OCR: {e}")
        return None


def extract_text_from_pdf(pdf_path: Path, use_ocr: bool = True) -> Optional[str]:
    """
    Extract text from PDF file, trying multiple methods.
    
    Args:
        pdf_path: Path to PDF file
        use_ocr: Whether to use OCR for scanned PDFs
    
    Returns:
        Extracted text or None if failed
    """
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        return None
    
    print(f"Extracting text from: {pdf_path.name}")
    
    # Try pdfplumber first (fastest, works for text-based PDFs)
    if PDFPLUMBER_AVAILABLE:
        print("  Trying pdfplumber...")
        text = extract_text_with_pdfplumber(pdf_path)
        if text and len(text.strip()) > 50:  # If we got substantial text
            print(f"  ✓ Extracted {len(text)} characters using pdfplumber")
            return text
    
    # Try PyPDF2 as fallback
    if PYPDF2_AVAILABLE:
        print("  Trying PyPDF2...")
        text = extract_text_with_pypdf2(pdf_path)
        if text and len(text.strip()) > 50:
            print(f"  ✓ Extracted {len(text)} characters using PyPDF2")
            return text
    
    # If no text extracted, try OCR (for scanned PDFs)
    if use_ocr and OCR_AVAILABLE:
        print("  No text found, trying OCR...")
        text = extract_text_with_ocr(pdf_path)
        if text and len(text.strip()) > 50:
            print(f"  ✓ Extracted {len(text)} characters using OCR")
            return text
    
    print("  ✗ Could not extract text from PDF")
    return None


def extract_structured_info(text: str) -> Dict[str, any]:
    """
    Extract structured information from extracted text.
    
    Args:
        text: Extracted text from PDF
    
    Returns:
        Dictionary with extracted information
    """
    info = {
        'full_text': text,
        'project_id': None,
        'project_name': None,
        'date': None,
        'signatures': [],
        'key_phrases': [],
    }
    
    # Extract project ID (common patterns)
    project_id_patterns = [
        r'Project\s+(?:ID|No\.?|Number)[\s:]+(\d+)',
        r'Project\s+(\d{6,})',
        r'ID[:\s]+(\d{6,})',
        r'USINT\d+',
    ]
    for pattern in project_id_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['project_id'] = match.group(1) if match.lastindex else match.group(0)
            break
    
    # Extract dates
    date_patterns = [
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
        r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
    ]
    dates = []
    for pattern in date_patterns:
        dates.extend(re.findall(pattern, text))
    if dates:
        info['date'] = dates[0]
    
    # Extract signatures (look for signature-related text)
    signature_patterns = [
        r'(?:Signed|Signature|Signatory)[\s:]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'([A-Z][a-z]+\s+[A-Z][a-z]+)[\s,]+(?:Director|Manager|Coordinator)',
    ]
    for pattern in signature_patterns:
        matches = re.findall(pattern, text)
        info['signatures'].extend(matches)
    
    # Extract key phrases (project document related)
    key_phrases = [
        'project document',
        'project description',
        'project agreement',
        'signed',
        'approved',
        'budget',
        'duration',
        'objectives',
    ]
    found_phrases = []
    for phrase in key_phrases:
        if phrase.lower() in text.lower():
            found_phrases.append(phrase)
    info['key_phrases'] = found_phrases
    
    # Try to extract project name (usually in first few lines)
    lines = text.split('\n')[:20]
    for line in lines:
        line = line.strip()
        if len(line) > 10 and len(line) < 200:
            # Check if it looks like a title/project name
            if any(word in line.lower() for word in ['project', 'programme', 'program']):
                info['project_name'] = line
                break
    
    return info


def save_extracted_text(text: str, output_path: Path) -> None:
    """
    Save extracted text to a file.
    
    Args:
        text: Extracted text
        output_path: Path to save text file
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"  ✓ Saved extracted text to: {output_path}")
    except Exception as e:
        print(f"  ✗ Error saving text: {e}")


def process_pdf(pdf_path: str, output_dir: Optional[str] = None, save_text: bool = True) -> None:
    """
    Process a PDF file and extract information.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save extracted text (optional)
        save_text: Whether to save extracted text to file
    """
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"Error: File not found: {pdf_path}")
        return
    
    print("=" * 60)
    print("PDF Text Extraction")
    print("=" * 60)
    
    # Check available libraries
    print("\nAvailable libraries:")
    print(f"  pdfplumber: {'✓' if PDFPLUMBER_AVAILABLE else '✗'}")
    print(f"  PyPDF2: {'✓' if PYPDF2_AVAILABLE else '✗'}")
    print(f"  OCR (pytesseract + pdf2image): {'✓' if OCR_AVAILABLE else '✗'}")
    
    if not any([PDFPLUMBER_AVAILABLE, PYPDF2_AVAILABLE, OCR_AVAILABLE]):
        print("\nError: No PDF extraction libraries available!")
        print("Please install one of:")
        print("  pip install pdfplumber")
        print("  pip install PyPDF2")
        print("  pip install pytesseract pdf2image")
        print("  (For OCR, also install Tesseract: https://github.com/tesseract-ocr/tesseract)")
        return
    
    # Extract text
    print()
    text = extract_text_from_pdf(pdf_file, use_ocr=True)
    
    if not text:
        print("\n✗ Could not extract text from PDF")
        return
    
    # Extract structured information
    print("\nExtracting structured information...")
    info = extract_structured_info(text)
    
    # Display results
    print("\n" + "=" * 60)
    print("Extracted Information")
    print("=" * 60)
    
    if info['project_id']:
        print(f"\nProject ID: {info['project_id']}")
    if info['project_name']:
        print(f"Project Name: {info['project_name']}")
    if info['date']:
        print(f"Date: {info['date']}")
    if info['signatures']:
        print(f"Signatures: {', '.join(info['signatures'])}")
    if info['key_phrases']:
        print(f"Key Phrases: {', '.join(info['key_phrases'])}")
    
    print(f"\nTotal characters extracted: {len(text)}")
    print(f"Total words: {len(text.split())}")
    
    # Show preview of text
    print("\n" + "=" * 60)
    print("Text Preview (first 500 characters)")
    print("=" * 60)
    print(text[:500])
    if len(text) > 500:
        print("...")
    
    # Save to file
    if save_text:
        if output_dir:
            output_path = Path(output_dir) / f"{pdf_file.stem}_extracted.txt"
        else:
            output_path = pdf_file.parent / f"{pdf_file.stem}_extracted.txt"
        
        save_extracted_text(text, output_path)
        
        # Also save structured info as JSON
        try:
            import json
            json_path = output_path.with_suffix('.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Saved structured info to: {json_path}")
        except Exception as e:
            print(f"  ⚠ Could not save JSON: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default: process the example file
        pdf_file = Path("project docs/100008_USINT11022_prodoc_signed.pdf")
        if pdf_file.exists():
            process_pdf(str(pdf_file))
        else:
            print("Usage: python extract_pdf.py <path_to_pdf>")
            print("Example: python extract_pdf.py 'project docs/100008_USINT11022_prodoc_signed.pdf'")
    else:
        pdf_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        process_pdf(pdf_path, output_dir)

