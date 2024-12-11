import json
from pathlib import Path
from typing import Dict, List


def sort_mappings(endpoint_mappings: Dict[str, List[str]]) -> Dict[str, List[str]]:
    # Sort the top-level keys (network IDs)
    sorted_data = dict(sorted(endpoint_mappings.items(), key=lambda x: int(x[0])))

    # Sort the RPC endpoints within each array
    for key in sorted_data:
        sorted_data[key] = sorted(sorted_data[key])

    return sorted_data


def write_endpoint_mappings_to_file(
    json_file: Path, endpoint_mappings: Dict[str, List[str]], sort: bool = True
):
    if sort:
        data = sort_mappings(endpoint_mappings)
    else:
        data = endpoint_mappings

    with open(json_file, "w") as f:
        json.dump(data, f, indent=4)
        # add new line at the end
        f.write("\n")


def get_file_for_domain(domain: str) -> Path:
    if not domain:
        raise ValueError("Domain not specified")

    domain_json_file = Path(__file__).parent.parent / f"{domain}.json"
    return domain_json_file
