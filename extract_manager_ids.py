"""
Extract unique manager IDs from the manager column in unido_projects.xlsx
and save them to a new Excel file named 'manager id.xlsx'
"""

import pandas as pd
import json
import ast
from openpyxl.utils import get_column_letter
from pathlib import Path

def extract_manager_ids(input_file='unido_projects.xlsx', output_file='manager id.xlsx'):
    """
    Extract unique manager IDs from the manager column in the input Excel file.
    
    Args:
        input_file (str): Path to the input Excel file
        output_file (str): Path to the output Excel file
    """
    # Check if input file exists
    if not Path(input_file).exists():
        print(f"Error: File '{input_file}' not found.")
        print(f"Looking for file in current directory: {Path.cwd()}")
        return
    
    print(f"Reading Excel file: {input_file}")
    
    try:
        # Read the Excel file (assuming data is in Sheet1)
        df = pd.read_excel(input_file, sheet_name='Sheet1')
        
        def parse_manager_data(manager_value):
            """Parse manager data that might be a dict/JSON string or regular string."""
            if pd.isna(manager_value) or not manager_value:
                return None, None
            
            manager_str = str(manager_value).strip()
            
            # Try to parse as dictionary/JSON
            try:
                # Try parsing as Python dict literal
                if manager_str.startswith('{'):
                    manager_dict = ast.literal_eval(manager_str)
                    if isinstance(manager_dict, dict):
                        manager_id = manager_dict.get('id')
                        manager_name = manager_dict.get('name', '')
                        return manager_id, manager_name
            except (ValueError, SyntaxError):
                pass
            
            try:
                # Try parsing as JSON
                manager_dict = json.loads(manager_str)
                if isinstance(manager_dict, dict):
                    manager_id = manager_dict.get('id')
                    manager_name = manager_dict.get('name', '')
                    return manager_id, manager_name
            except (json.JSONDecodeError, TypeError):
                pass
            
            # If not a dict, return as name only
            return None, manager_str
        
        # Check if both 'manager_id' and 'manager' columns exist
        if 'manager_id' in df.columns and 'manager' in df.columns:
            # Process each row to extract manager_id and manager_name
            manager_list = []
            
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
                
                # Only add if we have at least manager_id or manager_name
                if not pd.isna(manager_id_val) and manager_id_val != '':
                    manager_list.append({
                        'manager_id': int(manager_id_val) if manager_id_val else None,
                        'manager_name': str(manager_val) if not pd.isna(manager_val) else ''
                    })
                elif not pd.isna(manager_val) and manager_val != '':
                    manager_list.append({
                        'manager_id': None,
                        'manager_name': str(manager_val)
                    })
            
            if not manager_list:
                print("Warning: No valid manager data found.")
                return
            
            # Create DataFrame and remove duplicates
            manager_df = pd.DataFrame(manager_list)
            manager_df = manager_df.drop_duplicates()
            
            # Sort by manager_id (putting None/NaN at the end)
            manager_df = manager_df.sort_values('manager_id', na_position='last')
            
            print(f"Found {len(manager_df)} unique manager(s):")
            for _, row in manager_df.iterrows():
                manager_id = row['manager_id'] if pd.notna(row['manager_id']) else 'N/A'
                manager_name = row['manager_name'] if pd.notna(row['manager_name']) else 'N/A'
                print(f"  - ID: {manager_id}, Name: {manager_name}")
            
        elif 'manager_id' in df.columns:
            # Only manager_id available
            unique_manager_ids = df['manager_id'].dropna().unique()
            unique_manager_ids = sorted([int(m) for m in unique_manager_ids if pd.notna(m) and str(m).strip()])
            
            if not unique_manager_ids:
                print("Warning: No manager IDs found in the 'manager_id' column.")
                return
            
            print(f"Found {len(unique_manager_ids)} unique manager ID(s) (no names available):")
            for manager_id in unique_manager_ids:
                print(f"  - {manager_id}")
            
            # Create DataFrame with manager IDs only
            manager_df = pd.DataFrame({
                'manager_id': unique_manager_ids,
                'manager_name': [''] * len(unique_manager_ids)
            })
            
        elif 'manager' in df.columns:
            # Process manager column which might contain JSON/dict data
            manager_list = []
            
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
            
            if not manager_list:
                print("Warning: No manager values found in the 'manager' column.")
                return
            
            # Create DataFrame and remove duplicates
            manager_df = pd.DataFrame(manager_list)
            manager_df = manager_df.drop_duplicates()
            
            # Sort by manager_id (putting None/NaN at the end)
            manager_df = manager_df.sort_values('manager_id', na_position='last')
            
            print(f"Found {len(manager_df)} unique manager(s):")
            for _, row in manager_df.iterrows():
                manager_id = row['manager_id'] if pd.notna(row['manager_id']) else 'N/A'
                manager_name = row['manager_name'] if pd.notna(row['manager_name']) else 'N/A'
                print(f"  - ID: {manager_id}, Name: {manager_name}")
        else:
            print(f"Error: Neither 'manager_id' nor 'manager' column found in the Excel file.")
            print(f"Available columns: {list(df.columns)}")
            return
        
        # Export to Excel
        print(f"\nExporting to: {output_file}")
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            manager_df.to_excel(writer, sheet_name='Sheet1', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Sheet1']
            for idx, col in enumerate(manager_df.columns, 1):
                max_length = max(
                    manager_df[col].astype(str).map(len).max(),
                    len(str(col))
                )
                adjusted_width = min(max_length + 2, 50)
                column_letter = get_column_letter(idx)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        num_records = len(manager_df)
        print(f"✓ Successfully exported {num_records} unique manager ID(s) to '{output_file}'")
        print(f"  File saved in: {Path(output_file).absolute()}")
        
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Try different possible filenames
    possible_files = ['unido_projects.xlsx', 'managers_projects.xlsx']
    
    input_file = None
    for filename in possible_files:
        if Path(filename).exists():
            input_file = filename
            break
    
    if input_file:
        extract_manager_ids(input_file=input_file, output_file='manager id.xlsx')
    else:
        print("Error: Could not find the Excel file.")
        print(f"Looking for: {', '.join(possible_files)}")
        print(f"Current directory: {Path.cwd()}")
        print("\nPlease specify the correct filename or ensure the file exists in the current directory.")

