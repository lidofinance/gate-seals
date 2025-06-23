from ape import networks
from utils.constants import TOTAL_LIFETIME_SECONDS


def construct_deployed_filename(address: str, type="gateseal", check=False) -> str:
    network = networks.active_provider.network.name
    if check:
        network = networks.active_provider.network.name.replace("-fork", "")
    return f"deployed/{network}/{type}/{address.lower()}.json"


def calculated_max_prolongations(lifetime_seconds: int) -> int:
    if lifetime_seconds == 0:
        raise ValueError("lifetime_seconds cannot be zero")
    return (TOTAL_LIFETIME_SECONDS // lifetime_seconds) - 1
