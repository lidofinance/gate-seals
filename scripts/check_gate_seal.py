import sys
from ape import project, accounts, chain, networks
from ape.logging import logger
from eth_utils.address import to_checksum_address
from tests.conftest import sealables, sealing_committee
from utils.constants import MAX_EXPIRY_PERIOD_SECONDS
from utils.env import load_env_variable


def main():
    gate_seal_address = load_env_variable("GATE_SEAL")

    if not gate_seal_address:
        sys.exit()

    gate_seal = project.GateSeal.at(to_checksum_address(gate_seal_address))

    # simulating GateSeal flow

    with accounts.use_sender(gate_seal.get_sealing_committee()):
        sealables = gate_seal.get_sealables()
        logger.warning(sealables)
        seal_tx = gate_seal.seal(sealables, sender=accounts.test_accounts[0])
        logger.warning("HERE")

        assert gate_seal.is_expired()
        assert gate_seal.get_expiry_timestamp() == 0
        for sealable in sealables:
            assert project.SealableMock.at(sealable).isPaused()

        seal_timestamp = networks.active_provider.get_block(
            seal_tx.block_number
        ).timestamp

        networks.active_provider.set_timestamp(seal_timestamp + seal_duration_seconds)
        chain.mine()

        for sealable in sealables:
            assert not project.SealableMock.at(sealable).isPaused()
