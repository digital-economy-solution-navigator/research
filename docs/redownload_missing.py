"""Re-download missing project documents with valid URLs."""

import pandas as pd
from pathlib import Path
from download import (
    download_file,
    extract_filename_from_url,
    sanitize_filename,
    format_file_size,
    project_file_exists
)
from config import FOLDER_SOURCE, CLOUD_BASE_PATH
import os

# Constants
SCRIPT_DIR = Path(__file__).parent
PROJECT_DOCS_EXCEL = SCRIPT_DIR / "project_documents.xlsx"
DIAGNOSIS_FILE = SCRIPT_DIR / "missing_docs_diagnosis.txt"

# Output directory based on FOLDER_SOURCE
if FOLDER_SOURCE == "cloud":
    OUTPUT_DIR = Path(CLOUD_BASE_PATH) / "project docs"
else:
    OUTPUT_DIR = SCRIPT_DIR / "project docs"


def get_missing_project_ids():
    """Read missing project IDs from the diagnosis file."""
    missing_ids = []
    
    if not DIAGNOSIS_FILE.exists():
        print(f"Error: Diagnosis file not found: {DIAGNOSIS_FILE}")
        return missing_ids
    
    with open(DIAGNOSIS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        in_valid_section = False
        skip_next_separator = False
        for line in lines:
            if "Valid Url:" in line:
                in_valid_section = True
                skip_next_separator = True  # Skip the separator line right after "Valid Url:"
                continue
            if skip_next_separator and line.strip().startswith("-"):
                skip_next_separator = False
                continue  # Skip the first separator line
            if in_valid_section and line.strip().startswith("-"):
                break  # Stop at the second separator line (end of list)
            if in_valid_section and line.strip():
                # Extract project ID (may have leading spaces)
                pid = line.strip()
                if pid.isdigit():
                    missing_ids.append(pid)
    
    return missing_ids


def redownload_missing_projects():
    """Re-download missing project documents."""
    print("=" * 70)
    print("RE-DOWNLOADING MISSING PROJECT DOCUMENTS")
    print("=" * 70)
    
    # Get missing project IDs
    missing_ids = get_missing_project_ids()
    if not missing_ids:
        print("\nNo missing project IDs found in diagnosis file.")
        return
    
    print(f"\nFound {len(missing_ids)} missing projects to re-download")
    
    # Read project_documents.xlsx
    if not PROJECT_DOCS_EXCEL.exists():
        print(f"\nError: Project documents Excel file not found: {PROJECT_DOCS_EXCEL}")
        return
    
    print(f"\nReading {PROJECT_DOCS_EXCEL}...")
    try:
        df = pd.read_excel(PROJECT_DOCS_EXCEL)
        df['project_id'] = df['project_id'].astype(str)
        print(f"  ✓ Loaded {len(df)} document records")
    except Exception as e:
        print(f"  ✗ Error reading file: {e}")
        return
    
    # Validate required columns
    required_columns = ['project_id', 'document_name', 'url']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"  ✗ Error: Missing required columns: {', '.join(missing_columns)}")
        return
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {OUTPUT_DIR.absolute()}")
    
    # Process each missing project
    print(f"\n{'=' * 70}")
    print("Downloading missing project documents...")
    print(f"{'=' * 70}")
    
    downloaded_count = 0
    skipped_count = 0
    error_count = 0
    not_found_count = 0
    error_project_ids = []  # Track project IDs with errors
    
    for i, project_id in enumerate(missing_ids, 1):
        print(f"\n[{i}/{len(missing_ids)}] Project {project_id}:")
        
        # Find project in Excel
        project_rows = df[df['project_id'] == project_id]
        
        if len(project_rows) == 0:
            print(f"  ✗ Not found in project_documents.xlsx")
            not_found_count += 1
            error_project_ids.append(project_id)
            continue
        
        # Get the first document (or best one if multiple)
        if len(project_rows) > 1:
            print(f"  ⚠ Multiple documents found ({len(project_rows)}), using first one")
        
        doc = project_rows.iloc[0]
        doc_name = str(doc['document_name'])
        url = str(doc['url'])
        
        # Validate URL
        if not url or pd.isna(url) or not url.startswith(('http://', 'https://')):
            print(f"  ✗ Invalid URL: {url}")
            error_count += 1
            error_project_ids.append(project_id)
            continue
        
        # Check if file already exists
        existing_file = project_file_exists(project_id, OUTPUT_DIR)
        if existing_file:
            print(f"  ⊙ Already exists: {existing_file.name}")
            skipped_count += 1
            continue
        
        # Prepare filename
        # Extract filename from URL if document_name doesn't have extension
        if '.' not in doc_name.split()[-1]:
            filename_from_url = extract_filename_from_url(url)
            if filename_from_url and filename_from_url != 'download.pdf':
                doc_name = filename_from_url
        
        # Create final filename: {project_id}_{document_name}.pdf
        doc_name_base = os.path.splitext(doc_name)[0]
        filename = f"{project_id}_{sanitize_filename(doc_name_base)}.pdf"
        filepath = OUTPUT_DIR / filename
        
        # Download
        print(f"  Document: '{doc_name}'")
        print(f"  URL: {url[:80]}...")
        success = download_file(url, filepath)
        
        if success:
            file_size = filepath.stat().st_size
            print(f"  ✓ Downloaded: {filename} ({format_file_size(file_size)})")
            downloaded_count += 1
        else:
            error_count += 1
            error_project_ids.append(project_id)
    
    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total missing projects: {len(missing_ids)}")
    print(f"  Successfully downloaded: {downloaded_count}")
    print(f"  Skipped (already exists): {skipped_count}")
    print(f"  Not found in Excel: {not_found_count}")
    print(f"  Errors: {error_count}")
    print(f"  Output directory: {OUTPUT_DIR.absolute()}")
    print(f"{'=' * 70}")
    
    # Display error project IDs
    if error_project_ids:
        print(f"\n{'=' * 70}")
        print(f"PROJECT IDs WITH ERRORS ({len(error_project_ids)}):")
        print(f"{'=' * 70}")
        # Sort numerically
        sorted_error_ids = sorted(error_project_ids, key=lambda x: int(x) if x.isdigit() else 0)
        for i, pid in enumerate(sorted_error_ids, 1):
            print(f"  {i:3d}. {pid}")
        print(f"{'=' * 70}")
        
        # Save to file
        error_file = SCRIPT_DIR / "failed_downloads.txt"
        with open(error_file, 'w', encoding='utf-8') as f:
            for pid in sorted_error_ids:
                f.write(f"{pid}\n")
        print(f"\nFailed project IDs saved to: {error_file}")


if __name__ == "__main__":
    redownload_missing_projects()

