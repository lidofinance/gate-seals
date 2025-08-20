import pytest
from random import randint
from utils.blueprint import deploy_blueprint, construct_blueprint_deploy_bytecode
from utils.constants import (
    MAX_SEALABLES,
    MIN_SEALABLES,
    SECONDS_PER_DAY,
)

# Default parameters for contracts under test
PROLONGATION_PERIOD_SECONDS = SECONDS_PER_DAY * 365
PROLONGATION_WINDOW_SECONDS = SECONDS_PER_DAY * 14
PRE_EXPIRATION_OFFSET = SECONDS_PER_DAY * 60
MIN_EXPIRY_OFFSET_SECONDS = PROLONGATION_WINDOW_SECONDS + PRE_EXPIRATION_OFFSET

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
    return project.GateSealFactoryV2.deploy(
        blueprint_address,
        sender=deployer,
    )


@pytest.fixture(scope="function")
def gate_seal(
    project,
    deployer,
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    get_expiry_timestamp,
    prolongation_limit,
    now,
):
    expiry_timestamp = get_expiry_timestamp()
    transaction = gate_seal_factory.create_gate_seal(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        prolongation_limit,
        PROLONGATION_PERIOD_SECONDS,
        PROLONGATION_WINDOW_SECONDS,
        PRE_EXPIRATION_OFFSET,
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
    return SECONDS_PER_DAY * 11


DEFAULT_EXPIRY_OFFSET_SECONDS = MIN_EXPIRY_OFFSET_SECONDS + SECONDS_PER_DAY


@pytest.fixture(scope="function")
def get_expiry_timestamp(now):
    return lambda: now() + DEFAULT_EXPIRY_OFFSET_SECONDS


@pytest.fixture(scope="session")
def prolongation_limit():
    return 1


@pytest.fixture(scope="function")
def now(chain):
    return lambda: chain.pending_timestamp


"""

    UTILS

"""


@pytest.fixture(scope="session")
def generate_sealables(project, deployer):
    def _generate_sealables(n, unpausable=False, reverts=False):
        sealables = []
        for _ in range(n):
            sealable = project.SealableMock.deploy(unpausable, reverts, sender=deployer)
            sealables.append(sealable)
        return sealables

    return _generate_sealables


@pytest.fixture(scope="function")
def normal_sealable(project, deployer):
    return project.SealableMock.deploy(False, False, sender=deployer)


@pytest.fixture(scope="function")
def sealable_with_broken_pause(project, deployer):
    return project.SealableMock.deploy(True, False, sender=deployer)


@pytest.fixture(scope="function")
def reverting_sealable(project, deployer):
    return project.SealableMock.deploy(False, True, sender=deployer)


@pytest.fixture(scope="function")
def deploy_gate_seal(
    project,
    deployer,
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    get_expiry_timestamp,
    prolongation_limit,
    now,
):
    def _deploy_gate_seal(
        sealing_committee_=None,
        seal_duration_seconds_=None,
        sealables_=None,
        expiry_timestamp_=None,
        prolongation_limit_=None,
        prolongation_period_seconds_=None,
        prolongation_window_seconds_=None,
        pre_expiration_offset_=None,
        sender=None,
    ):
        # Use defaults if not overridden
        final_committee = (
            sealing_committee_ if sealing_committee_ is not None else sealing_committee
        )
        final_seal_duration = (
            seal_duration_seconds_
            if seal_duration_seconds_ is not None
            else seal_duration_seconds
        )
        final_sealables = sealables_ if sealables_ is not None else sealables
        final_expiry = (
            expiry_timestamp_
            if expiry_timestamp_ is not None
            else get_expiry_timestamp()
        )
        final_prolongation_limit = (
            prolongation_limit_
            if prolongation_limit_ is not None
            else prolongation_limit
        )
        final_prolongation_period = (
            prolongation_period_seconds_
            if prolongation_period_seconds_ is not None
            else PROLONGATION_PERIOD_SECONDS
        )
        final_prolongation_window = (
            prolongation_window_seconds_
            if prolongation_window_seconds_ is not None
            else PROLONGATION_WINDOW_SECONDS
        )
        final_pre_expiration_offset = (
            pre_expiration_offset_
            if pre_expiration_offset_ is not None
            else PRE_EXPIRATION_OFFSET
        )
        final_sender = sender if sender is not None else deployer

        transaction = gate_seal_factory.create_gate_seal(
            final_committee,
            final_seal_duration,
            final_sealables,
            final_expiry,
            final_prolongation_limit,
            final_prolongation_period,
            final_prolongation_window,
            final_pre_expiration_offset,
            sender=final_sender,
        )

        gate_seal_address = transaction.events[0].gate_seal
        return project.GateSealV2.at(gate_seal_address)

    return _deploy_gate_seal
