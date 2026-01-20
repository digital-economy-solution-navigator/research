#!/usr/bin/env python3
"""
Organize irrelevant project files into separate folders.

This script:
1. Reads managers_projects.xlsx to identify relevant project IDs (where doc = "yes")
2. Moves files that don't match relevant project IDs to "irrelevant" folders in:
   - docs/text/irrelevant/ (for .txt files)
   - docs/project docs/irrelevant/ (for .pdf files)

Only files matching relevant project IDs (1928 projects) are kept in the main folders.
"""

import pandas as pd
import re
from pathlib import Path
import sys
import shutil

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent))
from config import FOLDER_SOURCE, CLOUD_BASE_PATH


def extract_project_id(filename):
    """
    Extract project ID from filename.
    Files are typically named: {project_id}_{rest_of_name}.txt or .pdf
    """
    if isinstance(filename, Path):
        basename = filename.name
    else:
        basename = Path(filename).name
    
    # Try to extract project ID from the beginning of filename (format: {project_id}_{rest})
    match = re.match(r'^(\d+)_', basename)
    if match:
        return match.group(1)
    
    # Fallback: try to extract numeric ID at the beginning (without underscore)
    match = re.match(r'^(\d+)', basename)
    if match:
        return match.group(1)
    
    # Last resort: try to find any numeric sequence in the filename
    match = re.search(r'(\d{5,})', basename)
    if match:
        return match.group(1)
    
    return None


def get_relevant_project_ids(excel_file: Path) -> set:
    """
    Read managers_projects.xlsx and return set of project IDs where doc = "yes".
    
    Returns:
        Set of relevant project IDs as strings
    """
    try:
        df = pd.read_excel(excel_file)
        
        # Check if 'doc' column exists
        if 'doc' not in df.columns:
            print(f"Error: 'doc' column not found in {excel_file}")
            print(f"Available columns: {list(df.columns)}")
            return set()
        
        # Check if 'id' or 'project_id' column exists
        id_column = None
        for col in ['id', 'project_id', 'ID', 'Project ID']:
            if col in df.columns:
                id_column = col
                break
        
        if id_column is None:
            print(f"Error: No project ID column found in {excel_file}")
            print(f"Available columns: {list(df.columns)}")
            return set()
        
        # Filter rows where doc = "yes" (case-insensitive)
        relevant_df = df[df['doc'].astype(str).str.lower().str.strip() == 'yes']
        
        # Extract project IDs
        project_ids = relevant_df[id_column].astype(str).str.strip()
        relevant_ids = set(project_ids.dropna().unique())
        
        print(f"Found {len(relevant_ids)} relevant project IDs (doc = 'yes')")
        print(f"Total rows in Excel: {len(df)}")
        print(f"Rows with doc = 'yes': {len(relevant_df)}")
        
        return relevant_ids
    
    except Exception as e:
        print(f"Error reading Excel file {excel_file}: {e}")
        return set()


