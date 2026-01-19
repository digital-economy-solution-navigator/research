"""
Script to extract text from PDF files, including scanned PDFs using OCR.
For normal PDFs: extracts structured text directly.
For scanned PDFs: can use OCR or move them to a "scanned" folder.

Configuration:
    See config.py for FOLDER_SOURCE, CLOUD_BASE_PATH, and USE_OCR_FOR_SCANNED settings.
    - "local": uses "project docs" folder
    - "cloud": uses cloud folder paths (constructed from CLOUD_BASE_PATH)
    You can still override by providing a path as command-line argument.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import re
from config import FOLDER_SOURCE, CLOUD_BASE_PATH, USE_OCR_FOR_SCANNED

# Try to import PDF text extraction libraries
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

# Folder paths based on FOLDER_SOURCE
if FOLDER_SOURCE == "cloud":
    # Construct paths from base path
    DEFAULT_PDF_FOLDER = str(Path(CLOUD_BASE_PATH) / "project docs")
    DEFAULT_TEXT_FOLDER = str(Path(CLOUD_BASE_PATH) / "text")
else:  # local
    DEFAULT_PDF_FOLDER = "project docs"
    DEFAULT_TEXT_FOLDER = None  # Will use script_dir / "text" for local

# Global list to track scanned PDFs (store full paths)
SCANNED_PDFS: List[Path] = []


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


def is_scanned_pdf(text: Optional[str], min_text_threshold: int = 50) -> bool:
    """
    Determine if PDF is likely scanned (image-based) based on extracted text.
    
    Args:
        text: Extracted text from PDF
        min_text_threshold: Minimum characters to consider it a normal PDF
    
    Returns:
        True if PDF appears to be scanned, False otherwise
    """
    if not text:
        return True
    
    # Remove whitespace and check length
    clean_text = text.strip()
    if len(clean_text) < min_text_threshold:
        return True
    
    # Check if text looks like OCR output (many single characters, poor formatting)
    # This is a heuristic - OCR often produces fragmented text
    words = clean_text.split()
    if len(words) < 10:  # Very few words suggests scanned
        return True
    
    # Check character-to-word ratio (OCR often has spacing issues)
    if len(clean_text) / max(len(words), 1) < 3:  # Average word length very short
        return True
    
    return False


def extract_text_from_pdf(pdf_path: Path, use_ocr: bool = True) -> Tuple[Optional[str], bool]:
    """
    Extract text from PDF file, trying multiple methods.
    
    Args:
        pdf_path: Path to PDF file
        use_ocr: Whether to use OCR for scanned PDFs
    
    Returns:
        Tuple of (extracted text or None, is_scanned: bool)
    
    Args:
        pdf_path: Path to PDF file
        use_ocr: Whether to use OCR for scanned PDFs
    
    Returns:
        Tuple of (extracted text or None, is_scanned: bool)
    """
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        return None, False
    
    print(f"Extracting text from: {pdf_path.name}")
    
    # Try pdfplumber first (fastest, works for text-based PDFs)
    if PDFPLUMBER_AVAILABLE:
        print("  Trying pdfplumber...")
        text = extract_text_with_pdfplumber(pdf_path)
        if text and len(text.strip()) > 50:
            # Check if it's a scanned PDF
            if not is_scanned_pdf(text):
                print(f"  ✓ Extracted {len(text)} characters using pdfplumber (normal PDF)")
                return text, False
            else:
                print(f"  ⚠ Minimal text extracted, likely scanned PDF")
                # Continue to try other methods or OCR
        elif text:
            print(f"  ⚠ Minimal text extracted, likely scanned PDF")
    
    # Try PyPDF2 as fallback
    if PYPDF2_AVAILABLE:
        print("  Trying PyPDF2...")
        text = extract_text_with_pypdf2(pdf_path)
        if text and len(text.strip()) > 50:
            if not is_scanned_pdf(text):
                print(f"  ✓ Extracted {len(text)} characters using PyPDF2 (normal PDF)")
                return text, False
            else:
                print(f"  ⚠ Minimal text extracted, likely scanned PDF")
    
    # If no text extracted or minimal text, try OCR (for scanned PDFs)
    if use_ocr and OCR_AVAILABLE:
        print("  No substantial text found, trying OCR...")
        text = extract_text_with_ocr(pdf_path)
        if text and len(text.strip()) > 50:
            print(f"  ✓ Extracted {len(text)} characters using OCR")
            return text, False  # OCR succeeded, so not "scanned" in the sense of needing to move
    
    # If OCR is disabled or failed, mark as scanned
    print("  ✗ Could not extract substantial text from PDF")
    return None, True


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


def move_scanned_pdfs(scanned_pdfs: List[Path], scanned_folder: Path) -> None:
    """
    Move scanned PDFs to a scanned folder.
    
    Args:
        scanned_pdfs: List of scanned PDF file paths
        scanned_folder: Path to the scanned folder where PDFs should be moved
    """
    if not scanned_pdfs:
        return
    
    try:
        # Create scanned folder if it doesn't exist
        scanned_folder.mkdir(parents=True, exist_ok=True)
        
        moved_count = 0
        for pdf_path in scanned_pdfs:
            if not pdf_path.exists():
                print(f"  ⚠ PDF not found, skipping: {pdf_path.name}")
                continue
            
            # Destination path in scanned folder
            dest_path = scanned_folder / pdf_path.name
            
            # If file with same name exists, add a number suffix
            if dest_path.exists():
                base_name = pdf_path.stem
                extension = pdf_path.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = scanned_folder / f"{base_name}_{counter}{extension}"
                    counter += 1
            
            # Move the file
            pdf_path.rename(dest_path)
            print(f"  ✓ Moved {pdf_path.name} to {scanned_folder}")
            moved_count += 1
        
        print(f"\n✓ Moved {moved_count} scanned PDF(s) to: {scanned_folder}")
    except Exception as e:
        print(f"  ✗ Error moving scanned PDFs: {e}")


def process_pdf(pdf_path: str, output_dir: Optional[str] = None, save_text: bool = True) -> None:
    """
    Process a PDF file and extract information.
    For normal PDFs: extracts structured text.
    For scanned PDFs: uses OCR if enabled, otherwise adds to list for moving.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save extracted text (optional)
        save_text: Whether to save extracted text to file
    """
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"Error: File not found: {pdf_path}")
        return
    
    # Check if already processed (txt file exists in text folder)
    script_dir = Path(__file__).parent.absolute()
    if output_dir:
        text_dir = Path(output_dir)
        if not text_dir.is_absolute():
            text_dir = script_dir / text_dir
    else:
        # Use cloud text folder if configured, otherwise use local text folder
        if FOLDER_SOURCE == "cloud" and DEFAULT_TEXT_FOLDER:
            text_dir = Path(DEFAULT_TEXT_FOLDER)
        else:
            text_dir = script_dir / "text"
    
    # Check if extracted text file already exists
    text_output_path = text_dir / f"{pdf_file.stem}.txt"
    if text_output_path.exists():
        print(f"⏭ Skipping {pdf_file.name} - already processed (txt file exists)")
        return
    
    print("=" * 60)
    print("PDF Text Extraction")
    print("=" * 60)
    
    # Check available libraries
    print("\nAvailable libraries:")
    print(f"  pdfplumber: {'✓' if PDFPLUMBER_AVAILABLE else '✗'}")
    print(f"  PyPDF2: {'✓' if PYPDF2_AVAILABLE else '✗'}")
    print(f"  OCR (pytesseract + pdf2image): {'✓' if OCR_AVAILABLE else '✗'}")
    
    if not any([PDFPLUMBER_AVAILABLE, PYPDF2_AVAILABLE]):
        print("\nError: No PDF extraction libraries available!")
        print("Please install: pip install pdfplumber")
        if not OCR_AVAILABLE:
            print("  (Optional) For OCR support: pip install pytesseract pdf2image")
            print("  (Also install Tesseract: https://github.com/tesseract-ocr/tesseract)")
        return
    
    # Extract text
    print()
    use_ocr = USE_OCR_FOR_SCANNED and OCR_AVAILABLE
    text, is_scanned = extract_text_from_pdf(pdf_file, use_ocr=use_ocr)
    
    # Handle scanned PDFs
    if is_scanned or not text:
        if USE_OCR_FOR_SCANNED and OCR_AVAILABLE:
            # OCR was attempted but failed
            print(f"\n📄 Scanned PDF detected: {pdf_file.name}")
            print(f"  OCR extraction failed or disabled")
        else:
            print(f"\n📄 Scanned PDF detected: {pdf_file.name}")
        
        # Add to list for moving later (if OCR is disabled or failed)
        if not USE_OCR_FOR_SCANNED or not text:
            global SCANNED_PDFS
            SCANNED_PDFS.append(pdf_file)
            print(f"  Added to scanned PDFs list (will be moved to scanned folder)")
            return
        else:
            # OCR succeeded, continue processing
            pass
    
    # Handle normal PDFs or OCR-extracted PDFs - extract structured information
    if text:
        print("\n📝 Extracting structured information...")
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
        # Get script directory for default paths
        script_dir = Path(__file__).parent.absolute()
        
        # Determine text folder location
        if output_dir:
            text_dir = Path(output_dir)
            if not text_dir.is_absolute():
                text_dir = script_dir / text_dir
        else:
            # Use cloud text folder if configured, otherwise use local text folder
            if FOLDER_SOURCE == "cloud" and DEFAULT_TEXT_FOLDER:
                text_dir = Path(DEFAULT_TEXT_FOLDER)
            else:
                text_dir = script_dir / "text"
        
        # Save extracted text to text folder
        text_output_path = text_dir / f"{pdf_file.stem}.txt"
        save_extracted_text(text, text_output_path)
        
        # Also save structured info as JSON
        try:
            import json
            json_path = text_output_path.with_suffix('.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Saved structured info to: {json_path}")
        except Exception as e:
            print(f"  ⚠ Could not save JSON: {e}")


if __name__ == "__main__":
    # Reset scanned PDFs list
    SCANNED_PDFS.clear()
    
    # Get the script's directory to resolve relative paths
    script_dir = Path(__file__).parent.absolute()
    output_dir = None  # Initialize output_dir
    processing_folder = None  # Track where PDFs are being processed from
    
    if len(sys.argv) < 2:
        # Default: process all PDFs in the configured folder
        default_folder = Path(DEFAULT_PDF_FOLDER)
        if default_folder.is_absolute():
            input_path = default_folder
        else:
            input_path = script_dir / default_folder
        
        if not input_path.exists():
            print(f"Error: Default folder not found: {input_path}")
            print(f"Please update DEFAULT_PDF_FOLDER in the script or provide a folder path as argument")
            print("\nUsage: python extract_pdf.py [path_to_pdf_or_folder] [output_dir]")
            print(f"       Default folder: {DEFAULT_PDF_FOLDER}")
            sys.exit(1)
        
        if not input_path.is_dir():
            print(f"Error: Default path is not a directory: {input_path}")
            sys.exit(1)
        
        # Process all PDFs in the configured folder
        processing_folder = input_path
        pdf_files = list(input_path.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in: {input_path}")
            sys.exit(1)
        
        print(f"Processing {len(pdf_files)} PDF file(s) from: {DEFAULT_PDF_FOLDER}\n")
        for pdf_file in pdf_files:
            process_pdf(str(pdf_file), output_dir)
            print()  # Add spacing between files
    else:
        input_path = Path(sys.argv[1])
        # If path is relative, make it relative to script directory
        if not input_path.is_absolute():
            input_path = script_dir / input_path
        
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        if output_dir and not Path(output_dir).is_absolute():
            output_dir = str(script_dir / output_dir)
        
        # Check if input is a directory or a file
        if input_path.is_dir():
            # Processing folder is the input directory
            processing_folder = input_path
            # Process all PDFs in directory
            pdf_files = list(input_path.glob("*.pdf"))
            if not pdf_files:
                print(f"No PDF files found in: {input_path}")
                sys.exit(1)
            
            print(f"Found {len(pdf_files)} PDF file(s) to process\n")
            for pdf_file in pdf_files:
                process_pdf(str(pdf_file), output_dir)
                print()  # Add spacing between files
        elif input_path.is_file():
            # Processing folder is the parent directory of the file
            processing_folder = input_path.parent
            # Process single file
            process_pdf(str(input_path), output_dir)
        else:
            print(f"Error: Path not found: {input_path}")
            sys.exit(1)
    
    # Move scanned PDFs to scanned folder if any were found
    if SCANNED_PDFS:
        if processing_folder is None:
            # Fallback to script directory
            processing_folder = script_dir
        
        # Create scanned folder under processing folder
        scanned_folder = processing_folder / "scanned"
        
        print("\n" + "=" * 60)
        print("Moving Scanned PDFs")
        print("=" * 60)
        move_scanned_pdfs(SCANNED_PDFS, scanned_folder)
    else:
        print("\n✓ No scanned PDFs detected - all PDFs had extractable text")

