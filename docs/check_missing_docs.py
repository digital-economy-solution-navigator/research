"""
Script to compare project IDs from managers_projects.xlsx (where doc = "yes")
with actual project documents in the cloud folders.

Identifies which project documents failed to download.
"""

import pandas as pd
import re
from pathlib import Path
from typing import Set, List, Dict
from config import FOLDER_SOURCE, CLOUD_BASE_PATH

# Excel file path
EXCEL_FILE = Path(__file__).parent.parent / "project" / "managers_projects.xlsx"
SHEET_NAME = "Sheet1"

# Folder paths based on FOLDER_SOURCE
if FOLDER_SOURCE == "cloud":
    PROJECT_DOCS_FOLDER = Path(CLOUD_BASE_PATH) / "project docs"
    SCANNED_FOLDER = PROJECT_DOCS_FOLDER / "scanned"
else:  # local
    PROJECT_DOCS_FOLDER = Path(__file__).parent / "project docs"
    SCANNED_FOLDER = PROJECT_DOCS_FOLDER / "scanned"


def extract_project_id(filename: str) -> str:
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


def get_project_ids_from_excel(excel_file: Path, sheet_name: str) -> Set[str]:
    """
    Read Excel file and get project IDs where doc = "yes".
    
    Args:
        excel_file: Path to Excel file
        sheet_name: Name of the sheet to read
    
    Returns:
        Set of project IDs as strings
    """
    print(f"Reading Excel file: {excel_file}")
    try:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        # Check if 'doc' column exists
        if 'doc' not in df.columns:
            print(f"Error: 'doc' column not found in Excel file.")
            print(f"Available columns: {df.columns.tolist()}")
            return set()
        
        # Filter rows where doc = "yes" (case-insensitive)
        # Handle different possible values: "yes", "Yes", "YES", True, etc.
        doc_yes = df[df['doc'].astype(str).str.lower().str.strip() == 'yes']
        
        # Get project IDs - check common column names (prioritize 'id' as confirmed by user)
        project_id_col = None
        for col in ['id', 'project_id', 'project id', 'Project ID', 'Project_ID']:
            if col in df.columns:
                project_id_col = col
                break
        
        if project_id_col is None:
            print(f"Error: Could not find project ID column.")
            print(f"Available columns: {df.columns.tolist()}")
            return set()
        
        project_ids = doc_yes[project_id_col].astype(str).unique()
        project_ids_set = {str(pid).strip() for pid in project_ids if pd.notna(pid) and str(pid).strip()}
        
        print(f"Found {len(project_ids_set)} project IDs with doc = 'yes'")
        return project_ids_set
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return set()


