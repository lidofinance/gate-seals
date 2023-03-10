from ape import reverts
from ape.logging import logger
import pytest

from utils.constants import (
    MAX_SEAL_DURATION_SECONDS,
    MAX_SEALABLES,
    ZERO_ADDRESS,
)


def test_committee_cannot_be_zero_address(
    project, deployer, seal_duration_seconds, sealables, expiry_timestamp
):
    with reverts("sealing committee: zero address"):
        project.GateSeal.deploy(
            ZERO_ADDRESS,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            sender=deployer,
        )


def test_seal_duration_cannot_be_zero(
    project, deployer, sealing_committee, sealables, expiry_timestamp
):
    with reverts("seal duration: zero"):
        project.GateSeal.deploy(
            sealing_committee, 0, sealables, expiry_timestamp, sender=deployer
        )


def test_seal_duration_max(
    project,
    deployer,
    sealing_committee,
    sealables,
    expiry_timestamp,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        MAX_SEAL_DURATION_SECONDS,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    assert (
        gate_seal.get_seal_duration_seconds() == MAX_SEAL_DURATION_SECONDS
    ), "seal duration can be up to 14 days"


def test_seal_duration_exceeds_max(
    project,
    deployer,
    sealing_committee,
    sealables,
    expiry_timestamp,
):
    with reverts("seal duration: exceeds max"):
        project.GateSeal.deploy(
            sealing_committee,
            MAX_SEAL_DURATION_SECONDS + 1,
            sealables,
            expiry_timestamp,
            sender=deployer,
        )


def test_sealables_exceeds_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
):
    with reverts("sealables: empty list"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            [],
            expiry_timestamp,
            sender=deployer,
        )


def test_expiry_timestamp_cannot_be_now(
    project, deployer, sealing_committee, seal_duration_seconds, sealables, now
):
    with reverts("expiry timestamp: must be in the future"):
        project.GateSeal.deploy(
            sealing_committee, seal_duration_seconds, sealables, now, sender=deployer
        )


def test_expiry_timestamp_cannot_exceed_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
):
    with reverts("expiry timestamp: exceeds max expiry period"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp + 1,
            sender=deployer,
        )


@pytest.mark.parametrize("zero_address_index", range(MAX_SEALABLES))
def test_sealables_cannot_include_zero_address(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    zero_address_index,
    generate_sealables,
):
    sealables = generate_sealables(MAX_SEALABLES)
    sealables[zero_address_index] = ZERO_ADDRESS

    with reverts("sealables: includes zero address"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            sender=deployer,
        )


def test_sealables_cannot_exceed_max_length(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    generate_sealables,
):
    sealables = generate_sealables(MAX_SEALABLES + 1)

    with reverts():
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            sender=deployer,
        )


def test_deploy_params_must_match(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    assert (
        gate_seal.get_sealing_committee() == sealing_committee
    ), "sealing committee doesn't match"
    assert (
        gate_seal.get_seal_duration_seconds() == seal_duration_seconds
    ), "seal duration doesn't match"
    assert gate_seal.get_sealables() == sealables, "sealables don't match"
    assert (
        gate_seal.get_expiry_timestamp() == expiry_timestamp
    ), "expiry timestamp don't match"
    assert gate_seal.is_expired() == False, "should not be expired"


def test_seal_all(project, gate_seal, sealing_committee, sealables):
    gate_seal.seal(sealables, sender=sealing_committee)
    assert (
        gate_seal.is_expired() == True
    ), "gate seal must be expired immediately after sealing"

    for sealable in sealables:
        assert project.SealableMock.at(sealable).isPaused(), "sealable must be sealed"


def test_seal_partial(project, gate_seal, sealing_committee, sealables):
    sealable_to_seal = sealables[0]

    gate_seal.seal([sealable_to_seal], sender=sealing_committee)
    assert (
        gate_seal.is_expired() == True
    ), "gate seal must be expired immediately after sealing"

    for sealable in sealables:
        sealable_contract = project.SealableMock.at(sealable)
        if sealable == sealable_to_seal:
            assert sealable_contract.isPaused(), "sealable must be sealed"
        else:
            assert not sealable_contract.isPaused(), "sealable must not be sealed"


def test_seal_as_stranger(gate_seal, stranger, sealables):
    with reverts("sender: not SEALING_COMMITTEE"):
        gate_seal.seal(sealables, sender=stranger)


def test_seal_empty_subset(gate_seal, sealing_committee):
    with reverts("sealables: empty subset"):
        gate_seal.seal([], sender=sealing_committee)


def test_seal_nonintersecting_subset(accounts, gate_seal, sealing_committee):
    with reverts("sealables: includes a non-sealable"):
        gate_seal.seal([accounts[0]], sender=sealing_committee)


def test_seal_partially_intersecting_subset(
    accounts, gate_seal, sealing_committee, sealables
):
    with reverts("sealables: includes a non-sealable"):
        gate_seal.seal([sealables[0], accounts[0]], sender=sealing_committee)


def test_natural_expiry(
    networks,
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    networks.active_provider.set_timestamp(expiry_timestamp)
    networks.active_provider.mine()

    assert not gate_seal.is_expired(), "expired prematurely"

    networks.active_provider.set_timestamp(expiry_timestamp + 1)
    networks.active_provider.mine()

    assert gate_seal.is_expired(), "must already be expired"


def test_seal_only_once(gate_seal, sealing_committee, sealables):
    gate_seal.seal(sealables, sender=sealing_committee)

    with reverts("gate seal: expired"):
        gate_seal.seal(sealables, sender=sealing_committee)
