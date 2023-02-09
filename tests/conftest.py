import pytest


@pytest.fixture(scope="session")
def deployer(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def dao_agent(accounts):
    return accounts[1]


@pytest.fixture(scope="session")
def seal_committee(accounts):
    return accounts[2]


@pytest.fixture(scope="session")
def stranger(accounts):
    return accounts[2]


@pytest.fixture(scope="function")
def gate_seal(project, deployer, dao_agent):
    return project.GateSeal.deploy(dao_agent, sender=deployer)


@pytest.fixture(scope="function")
def sealable_mock(project, deployer):
    return project.SealableMock.deploy(sender=deployer)


@pytest.fixture(scope="function", params=["minute", "hour", "day", "week"])
def seal_duration(request):
    return request.getfixturevalue(request.param)


@pytest.fixture(scope="function", params=["minute", "hour", "day", "week"])
def expiry_period(request):
    return request.getfixturevalue(request.param)


"""

    TIME PERIODS

"""


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
