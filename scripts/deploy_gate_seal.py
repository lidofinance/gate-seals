import json
import os
from ape import project
from ape.logging import logger
from eth_utils.address import to_checksum_address


from utils.config import get_deployer
from utils.env import load_env_variable
from utils.helpers import construct_deployed_filename
from utils.constants import PROLONGATION_PERIOD_SECONDS


def main():
    deployer = get_deployer()
    logger.success(f"Deployer: {deployer}")

    factory_address = load_env_variable("FACTORY")
    sealing_committee = load_env_variable("SEALING_COMMITTEE")
    seal_duration_seconds = int(load_env_variable("SEAL_DURATION_SECONDS"))
    sealables = load_env_variable("SEALABLES").split(",")
    initial_lifetime_seconds = int(load_env_variable("INITIAL_LIFETIME_SECONDS"))
    prolongations = int(load_env_variable("PROLONGATIONS"))

    logger.info(
        f"Deploying GateSeal with {prolongations} prolongations (initial: {initial_lifetime_seconds // (60*60*24)} days → total: {(initial_lifetime_seconds + prolongations * PROLONGATION_PERIOD_SECONDS) // (60*60*24)} days)"
    )

    factory = project.GateSealFactoryV2.at(to_checksum_address(factory_address))

    transaction = factory.create_gate_seal(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        initial_lifetime_seconds,
        prolongations,
        sender=deployer,
        max_priority_fee="5 gwei",
    )

    gate_seal_address = transaction.events[0].gate_seal
    logger.success(f"GateSeal deployed to {gate_seal_address}")

    deployed_filename = construct_deployed_filename(gate_seal_address, "gateseal")
    os.makedirs(os.path.dirname(deployed_filename), exist_ok=True)

    with open(deployed_filename, "w") as deployed_file:
        deployed_file.write(
            json.dumps(
                {
                    "factory": factory.address,
                    "gate_seal": gate_seal_address,
                    "tx_hash": transaction.txn_hash,
                    "deployer": deployer.address,
                    "params": {
                        "sealing_committee": sealing_committee,
                        "seal_duration_seconds": seal_duration_seconds,
                        "sealables": sealables,
                        "initial_lifetime_seconds": initial_lifetime_seconds,
                        "prolongations": prolongations,
                    },
                }
            )
        )

    logger.success(f"Deployed file: {deployed_filename}")
