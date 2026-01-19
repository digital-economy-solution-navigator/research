"""Download project documents from missing_project_url_update.txt."""

import re
from pathlib import Path
from urllib.parse import unquote
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
UPDATE_FILE = SCRIPT_DIR / "missing_project_url_update.txt"

# Output directory based on FOLDER_SOURCE
if FOLDER_SOURCE == "cloud":
    OUTPUT_DIR = Path(CLOUD_BASE_PATH) / "project docs"
else:
    OUTPUT_DIR = SCRIPT_DIR / "project docs"


def parse_update_file():
    """Parse the update file to extract project IDs and URLs."""
    project_urls = []
    
    if not UPDATE_FILE.exists():
        print(f"Error: Update file not found: {UPDATE_FILE}")
        return project_urls
    
    with open(UPDATE_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Format: "1. 101000 https://..."
            # Match: number. project_id url
            match = re.match(r'^\d+\.\s+(\d+)\s+(https?://.+)', line)
            if match:
                project_id = match.group(1)
                url = match.group(2).strip()
                project_urls.append((project_id, url))
            else:
                print(f"Warning: Could not parse line: {line}")
    
    return project_urls


def download_from_update_file():
    """Download project documents from the update file."""
    print("=" * 70)
    print("DOWNLOADING PROJECT DOCUMENTS FROM UPDATE FILE")
    print("=" * 70)
    
    # Parse update file
    project_urls = parse_update_file()
    if not project_urls:
        print("\nNo project URLs found in update file.")
        return
    
    print(f"\nFound {len(project_urls)} projects to download")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {OUTPUT_DIR.absolute()}")
    
    # Process each project
    print(f"\n{'=' * 70}")
    print("Downloading project documents...")
    print(f"{'=' * 70}")
    
    downloaded_count = 0
    skipped_count = 0
    error_count = 0
    error_project_ids = []
    
    for i, (project_id, url) in enumerate(project_urls, 1):
        print(f"\n[{i}/{len(project_urls)}] Project {project_id}:")
        
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
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
        
        # Extract filename from URL
        filename_from_url = extract_filename_from_url(url)
        if not filename_from_url or filename_from_url == 'download.pdf':
            # Try to extract from URL path
            try:
                # Decode URL-encoded filename
                decoded_url = unquote(url)
                # Extract filename from path
                url_path = decoded_url.split('/')[-1]
                if url_path and '.' in url_path:
                    filename_from_url = url_path
                else:
                    filename_from_url = f"document_{project_id}.pdf"
            except:
                filename_from_url = f"document_{project_id}.pdf"
        
        # Create final filename: {project_id}_{document_name}.pdf
        doc_name_base = os.path.splitext(filename_from_url)[0]
        filename = f"{project_id}_{sanitize_filename(doc_name_base)}.pdf"
        filepath = OUTPUT_DIR / filename
        
        # Download
        print(f"  URL: {url[:80]}...")
        print(f"  Target: {filename}")
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
    print(f"  Total projects: {len(project_urls)}")
    print(f"  Successfully downloaded: {downloaded_count}")
    print(f"  Skipped (already exists): {skipped_count}")
    print(f"  Errors: {error_count}")
    print(f"  Output directory: {OUTPUT_DIR.absolute()}")
    print(f"{'=' * 70}")
    
    # Display error project IDs
    if error_project_ids:
        print(f"\n{'=' * 70}")
        print(f"PROJECT IDs WITH ERRORS ({len(error_project_ids)}):")
        print(f"{'=' * 70}")
        sorted_error_ids = sorted(error_project_ids, key=lambda x: int(x) if x.isdigit() else 0)
        for i, pid in enumerate(sorted_error_ids, 1):
            print(f"  {i:3d}. {pid}")
        print(f"{'=' * 70}")
        
        # Save to file
        error_file = SCRIPT_DIR / "update_download_errors.txt"
        with open(error_file, 'w', encoding='utf-8') as f:
            for pid in sorted_error_ids:
                f.write(f"{pid}\n")
        print(f"\nFailed project IDs saved to: {error_file}")


if __name__ == "__main__":
    download_from_update_file()

