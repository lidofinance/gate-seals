import pytest
from random import randint
from ape.logging import logger
from utils.blueprint import deploy_blueprint, construct_blueprint_deploy_bytecode
from utils.constants import (
    MAX_LIFETIME_DURATION_SECONDS,
    MIN_LIFETIME_DURATION_SECONDS,
    MAX_PROLONGATION_WINDOW_SECONDS,
    MIN_PROLONGATION_WINDOW_SECONDS,
    MAX_PROLONGATIONS,
    MAX_SEALABLES,
    MIN_SEALABLES,
)

"""

    ACCOUNTS

"""


@pytest.fixture(scope="session")
def deployer(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def sealing_committee(accounts):
    return accounts[1]


@pytest.fixture(scope="session")
def stranger(accounts):
    return accounts[2]


"""

    CONTRACTS

"""


@pytest.fixture(scope="function")
def blueprint_address(project, deployer):
    gate_seal_bytecode = project.GateSeal.contract_type.deployment_bytecode.bytecode
    gate_seal_deploy_code = construct_blueprint_deploy_bytecode(gate_seal_bytecode)
    return deploy_blueprint(deployer, gate_seal_deploy_code)


@pytest.fixture(scope="function")
def gate_seal_factory(project, deployer, blueprint_address):
    return project.GateSealFactory.deploy(blueprint_address, sender=deployer)


@pytest.fixture(scope="function")
def gate_seal(
    project,
    deployer,
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):
    transaction = gate_seal_factory.create_gate_seal(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        max_prolongations,
        prolongation_window_seconds,
        sender=deployer,
    )

    gate_seal_address = transaction.events[0].gate_seal

    return project.GateSeal.at(gate_seal_address)


@pytest.fixture(scope="function")
def sealables(generate_sealables):
    return generate_sealables(randint(MIN_SEALABLES, MAX_SEALABLES))


"""

    TIME PERIODS

"""


@pytest.fixture(scope="session")
def seal_duration_seconds(day):
    return day * 7


@pytest.fixture(scope="session")
def lifetime_duration_seconds(day):
    return MAX_LIFETIME_DURATION_SECONDS


@pytest.fixture(scope="session")
def max_prolongations():
    return MAX_PROLONGATIONS


@pytest.fixture(scope="session")
def prolongation_window_seconds(day):
    return MIN_PROLONGATION_WINDOW_SECONDS





@pytest.fixture(scope="function")
def now(chain):
    return lambda: chain.pending_timestamp


@pytest.fixture(scope="session")
def day():
    return 60 * 60 * 24


"""

    UTILS

"""


@pytest.fixture(scope="session")
def generate_sealables(project, deployer):
    return lambda n, unpausable=False, reverts=False: [
        project.SealableMock.deploy(unpausable, reverts, sender=deployer)
        for _ in range(n)
    ]
