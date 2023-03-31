import sys
from ape import project, accounts, chain, networks
from ape.logging import logger
from eth_utils.address import to_checksum_address
from tests.conftest import sealing_committee
from utils.constants import MAX_EXPIRY_PERIOD_SECONDS
from utils.env import load_env_variable


def main():
    factory_address = load_env_variable("FACTORY")

    if not factory_address:
        sys.exit()

    factory = project.GateSealFactory.at(to_checksum_address(factory_address))

    # simulating GateSeal flow

    deployer = accounts.test_accounts[0]
    sealable = project.SealableMock.deploy(sender=deployer)

    sealing_committee = deployer
    seal_duration_seconds = 60 * 60 * 24 * 7  # week
    sealables = [sealable.address]
    expiry_timestamp = chain.pending_timestamp + MAX_EXPIRY_PERIOD_SECONDS

    tx = factory.create_gate_seal(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    gate_seal_address = tx.events[0].gate_seal

    gate_seal = project.GateSeal.at(gate_seal_address)

    assert gate_seal.get_sealing_committee() == sealing_committee
    assert gate_seal.get_seal_duration_seconds() == seal_duration_seconds
    assert gate_seal.get_sealables() == sealables
    assert gate_seal.get_expiry_timestamp() == expiry_timestamp

    assert not sealable.isPaused()

    seal_tx = gate_seal.seal(sealables, sender=deployer)

    assert gate_seal.is_expired()
    assert gate_seal.get_expiry_timestamp() == 0
    assert sealable.isPaused()

    seal_timestamp = networks.active_provider.get_block(seal_tx.block_number).timestamp

    networks.active_provider.set_timestamp(seal_timestamp + seal_duration_seconds)
    chain.mine()

    assert not sealable.isPaused()
