from ape import networks, project
from ape.logging import logger

from utils.blueprint import (
    construct_blueprint_deploy_bytecode,
    deploy_blueprint,
    verify_blueprint_deploy_preamble,
    verify_eip522_blueprint,
)
from utils.config import get_deployer
from utils.env import load_env_variable


def main():
    logger.info("Loading deployer...")
    deployer = get_deployer()
    logger.success(f"Deployer: {deployer}")

    """
        DEPLOY BLUEPRINT
    """
    gate_seal_bytecode = project.GateSeal.contract_type.deployment_bytecode.bytecode
    blueprint_deploy_bytecode = construct_blueprint_deploy_bytecode(gate_seal_bytecode)
    verify_blueprint_deploy_preamble(blueprint_deploy_bytecode)
    blueprint_address = load_env_variable(
        "BLUEPRINT", required=False
    ) or deploy_blueprint(deployer, blueprint_deploy_bytecode)
    verify_eip522_blueprint(networks.active_provider.get_code(blueprint_address))
    logger.success(f"Blueprint deployed: {blueprint_address}")

    """
        DEPLOY FACTORY
    """

    factory = project.GateSealFactory.deploy(
        blueprint_address, sender=deployer, max_priority_fee="50 gwei", publish=True
    )
    assert factory.get_blueprint() == blueprint_address
    logger.success(f"Factory deployed: {factory.address}")