def get_project_ids_from_folder(folder: Path) -> Dict[str, List[str]]:
    """
    Scan folder for PDF files and extract project IDs from filenames.
    
    Args:
        folder: Path to folder to scan
    
    Returns:
        Dictionary mapping project IDs to list of filenames
    """
    project_files = {}
    
    if not folder.exists():
        print(f"Warning: Folder does not exist: {folder}")
        return project_files
    
    print(f"Scanning folder: {folder}")
    pdf_files = list(folder.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files")
    
    for pdf_file in pdf_files:
        project_id = extract_project_id(pdf_file.name)
        if project_id:
            if project_id not in project_files:
                project_files[project_id] = []
            project_files[project_id].append(pdf_file.name)
    
    return project_files


def compare_project_documents() -> Set[str]:
    """
    Main function to compare Excel project IDs with downloaded documents.
    """
    print("=" * 70)
    print("Project Document Comparison Tool")
    print("=" * 70)
    print()
    
    # Get project IDs from Excel
    excel_project_ids = get_project_ids_from_excel(EXCEL_FILE, SHEET_NAME)
    
    if not excel_project_ids:
        print("No project IDs found in Excel file. Exiting.")
        return set()
    
    print()
    
    # Get project IDs from folders
    main_folder_files = get_project_ids_from_folder(PROJECT_DOCS_FOLDER)
    scanned_folder_files = get_project_ids_from_folder(SCANNED_FOLDER)
    
    # Combine both folders (scanned takes precedence if duplicate project ID)
    all_downloaded_ids = set(main_folder_files.keys())
    all_downloaded_ids.update(scanned_folder_files.keys())
    
    print()
    
    # Find missing documents
    missing_ids = excel_project_ids - all_downloaded_ids
    found_ids = excel_project_ids & all_downloaded_ids
    
    # Sort missing IDs for easier reading
    sorted_missing = sorted(missing_ids, key=lambda x: int(x) if x.isdigit() else 0)
    
    # Print comprehensive summary
    print("=" * 70)
    print("PROJECT DOCUMENT SUMMARY")
    print("=" * 70)
    print()
    print(f"1. Expected project docs (from managers_projects.xlsx where doc='yes'): {len(excel_project_ids)}")
    print()
    print(f"2. Project documents found in cloud path:")
    print(f"   - Root folder (project docs): {len(main_folder_files)} projects")
    print(f"   - Scanned folder: {len(scanned_folder_files)} projects")
    print(f"   - Total unique projects with documents: {len(all_downloaded_ids)}")
    print()
    print(f"3. Missing project docs: {len(missing_ids)}")
    print()
    
    if missing_ids:
        print("4. List of missing project IDs:")
        print("-" * 70)
        for i, pid in enumerate(sorted_missing, 1):
            print(f"   {i:4d}. {pid}")
        print("-" * 70)
    else:
        print("4. ✓ All projects have documents!")
    
    print()
    print("=" * 70)
    
    # Save missing IDs to file
    if missing_ids:
        output_file = Path(__file__).parent / "missing_project_docs.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("Missing Project Documents\n")
            f.write("=" * 70 + "\n")
            f.write(f"Total missing: {len(missing_ids)}\n\n")
            for project_id in sorted_missing:
                f.write(f"{project_id}\n")
        print(f"\n✓ Missing project IDs saved to: {output_file}")
    
    # Save comprehensive summary to file
    summary_file = Path(__file__).parent / "project_docs_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("PROJECT DOCUMENT SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"1. Expected project docs (from managers_projects.xlsx where doc='yes'): {len(excel_project_ids)}\n\n")
        f.write(f"2. Project documents found in cloud path:\n")
        f.write(f"   - Root folder (project docs): {len(main_folder_files)} projects\n")
        f.write(f"   - Scanned folder: {len(scanned_folder_files)} projects\n")
        f.write(f"   - Total unique projects with documents: {len(all_downloaded_ids)}\n\n")
        f.write(f"3. Missing project docs: {len(missing_ids)}\n\n")
        if missing_ids:
            f.write(f"4. List of missing project IDs:\n")
            f.write("-" * 70 + "\n")
            for i, pid in enumerate(sorted_missing, 1):
                f.write(f"   {i:4d}. {pid}\n")
            f.write("-" * 70 + "\n")
        else:
            f.write("4. ✓ All projects have documents!\n")
    print(f"✓ Summary saved to: {summary_file}")
    
    print()
    
    # Show some statistics
    if found_ids:
        print("=" * 70)
        print("STATISTICS")
        print("=" * 70)
        print(f"Success rate: {len(found_ids)}/{len(excel_project_ids)} ({100*len(found_ids)/len(excel_project_ids):.1f}%)")
        
        # Show projects with multiple files
        multi_file_projects = []
        for pid in found_ids:
            main_count = len(main_folder_files.get(pid, []))
            scanned_count = len(scanned_folder_files.get(pid, []))
            total = main_count + scanned_count
            if total > 1:
                multi_file_projects.append((pid, main_count, scanned_count, total))
        
        if multi_file_projects:
            print(f"\nProjects with multiple files: {len(multi_file_projects)}")
            print("(First 10 shown)")
            for pid, main_count, scanned_count, total in multi_file_projects[:10]:
                location = []
                if main_count > 0:
                    location.append(f"{main_count} in main")
                if scanned_count > 0:
                    location.append(f"{scanned_count} in scanned")
                print(f"  Project {pid}: {total} file(s) ({', '.join(location)})")
    
    print()
    
    return missing_ids


if __name__ == "__main__":
    missing = compare_project_documents()
    print("\n" + "=" * 70)
    print("MISSING PROJECT IDs (as list):")
    print("=" * 70)
    if missing:
        sorted_missing = sorted(missing, key=lambda x: int(x) if x.isdigit() else 0)
        print(f"[{', '.join(sorted_missing)}]")
    else:
        print("[]")

