import json
from pathlib import Path

import click

from utils import write_endpoint_mappings_to_file


def sort_json_file(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)

    # sort=True is not needed, but just to be explicit about what the write call is doing
    write_endpoint_mappings_to_file(
        json_file=file_path, endpoint_mappings=data, sort=True
    )
    print(f"Sorted {file_path}")


@click.command()
@click.option(
    "--domain",
    "domain",
    help="TACo Domain",
    type=click.Choice(["lynx", "tapir", "mainnet"]),
    required=False,
)
def sort_endpoint_mapping(domain):
    """
    Sort endpoint mappings file(s) for domain(s). If domain is not specified, all
    domain endpoint mappings files are sorted.
    """
    file_list = Path(__file__).parent.parent.glob(f"{domain if domain else '*'}.json")
    # Process JSON file(s)
    for json_file in file_list:
        sort_json_file(json_file)


if __name__ == "__main__":
    sort_endpoint_mapping()
