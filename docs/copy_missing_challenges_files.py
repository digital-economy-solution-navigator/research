#!/usr/bin/env python3
"""
Copy project documents for projects with missing challenges_problem_statements.

Reads project IDs from null_values_analysis.txt (lines 77-421) and copies
the corresponding .txt files from the text folder to a new folder called
"missing challenges_problem_statements".
"""

import sys
import shutil
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent))
from config import FOLDER_SOURCE, CLOUD_BASE_PATH


def get_project_ids_from_file(filepath: Path, start_line: int, end_line: int) -> list:
    """
    Read project IDs from null_values_analysis.txt between specified line numbers.
    
    Args:
        filepath: Path to null_values_analysis.txt
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed, inclusive)
    
    Returns:
        List of project IDs as strings
    """
    project_ids = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Extract project IDs from specified line range
        for i in range(start_line - 1, min(end_line, len(lines))):  # Convert to 0-indexed
            line = lines[i].strip()
            if line and line.isdigit():  # Only add if it's a valid project ID
                project_ids.append(line)
    
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return []
    
    return project_ids


def copy_files_for_project_ids(source_dir: Path, dest_dir: Path, project_ids: list) -> dict:
    """
    Copy .txt files matching project IDs from source to destination.
    
    Files are expected to be named: {project_id}_{rest}.txt
    
    Args:
        source_dir: Source directory containing .txt files
        dest_dir: Destination directory to copy files to
        project_ids: List of project IDs to copy
    
    Returns:
        Dictionary with counts: {'copied': int, 'not_found': int, 'errors': int}
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    project_ids_set = set(project_ids)
    results = {'copied': 0, 'not_found': 0, 'errors': 0}
    not_found_ids = []
    
    # Find all .txt files in source directory
    txt_files = list(source_dir.glob('*.txt'))
    
    for filepath in txt_files:
        # Extract project ID from filename
        filename = filepath.name
        
        # Try to match project ID at the beginning of filename
        # Format: {project_id}_{rest}.txt or {project_id}.txt
        project_id = None
        
        # Try format: {project_id}_{rest}
        if '_' in filename:
            potential_id = filename.split('_')[0]
            if potential_id.isdigit() and potential_id in project_ids_set:
                project_id = potential_id
        else:
            # Try format: {project_id}.txt
            potential_id = filepath.stem
            if potential_id.isdigit() and potential_id in project_ids_set:
                project_id = potential_id
        
        if project_id:
            try:
                dest_file = dest_dir / filepath.name
                # Handle name conflicts
                if dest_file.exists():
                    # Add a suffix to avoid overwriting
                    counter = 1
                    while dest_file.exists():
                        stem = filepath.stem
                        suffix = filepath.suffix
                        dest_file = dest_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                
                shutil.copy2(filepath, dest_file)
                results['copied'] += 1
                if results['copied'] <= 10:  # Show first 10 copies
                    print(f"  ✓ Copied: {filepath.name}")
            
            except Exception as e:
                print(f"  ✗ Error copying {filepath.name}: {e}")
                results['errors'] += 1
    
    # Check which project IDs were not found
    found_ids = set()
    for filepath in txt_files:
        filename = filepath.name
        if '_' in filename:
            potential_id = filename.split('_')[0]
            if potential_id.isdigit() and potential_id in project_ids_set:
                found_ids.add(potential_id)
        else:
            potential_id = filepath.stem
            if potential_id.isdigit() and potential_id in project_ids_set:
                found_ids.add(potential_id)
    
    not_found_ids = sorted(list(project_ids_set - found_ids))
    results['not_found'] = len(not_found_ids)
    
    if not_found_ids:
        print(f"\n  ⚠ Project IDs not found in source directory ({len(not_found_ids)}):")
        # Show first 20 and last 20 if there are many
        if len(not_found_ids) <= 40:
            for pid in not_found_ids:
                print(f"    - {pid}")
        else:
            for pid in not_found_ids[:20]:
                print(f"    - {pid}")
            print(f"    ... ({len(not_found_ids) - 40} more) ...")
            for pid in not_found_ids[-20:]:
                print(f"    - {pid}")
    
    return results, not_found_ids


def main():
    """Main function"""
    print("=" * 70)
    print("COPY FILES FOR MISSING CHALLENGES_PROBLEM_STATEMENTS")
    print("=" * 70)
    print()
    
    # Determine paths based on FOLDER_SOURCE
    if FOLDER_SOURCE == "cloud":
        base_path = Path(CLOUD_BASE_PATH)
        text_dir = base_path / "text"
    else:  # local
        script_dir = Path(__file__).parent
        text_dir = script_dir / "text"
    
    # Path to null_values_analysis.txt
    analysis_file = Path(__file__).parent / "null_values_analysis.txt"
    
    if not analysis_file.exists():
        print(f"Error: Analysis file not found: {analysis_file}")
        return
    
    if not text_dir.exists():
        print(f"Error: Text directory does not exist: {text_dir}")
        return
    
    # Read project IDs from lines 77-421
    print(f"Reading project IDs from: {analysis_file}")
    print("Line range: 77-421")
    project_ids = get_project_ids_from_file(analysis_file, 77, 421)
    
    if not project_ids:
        print("\n✗ No project IDs found in specified line range.")
        return
    
    print(f"✓ Found {len(project_ids)} project IDs")
    print()
    
    # Create destination directory
    dest_dir = text_dir.parent / "missing challenges_problem_statements"
    
    print("=" * 70)
    print("COPYING FILES")
    print("=" * 70)
    print(f"Source: {text_dir}")
    print(f"Destination: {dest_dir}")
    print()
    
    # Copy files
    results, not_found_ids = copy_files_for_project_ids(text_dir, dest_dir, project_ids)
    
    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total project IDs: {len(project_ids)}")
    print(f"Files copied: {results['copied']}")
    print(f"Files not found: {results['not_found']}")
    print(f"Errors: {results['errors']}")
    print(f"\nDestination: {dest_dir}")
    print("=" * 70)
    
    if not_found_ids:
        # Save not found IDs to a file
        not_found_file = dest_dir.parent / "missing_challenges_not_found_ids.txt"
        with open(not_found_file, 'w', encoding='utf-8') as f:
            for pid in not_found_ids:
                f.write(f"{pid}\n")
        print(f"\nNot found project IDs saved to: {not_found_file}")


if __name__ == '__main__':
    main()

