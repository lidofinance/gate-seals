import json
import sys
from ape import project, accounts, chain, networks
from ape.logging import logger
from eth_utils.address import to_checksum_address
from utils.env import load_env_variable
from utils.helpers import construct_deployed_filename


def main():
    gate_seal_address = load_env_variable("GATE_SEAL")

    if not gate_seal_address:
        logger.error("GATE_SEAL not found")
        sys.exit()

    gate_seal = project.GateSeal.at(to_checksum_address(gate_seal_address))

    deployed_filename = construct_deployed_filename(gate_seal_address, "gateseal", check=True)

    with open(deployed_filename, "r") as deployed_file:
        deployed_data = json.load(deployed_file)


    assert gate_seal.get_sealing_committee() == deployed_data["params"]["sealing_committee"]
    logger.success("sealing_committee matches!")

    assert gate_seal.get_seal_duration_seconds() == deployed_data["params"]["seal_duration_seconds"]
    logger.success("seal_duration_seconds matches!")

    assert gate_seal.get_sealables() == deployed_data["params"]["sealables"]
    logger.success("sealables matches!")

    assert gate_seal.get_expiry_timestamp() == deployed_data["params"]["expiry_timestamp"]
    logger.success("expiry_timestamp matches!")

    # simulating GateSeal flow

    logger.info("simulating GateSeal flow")
    with accounts.use_sender(gate_seal.get_sealing_committee()):
        sealables = gate_seal.get_sealables()

        expiry_timestamp = chain.pending_timestamp
        gate_seal.seal(sealables)
        logger.success("Sealed")

        assert gate_seal.is_expired()
        assert gate_seal.get_expiry_timestamp() == expiry_timestamp

        logger.success(f"Expired")
        for sealable in sealables:
            assert project.SealableMock.at(sealable).isPaused()

        logger.success("Sealables paused")
        networks.active_provider.set_timestamp(expiry_timestamp + gate_seal.get_seal_duration_seconds())
        chain.mine()

        for sealable in sealables:
            assert not project.SealableMock.at(sealable).isPaused()

        logger.success(f"Sealables unpaused in {gate_seal.get_seal_duration_seconds()}")

        logger.success("GateSeal is good to go!")
