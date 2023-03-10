from ape import project
from ape.logging import logger
from eth_utils.address import to_checksum_address


from utils.config import get_deployer
from utils.env import load_env_variable


def main():
    deployer = get_deployer()
    logger.success(f"Deployer: {deployer}")

    factory_address = load_env_variable("FACTORY")
    logger.success(f"Factory: {factory_address}")

    sealing_committee = load_env_variable("SEALING_COMMITTEE")
    logger.success(f"Sealing committee: {sealing_committee}")

    seal_duration_seconds = int(load_env_variable("SEAL_DURATION_SECONDS"))
    logger.success(f"Seal duration in seconds: {seal_duration_seconds}")

    sealables = load_env_variable("SEALABLES").split(",")
    logger.success(f"Sealables: {sealables}")

    expiry_period = int(load_env_variable("EXPIRY_PERIOD"))
    logger.success(f"Sealables: {expiry_period}")

    factory = project.GateSealFactory.at(to_checksum_address(factory_address))

    transaction = factory.create_gate_seal(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_period,
        sender=deployer,
    )

    logger.success(f"GateSeal deployed to {transaction.events[0].gate_seal}")
