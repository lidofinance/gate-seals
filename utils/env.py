import os
import sys
from ape.logging import logger


def load_env_variable(variable_name) -> str:
    value = os.getenv(variable_name)

    if value:
        logger.success(f"`{variable_name}` loaded: {value}")
        return value

    logger.error(f"`{variable_name}` not found. Exiting...")
    sys.exit()
