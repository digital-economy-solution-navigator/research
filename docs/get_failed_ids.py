"""Get project IDs that failed to download."""

from pathlib import Path
from config import FOLDER_SOURCE, CLOUD_BASE_PATH
import re

# Constants
SCRIPT_DIR = Path(__file__).parent
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
                skip_next_separator = True
                continue
            if skip_next_separator and line.strip().startswith("-"):
                skip_next_separator = False
                continue
            if in_valid_section and line.strip().startswith("-"):
                break
            if in_valid_section and line.strip():
                pid = line.strip()
                if pid.isdigit():
                    missing_ids.append(pid)
    
    return missing_ids


def extract_project_id(filename: str):
    """Extract project ID from filename."""
    match = re.match(r'^(\d+)_', filename)
    return match.group(1) if match else None


def get_failed_project_ids():
    """Get project IDs that still don't have files (failed downloads)."""
    # Get all missing project IDs
    missing_ids = get_missing_project_ids()
    print(f"Total missing projects from diagnosis: {len(missing_ids)}")
    
    # Get all downloaded project IDs
    downloaded_ids = set()
    if OUTPUT_DIR.exists():
        for pdf in OUTPUT_DIR.glob("*.pdf"):
            pid = extract_project_id(pdf.name)
            if pid:
                downloaded_ids.add(pid)
    
    print(f"Found {len(downloaded_ids)} projects with files in output directory")
    
    # Find which ones are still missing (failed)
    failed_ids = [pid for pid in missing_ids if pid not in downloaded_ids]
    
    return failed_ids


if __name__ == "__main__":
    failed_ids = get_failed_project_ids()
    
    print(f"\n{'=' * 70}")
    print(f"PROJECT IDs WITH ERRORS ({len(failed_ids)}):")
    print(f"{'=' * 70}")
    
    if failed_ids:
        sorted_failed = sorted(failed_ids, key=lambda x: int(x) if x.isdigit() else 0)
        for i, pid in enumerate(sorted_failed, 1):
            print(f"  {i:3d}. {pid}")
        
        # Save to file
        error_file = SCRIPT_DIR / "failed_downloads.txt"
        with open(error_file, 'w', encoding='utf-8') as f:
            for pid in sorted_failed:
                f.write(f"{pid}\n")
        print(f"\n{'=' * 70}")
        print(f"Failed project IDs saved to: {error_file}")
    else:
        print("  No failed downloads found!")
    print(f"{'=' * 70}")

