import asyncio
import time
from functools import wraps

import click
from aiohttp import ClientSession
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from utils import get_file_for_domain, write_endpoint_mappings_to_file

MAINNET_CHAINS = [1, 137]  # Ethereum Mainnet  # Polygon Mainnet

TAPIR_CHAINS = [80002, 11155111]  # Polygon Amoy  # Sepolia

LYNX_CHAINS = {
    1,  # Ethereum Mainnet
    10,  # OP Mainnet
    56,  # BNB Smart Chain Mainnet
    97,  # BNB Smart Chain Testnet
    100,  # Gnosis
    137,  # Polygon Mainnet
    300,  # zkSync Sepolia Testnet
    314,  # Filecoin - Mainnet
    397,  # NEAR Protocol
    398,  # NEAR Protocol Testnet
    7700,  # Canto
    7701,  # Canto Testnet
    8453,  # Base
    10200,  # Gnosis Chiado Testnet
    42161,  # Arbitrum One
    42220,  # Celo Mainnet
    43114,  # Avalanche C-Chain
    80002,  # Amoy
    84532,  # Base Sepolia Testnet
    314159,  # Filecoin - Calibration testnet
    421614,  # Arbitrum Sepolia
    534351,  # Scroll Sepolia Testnet
    534352,  # Scroll
    11155111,  # Sepolia
    11155420,  # OP Sepolia Testnet
}

#
# Additional endpoints to augment chainid.network list:
# - chains with less endpoints
# - chains that didn't have drpc endpoints
# - use of nodies.app public endpoints

# -
# - drpc: chainid.network doesn't use drpc endpoints for some chains
EXTRA_KNOWN_RPC_ENDPOINTS = {
    1: ["https://ethereum-public.nodies.app"],
    10: ["https://optimism-public.nodies.app"],
    56: ["https://bsc.drpc.org", "https://binance-smart-chain-public.nodies.app"],
    97: ["https://bsc-testnet.drpc.org"],
    100: [
        "https://gnosis.drpc.org",
        "https://gnosis-public.nodies.app",
    ],
    137: ["https://polygon-public.nodies.app"],
    300: [
        "https://zksync-era-sepolia.blockpi.network/v1/rpc/public",
        "https://sepolia.era.zksync.dev",
        "https://zksync-sepolia.drpc.org",
    ],
    7701: ["https://canto-testnet.plexnode.wtf"],
    8453: [
        "https://base.drpc.org",
        "https://base-public.nodies.app",
    ],
    42161: [
        "https://arbitrum.drpc.org",
        "https://arbitrum-one-public.nodies.app",
    ],
    42220: [
        "https://celo.drpc.org",
        "https://1rpc.io/celo",
        "https://celo.api.onfinality.io/public",
    ],
    43114: ["https://avalanche.drpc.org"],
    80002: [
        "https://polygon-amoy.drpc.org",
        "https://polygon-amoy-public.nodies.app",
    ],
    84532: [
        "https://base-sepolia.gateway.tenderly.co",
        "https://base-sepolia.drpc.org",
        "https://base-sepolia-public.nodies.app",
    ],
    421614: [
        "https://api.zan.top/arb-sepolia",
        "https://arbitrum-sepolia.gateway.tenderly.co",
        "https://arbitrum-sepolia.drpc.org",
    ],
    534351: [
        "https://scroll-sepolia.drpc.org",
        "https://scroll-sepolia-public.nodies.app",
    ],
    534352: [
        "https://scroll.drpc.org",
        "https://scroll-public.nodies.app",
    ],
    11155420: [
        "https://api.zan.top/opt-sepolia",
        "https://endpoints.omniatech.io/v1/op/sepolia/public",
        "https://optimism-sepolia.blockpi.network/v1/rpc/public",
        "https://optimism-sepolia.gateway.tenderly.co",
        "https://optimism-sepolia-public.nodies.app",
    ],
}

DOMAINS = ["lynx", "tapir", "mainnet"]

DOMAIN_CHAINS = {
    "lynx": LYNX_CHAINS,
    "tapir": TAPIR_CHAINS,
    "mainnet": MAINNET_CHAINS,
}

CHAINID_NETWORK = "https://chainid.network/chains.json"
LYNX_JSON = Path(__file__).parent.parent / "lynx.json"


class InvalidChainConfiguration(ValueError):
    """
    Raised when endpoint's chain id does not matched expected chain id.
    """

    pass


def process_rpc_endpoints(endpoints: List[str]) -> List[str]:
    rpc_endpoints = set()
    for endpoint in endpoints:
        # ensure no infura key
        if "${" in endpoint:
            # filter out urls that are f-strings e.g.:
            # - https://mainnet.infura.io/v3/${INFURA_API_KEY},
            # - https://mainnet.infura.io/v3/${ALCHEMY_API_KEY}
            continue

        # only use https endpoints
        url_components = urlparse(endpoint)
        if url_components.scheme != "https":
            continue

        rpc_endpoints.add(endpoint)
    return list(rpc_endpoints)


