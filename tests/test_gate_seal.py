import pytest
from ape.exceptions import VirtualMachineError
from utils.constants import (
    MIN_INITIAL_LIFETIME_SECONDS,
    MAX_INITIAL_LIFETIME_SECONDS,
    PROLONGATION_PERIOD_SECONDS,
    TOTAL_LIFETIME_SECONDS,
)


def test_invalid_seal_duration(deploy_gate_seal):
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(seal_duration_seconds_=0)


def test_deploy_fails_with_no_sealables(deploy_gate_seal):
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(sealables_=[])


def test_deploy_fails_with_too_many_sealables(deploy_gate_seal, generate_sealables):
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(sealables_=generate_sealables(9))


def test_deploy_fails_with_duplicate_sealables(deploy_gate_seal, generate_sealables):
    sealables = generate_sealables(1)
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(sealables_=sealables * 2)


def test_deploy_fails_with_too_short_initial_lifetime(deploy_gate_seal):
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(initial_lifetime_seconds_=MIN_INITIAL_LIFETIME_SECONDS - 1)


def test_deploy_fails_with_too_long_initial_lifetime(deploy_gate_seal):
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(initial_lifetime_seconds_=MAX_INITIAL_LIFETIME_SECONDS + 1)


def test_deploy_fails_with_too_many_prolongations(deploy_gate_seal):
    prolongations = 4
    calculated_total_lifetime = (
        MAX_INITIAL_LIFETIME_SECONDS + PROLONGATION_PERIOD_SECONDS * prolongations
    )
    # ensure calculated total lifetime exceeds the total (5 years), so deployment must revert
    assert calculated_total_lifetime > TOTAL_LIFETIME_SECONDS
    with pytest.raises(VirtualMachineError, match="total lifetime: exceeds max"):
        deploy_gate_seal(
            prolongations_=prolongations,
            initial_lifetime_seconds_=MAX_INITIAL_LIFETIME_SECONDS,
        )


def test_prolongation_too_early(
    networks,
    gate_seal,
    sealing_committee,
):
    window_start = gate_seal.get_prolongation_window_start()
    networks.active_provider.set_timestamp(
        window_start
        - 25  # shift back to land in previous slot (12s slot time + buffer)
    )
    networks.active_provider.mine()
    with pytest.raises(VirtualMachineError, match="prolongation window: too early"):
        gate_seal.prolongLifetime(sender=sealing_committee)


def test_prolongation_too_late(
    networks,
    gate_seal,
    sealing_committee,
):
    window_end = gate_seal.get_prolongation_window_end()
    networks.active_provider.set_timestamp(window_end + 1)
    networks.active_provider.mine()
    with pytest.raises(VirtualMachineError, match="prolongation window: expired"):
        gate_seal.prolongLifetime(sender=sealing_committee)


def test_seal_and_fail_to_prolong(
    project,
    sealing_committee,
    sealables,
    gate_seal,
):
    assert not gate_seal.is_expired()
    tx = gate_seal.seal(sender=sealing_committee)
    assert tx.events[0].sealed_by == sealing_committee
    assert tx.events[0].sealed_for == gate_seal.get_seal_duration_seconds()
    assert tx.events[0].sealable == sealables[0]
    assert gate_seal.is_expired()

    for addr in sealables:
        assert project.SealableMock.at(addr).isPaused()

    with pytest.raises(VirtualMachineError, match="gate seal: expired"):
        gate_seal.prolongLifetime(sender=sealing_committee)


def test_prolongation_in_window(
    networks,
    gate_seal,
    sealing_committee,
):
    window_start = gate_seal.get_prolongation_window_start()
    expiry = gate_seal.get_expiry_timestamp()
    prolongations_remaining = gate_seal.get_prolongations_remaining()
    prolongation_period = gate_seal.get_prolongation_period_seconds()
    networks.active_provider.set_timestamp(window_start + 1)
    networks.active_provider.mine()
    tx = gate_seal.prolongLifetime(sender=sealing_committee)

    assert tx.events[0].prolonged_by == sealing_committee
    assert tx.events[0].prolongations_remaining == prolongations_remaining - 1
    assert tx.events[0].new_expiry == expiry + prolongation_period

    assert gate_seal.get_expiry_timestamp() == expiry + prolongation_period
    assert gate_seal.get_prolongations_remaining() == prolongations_remaining - 1


def test_cannot_prolong_twice(
    networks,
    gate_seal,
    sealing_committee,
):
    window_start = gate_seal.get_prolongation_window_start()
    networks.active_provider.set_timestamp(window_start + 1)
    networks.active_provider.mine()
    gate_seal.prolongLifetime(sender=sealing_committee)
    with pytest.raises(VirtualMachineError, match="prolongation window: too early"):
        gate_seal.prolongLifetime(sender=sealing_committee)


def test_seal_under_invalid_committee(gate_seal, stranger):
    with pytest.raises(VirtualMachineError):
        gate_seal.seal(sender=stranger)


def test_prolong_under_invalid_committee(gate_seal, stranger):
    with pytest.raises(VirtualMachineError):
        gate_seal.prolongLifetime(sender=stranger)
