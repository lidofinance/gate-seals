import pytest
from random import randint
from utils.blueprint import deploy_blueprint, construct_blueprint_deploy_bytecode
from utils.constants import (
    PROLONGATION_PERIOD_SECONDS,
    MAX_SEALABLES,
    MIN_SEALABLES,
    SECONDS_PER_DAY,
)
from utils.helpers import calculated_max_prolongations

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
    gate_seal_bytecode = project.GateSealV2.contract_type.deployment_bytecode.bytecode
    gate_seal_deploy_code = construct_blueprint_deploy_bytecode(gate_seal_bytecode)
    return deploy_blueprint(deployer, gate_seal_deploy_code)


@pytest.fixture(scope="function")
def gate_seal_factory(project, deployer, blueprint_address):
    return project.GateSealFactoryV2.deploy(blueprint_address, sender=deployer)


@pytest.fixture(scope="function")
def gate_seal(
    project,
    deployer,
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    initial_lifetime_seconds,
    max_prolongations,
):
    transaction = gate_seal_factory.create_gate_seal(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        initial_lifetime_seconds,
        max_prolongations,
        sender=deployer,
    )

    gate_seal_address = transaction.events[0].gate_seal

    return project.GateSealV2.at(gate_seal_address)


@pytest.fixture(scope="function")
def sealables(generate_sealables):
    return generate_sealables(randint(MIN_SEALABLES, MAX_SEALABLES))


"""

    TIME PERIODS

"""


@pytest.fixture(scope="session")
def seal_duration_seconds():
    return SECONDS_PER_DAY * 11  # 11 days for DG compatibility


@pytest.fixture(scope="session")
def initial_lifetime_seconds():
    return PROLONGATION_PERIOD_SECONDS


@pytest.fixture(scope="session")
def max_prolongations(initial_lifetime_seconds):
    return calculated_max_prolongations(initial_lifetime_seconds)


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