async def _fetch_chain_id_network_public_rpc_endpoints(
    session: ClientSession, domain_chains: List[int]
) -> Dict[int, List[str]]:
    async with session.get(CHAINID_NETWORK) as response:
        chain_id_network_result = await response.json()
        chain_id_endpoints_dict = {}
        for entry in chain_id_network_result:
            chain_id = entry["chainId"]
            if chain_id in domain_chains:
                chain_id_endpoints_dict[chain_id] = process_rpc_endpoints(
                    entry.get("rpc", [])
                )

        return chain_id_endpoints_dict


async def _validate_chain_id(
    session: ClientSession, rpc_endpoint: str, expected_chain_id: int
) -> bool:
    data = {
        "jsonrpc": "2.0",
        "method": "eth_chainId",
        "params": [],
        "id": 1,
    }

    async with session.post(
        rpc_endpoint,
        json=data,
        timeout=5,
    ) as response:
        data = await response.json()
        rpc_chain_id = data["result"]
        return rpc_chain_id == hex(expected_chain_id)


async def _validate_block_time(
    session: ClientSession, rpc_endpoint: str, max_drift_seconds: int
) -> bool:
    data = {
        "jsonrpc": "2.0",
        "method": "eth_getBlockByNumber",
        "params": ["latest", False],
        "id": 1,
    }

    async with session.post(
        rpc_endpoint,
        json=data,
        timeout=5,
    ) as response:
        data = await response.json()
        block_data = data["result"]
        timestamp = int(block_data["timestamp"], 16)

        system_time = time.time()
        drift = abs(system_time - timestamp)
        return drift <= max_drift_seconds


async def _rpc_endpoint_health_check(
    session: ClientSession,
    endpoint: str,
    expected_chain_id: int,
    max_drift_seconds: int = 60,
) -> Tuple[bool, str]:
    """
    Checks the health of an Ethereum RPC endpoint by checking chain id matches
    provided chain id, and comparing the timestamp of the latest block
    with the system time. The maximum drift allowed is `max_drift_seconds`.
    """
    try:
        validated_chain_id = await _validate_chain_id(
            session, endpoint, expected_chain_id
        )
        if not validated_chain_id:
            raise InvalidChainConfiguration(
                f"[x!] chain={expected_chain_id}: [CONFIG ERROR] RPC endpoint {endpoint} configured for incorrect chain"
            )

        validated_block_time = await _validate_block_time(
            session, endpoint, max_drift_seconds
        )
        if not validated_block_time:
            print(
                f"[x] chain={expected_chain_id}: RPC endpoint {endpoint} failed health check: drift too large"
            )
            return False, endpoint

        return True, endpoint

    except InvalidChainConfiguration as e:
        raise e
    except Exception as e:
        print(
            f"[x] chain={expected_chain_id}: RPC endpoint {endpoint} failed health check: {e.__class__} - {e}"
        )
        return False, endpoint


async def collect_rpc_endpoint_mappings(domain) -> Dict[str, List[str]]:
    rpc_endpoints_dict = {}

    domain_chains = DOMAIN_CHAINS[domain]

    # do this once
    async with ClientSession() as session:
        chain_id_network_rpc_endpoints = (
            await _fetch_chain_id_network_public_rpc_endpoints(session, domain_chains)
        )
        for chain_id in domain_chains:
            endpoints_for_chain = set()

            # 1. get endpoints from chain id source
            chain_id_network_endpoints = chain_id_network_rpc_endpoints.get(
                chain_id, []
            )
            endpoints_for_chain.update(chain_id_network_endpoints)

            # 2. get endpoints from extra rpc urls source
            extra_endpoints = EXTRA_KNOWN_RPC_ENDPOINTS.get(chain_id, [])
            endpoints_for_chain.update(extra_endpoints)

            # 3. perform health check on rpc endpoints
            if not endpoints_for_chain:
                raise Exception(
                    f"[x!] chain={chain_id}: No endpoints/healthy endpoints available"
                )

            tasks = set()
            for endpoint in endpoints_for_chain:
                tasks.add(_rpc_endpoint_health_check(session, endpoint, chain_id))

            for task in asyncio.as_completed(tasks):
                if task:
                    healthy, endpoint = await task
                    if not healthy:
                        endpoints_for_chain.remove(endpoint)

            if not endpoints_for_chain:
                raise Exception(
                    f"[x!] chain={chain_id}: No endpoints/healthy endpoints available"
                )
            else:
                # only healthy endpoints remain
                rpc_endpoints_dict[str(chain_id)] = list(endpoints_for_chain)

    return rpc_endpoints_dict


# We can use `asyncclick` instead but not looking to add more dependencies than we need.
def async_coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--domain",
    "domain",
    help="TACo Domain",
    type=click.Choice(["lynx", "tapir", "mainnet"]),
    required=False,
)
@async_coro
async def generate_endpoint_mapping(domain):
    """
    Generate rpc endpoint mappings file for chains associated with domain. If domain is not
    specified, then mappings files are generated for all supported domains.
    """
    domains = [domain] if domain else DOMAINS
    for domain in domains:
        endpoint_mappings = await collect_rpc_endpoint_mappings(domain)
        domain_json_file = get_file_for_domain(domain)
        write_endpoint_mappings_to_file(
            json_file=domain_json_file, endpoint_mappings=endpoint_mappings
        )

    print("\n-- All done! --")


asyncio.run(generate_endpoint_mapping())
