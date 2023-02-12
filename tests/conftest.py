import pytest
import ape
from ape.logging import logger
from utils.blueprint import get_blueprint_address, get_blueprint_initcode
from utils.constants import ZERO_ADDRESS

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
    expiry_period,
    sealing_committee,
    seal_duration,
    sealable_mock,
    sealable_mock_2,
):
    transaction = gate_seal_factory.create_gate_seal(
        sealing_committee,
        seal_duration,
        [
            sealable_mock,
            sealable_mock_2,
        ],
        expiry_period,
        sender=deployer,
    )

    gate_seal_address = transaction.events[0].gate_seal

    return project.GateSeal.at(gate_seal_address)


@pytest.fixture(scope="function")
def sealable_mock(project, deployer):
    return project.SealableMock.deploy(sender=deployer)


@pytest.fixture(scope="function")
def sealable_mock_2(project, deployer):
    return project.SealableMock.deploy(sender=deployer)


@pytest.fixture(scope="function")
def sealable_mock_3(project, deployer):
    return project.SealableMock.deploy(sender=deployer)


"""

    TIME PERIODS

"""


@pytest.fixture(scope="session", params=["week"])
def seal_duration(request):
    return request.getfixturevalue(request.param)


@pytest.fixture(scope="session", params=["year"])
def expiry_period(request):
    return request.getfixturevalue(request.param)


@pytest.fixture(scope="session")
def minute():
    return 60 * 60


@pytest.fixture(scope="session")
def hour(minute):
    return minute * 60


@pytest.fixture(scope="session")
def day(hour):
    return hour * 24


@pytest.fixture(scope="session")
def week(day):
    return day * 7


@pytest.fixture(scope="session")
def year(day):
    return day * 365
