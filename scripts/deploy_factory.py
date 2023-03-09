from ape.logging import logger
from utils.blueprint import (
    construct_blueprint_deploy_bytecode,
    verify_blueprint_deploy_preamble,
    verify_eip522_blueprint,
    deploy_blueprint,
)
from utils.config import get_deployer
from utils.env import load_env_variable
from ape import project, networks


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
    blueprint_address = deploy_blueprint(deployer, blueprint_deploy_bytecode)
    verify_eip522_blueprint(networks.active_provider.get_code(blueprint_address))
    logger.success(f"Blueprint deployed: {blueprint_address}")

    """
        DEPLOY FACTORY
    """

    factory = project.GateSealFactory.deploy(blueprint_address, sender=deployer)
    assert factory.get_blueprint() == blueprint_address
    logger.success(f"Factory deployed: {factory.address}")
