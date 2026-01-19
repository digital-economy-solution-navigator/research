"""
Script to find and remove duplicate files between project docs folder and scanned folder.
Files in the scanned folder take precedence - duplicates in the main folder will be deleted.

Configuration:
    FOLDER_SOURCE: Set to "local" or "cloud" to switch between folder locations.
                   - "local": uses "project docs" folder (relative to script)
                   - "cloud": uses {CLOUD_BASE_PATH}/project docs
    CLOUD_BASE_PATH: Base path for cloud folders (only used when FOLDER_SOURCE = "cloud")
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

# Configuration (same as download.py)
FOLDER_SOURCE = "cloud"  # Set to "local" or "cloud" to switch between folder locations

# Cloud base path (only used when FOLDER_SOURCE = "cloud")
CLOUD_BASE_PATH = r"C:\Users\hez\OneDrive - UNIDO\TCS\1. Expertise\research"  # Base path for cloud folders

# Get script directory for local paths
script_dir = Path(__file__).parent.absolute()

# Folder paths based on FOLDER_SOURCE
if FOLDER_SOURCE == "cloud":
    PROJECT_DOCS_FOLDER = Path(CLOUD_BASE_PATH) / "project docs"
else:  # local
    PROJECT_DOCS_FOLDER = script_dir / "project docs"

SCANNED_FOLDER = PROJECT_DOCS_FOLDER / "scanned"


def extract_project_id(filename: str) -> Optional[str]:
    """
    Extract project ID from filename.
    Files are typically named: {project_id}_{rest_of_name}.pdf
    
    Args:
        filename: Name of the file
    
    Returns:
        Project ID if found, None otherwise
    """
    # Try to extract project ID from the beginning of filename
    # Pattern: digits at the start, followed by underscore
    match = re.match(r'^(\d+)_', filename)
    if match:
        return match.group(1)
    return None


def find_duplicates(main_folder: Path, scanned_folder: Path) -> List[Tuple[Path, Path]]:
    """
    Find duplicate files between main folder and scanned folder.
    Files are considered duplicates if they have the same project ID.
    
    Args:
        main_folder: Main project docs folder
        scanned_folder: Scanned folder
    
    Returns:
        List of tuples (main_file_path, scanned_file_path) for duplicates
    """
    duplicates = []
    
    if not main_folder.exists():
        print(f"Error: Main folder not found: {main_folder}")
        return duplicates
    
    if not scanned_folder.exists():
        print(f"Info: Scanned folder not found: {scanned_folder}")
        print("No duplicates to check.")
        return duplicates
    
    # Get all PDF files in scanned folder and index by project ID
    scanned_files: Dict[str, Path] = {}
    for file in scanned_folder.glob("*.pdf"):
        project_id = extract_project_id(file.name)
        if project_id:
            # If multiple files with same project ID, keep the first one found
            if project_id not in scanned_files:
                scanned_files[project_id] = file
    
    print(f"Found {len(scanned_files)} unique project IDs in scanned folder")
    
    # Check main folder for files with matching project IDs
    main_files: Dict[str, Path] = {}
    for file in main_folder.glob("*.pdf"):
        project_id = extract_project_id(file.name)
        if project_id:
            main_files[project_id] = file
    
    print(f"Found {len(main_files)} unique project IDs in main folder")
    
    # Find duplicates (same project ID in both folders)
    for project_id, scanned_file in scanned_files.items():
        if project_id in main_files:
            duplicates.append((main_files[project_id], scanned_file))
    
    return duplicates


def remove_duplicates(dry_run: bool = False) -> None:
    """
    Find and remove duplicate files from main folder.
    
    Args:
        dry_run: If True, only show what would be deleted without actually deleting
    """
    print("=" * 60)
    print("Duplicate File Remover")
    print("=" * 60)
    print(f"\nMain folder: {PROJECT_DOCS_FOLDER}")
    print(f"Scanned folder: {SCANNED_FOLDER}")
    
    if dry_run:
        print("\n⚠ DRY RUN MODE - No files will be deleted")
    else:
        print("\n⚠ DELETION MODE - Files will be permanently deleted!")
    
    print("\n" + "=" * 60)
    print("Scanning for duplicates...")
    print("=" * 60)
    
    duplicates = find_duplicates(PROJECT_DOCS_FOLDER, SCANNED_FOLDER)
    
    if not duplicates:
        print("\n✓ No duplicates found!")
        return
    
    print(f"\nFound {len(duplicates)} duplicate file(s):\n")
    
    deleted_count = 0
    error_count = 0
    
    for main_file, scanned_file in duplicates:
        project_id = extract_project_id(main_file.name)
        print(f"Project {project_id}:")
        print(f"  Main:   {main_file.name}")
        print(f"  Scanned: {scanned_file.name}")
        
        if not dry_run:
            try:
                main_file.unlink()
                print(f"  ✓ Deleted: {main_file.name}")
                deleted_count += 1
            except Exception as e:
                print(f"  ✗ Error deleting {main_file.name}: {e}")
                error_count += 1
        else:
            print(f"  [Would delete: {main_file.name}]")
            deleted_count += 1
        print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    if dry_run:
        print(f"  Files that would be deleted: {deleted_count}")
        print(f"  Run without --dry-run flag to actually delete files")
    else:
        print(f"  Files deleted: {deleted_count}")
        if error_count > 0:
            print(f"  Errors: {error_count}")
    print("=" * 60)


if __name__ == "__main__":
    # Check for --dry-run flag (default is to delete)
    dry_run = False
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        dry_run = True
    
    remove_duplicates(dry_run=dry_run)

