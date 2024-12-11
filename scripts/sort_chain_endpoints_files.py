import json
from pathlib import Path

"""
Run this file with `python3 ./scripts/sort_chain_endpoints_files.py`
"""


def sort_json_file(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Sort the top-level keys (network IDs)
        sorted_data = dict(sorted(data.items(), key=lambda x: int(x[0])))
        
        # Sort the RPC endpoints within each array
        for key in sorted_data:
            sorted_data[key] = sorted(sorted_data[key])
        
        # Write back the sorted data directly
        with open(file_path, 'w') as f:
            json.dump(sorted_data, f, indent=4)
        print(f"Sorted {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")


# Process all JSON files in the directory
for json_file in Path(__file__).parent.parent.glob("*.json"):
    sort_json_file(json_file)
