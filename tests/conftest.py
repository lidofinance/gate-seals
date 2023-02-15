from random import randint
import pytest
import ape
from ape.logging import logger
from utils.blueprint import get_blueprint_address, get_blueprint_initcode
from utils.constants import MAX_SEALABLES, MIN_SEALABLES

"""

    ACCOUNTS

"""


@pytest.fixture(scope="session")
def deployer(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def dao_agent(accounts):
    return accounts[1]


@pytest.fixture(scope="session")
def sealing_committee(accounts):
    return accounts[2]


@pytest.fixture(scope="session")
def stranger(accounts):
    return accounts[2]


"""

    CONTRACTS

"""


@pytest.fixture(scope="function")
def blueprint_address(project, deployer):
    gate_seal_bytecode = project.GateSeal.contract_type.deployment_bytecode.bytecode
    gate_seal_initcode = get_blueprint_initcode(gate_seal_bytecode)
    return get_blueprint_address(deployer, gate_seal_initcode)


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
    expiry_period,
):
    transaction = gate_seal_factory.create_gate_seal(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_period,
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
def seal_duration_seconds(week):
    return week


@pytest.fixture(scope="session")
def expiry_period(year):
    return year


@pytest.fixture(scope="session")
def day():
    return 60 * 60 * 24


@pytest.fixture(scope="session")
def week(day):
    return day * 7


@pytest.fixture(scope="session")
def year(day):
    return day * 365


"""

    UTILS

"""


@pytest.fixture(scope="session")
def generate_sealables(project, deployer):
    return lambda n: [project.SealableMock.deploy(sender=deployer) for _ in range(n)]
