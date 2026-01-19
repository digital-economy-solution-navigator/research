"""Analyze which documents have missing extractions and why."""

import json
from pathlib import Path
from collections import defaultdict

# Read the project_info.json
script_dir = Path(__file__).parent
project_info_file = script_dir.parent / "project_info.json"

if not project_info_file.exists():
    print(f"Error: {project_info_file} not found")
    exit(1)

with open(project_info_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Analyze missing extractions
missing_brief = []
missing_challenges = []
missing_both = []

for item in data:
    project_id = item.get('project_id', 'unknown')
    has_brief = item.get('brief_description') is not None
    has_challenges = item.get('challenges_problem_statements') is not None
    
    if not has_brief and not has_challenges:
        missing_both.append(project_id)
    elif not has_brief:
        missing_brief.append(project_id)
    elif not has_challenges:
        missing_challenges.append(project_id)

print("=" * 70)
print("MISSING EXTRACTION ANALYSIS")
print("=" * 70)
print(f"\nTotal documents: {len(data)}")
print(f"Missing brief description only: {len(missing_brief)}")
print(f"Missing challenges only: {len(missing_challenges)}")
print(f"Missing both: {len(missing_both)}")
print(f"\nTotal with missing brief: {len(missing_brief) + len(missing_both)}")
print(f"Total with missing challenges: {len(missing_challenges) + len(missing_both)}")

# Sample some files to analyze
print("\n" + "=" * 70)
print("SAMPLING FILES FOR ANALYSIS")
print("=" * 70)

# Get text folder
from config import FOLDER_SOURCE, CLOUD_BASE_PATH
if FOLDER_SOURCE == "cloud":
    text_dir = Path(CLOUD_BASE_PATH) / "text"
else:
    text_dir = script_dir

# Sample a few files with missing extractions
sample_ids = (missing_both[:5] + missing_brief[:3] + missing_challenges[:3])
sample_ids = list(set(sample_ids))[:10]

print(f"\nAnalyzing {len(sample_ids)} sample files...")
for pid in sample_ids:
    # Find txt file for this project
    txt_files = list(text_dir.glob(f"{pid}_*.txt"))
    if not txt_files:
        txt_files = list(text_dir.glob(f"{pid}*.txt"))
    
    if txt_files:
        txt_file = txt_files[0]
        print(f"\n--- Project {pid}: {txt_file.name} ---")
        try:
            with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check for common patterns
            has_brief_marker = any(marker in content[:2000] for marker in [
                'Brief description', 'Brief Description', 'BRIEF DESCRIPTION',
                'This project aims', 'Project Objective', 'Executive Summary',
                'Project Summary', 'Project Description'
            ])
            
            has_challenge_marker = any(marker in content for marker in [
                'Challenges to be addressed', 'CHALLENGES TO BE ADDRESSED',
                'Problem Statement', 'Situation Analysis', 'SITUATION ANALYSIS',
                'challenges facing', 'problems include', 'barriers'
            ])
            
            print(f"  Has brief marker: {has_brief_marker}")
            print(f"  Has challenge marker: {has_challenge_marker}")
            print(f"  First 200 chars: {content[:200].replace(chr(10), ' ').replace(chr(13), ' ')}")
            
        except Exception as e:
            print(f"  Error reading file: {e}")

