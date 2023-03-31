import os
import sys
from ape.logging import logger


def load_env_variable(variable_name, required=True) -> str | None:
    value = os.getenv(variable_name)

    if value:
        logger.success(f"`{variable_name}` loaded: {value}")
        return value

    if required:
        logger.error(f"`{variable_name}` not found. Exiting...")
        sys.exit()
    else:
        logger.warning(f"`{variable_name}` not found. Proceeding...")
