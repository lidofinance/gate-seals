from ape.exceptions import VirtualMachineError
import pytest
import random
from utils.constants import (
    MAX_SEAL_DURATION_SECONDS,
    MAX_SEALABLES,
    MIN_SEAL_DURATION_SECONDS,
    ZERO_ADDRESS,
    MAX_PROLONGATIONS,
    MIN_LIFETIME_DURATION_SECONDS,
    MAX_LIFETIME_DURATION_SECONDS,
    MIN_PROLONGATION_WINDOW_SECONDS,
    MAX_PROLONGATION_WINDOW_SECONDS,
)


# TESTS FOR _sealing_committee
def test_committee_cannot_be_zero_address(
    project,
    deployer,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
    now,
):
    with pytest.raises(VirtualMachineError, match="sealing committee: zero address"):
        project.GateSeal.deploy(
            ZERO_ADDRESS,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


# TESTS FOR _seal_duration_seconds
def test_seal_duration_too_short(
    project,
    deployer,
    sealing_committee,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
    now,
):
    with pytest.raises(VirtualMachineError, match="seal duration: too short"):
        project.GateSeal.deploy(
            sealing_committee,
            MIN_SEAL_DURATION_SECONDS - 1,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


def test_seal_duration_shortest(
    project,
    deployer,
    sealing_committee,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        MIN_SEAL_DURATION_SECONDS,
        sealables,
        lifetime_duration_seconds,
        max_prolongations,
        prolongation_window_seconds,
        sender=deployer,
    )

    assert (
        gate_seal.get_seal_duration_seconds() == MIN_SEAL_DURATION_SECONDS
    ), f"seal duration must be {MIN_SEAL_DURATION_SECONDS} seconds"


def test_seal_duration_max(
    project,
    deployer,
    sealing_committee,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        MAX_SEAL_DURATION_SECONDS,
        sealables,
        lifetime_duration_seconds,
        max_prolongations,
        prolongation_window_seconds,
        sender=deployer,
    )

    assert (
        gate_seal.get_seal_duration_seconds() == MAX_SEAL_DURATION_SECONDS
    ), f"seal duration must be {MAX_SEAL_DURATION_SECONDS} seconds"


def test_seal_duration_exceeds_max(
    project,
    deployer,
    sealing_committee,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):
    with pytest.raises(VirtualMachineError, match="seal duration: exceeds max"):
        project.GateSeal.deploy(
            sealing_committee,
            MAX_SEAL_DURATION_SECONDS + 1,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


# TESTS FOR _sealables
def test_sealables_cannot_be_empty(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):
    with pytest.raises(VirtualMachineError, match="sealables: empty list"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            [],
            lifetime_duration_seconds,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


@pytest.mark.parametrize("zero_address_index", range(MAX_SEALABLES))
def test_sealables_cannot_include_zero_address(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    lifetime_duration_seconds,
    zero_address_index,
    generate_sealables,
    max_prolongations,
    prolongation_window_seconds,
):
    sealables = generate_sealables(MAX_SEALABLES)
    sealables[zero_address_index] = ZERO_ADDRESS

    with pytest.raises(VirtualMachineError, match="sealables: includes zero address"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


def test_sealables_cannot_include_duplicates(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):
    if len(sealables) == MAX_SEALABLES:
        sealables[-1] = sealables[0]
    else:
        sealables.append(sealables[0])

    with pytest.raises(VirtualMachineError, match="sealables: includes duplicates"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


def test_sealables_cannot_exceed_max_length(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    lifetime_duration_seconds,
    generate_sealables,
    max_prolongations,
    prolongation_window_seconds,
):
    sealables = generate_sealables(MAX_SEALABLES + 1)

    with pytest.raises(VirtualMachineError):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


# TESTS FOR _lifetime_duration_seconds
def test_lifetime_duration_too_short(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    max_prolongations,
    prolongation_window_seconds,
):
    with pytest.raises(
        VirtualMachineError, match="lifetime duration: too short"
    ):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            MIN_LIFETIME_DURATION_SECONDS - 1,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


def test_lifetime_duration_exceeds_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):

    with pytest.raises(
        VirtualMachineError, match="lifetime duration: exceeds max"
    ):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            MAX_LIFETIME_DURATION_SECONDS + 1,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


def test_prolongation_window_bounds(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
):
    with pytest.raises(VirtualMachineError, match="prolongation window: too short"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            MIN_PROLONGATION_WINDOW_SECONDS - 1,
            sender=deployer,
        )

    with pytest.raises(VirtualMachineError, match="prolongation window: exceeds max"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            MAX_PROLONGATION_WINDOW_SECONDS + 1,
            sender=deployer,
        )


def test_prolong_lifetime_window(
    project,
    gate_seal,
    sealing_committee,
    lifetime_duration_seconds,
    prolongation_window_seconds,
):
    with pytest.raises(VirtualMachineError, match="prolongation window: too early"):
        gate_seal.prolongLifetime(sender=sealing_committee)

    expiry = gate_seal.get_expiry_timestamp()
    project.provider.set_timestamp(expiry - prolongation_window_seconds)
    project.provider.mine()
    gate_seal.prolongLifetime(sender=sealing_committee)
    assert gate_seal.get_expiry_timestamp() == expiry + lifetime_duration_seconds


# TESTS FOR _max_prolongations
def test_max_prolongations_cannot_exceed_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    prolongation_window_seconds,
):
    with pytest.raises(VirtualMachineError, match="max prolongations: exceeds max"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            MAX_PROLONGATIONS + 1,
            prolongation_window_seconds,
            sender=deployer,
        )


def test_max_prolongations_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    prolongation_window_seconds,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        MAX_PROLONGATIONS,
        prolongation_window_seconds,
        sender=deployer,
    )
    assert (
        gate_seal.get_prolongations_remaining() == MAX_PROLONGATIONS
    ), f"max_prolongations remaining must be max: {MAX_PROLONGATIONS}"


def test_max_prolongations_zero(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        0,
        MIN_PROLONGATION_WINDOW_SECONDS,
        sender=deployer,
    )
    assert (
        gate_seal.get_prolongations_remaining() == 0
    ), "max_prolongations remaining must be zero"


def test_max_prolongations_zero_allows_nonzero_window(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        0,
        MIN_PROLONGATION_WINDOW_SECONDS,
        sender=deployer,
    )
    assert gate_seal.get_prolongations_remaining() == 0


def test_prolongation_window_cannot_exceed_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
):
    with pytest.raises(VirtualMachineError, match="prolongation window: exceeds max"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            MAX_PROLONGATION_WINDOW_SECONDS + 1,
            sender=deployer,
        )


def test_prolongation_window_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        max_prolongations,
        MAX_PROLONGATION_WINDOW_SECONDS,
        sender=deployer,
    )
    assert (
        gate_seal.get_prolongation_window_seconds()
        == MAX_PROLONGATION_WINDOW_SECONDS
    ), "prolongation window must be max"


def test_prolongation_window_must_be_positive(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
):
    with pytest.raises(
        VirtualMachineError, match="prolongation window: too short"
    ):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            0,
            sender=deployer,
        )