def organize_files(source_dir: Path, irrelevant_dir: Path, relevant_ids: set, file_ext: str, recursive: bool = False):
    """
    Move files that don't match relevant project IDs to irrelevant folder.
    
    Args:
        source_dir: Directory containing files to check
        irrelevant_dir: Directory to move irrelevant files to
        relevant_ids: Set of relevant project IDs
        file_ext: File extension to process (e.g., '.txt', '.pdf')
        recursive: If True, also process files in subdirectories
    """
    if not source_dir.exists():
        print(f"Warning: Source directory does not exist: {source_dir}")
        return 0, 0
    
    # Create irrelevant directory if it doesn't exist
    irrelevant_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all files with the specified extension
    if recursive:
        # Use ** to search recursively in all subdirectories
        files = list(source_dir.glob(f'**/*{file_ext}'))
        # Exclude files already in irrelevant folder
        files = [f for f in files if 'irrelevant' not in f.parts]
    else:
        # Only search in root directory
        files = list(source_dir.glob(f'*{file_ext}'))
    
    moved_count = 0
    kept_count = 0
    
    for filepath in files:
        project_id = extract_project_id(filepath)
        
        if project_id is None:
            print(f"  ⚠ Could not extract project ID from: {filepath.relative_to(source_dir)}")
            # Move files without extractable project IDs to irrelevant
            try:
                dest = irrelevant_dir / filepath.name
                # Handle name conflicts
                if dest.exists():
                    dest = irrelevant_dir / f"{filepath.stem}_{filepath.parent.name}{filepath.suffix}"
                shutil.move(str(filepath), str(dest))
                moved_count += 1
            except Exception as e:
                print(f"    ✗ Error moving file: {e}")
            continue
        
        if project_id not in relevant_ids:
            # Move to irrelevant folder
            try:
                dest = irrelevant_dir / filepath.name
                # Handle name conflicts (e.g., if same filename exists in root and scanned)
                if dest.exists():
                    # Add subdirectory name to avoid conflicts
                    rel_path = filepath.relative_to(source_dir)
                    if len(rel_path.parts) > 1:
                        # File is in a subdirectory
                        dest = irrelevant_dir / f"{filepath.stem}_{rel_path.parts[0]}{filepath.suffix}"
                    else:
                        dest = irrelevant_dir / f"{filepath.stem}_duplicate{filepath.suffix}"
                
                shutil.move(str(filepath), str(dest))
                moved_count += 1
                if moved_count <= 10:  # Show first 10 moves
                    rel_display = filepath.relative_to(source_dir)
                    print(f"  → Moved: {rel_display} (project ID: {project_id})")
            except Exception as e:
                print(f"    ✗ Error moving {filepath.name}: {e}")
        else:
            kept_count += 1
    
    return moved_count, kept_count


def main():
    """Main function"""
    print("=" * 70)
    print("ORGANIZE IRRELEVANT PROJECT FILES")
    print("=" * 70)
    print()
    
    # Determine paths based on FOLDER_SOURCE
    if FOLDER_SOURCE == "cloud":
        base_path = Path(CLOUD_BASE_PATH)
        text_dir = base_path / "text"
        project_docs_dir = base_path / "project docs"
    else:  # local
        script_dir = Path(__file__).parent
        text_dir = script_dir / "text"
        project_docs_dir = script_dir / "project docs"
    
    # Excel file path
    excel_file = Path(__file__).parent.parent / "project" / "managers_projects.xlsx"
    
    if not excel_file.exists():
        print(f"Error: Excel file not found: {excel_file}")
        return
    
    print(f"Reading relevant project IDs from: {excel_file}")
    relevant_ids = get_relevant_project_ids(excel_file)
    
    if not relevant_ids:
        print("\n✗ No relevant project IDs found. Exiting.")
        return
    
    print(f"\n✓ Found {len(relevant_ids)} relevant project IDs")
    print()
    
    # Create irrelevant directories
    text_irrelevant_dir = text_dir / "irrelevant"
    project_docs_irrelevant_dir = project_docs_dir / "irrelevant"
    
    print("=" * 70)
    print("ORGANIZING TEXT FILES")
    print("=" * 70)
    print(f"Source: {text_dir}")
    print(f"Moving irrelevant files to: {text_irrelevant_dir}")
    print()
    
    moved_txt, kept_txt = organize_files(text_dir, text_irrelevant_dir, relevant_ids, '.txt')
    
    print()
    print(f"Text files - Moved: {moved_txt}, Kept: {kept_txt}")
    print()
    
    print("=" * 70)
    print("ORGANIZING PDF FILES")
    print("=" * 70)
    print(f"Source: {project_docs_dir} (including subdirectories)")
    print(f"Moving irrelevant files to: {project_docs_irrelevant_dir}")
    print()
    
    # Process PDF files recursively to include scanned subfolder
    moved_pdf, kept_pdf = organize_files(project_docs_dir, project_docs_irrelevant_dir, relevant_ids, '.pdf', recursive=True)
    
    print()
    print(f"PDF files - Moved: {moved_pdf}, Kept: {kept_pdf}")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Relevant project IDs: {len(relevant_ids)}")
    print(f"\nText files:")
    print(f"  - Moved to irrelevant: {moved_txt}")
    print(f"  - Kept in main folder: {kept_txt}")
    print(f"\nPDF files:")
    print(f"  - Moved to irrelevant: {moved_pdf}")
    print(f"  - Kept in main folder: {kept_pdf}")
    print("=" * 70)


if __name__ == '__main__':
    main()

