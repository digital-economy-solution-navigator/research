import pandas as pd
import json
import os
from pathlib import Path

# Define the results folder and output Excel file
results_folder = 'results'
output_excel = 'results_combined.xlsx'

# List to store all records
all_records = []

# Get all JSON files from the results folder
results_path = Path(results_folder)
json_files = sorted(results_path.glob('*.json'))

if not json_files:
    print(f"No JSON files found in '{results_folder}' folder.")
    exit(1)

print(f"Found {len(json_files)} JSON file(s) in '{results_folder}' folder:")
for json_file in json_files:
    print(f"  - {json_file.name}")

# Read and combine all JSON files
for json_file in json_files:
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # If data is a list, extend all_records; if it's a dict, append it
        if isinstance(data, list):
            all_records.extend(data)
            print(f"  ✓ Loaded {len(data)} records from {json_file.name}")
        elif isinstance(data, dict):
            all_records.append(data)
            print(f"  ✓ Loaded 1 record from {json_file.name}")
        else:
            print(f"  ⚠ Warning: {json_file.name} contains unexpected data type")
            
    except json.JSONDecodeError as e:
        print(f"  ✗ Error reading {json_file.name}: Invalid JSON - {e}")
    except Exception as e:
        print(f"  ✗ Error reading {json_file.name}: {e}")

if not all_records:
    print("\nNo records found to export. Exiting.")
    exit(1)

# Convert to DataFrame
print(f"\nConverting {len(all_records)} total records to DataFrame...")
df = pd.DataFrame(all_records)

# Display column information
print(f"\nColumns found: {list(df.columns)}")
print(f"Total rows: {len(df)}")

# Export to Excel
print(f"\nExporting to Excel: {output_excel}")
try:
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Results', index=False)
        
        # Auto-adjust column widths
        from openpyxl.utils import get_column_letter
        worksheet = writer.sheets['Results']
        for idx, col in enumerate(df.columns, 1):
            column_letter = get_column_letter(idx)
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(str(col))
            ) + 2
            worksheet.column_dimensions[column_letter].width = min(max_length, 50)
    
    print(f"✓ Successfully exported {len(df)} records to '{output_excel}'")
    print(f"  File saved in: {os.path.abspath(output_excel)}")
    
except Exception as e:
    print(f"✗ Error exporting to Excel: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

