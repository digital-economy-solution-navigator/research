"""Diagnose why projects are missing documents."""

import pandas as pd
import re
from pathlib import Path
from urllib.parse import urlparse

# Excel file paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DOCS_EXCEL = SCRIPT_DIR / "project_documents.xlsx"
MANAGERS_PROJECTS_EXCEL = SCRIPT_DIR.parent / "project" / "managers_projects.xlsx"
SUMMARY_FILE = SCRIPT_DIR / "project_docs_summary.txt"


def get_missing_ids():
    """Read missing project IDs from the summary file."""
    missing_ids = []
    
    if not SUMMARY_FILE.exists():
        print(f"Warning: Summary file not found: {SUMMARY_FILE}")
        return missing_ids
    
    with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        in_list = False
        skip_next_separator = False
        for line in lines:
            if "List of missing project IDs:" in line:
                in_list = True
                skip_next_separator = True  # Skip the separator line right after the header
                continue
            if skip_next_separator and line.strip().startswith("-"):
                skip_next_separator = False
                continue  # Skip the first separator line
            if in_list and line.strip().startswith("-"):
                break  # Stop at the second separator line (end of list)
            if in_list and line.strip():
                # Extract project ID (format: "     1. 100186")
                # Simple approach: split by spaces and take the last part if it's a number
                parts = line.strip().split()
                if len(parts) >= 2:
                    potential_id = parts[-1]
                    if potential_id.isdigit():
                        missing_ids.append(potential_id)
    
    return missing_ids


def diagnose_missing_projects(missing_ids):
    """Analyze why projects are missing documents."""
    print("=" * 70)
    print("DIAGNOSING MISSING PROJECT DOCUMENTS")
    print("=" * 70)
    print(f"\nFound {len(missing_ids)} missing project IDs")
    if missing_ids:
        print(f"First 5: {missing_ids[:5]}")
    print()
    
    # Read project_documents.xlsx if it exists
    if not PROJECT_DOCS_EXCEL.exists():
        print(f"Error: Project documents Excel file not found: {PROJECT_DOCS_EXCEL}")
        return
    
    print(f"Reading {PROJECT_DOCS_EXCEL}...")
    df = pd.read_excel(PROJECT_DOCS_EXCEL)
    
    # Ensure project_id column exists and is string
    if 'project_id' not in df.columns:
        print("Error: 'project_id' column not found in Excel file")
        print(f"Available columns: {list(df.columns)}")
        return
    
    df['project_id'] = df['project_id'].astype(str)
    print(f"Total records: {len(df)}")
    print(f"Unique projects: {df['project_id'].nunique()}")
    
    # Check each missing ID
    results = {
        'not_in_excel': [],
        'no_url': [],
        'empty_url': [],
        'invalid_url': [],
        'valid_url': []
    }
    
    for pid in missing_ids:
        project_rows = df[df['project_id'] == pid]
        
        if len(project_rows) == 0:
            results['not_in_excel'].append(pid)
        else:
            # Check URL column
            if 'url' not in project_rows.columns:
                results['no_url'].append(pid)
            else:
                urls = project_rows['url'].dropna()
                if len(urls) == 0:
                    results['no_url'].append(pid)
                else:
                    url_str = str(urls.iloc[0]).strip()
                    if not url_str or url_str.lower() in ['nan', 'none', '']:
                        results['empty_url'].append(pid)
                    elif not url_str.startswith(('http://', 'https://')):
                        results['invalid_url'].append(pid)
                    else:
                        results['valid_url'].append(pid)
    
    # Print results
    print("\n" + "=" * 70)
    print("DIAGNOSIS RESULTS")
    print("=" * 70)
    
    print(f"\n1. Not in project_documents.xlsx: {len(results['not_in_excel'])}")
    if results['not_in_excel']:
        print(f"   IDs: {', '.join(results['not_in_excel'][:10])}")
        if len(results['not_in_excel']) > 10:
            print(f"   ... and {len(results['not_in_excel']) - 10} more")
    
    print(f"\n2. No URL column or empty URLs: {len(results['no_url'])}")
    if results['no_url']:
        print(f"   IDs: {', '.join(results['no_url'][:10])}")
        if len(results['no_url']) > 10:
            print(f"   ... and {len(results['no_url']) - 10} more")
    
    print(f"\n3. Empty/null URLs: {len(results['empty_url'])}")
    if results['empty_url']:
        print(f"   IDs: {', '.join(results['empty_url'][:10])}")
        if len(results['empty_url']) > 10:
            print(f"   ... and {len(results['empty_url']) - 10} more")
    
    print(f"\n4. URLs not starting with http/https: {len(results['invalid_url'])}")
    if results['invalid_url']:
        print(f"   First 5 IDs with sample URLs:")
        for pid in results['invalid_url'][:5]:
            rows = df[df['project_id'] == pid]
            if len(rows) > 0 and 'url' in rows.columns:
                url = str(rows['url'].iloc[0])
                print(f"   {pid}: {url[:80]}")
    
    print(f"\n5. Valid URLs but still missing: {len(results['valid_url'])}")
    if results['valid_url']:
        print(f"   First 5 IDs with sample URLs:")
        for pid in results['valid_url'][:5]:
            rows = df[df['project_id'] == pid]
            if len(rows) > 0 and 'url' in rows.columns:
                url = str(rows['url'].iloc[0])
                print(f"   {pid}: {url[:80]}")
    
    # Save to file
    diagnosis_file = SCRIPT_DIR / 'missing_docs_diagnosis.txt'
    with open(diagnosis_file, 'w', encoding='utf-8') as f:
        f.write("MISSING PROJECT DOCUMENTS DIAGNOSIS\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Total missing projects analyzed: {len(missing_ids)}\n\n")
        
        for category, pids in results.items():
            if pids:
                f.write(f"{category.replace('_', ' ').title()}: {len(pids)} projects\n")
                f.write("-" * 70 + "\n")
                for pid in pids:
                    f.write(f"  {pid}\n")
                f.write("\n")
    
    print(f"\n[OK] Diagnosis saved to: {diagnosis_file}")
    
    return results


if __name__ == "__main__":
    missing_ids = get_missing_ids()
    if missing_ids:
        diagnose_missing_projects(missing_ids)
    else:
        print("No missing project IDs found in summary file.")
