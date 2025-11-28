"""
Extract unique manager IDs from the manager column in unido_projects.xlsx
and save them to a new Excel file named 'manager id.xlsx'
"""

import pandas as pd
import json
import ast
from openpyxl.utils import get_column_letter
from pathlib import Path
from typing import Optional, Tuple

# Constants
DEFAULT_INPUT_FILES = ['unido_projects.xlsx', 'managers_projects.xlsx']
DEFAULT_OUTPUT_FILE = 'manager id.xlsx'
SHEET_NAME = 'Sheet1'
MAX_COLUMN_WIDTH = 50


def parse_manager_data(manager_value) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse manager data that might be a dict/JSON string or regular string.
    
    Args:
        manager_value: The manager value to parse (can be dict, JSON string, or plain string)
    
    Returns:
        Tuple of (manager_id, manager_name). Either can be None.
    """
    if pd.isna(manager_value) or not manager_value:
        return None, None
    
    manager_str = str(manager_value).strip()
    if not manager_str:
        return None, None
    
    # Try to parse as dictionary/JSON
    if manager_str.startswith('{'):
        try:
            # Try parsing as Python dict literal first (safer)
            manager_dict = ast.literal_eval(manager_str)
            if isinstance(manager_dict, dict):
                return manager_dict.get('id'), manager_dict.get('name', '')
        except (ValueError, SyntaxError):
            pass
        
        try:
            # Try parsing as JSON
            manager_dict = json.loads(manager_str)
            if isinstance(manager_dict, dict):
                return manager_dict.get('id'), manager_dict.get('name', '')
        except (json.JSONDecodeError, TypeError):
            pass
    
    # If not a dict, return as name only
    return None, manager_str


def extract_manager_ids(input_file: str = 'unido_projects.xlsx', 
                       output_file: str = DEFAULT_OUTPUT_FILE) -> bool:
    """
    Extract unique manager IDs from the manager column in the input Excel file.
    
    Args:
        input_file: Path to the input Excel file
        output_file: Path to the output Excel file
    
    Returns:
        True if successful, False otherwise
    """
    # Check if input file exists
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File '{input_file}' not found.")
        print(f"Looking for file in current directory: {Path.cwd()}")
        return False
    
    print(f"Reading Excel file: {input_file}")
    
    try:
        # Read the Excel file (assuming data is in Sheet1)
        df = pd.read_excel(input_file, sheet_name=SHEET_NAME)
        
        # Process manager data based on available columns
        manager_list = []
        
        if 'manager_id' in df.columns and 'manager' in df.columns:
            # Both columns available - process each row
            for _, row in df.iterrows():
                manager_id_val = row.get('manager_id')
                manager_val = row.get('manager')
                
                # If manager_id is empty/NaN, try to extract from manager column
                if pd.isna(manager_id_val) or manager_id_val == '':
                    parsed_id, parsed_name = parse_manager_data(manager_val)
                    if parsed_id is not None:
                        manager_id_val = parsed_id
                    if parsed_name:
                        manager_val = parsed_name
                else:
                    # If manager_id exists, check if manager needs parsing
                    _, parsed_name = parse_manager_data(manager_val)
                    if parsed_name:
                        manager_val = parsed_name
                
                # Add record if we have at least manager_id or manager_name
                if not pd.isna(manager_id_val) and manager_id_val != '':
                    manager_list.append({
                        'manager_id': int(manager_id_val),
                        'manager_name': str(manager_val) if not pd.isna(manager_val) else ''
                    })
                elif not pd.isna(manager_val) and manager_val != '':
                    manager_list.append({
                        'manager_id': None,
                        'manager_name': str(manager_val)
                    })
        
        elif 'manager_id' in df.columns:
            # Only manager_id available
            unique_manager_ids = df['manager_id'].dropna().unique()
            unique_manager_ids = sorted([
                int(m) for m in unique_manager_ids 
                if pd.notna(m) and str(m).strip()
            ])
            
            manager_list = [
                {'manager_id': mid, 'manager_name': ''} 
                for mid in unique_manager_ids
            ]
        
        elif 'manager' in df.columns:
            # Only manager column available - process JSON/dict data
            for manager_val in df['manager'].dropna():
                parsed_id, parsed_name = parse_manager_data(manager_val)
                
                if parsed_id is not None:
                    manager_list.append({
                        'manager_id': int(parsed_id),
                        'manager_name': parsed_name or ''
                    })
                elif parsed_name:
                    manager_list.append({
                        'manager_id': None,
                        'manager_name': parsed_name
                    })
        else:
            print(f"Error: Neither 'manager_id' nor 'manager' column found in the Excel file.")
            print(f"Available columns: {list(df.columns)}")
            return False
        
        # Validate we have data
        if not manager_list:
            print("Warning: No valid manager data found.")
            return False
        
        # Create DataFrame and remove duplicates
        manager_df = pd.DataFrame(manager_list)
        manager_df = manager_df.drop_duplicates()
        
        # Sort by manager_id (putting None/NaN at the end)
        manager_df = manager_df.sort_values('manager_id', na_position='last')
        
        # Display results
        print(f"Found {len(manager_df)} unique manager(s):")
        for _, row in manager_df.iterrows():
            manager_id = row['manager_id'] if pd.notna(row['manager_id']) else 'N/A'
            manager_name = row['manager_name'] if pd.notna(row['manager_name']) else 'N/A'
            print(f"  - ID: {manager_id}, Name: {manager_name}")
        
        # Export to Excel
        return export_to_excel(manager_df, output_file)
        
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def export_to_excel(df: pd.DataFrame, output_file: str) -> bool:
    """
    Export DataFrame to Excel with auto-adjusted column widths.
    
    Args:
        df: DataFrame to export
        output_file: Path to output Excel file
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\nExporting to: {output_file}")
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=SHEET_NAME, index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets[SHEET_NAME]
            for idx, col in enumerate(df.columns, 1):
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(str(col))
                )
                adjusted_width = min(max_length + 2, MAX_COLUMN_WIDTH)
                column_letter = get_column_letter(idx)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        num_records = len(df)
        print(f"✓ Successfully exported {num_records} unique manager ID(s) to '{output_file}'")
        print(f"  File saved in: {Path(output_file).absolute()}")
        return True
    except Exception as e:
        print(f"Error exporting to Excel: {e}")
        return False

if __name__ == "__main__":
    # Try different possible filenames
    input_file = None
    for filename in DEFAULT_INPUT_FILES:
        if Path(filename).exists():
            input_file = filename
            break
    
    if input_file:
        success = extract_manager_ids(input_file=input_file, output_file=DEFAULT_OUTPUT_FILE)
        if not success:
            exit(1)
    else:
        print("Error: Could not find the Excel file.")
        print(f"Looking for: {', '.join(DEFAULT_INPUT_FILES)}")
        print(f"Current directory: {Path.cwd()}")
        print("\nPlease specify the correct filename or ensure the file exists in the current directory.")
        exit(1)

