"""
Script to download project documents from UNIDO Compass.
Analyzes document names and URLs to identify the most likely project document for each project.

Configuration:
    FOLDER_SOURCE: Set to "local" or "cloud" to switch between folder locations.
                   - "local": downloads to "project docs" folder (relative to script)
                   - "cloud": downloads to {CLOUD_BASE_PATH}/project docs
    CLOUD_BASE_PATH: Base path for cloud folders (only used when FOLDER_SOURCE = "cloud")
"""

import requests
import pandas as pd
import re
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse
from collections import Counter

# Configuration
FOLDER_SOURCE = "cloud"  # Set to "local" or "cloud" to switch between folder locations

# Cloud base path (only used when FOLDER_SOURCE = "cloud")
CLOUD_BASE_PATH = r"C:\Users\hez\OneDrive - UNIDO\TCS\research"  # Base path for cloud folders

# Constants
CHUNK_SIZE = 8192
KB_SIZE = 1024
REQUEST_TIMEOUT = 30
EXCEL_FILE = 'project_documents.xlsx'

# Output directory based on FOLDER_SOURCE
if FOLDER_SOURCE == "cloud":
    # Construct path from base path
    OUTPUT_DIR = str(Path(CLOUD_BASE_PATH) / "project docs")
else:  # local
    OUTPUT_DIR = "project docs"


