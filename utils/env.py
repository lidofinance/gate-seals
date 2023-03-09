import os
import sys
from ape.logging import logger


def load_env_variable(variable_name):
    value = os.getenv(variable_name)
    logger.success(value)
    if value:
        logger.success(f"`{variable_name}` loaded: {value}")
        return value
    else:
        logger.error(f"{variable_name} not found. Exiting...")
        sys.exit()
