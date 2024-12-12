# Overview

This repository hosts public RPC URLs for various blockchains used by Threshold Access Control (TACo).
Each TACo domain has a corresponding `<domain>.json` file, which maps chain IDs to public RPC endpoints
for the chains supported by the relevant domain.

# Generate Endpoint Mapping Files

> [!IMPORTANT]
> The JSON files should not be updated manually

To get started, set up a Python environment:

```bash
$ pipenv shell

$ pipenv install
```

To regenerate endpoint mapping files for all domains, execute the following command:

```bash
$ python scripts/generate_endpoint_mapping.py
```

To generate an endpoint mapping file for a specific domain, include the domain parameter:

```bash
python scripts/generate_endpoint_mapping.py --domain <DOMAIN>
```

## Health Checks

During the generation of endpoint files, each endpoint undergoes a health check, which includes:

1. Confirming the chain ID matches the provided endpoint. If the chain ID does not match, a configuration error is detected, and the script raises an exception.
2. Ensuring the latest block retrieved from the endpoint is recent enough. Endpoints with outdated blocks are excluded, and the script proceeds

*If due to failed health checks, a supported chain has no valid RPC endpoints, the script will raise an exception.*

Due to the nature of the health checks, the script can produce different results after each run.

## Adding Specific Endpoints

To expand the list of endpoints, include additional entries in the `EXTRA_KNOWN_RPC_ENDPOINTS` dictionary
located in the `scripts/generate_endpoint_mapping.py` file.