# other tests
def test_deploy_params_must_match(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
    now,
):
    expected_timestamp = now() + lifetime_duration_seconds
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        max_prolongations,
        prolongation_window_seconds,
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
        gate_seal.get_lifetime_duration_seconds() == lifetime_duration_seconds
    ), "lifetime duration doesn't match"
    assert (
        gate_seal.get_expiry_timestamp() == expected_timestamp
    ), "expiry timestamp don't match"
    assert not gate_seal.is_expired(), "should not be expired"


def test_seal_all(
    now,
    project,
    gate_seal,
    sealing_committee,
    seal_duration_seconds,
    sealables,
):
    expected_timestamp = now()
    tx = gate_seal.seal(sealables, sender=sealing_committee)

    for i, event in enumerate(tx.events):
        assert event.event_name == "Sealed"
        assert event.sealed_by == sealing_committee
        assert event.sealed_for == seal_duration_seconds
        assert event.sealable == sealables[i]
        assert event.sealed_at == expected_timestamp

    assert (
        gate_seal.get_expiry_timestamp() == expected_timestamp
    ), "expiry timestamp matches"

    assert gate_seal.is_expired(), "gate seal must be expired immediately after sealing"

    for sealable in sealables:
        assert project.SealableMock.at(sealable).isPaused(), "sealable must be sealed"


