from ape import chain, accounts
from ape.logging import logger
from utils.constants import GOERLI_ID, MAINNET_ID
from utils.env import load_env_variable


def get_deployer() -> str:
    if not is_live_network():
        return accounts.test_accounts[0]
    else:
        alias = load_env_variable("DEPLOYER")
        return accounts.load(alias)


def is_live_network() -> bool:
    return chain.chain_id in [MAINNET_ID, GOERLI_ID]  # type: ignore
