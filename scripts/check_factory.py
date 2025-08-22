import json
from ape import project, accounts, chain, networks
from ape.logging import logger
from eth_utils.address import to_checksum_address
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
    prolongation_extension_seconds = int(
        load_env_variable("PROLONGATION_EXTENSION_SECONDS")
    )
    prolongation_window_seconds = int(load_env_variable("PROLONGATION_WINDOW_SECONDS"))
    expiration_buffer_seconds = int(load_env_variable("EXPIRATION_BUFFER_SECONDS"))
    expiry_timestamp = chain.pending_timestamp + prolongation_extension_seconds
    prolongation_limit = 3

    tx = factory.create_gate_seal(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        prolongation_limit,
        prolongation_extension_seconds,
        prolongation_window_seconds,
        expiration_buffer_seconds,
        sender=deployer,
    )
    logger.success("GateSeal deployed!")

    gate_seal_address = tx.events[0].gate_seal
    gate_seal = project.GateSealV2.at(gate_seal_address)

    assert gate_seal.get_sealing_committee() == sealing_committee
    assert gate_seal.get_seal_duration_seconds() == seal_duration_seconds
    assert gate_seal.get_sealables() == sealables
    assert gate_seal.get_expiry_timestamp() == expiry_timestamp
    logger.success("Expiry timestamp matches")
    assert gate_seal.get_prolongations_remaining() == prolongation_limit
    logger.success("Prolongations remaining matches")
    assert (
        gate_seal.get_prolongation_extension_seconds() == prolongation_extension_seconds
    )
    logger.success("Prolongation extension matches")
    assert gate_seal.get_prolongation_window_seconds() == prolongation_window_seconds
    logger.success("Prolongation window matches")
    assert gate_seal.get_expiration_buffer_seconds() == expiration_buffer_seconds
    logger.success("expiration buffer matches")

    logger.info("Sealing...")
    assert not sealable.isPaused()

    seal_tx = gate_seal.seal_all(sender=deployer)
    logger.success("Sealed")

    assert gate_seal.is_expired()
    logger.success("GateSeal expired")

    seal_timestamp = networks.active_provider.get_block(seal_tx.block_number).timestamp
    assert gate_seal.get_expiry_timestamp() == seal_timestamp
    logger.success("Expiry timestamp updated")
    assert sealable.isPaused()
    logger.success("Sealable paused")

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
