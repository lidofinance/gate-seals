from ape import reverts
from ape.logging import logger
import pytest
import random


from utils.constants import (
    MAX_SEAL_DURATION_SECONDS,
    MAX_SEALABLES,
    MIN_SEAL_DURATION_SECONDS,
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


def test_seal_duration_too_short(
    project, deployer, sealing_committee, sealables, expiry_timestamp
):
    with reverts("seal duration: too short"):
        project.GateSeal.deploy(
            sealing_committee,
            MIN_SEAL_DURATION_SECONDS - 1,
            sealables,
            expiry_timestamp,
            sender=deployer,
        )


def test_seal_duration_shortest(
    project, deployer, sealing_committee, sealables, expiry_timestamp
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        MIN_SEAL_DURATION_SECONDS,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    assert (
        gate_seal.get_seal_duration_seconds() == MIN_SEAL_DURATION_SECONDS
    ), "seal duration can be at least 4 days"


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


def test_sealables_cannot_include_duplicates(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
):
    sealables[1] = sealables[0]

    with reverts("sealables: includes duplicates"):
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


def test_seal_all(
    networks,
    chain,
    project,
    gate_seal,
    sealing_committee,
    seal_duration_seconds,
    sealables,
):
    expected_timestamp = chain.pending_timestamp
    tx = gate_seal.seal(sealables, sender=sealing_committee)

    for i, event in enumerate(tx.events):
        assert event.event_name == "Sealed"
        assert event.gate_seal == gate_seal.address
        assert event.sealed_by == sealing_committee
        assert event.sealed_for == seal_duration_seconds
        assert event.sealable == sealables[i]
        assert event.sealed_at == expected_timestamp

    assert (
        gate_seal.get_expiry_timestamp() == expected_timestamp
    ), "expiry timestamp matches"

    networks.active_provider.mine()
    assert (
        gate_seal.is_expired() == True
    ), "gate seal must be expired immediately after sealing"

    for sealable in sealables:
        assert project.SealableMock.at(sealable).isPaused(), "sealable must be sealed"


def test_seal_partial(
    networks,
    chain,
    project,
    gate_seal,
    sealing_committee,
    seal_duration_seconds,
    sealables,
):
    expected_timestamp = chain.pending_timestamp
    sealables_to_seal = [sealables[0]]

    tx = gate_seal.seal(sealables_to_seal, sender=sealing_committee)

    for i, event in enumerate(tx.events):
        assert event.event_name == "Sealed"
        assert event.gate_seal == gate_seal.address
        assert event.sealed_by == sealing_committee
        assert event.sealed_for == seal_duration_seconds
        assert event.sealable == sealables_to_seal[i]
        assert event.sealed_at == expected_timestamp

    networks.active_provider.mine()
    assert (
        gate_seal.is_expired() == True
    ), "gate seal must be expired immediately after sealing"

    for sealable in sealables:
        sealable_contract = project.SealableMock.at(sealable)
        if sealable in sealables_to_seal:
            assert sealable_contract.isPaused(), "sealable must be sealed"
        else:
            assert not sealable_contract.isPaused(), "sealable must not be sealed"


def test_seal_as_stranger(gate_seal, stranger, sealables):
    with reverts("sender: not SEALING_COMMITTEE"):
        gate_seal.seal(sealables, sender=stranger)


def test_seal_empty_subset(gate_seal, sealing_committee):
    with reverts("sealables: empty subset"):
        gate_seal.seal([], sender=sealing_committee)


def test_seal_duplicates(gate_seal, sealables, sealing_committee):
    sealables_with_duplicates = sealables + [sealables[0]]
    with reverts("sealables: includes duplicates"):
        gate_seal.seal(sealables_with_duplicates, sender=sealing_committee)


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


@pytest.mark.parametrize("unpausable_index", range(MAX_SEALABLES))
def test_single_failed_sealable_error_message(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    unpausable_index,
    generate_sealables,
):
    sealables = generate_sealables(MAX_SEALABLES)
    sealables[unpausable_index] = generate_sealables(1, True)[0]

    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    with reverts(f"{unpausable_index}"):
        gate_seal.seal(
            sealables,
            sender=sealing_committee,
        )


@pytest.mark.parametrize("repeat", range(10))
def test_several_failed_sealables_error_message(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    generate_sealables,
    repeat,
):
    sealables = generate_sealables(MAX_SEALABLES)

    failed = random.sample(range(MAX_SEALABLES), random.choice(range(1, MAX_SEALABLES)))

    for index in failed:
        sealables[index] = generate_sealables(1, True)[0]

    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    failed.sort()
    failed.reverse()
    with reverts("".join([str(n) for n in failed])):
        gate_seal.seal(
            sealables,
            sender=sealing_committee,
        )
