from ape import networks


def construct_deployed_filename(address: str, type="gateseal") -> str:
    return f"deployed/{networks.active_provider.network.name}/{type}/{address.lower()}.json"
