import json
from ape import project, accounts, chain, networks
from ape.logging import logger
from eth_utils.address import to_checksum_address
from utils.constants import (
    MAX_INITIAL_LIFETIME_SECONDS,
)
from utils.env import load_env_variable
from utils.helpers import construct_deployed_filename


def main():
    factory_address = load_env_variable("FACTORY")

    deployed_filename = construct_deployed_filename(
        factory_address, "factory", check=True
    )

    with open(deployed_filename, "r") as deployed_file:
        deployed_data = json.load(deployed_file)

    factory = project.GateSealFactoryV2.at(to_checksum_address(factory_address))

    assert factory.get_blueprint() == deployed_data["blueprint"]
    logger.success("Onchain blueprint matches JSON")

    logger.info("Simulating GateSeal flow...")

    deployer = accounts.test_accounts[0]
    unpausable = False
    should_revert = False
    sealable = project.SealableMock.deploy(unpausable, should_revert, sender=deployer)
    logger.info("Deployed SealableMock")

    sealing_committee = deployer
    seal_duration_seconds = 60 * 60 * 24 * 7  # week
    sealables = [sealable.address]
    lifetime_duration_seconds = MAX_INITIAL_LIFETIME_SECONDS
    expiry_timestamp = chain.pending_timestamp + lifetime_duration_seconds
    prolongations = 3

    logger.info("Creating GateSeal...")
    tx = factory.create_gate_seal(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        prolongations,
        sender=deployer,
    )
    logger.info("GateSeal deployed!")

    gate_seal_address = tx.events[0].gate_seal

    gate_seal = project.GateSealV2.at(gate_seal_address)

    logger.info("Checking getters...")
    assert gate_seal.get_sealing_committee() == sealing_committee
    logger.success("Sealing committee matches")
    assert gate_seal.get_seal_duration_seconds() == seal_duration_seconds
    logger.success("Seal duration matches")
    assert gate_seal.get_sealables() == sealables
    logger.success("Sealables match")
    assert gate_seal.get_initial_lifetime_seconds() == lifetime_duration_seconds
    logger.success("Initial lifetime matches")
    assert gate_seal.get_prolongations_remaining() == prolongations
    logger.success("Prolongations remaining matches")
    assert gate_seal.get_expiry_timestamp() == expiry_timestamp
    logger.success("Expiry timestamp matches")

    logger.info("Sealing...")
    assert not sealable.isPaused()

    seal_tx = gate_seal.seal(sealables, sender=deployer)
    logger.success("Sealed")

    assert gate_seal.is_expired()
    logger.success("GateSeal expired")

    seal_timestamp = networks.active_provider.get_block(seal_tx.block_number).timestamp
    assert gate_seal.get_expiry_timestamp() == seal_timestamp
    logger.success("Expiry timestamp updated")
    assert sealable.isPaused()
    logger.success("Sealable paused")

    seal_timestamp = networks.active_provider.get_block(seal_tx.block_number).timestamp

    logger.info("Fast-forwarding time to the timestamp just before unpause...")
    networks.active_provider.set_timestamp(seal_timestamp + seal_duration_seconds - 1)
    chain.mine()
    assert sealable.isPaused()
    logger.success("Sealable still paused")

    logger.info("Fast-forwarding time to the unpause timestamp...")
    networks.active_provider.set_timestamp(seal_timestamp + seal_duration_seconds)
    chain.mine()
    assert not sealable.isPaused()
    logger.success("Sealable resumed")

    logger.success("Factory is good to go!")
