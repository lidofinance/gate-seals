import json
import os
from ape import project
from ape.logging import logger
from eth_utils.address import to_checksum_address


from utils.config import get_deployer
from utils.env import load_env_variable
from utils.helpers import construct_deployed_filename


def main():
    deployer = get_deployer()
    logger.success(f"Deployer: {deployer}")

    factory_address = load_env_variable("FACTORY")
    sealing_committee = load_env_variable("SEALING_COMMITTEE")
    seal_duration_seconds = int(load_env_variable("SEAL_DURATION_SECONDS"))
    sealables = load_env_variable("SEALABLES").split(",")
    expiry_timestamp = int(load_env_variable("EXPIRY_TIMESTAMP"))
    prolongation_limit = int(load_env_variable("PROLONGATION_LIMIT"))
    prolongation_extension_seconds = int(
        load_env_variable("PROLONGATION_EXTENSION_SECONDS")
    )
    prolongation_window_seconds = int(load_env_variable("PROLONGATION_WINDOW_SECONDS"))
    pre_expiration_offset = int(load_env_variable("PRE_EXPIRATION_OFFSET"))

    factory = project.GateSealFactoryV2.at(to_checksum_address(factory_address))

    logger.info(f"Deploying GateSeal with {prolongation_limit} prolongations")

    transaction = factory.create_gate_seal(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        prolongation_limit,
        prolongation_extension_seconds,
        prolongation_window_seconds,
        pre_expiration_offset,
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
                        "expiry_timestamp": expiry_timestamp,
                        "prolongation_limit": prolongation_limit,
                        "prolongation_extension_seconds": prolongation_extension_seconds,
                        "prolongation_window_seconds": prolongation_window_seconds,
                        "pre_expiration_offset": pre_expiration_offset,
                    },
                }
            )
        )

    logger.success(f"Deployed file: {deployed_filename}")
