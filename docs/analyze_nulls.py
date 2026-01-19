"""Analyze project_info.json and list all null values.

This script analyzes the project_info.json file and identifies all projects
with null values in brief_description or challenges_problem_statements fields.
It generates both a detailed analysis file and a simple list of all null project IDs.
"""

import json
from pathlib import Path

# Get script directory and project info file path
script_dir = Path(__file__).parent
project_info_file = script_dir / "project_info.json"

if not project_info_file.exists():
    print(f"Error: {project_info_file} not found")
    exit(1)

print("=" * 70)
print("ANALYZING NULL VALUES IN project_info.json")
print("=" * 70)

with open(project_info_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Analyze null values
null_brief = []
null_challenges = []
null_both = []
all_nulls = []  # All project IDs with any null

for item in data:
    project_id = item.get('project_id', 'unknown')
    brief = item.get('brief_description')
    challenges = item.get('challenges_problem_statements')
    
    has_brief = brief is not None and brief != ""
    has_challenges = challenges is not None and challenges != ""
    
    if not has_brief and not has_challenges:
        null_both.append(project_id)
        all_nulls.append(project_id)
    elif not has_brief:
        null_brief.append(project_id)
        all_nulls.append(project_id)
    elif not has_challenges:
        null_challenges.append(project_id)
        all_nulls.append(project_id)

# Print summary to console
print(f"\nTotal documents: {len(data)}")
print(f"\n{'=' * 70}")
print("NULL VALUES SUMMARY")
print(f"{'=' * 70}")
print(f"Missing brief_description only: {len(null_brief)}")
print(f"Missing challenges_problem_statements only: {len(null_challenges)}")
print(f"Missing both: {len(null_both)}")
print(f"\nTotal with null brief_description: {len(null_brief) + len(null_both)}")
print(f"Total with null challenges_problem_statements: {len(null_challenges) + len(null_both)}")

print(f"\n{'=' * 70}")
print("DETAILED LISTS")
print(f"{'=' * 70}")

if null_brief:
    print(f"\n1. Missing brief_description only ({len(null_brief)} projects):")
    print("-" * 70)
    for i, pid in enumerate(sorted(null_brief, key=lambda x: int(x) if x.isdigit() else 0), 1):
        print(f"   {i:4d}. {pid}")
    print("-" * 70)

if null_challenges:
    print(f"\n2. Missing challenges_problem_statements only ({len(null_challenges)} projects):")
    print("-" * 70)
    for i, pid in enumerate(sorted(null_challenges, key=lambda x: int(x) if x.isdigit() else 0), 1):
        print(f"   {i:4d}. {pid}")
    print("-" * 70)

if null_both:
    print(f"\n3. Missing both ({len(null_both)} projects):")
    print("-" * 70)
    for i, pid in enumerate(sorted(null_both, key=lambda x: int(x) if x.isdigit() else 0), 1):
        print(f"   {i:4d}. {pid}")
    print("-" * 70)

# Save detailed analysis to file
output_file = script_dir / "null_values_analysis.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("NULL VALUES ANALYSIS\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Total documents: {len(data)}\n\n")
    f.write("SUMMARY\n")
    f.write("-" * 70 + "\n")
    f.write(f"Missing brief_description only: {len(null_brief)}\n")
    f.write(f"Missing challenges_problem_statements only: {len(null_challenges)}\n")
    f.write(f"Missing both: {len(null_both)}\n")
    f.write(f"\nTotal with null brief_description: {len(null_brief) + len(null_both)}\n")
    f.write(f"Total with null challenges_problem_statements: {len(null_challenges) + len(null_both)}\n\n")
    
    if null_brief:
        f.write(f"\n1. Missing brief_description only ({len(null_brief)} projects):\n")
        f.write("-" * 70 + "\n")
        for pid in sorted(null_brief, key=lambda x: int(x) if x.isdigit() else 0):
            f.write(f"{pid}\n")
    
    if null_challenges:
        f.write(f"\n2. Missing challenges_problem_statements only ({len(null_challenges)} projects):\n")
        f.write("-" * 70 + "\n")
        for pid in sorted(null_challenges, key=lambda x: int(x) if x.isdigit() else 0):
            f.write(f"{pid}\n")
    
    if null_both:
        f.write(f"\n3. Missing both ({len(null_both)} projects):\n")
        f.write("-" * 70 + "\n")
        for pid in sorted(null_both, key=lambda x: int(x) if x.isdigit() else 0):
            f.write(f"{pid}\n")
    
    f.write(f"\n\n4. ALL PROJECT IDs WITH NULL VALUES (Total: {len(all_nulls)}):\n")
    f.write("-" * 70 + "\n")
    for pid in sorted(all_nulls, key=lambda x: int(x) if x.isdigit() else 0):
        f.write(f"{pid}\n")

# Also save simple list file (for compatibility with other scripts)
simple_list_file = script_dir / "all_null_project_ids.txt"
with open(simple_list_file, 'w', encoding='utf-8') as f:
    f.write("ALL PROJECT IDs WITH NULL VALUES\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Total: {len(all_nulls)}\n\n")
    f.write("Breakdown:\n")
    f.write(f"  - Missing brief_description only: {len(null_brief)}\n")
    f.write(f"  - Missing challenges_problem_statements only: {len(null_challenges)}\n")
    f.write(f"  - Missing both: {len(null_both)}\n\n")
    f.write("=" * 70 + "\n")
    f.write("COMPLETE LIST (sorted):\n")
    f.write("=" * 70 + "\n")
    for pid in sorted(all_nulls, key=lambda x: int(x) if x.isdigit() else 0):
        f.write(f"{pid}\n")

print(f"\n{'=' * 70}")
print("OUTPUT FILES")
print(f"{'=' * 70}")
print(f"Detailed analysis saved to: {output_file}")
print(f"Simple list saved to: {simple_list_file}")
print(f"{'=' * 70}")
print(f"\nComplete list of all {len(all_nulls)} project IDs with null values:")
print("-" * 70)
for pid in sorted(all_nulls, key=lambda x: int(x) if x.isdigit() else 0):
    print(pid)
print("-" * 70)

