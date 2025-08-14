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

    gate_seal = project.GateSealV2.at(to_checksum_address(gate_seal_address))

    deployed_filename = construct_deployed_filename(
        gate_seal_address, "gateseal", check=True
    )

    with open(deployed_filename, "r") as deployed_file:
        deployed_data = json.load(deployed_file)

    params = deployed_data["params"]
    assert gate_seal.get_sealing_committee() == params["sealing_committee"]
    logger.success("sealing_committee matches!")

    assert gate_seal.get_seal_duration_seconds() == params["seal_duration_seconds"]
    logger.success("seal_duration_seconds matches!")

    assert gate_seal.get_sealables() == params["sealables"]
    logger.success("sealables matches!")

    assert gate_seal.get_prolongations_remaining() == params["prolongation_limit"]
    logger.success("prolongation_limit matches!")
    assert gate_seal.get_expiry_timestamp() == params["expiry_timestamp"]
    logger.success("expiry_timestamp matches!")
    assert (
        gate_seal.get_prolongation_period_seconds()
        == params["prolongation_period_seconds"]
    )
    logger.success("prolongation_period_seconds matches!")
    assert (
        gate_seal.get_prolongation_window_seconds()
        == params["prolongation_window_seconds"]
    )
    logger.success("prolongation_window_seconds matches!")
    assert gate_seal.get_dao_ops_reserve_seconds() == params["dao_ops_reserve_seconds"]
    logger.success("dao_ops_reserve_seconds matches!")

    # simulating GateSeal flow
    logger.info("simulating GateSeal flow")
    with accounts.use_sender(gate_seal.get_sealing_committee()):
        sealables = gate_seal.get_sealables()

        expiry = chain.pending_timestamp
        gate_seal.seal()
        logger.success("Sealed")

        assert gate_seal.is_expired()
        assert gate_seal.get_expiry_timestamp() == expiry

        logger.success("Expired")
        for sealable in sealables:
            assert project.SealableMock.at(sealable).isPaused()

        logger.success("Sealables paused")
        networks.active_provider.set_timestamp(
            expiry + gate_seal.get_seal_duration_seconds()
        )
        chain.mine()

        for sealable in sealables:
            assert not project.SealableMock.at(sealable).isPaused()

        logger.success(f"Sealables unpaused in {gate_seal.get_seal_duration_seconds()}")

        logger.success("GateSeal is good to go!")