def extract_filename_from_url(url: str) -> str:
    """
    Extract filename from URL, removing query parameters.
    
    Args:
        url: URL to extract filename from
    
    Returns:
        Extracted filename or 'download.pdf' if not found
    """
    if not url or pd.isna(url):
        return 'download.pdf'
    
    parsed = urlparse(str(url))
    filename = os.path.basename(parsed.path)
    if not filename or '.' not in filename:
        filename = 'download.pdf'
    return filename


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string (KB or MB)
    """
    if size_bytes < KB_SIZE:
        return f"{size_bytes} B"
    elif size_bytes < KB_SIZE * KB_SIZE:
        return f"{size_bytes / KB_SIZE:.2f} KB"
    else:
        return f"{size_bytes / (KB_SIZE * KB_SIZE):.2f} MB"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to remove invalid characters for Windows/Unix.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    return filename


def analyze_document_patterns(df: pd.DataFrame) -> Dict[str, int]:
    """
    Analyze document names to learn patterns and identify keywords that indicate project documents.
    
    Args:
        df: DataFrame with document_name and url columns
    
    Returns:
        Dictionary of keyword scores (higher = more likely to be project document)
    """
    print("Analyzing document patterns...")
    
    # Keywords that indicate project documents (positive indicators)
    positive_keywords = {
        'project document': 10,
        'project doc': 9,
        'signed': 8,
        'project agreement': 9,
        'project description': 7,
        'project proposal': 7,
        'project document signed': 11,
        'signed project': 9,
        'final': 6,
        'approved': 6,
        'agreement': 7,
        'contract': 6,
        'project': 5,
    }
    
    # Keywords that indicate non-project documents (negative indicators)
    negative_keywords = {
        'photo': -10,
        'image': -10,
        'picture': -10,
        'logo': -10,
        'thumbnail': -10,
        'icon': -10,
        'summary': -5,
        'brief': -5,
        'newsletter': -8,
        'news': -8,
        'announcement': -7,
        'press release': -8,
        'presentation': -4,
        'ppt': -4,
        'powerpoint': -4,
        'excel': -4,
        'xlsx': -4,
        'xls': -4,
        'spreadsheet': -4,
    }
    
    # Count keyword occurrences in document names
    all_text = ' '.join(df['document_name'].astype(str).str.lower().tolist())
    all_text += ' ' + ' '.join(df['url'].astype(str).str.lower().tolist())
    
    # Learn from the data: count occurrences of common patterns
    keyword_scores = positive_keywords.copy()
    
    # Analyze common patterns in document names
    doc_names = df['document_name'].astype(str).str.lower()
    url_texts = df['url'].astype(str).str.lower()
    
    # Find patterns that appear frequently (likely project documents)
    common_words = Counter()
    for text in list(doc_names) + list(url_texts):
        words = re.findall(r'\b\w+\b', text.lower())
        common_words.update(words)
    
    # Boost scores for frequently occurring positive keywords
    for keyword, base_score in positive_keywords.items():
        if keyword in all_text:
            count = all_text.count(keyword)
            # Boost score based on frequency (but cap it)
            keyword_scores[keyword] = min(base_score + min(count // 10, 5), 15)
    
    # Combine positive and negative keywords
    all_keywords = {**keyword_scores, **negative_keywords}
    
    print(f"  Analyzed {len(df)} documents")
    print(f"  Identified {len(all_keywords)} keyword patterns")
    
    return all_keywords


def score_document(row: pd.Series, keyword_scores: Dict[str, int]) -> int:
    """
    Score a document based on its name and URL to determine if it's likely a project document.
    
    Args:
        row: DataFrame row with document_name and url
        keyword_scores: Dictionary of keyword scores
    
    Returns:
        Score (higher = more likely to be project document)
    """
    score = 0
    
    doc_name = str(row.get('document_name', '')).lower()
    url = str(row.get('url', '')).lower()
    combined_text = f"{doc_name} {url}"
    
    # Check for keywords
    for keyword, keyword_score in keyword_scores.items():
        if keyword in combined_text:
            score += keyword_score
    
    # Bonus for PDF files (project documents are usually PDFs)
    if '.pdf' in url or '.pdf' in doc_name:
        score += 3
    
    # Penalty for very short names (likely not project documents)
    if len(doc_name) < 10:
        score -= 2
    
    # Bonus for longer, descriptive names
    if len(doc_name) > 30:
        score += 2
    
    # Check for project ID in name/URL (strong indicator)
    project_id = str(row.get('project_id', ''))
    if project_id and project_id in combined_text:
        score += 5
    
    return score


def select_best_document(project_docs: pd.DataFrame, keyword_scores: Dict[str, int]) -> Optional[pd.Series]:
    """
    Select the best project document from multiple options for a project.
    
    Args:
        project_docs: DataFrame with documents for a single project
        keyword_scores: Dictionary of keyword scores
    
    Returns:
        Best document row, or None if no documents
    """
    if len(project_docs) == 0:
        return None
    
    if len(project_docs) == 1:
        return project_docs.iloc[0]
    
    # Score each document
    project_docs = project_docs.copy()
    project_docs['_score'] = project_docs.apply(
        lambda row: score_document(row, keyword_scores), axis=1
    )
    
    # Select the document with the highest score
    best_doc = project_docs.loc[project_docs['_score'].idxmax()]
    
    return best_doc


def project_file_exists(project_id: str, output_path: Path) -> Optional[Path]:
    """
    Check if any file with the project ID already exists in the output folder or scanned folder.
    
    Args:
        project_id: Project ID to search for
        output_path: Directory to search in
    
    Returns:
        Path to existing file if found, None otherwise
    """
    if not output_path.exists():
        return None
    
    # Look for any file that starts with the project_id
    pattern = f"{project_id}_*"
    
    # Check in the main output folder
    matching_files = list(output_path.glob(pattern))
    if matching_files:
        # Return the first matching file
        return matching_files[0]
    
    # Also check in the scanned folder
    scanned_folder = output_path / "scanned"
    if scanned_folder.exists():
        matching_files = list(scanned_folder.glob(pattern))
        if matching_files:
            # Return the first matching file from scanned folder
            return matching_files[0]
    
    return None


def download_file(url: str, filepath: Path) -> bool:
    """
    Download a file from a URL and save it.
    
    Args:
        url: URL of the file to download
        filepath: Path where to save the file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not url or pd.isna(url) or not str(url).startswith(('http://', 'https://')):
            print(f"  ✗ Invalid URL: {url}")
            return False
        
        response = requests.get(str(url), stream=True, verify=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        downloaded = 0
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r  Progress: {percent:.1f}%", end='', flush=True)
        
        print()  # New line after progress
        
        if filepath.exists() and filepath.stat().st_size > 0:
            return True
        else:
            print(f"  ✗ File was not saved successfully")
            return False
            
    except requests.exceptions.Timeout:
        print(f"  ✗ Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error downloading: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def process_project_documents(excel_file: str = EXCEL_FILE) -> None:
    """
    Main function to process project documents: analyze, select best, and download.
    
    Args:
        excel_file: Path to Excel file with project documents
    """
    print("=" * 60)
    print("Project Document Downloader")
    print("=" * 60)
    
    # Read Excel file
    print(f"\nReading Excel file: {excel_file}")
    try:
        df = pd.read_excel(excel_file)
        print(f"  ✓ Loaded {len(df)} document records")
        print(f"  Columns: {', '.join(df.columns.tolist())}")
    except FileNotFoundError:
        print(f"  ✗ Error: File '{excel_file}' not found")
        return
    except Exception as e:
        print(f"  ✗ Error reading file: {e}")
        return
    
    # Validate required columns
    required_columns = ['project_id', 'document_name', 'url']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"  ✗ Error: Missing required columns: {', '.join(missing_columns)}")
        return
    
    # Analyze document patterns
    keyword_scores = analyze_document_patterns(df)
    
    # Group by project_id
    print(f"\nProcessing projects...")
    projects = df.groupby('project_id')
    total_projects = len(projects)
    projects_with_multiple = sum(1 for _, group in projects if len(group) > 1)
    
    print(f"  Total projects: {total_projects}")
    print(f"  Projects with multiple documents: {projects_with_multiple}")
    print(f"  Projects with single document: {total_projects - projects_with_multiple}")
    
    # Create output directory
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)
    print(f"\nOutput directory: {output_path.absolute()}")
    
    # Process each project
    print(f"\n{'=' * 60}")
    print("Downloading project documents...")
    print(f"{'=' * 60}")
    
    downloaded_count = 0
    skipped_count = 0
    error_count = 0
    
    for project_id, project_docs in projects:
        print(f"\nProject {project_id} ({len(project_docs)} document(s)):")
        
        # Select best document
        if len(project_docs) > 1:
            best_doc = select_best_document(project_docs, keyword_scores)
            if best_doc is not None:
                score = score_document(best_doc, keyword_scores)
                print(f"  Selected: '{best_doc['document_name']}' (score: {score})")
                if len(project_docs) > 1:
                    print(f"  Other options: {len(project_docs) - 1} document(s) not selected")
        else:
            best_doc = project_docs.iloc[0]
            print(f"  Document: '{best_doc['document_name']}'")
        
        if best_doc is None:
            print(f"  ⚠ No document selected")
            skipped_count += 1
            continue
        
        # Prepare filename
        doc_name = str(best_doc['document_name'])
        url = str(best_doc['url'])
        
        # Extract filename from URL if document_name doesn't have extension
        if '.' not in doc_name.split()[-1]:
            filename_from_url = extract_filename_from_url(url)
            if filename_from_url and filename_from_url != 'download.pdf':
                doc_name = filename_from_url
        
        # Check if any file with this project ID already exists
        existing_file = project_file_exists(str(project_id), output_path)
        if existing_file:
            print(f"  ⊙ Already exists: {existing_file.name} (project {project_id})")
            skipped_count += 1
            continue
        
        # Create final filename: {project_id}_{document_name}.pdf
        # Remove extension if present and add .pdf
        doc_name_base = os.path.splitext(doc_name)[0]
        filename = f"{project_id}_{sanitize_filename(doc_name_base)}.pdf"
        filepath = output_path / filename
        
        # Download
        print(f"  Downloading: {url[:80]}...")
        success = download_file(url, filepath)
        
        if success:
            file_size = filepath.stat().st_size
            print(f"  ✓ Downloaded: {filename} ({format_file_size(file_size)})")
            downloaded_count += 1
        else:
            error_count += 1
    
    # Summary
    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    print(f"  Total projects processed: {total_projects}")
    print(f"  Successfully downloaded: {downloaded_count}")
    print(f"  Skipped (already exists): {skipped_count}")
    print(f"  Errors: {error_count}")
    print(f"  Output directory: {output_path.absolute()}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    process_project_documents()
