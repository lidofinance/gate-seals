from ape import networks


def construct_deployed_filename(address: str, type="gateseal", check=False) -> str:
    network = networks.active_provider.network.name
    if check:
        network = networks.active_provider.network.name.replace("-fork", "")
    return f"deployed/{network}/{type}/{address.lower()}.json"