def test_seal_partial(
    now,
    project,
    gate_seal,
    sealing_committee,
    seal_duration_seconds,
    sealables,
):
    expected_timestamp = now()
    sealables_to_seal = [sealables[0]]

    tx = gate_seal.seal(sealables_to_seal, sender=sealing_committee)

    for i, event in enumerate(tx.events):
        assert event.event_name == "Sealed"
        assert event.sealed_by == sealing_committee
        assert event.sealed_for == seal_duration_seconds
        assert event.sealable == sealables_to_seal[i]
        assert event.sealed_at == expected_timestamp

    assert gate_seal.is_expired(), "gate seal must be expired immediately after sealing"
    assert (
        gate_seal.get_expiry_timestamp() == expected_timestamp
    )

    for sealable in sealables:
        sealable_contract = project.SealableMock.at(sealable)
        if sealable in sealables_to_seal:
            assert sealable_contract.isPaused(), "sealable must be sealed"
        else:
            assert not sealable_contract.isPaused(), "sealable must not be sealed"


def test_natural_expiry(networks, gate_seal):
    expiry_timestamp = gate_seal.get_expiry_timestamp()
    networks.active_provider.set_timestamp(expiry_timestamp - 1)
    networks.active_provider.mine()

    assert not gate_seal.is_expired(), "expired prematurely"

    networks.active_provider.set_timestamp(expiry_timestamp)
    networks.active_provider.mine()

    assert gate_seal.is_expired(), "must already be expired"


def test_seal_as_stranger(gate_seal, stranger, sealables):
    with pytest.raises(VirtualMachineError, match="sender: not SEALING_COMMITTEE"):
        gate_seal.seal(sealables, sender=stranger)


def test_seal_empty_subset(gate_seal, sealing_committee):
    with pytest.raises(VirtualMachineError, match="sealables: empty subset"):
        gate_seal.seal([], sender=sealing_committee)


def test_seal_duplicates(gate_seal, sealables, sealing_committee):
    if len(sealables) == MAX_SEALABLES:
        sealables[-1] = sealables[0]
    else:
        sealables.append(sealables[0])
    with pytest.raises(VirtualMachineError, match="sealables: includes duplicates"):
        gate_seal.seal(sealables, sender=sealing_committee)


def test_seal_nonintersecting_subset(accounts, gate_seal, sealing_committee):
    with pytest.raises(VirtualMachineError, match="sealables: includes a non-sealable"):
        gate_seal.seal([accounts[0]], sender=sealing_committee)


def test_seal_partially_intersecting_subset(
    accounts, gate_seal, sealing_committee, sealables
):
    with pytest.raises(VirtualMachineError, match="sealables: includes a non-sealable"):
        gate_seal.seal([sealables[0], accounts[0]], sender=sealing_committee)


def test_seal_only_once(gate_seal, sealing_committee, sealables):
    gate_seal.seal(sealables, sender=sealing_committee)

    with pytest.raises(VirtualMachineError, match="gate seal: expired"):
        gate_seal.seal(sealables, sender=sealing_committee)


@pytest.mark.parametrize("failing_index", range(MAX_SEALABLES))
def test_single_failed_sealable_error_message(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    lifetime_duration_seconds,
    failing_index,
    generate_sealables,
    max_prolongations,
    prolongation_window_seconds,
):
    sealables = generate_sealables(MAX_SEALABLES)
    unpausable = random.choice([True, False])
    should_revert = not unpausable
    sealables[failing_index] = generate_sealables(1, unpausable, should_revert)[0]

    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        max_prolongations,
        prolongation_window_seconds,
        sender=deployer,
    )

    with pytest.raises(VirtualMachineError, match=str(failing_index)):
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
    lifetime_duration_seconds,
    generate_sealables,
    max_prolongations,
    prolongation_window_seconds,
    repeat,
):
    sealables = generate_sealables(MAX_SEALABLES)

    failed = random.sample(range(MAX_SEALABLES), random.choice(range(1, MAX_SEALABLES)))

    unpausable = True
    should_revert = False

    for index in failed:
        sealables[index] = generate_sealables(1, unpausable, should_revert)[0]

    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        max_prolongations,
        prolongation_window_seconds,
        sender=deployer,
    )

    failed.sort()
    failed.reverse()
    with pytest.raises(VirtualMachineError, match="".join([str(n) for n in failed])):
        gate_seal.seal(
            sealables,
            sender=sealing_committee,
        )


