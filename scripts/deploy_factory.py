import sys
import os
import json
from ape import networks, project
from ape.logging import logger

from utils.blueprint import (
    construct_blueprint_deploy_bytecode,
    deploy_blueprint,
    verify_blueprint_deploy_preamble,
    verify_eip522_blueprint,
)
from utils.config import get_deployer, is_live_network
from utils.env import load_env_variable


def main():
    logger.info("Loading deployer...")
    deployer = get_deployer()
    logger.success(f"Deployer: {deployer}")

    is_live = is_live_network()

    """
        DEPLOY BLUEPRINT
    """
    gate_seal_bytecode = project.GateSeal.contract_type.deployment_bytecode.bytecode
    blueprint_deploy_bytecode = construct_blueprint_deploy_bytecode(gate_seal_bytecode)
    verify_blueprint_deploy_preamble(blueprint_deploy_bytecode)
    blueprint_address = deploy_blueprint(
        deployer, blueprint_deploy_bytecode, prompt=True
    )

    verify_eip522_blueprint(networks.active_provider.get_code(blueprint_address))
    logger.success(f"Blueprint deployed: {blueprint_address}")

    """
        DEPLOY FACTORY
    """
    max_priority_fee = "50 gwei"
    etherscan_token = load_env_variable("ETHERSCAN_TOKEN", required=is_live)
    publish = bool(etherscan_token)

    logger.info("Factory deploy transaction")
    logger.info(f"Blueprint: {blueprint_address}")
    logger.info(f"Deployer: {deployer}")
    logger.info(f"Max priority fee: {max_priority_fee}")
    logger.info(f"Publish: {publish}")

    logger.info("Proceed?")
    proceed = input("> ")
    if proceed.lower() not in ["y", "yes"]:
        logger.error("Script stopped.")
        sys.exit()

    factory = project.GateSealFactory.deploy(
        blueprint_address,
        sender=deployer,
        max_priority_fee=max_priority_fee,
        publish=publish,
    )

    assert factory.get_blueprint() == blueprint_address

    if is_live_network():
        deployed_filename = (
            f"deployed/{networks.active_provider.network.name}/{factory.address}.json"
        )
        os.makedirs(os.path.dirname(deployed_filename), exist_ok=True)

        with open(deployed_filename, "w") as deployed_file:
            deployed_file.write(
                json.dumps(
                    {
                        "factory": factory.address,
                        "blueprint": blueprint_address,
                        "tx_hash": factory.receipt.txn_hash,
                        "deployer": deployer.address,
                    }
                )
            )

        logger.success(f"Deployed file: {deployed_filename}")