@pytest.mark.skip("only run this with automining disabled")
def test_cannot_seal_twice_in_one_tx(gate_seal, sealables, sealing_committee):
    gate_seal.seal(sealables, sender=sealing_committee)
    with pytest.raises(VirtualMachineError, match="gate seal: expired"):
        gate_seal.seal(sealables, sender=sealing_committee)


def test_raw_call_success_should_be_false_when_sealable_reverts_on_pause(
    project,
    deployer,
    generate_sealables,
    sealing_committee,
    seal_duration_seconds,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):
    """
        `raw_call` without `max_outsize` and with `revert_on_failure=True` for some reason returns the boolean value of memory[0] :^)

        Which is why we specify `max_outsize=32`, even though don't actually use it.

        To test that `success` returns actual value instead of returning bool of memory[0],
        we need to pause the contract before the sealing,
        so that the condition `success and is_paused()` is false (i.e `False and True`), see GateSeal.vy::seal()

    For that, we use `force_pause_for` on SealableMock to ignore any checks and forcefully pause the contract.
    After calling this function, the SealableMock is paused but the call to `pauseFor` will still revert,
    thus the returned `success` should be False, the condition fails and the call reverts altogether.

        Without `max_outsize=32`, the transaction would not revert.
    """

    unpausable = False
    should_revert = True
    # we'll use only 1 sealable
    sealables = generate_sealables(1, unpausable, should_revert)

    # deploy GateSeal
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        max_prolongations,
        prolongation_window_seconds,
        sender=deployer,
    )

    # making sure we have the right contract
    assert gate_seal.get_sealables() == sealables

    # forcefully pause the sealable before sealing
    sealables[0].force_pause_for(seal_duration_seconds, sender=deployer)
    assert sealables[0].isPaused(), "should be paused now"

    # seal() should revert because `raw_call` to sealable returns `success=False`, even though isPaused() is True.
    with pytest.raises(VirtualMachineError, match="reverted with reason string '0'"):
        gate_seal.seal(sealables, sender=sealing_committee)


def test_prolong_before_expiry(
    networks,
    gate_seal,
    sealing_committee,
    lifetime_duration_seconds,
    prolongation_window_seconds,
    max_prolongations,
):
    old_expiry = gate_seal.get_expiry_timestamp()
    networks.active_provider.set_timestamp(old_expiry - prolongation_window_seconds)
    networks.active_provider.mine()
    gate_seal.prolongLifetime(sender=sealing_committee)
    assert (
        gate_seal.get_expiry_timestamp() == old_expiry + lifetime_duration_seconds
    )
    assert gate_seal.get_prolongations_remaining() == max_prolongations - 1


def test_prolong_after_expiry(
    networks,
    gate_seal,
    sealing_committee,
):
    expiry_timestamp = gate_seal.get_expiry_timestamp()
    networks.active_provider.set_timestamp(expiry_timestamp + 1)
    networks.active_provider.mine()

    with pytest.raises(VirtualMachineError, match="gate seal: expired"):
        gate_seal.prolongLifetime(sender=sealing_committee)


def test_prolong_only_committee(gate_seal, stranger):
    with pytest.raises(VirtualMachineError, match="sender: not SEALING_COMMITTEE"):
        gate_seal.prolongLifetime(sender=stranger)


def test_cannot_prolong_after_seal(gate_seal, sealing_committee, sealables):
    gate_seal.seal(sealables, sender=sealing_committee)
    with pytest.raises(VirtualMachineError, match="gate seal: expired"):
        gate_seal.prolongLifetime(sender=sealing_committee)
