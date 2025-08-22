import pytest
from ape.exceptions import VirtualMachineError
from ape.utils import ZERO_ADDRESS
from utils.constants import (
    MAX_SEALABLES,
    TOTAL_LIFETIME_SECONDS,
    SECONDS_PER_DAY,
)
from .conftest import (
    MIN_EXPIRY_OFFSET_SECONDS,
    PROLONGATION_EXTENSION_SECONDS,
    PRE_EXPIRATION_OFFSET,
    PROLONGATION_WINDOW_SECONDS,
)


def test_invalid_seal_duration(deploy_gate_seal):
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(seal_duration_seconds_=0)


def test_deploy_fails_with_no_sealables(deploy_gate_seal):
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(sealables_=[])


def test_deploy_fails_with_too_many_sealables(deploy_gate_seal, generate_sealables):
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(sealables_=generate_sealables(MAX_SEALABLES + 1))


def test_deploy_fails_with_duplicate_sealables(deploy_gate_seal, generate_sealables):
    sealables = generate_sealables(1)
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(sealables_=sealables * 2)


def test_deploy_fails_with_zero_address_in_sealables(
    deploy_gate_seal, generate_sealables
):
    sealables = generate_sealables(1) + [ZERO_ADDRESS]
    with pytest.raises(VirtualMachineError, match="sealables: includes zero address"):
        deploy_gate_seal(sealables_=sealables)


def test_deploy_fails_with_expiry_too_early(deploy_gate_seal, now):
    with pytest.raises(VirtualMachineError, match="expiry timestamp: below minimum"):
        deploy_gate_seal(expiry_timestamp_=now() + MIN_EXPIRY_OFFSET_SECONDS - 1)


def test_deploy_fails_with_too_long_expiry_offset(deploy_gate_seal, now):
    excessive_expiry_offset = PROLONGATION_EXTENSION_SECONDS * 2 + 10
    with pytest.raises(VirtualMachineError, match="expiry timestamp: exceeds max"):
        deploy_gate_seal(expiry_timestamp_=now() + excessive_expiry_offset)


def test_deploy_fails_with_prolongation_extension_too_short(deploy_gate_seal, now):
    too_short_extension = PROLONGATION_WINDOW_SECONDS + PRE_EXPIRATION_OFFSET - 1
    with pytest.raises(
        VirtualMachineError, match="prolongation extension: below minimum"
    ):
        deploy_gate_seal(
            expiry_timestamp_=now() + MIN_EXPIRY_OFFSET_SECONDS,
            prolongation_extension_seconds_=too_short_extension,
        )


def test_deploy_fails_with_prolongation_limit_too_high(deploy_gate_seal, now):
    prolongation_limit = 5
    expiry_offset_seconds = PROLONGATION_EXTENSION_SECONDS + SECONDS_PER_DAY
    calculated_total_lifetime = (
        expiry_offset_seconds + PROLONGATION_EXTENSION_SECONDS * prolongation_limit
    )
    assert (
        calculated_total_lifetime > TOTAL_LIFETIME_SECONDS
    ), "calculated total lifetime should exceed maximum"
    with pytest.raises(VirtualMachineError, match="total lifetime: exceeds max"):
        deploy_gate_seal(
            prolongation_limit_=prolongation_limit,
            expiry_timestamp_=now() + expiry_offset_seconds,
        )


def test_deploy_fails_with_expiry_in_past(deploy_gate_seal, now):
    with pytest.raises(
        VirtualMachineError, match="expiry timestamp: must be in the future"
    ):
        deploy_gate_seal(expiry_timestamp_=now() - 1)


def test_prolongation_too_early(networks, gate_seal, sealing_committee):
    window_start = gate_seal.get_prolongation_window_start()
    networks.active_provider.set_timestamp(window_start - 2)
    networks.active_provider.mine()
    assert not gate_seal.is_in_prolongation_window()
    with pytest.raises(VirtualMachineError, match="prolongation window: not active"):
        gate_seal.prolong_lifetime(sender=sealing_committee)


def test_prolongation_too_late(networks, gate_seal, sealing_committee):
    window_end = gate_seal.get_prolongation_window_end()
    networks.active_provider.set_timestamp(window_end)
    networks.active_provider.mine()
    assert not gate_seal.is_in_prolongation_window()
    with pytest.raises(VirtualMachineError, match="prolongation window: not active"):
        gate_seal.prolong_lifetime(sender=sealing_committee)


def test_sealing_with_seal_all(project, sealing_committee, sealables, gate_seal):
    assert not gate_seal.is_expired()
    tx = gate_seal.seal_all(sender=sealing_committee)

    assert len(tx.events) == len(sealables)

    for i, sealable_addr in enumerate(sealables):
        sealed_event = tx.events[i]
        assert sealed_event.sealed_by == sealing_committee
        assert sealed_event.sealed_for == gate_seal.get_seal_duration_seconds()
        assert sealed_event.sealable == sealable_addr

    assert gate_seal.is_expired()

    for addr in sealables:
        assert project.SealableMock.at(addr).isPaused()


def test_prolong_after_seal(sealing_committee, gate_seal):
    assert not gate_seal.is_expired()
    gate_seal.seal_all(sender=sealing_committee)
    assert gate_seal.is_expired()

    with pytest.raises(VirtualMachineError, match="GateSeal: expired"):
        gate_seal.prolong_lifetime(sender=sealing_committee)

    assert not gate_seal.is_in_prolongation_window()

    assert gate_seal.get_prolongation_window_start() == 0
    assert gate_seal.get_prolongation_window_end() == 0


def test_prolong_in_window_at_the_start(networks, gate_seal, sealing_committee):
    window_start = gate_seal.get_prolongation_window_start()
    expiry = gate_seal.get_expiry_timestamp()
    prolongations_remaining = gate_seal.get_prolongations_remaining()
    prolongation_extension = gate_seal.get_prolongation_extension_seconds()
    networks.active_provider.set_timestamp(window_start)
    networks.active_provider.mine()
    assert gate_seal.is_in_prolongation_window()
    tx = gate_seal.prolong_lifetime(sender=sealing_committee)
    assert not gate_seal.is_in_prolongation_window()
    assert tx.events[0].prolonged_by == sealing_committee
    assert tx.events[0].prolongations_remaining == prolongations_remaining - 1
    assert tx.events[0].new_expiry == expiry + prolongation_extension

    assert gate_seal.get_expiry_timestamp() == expiry + prolongation_extension
    assert gate_seal.get_prolongations_remaining() == prolongations_remaining - 1


def test_prolong_in_window_at_the_end(networks, gate_seal, sealing_committee):
    window_end = gate_seal.get_prolongation_window_end()
    # Use window_end - 2 to account for Hardhat's complex timestamp behavior
    networks.active_provider.set_timestamp(window_end - 2)
    networks.active_provider.mine()
    assert gate_seal.is_in_prolongation_window()
    gate_seal.prolong_lifetime(sender=sealing_committee)
    assert not gate_seal.is_in_prolongation_window()


def test_cannot_prolong_twice(networks, gate_seal, sealing_committee):
    window_start = gate_seal.get_prolongation_window_start()
    networks.active_provider.set_timestamp(window_start)
    networks.active_provider.mine()

    assert gate_seal.is_in_prolongation_window()
    gate_seal.prolong_lifetime(sender=sealing_committee)
    assert not gate_seal.is_in_prolongation_window()

    with pytest.raises(VirtualMachineError, match="prolongations: exhausted"):
        gate_seal.prolong_lifetime(sender=sealing_committee)


def test_prolong_under_invalid_committee(gate_seal, stranger):
    with pytest.raises(VirtualMachineError):
        gate_seal.prolong_lifetime(sender=stranger)


def test_seal_under_invalid_committee(gate_seal, stranger):
    with pytest.raises(VirtualMachineError):
        gate_seal.seal_all(sender=stranger)


def test_prolong_after_natural_expiry_reverts(networks, gate_seal, sealing_committee):
    expiry_timestamp = gate_seal.get_expiry_timestamp()
    networks.active_provider.set_timestamp(expiry_timestamp)
    networks.active_provider.mine()

    assert gate_seal.is_expired()

    with pytest.raises(VirtualMachineError, match="GateSeal: expired"):
        gate_seal.prolong_lifetime(sender=sealing_committee)

    assert gate_seal.get_prolongation_window_start() == 0
    assert gate_seal.get_prolongation_window_end() == 0


def test_seal_after_expiry_reverts(networks, gate_seal, sealing_committee):
    expiry_timestamp = gate_seal.get_expiry_timestamp()
    networks.active_provider.set_timestamp(expiry_timestamp)
    networks.active_provider.mine()

    assert gate_seal.is_expired()

    with pytest.raises(VirtualMachineError, match="GateSeal: expired"):
        gate_seal.seal_all(sender=sealing_committee)


def test_gate_seal_stores_immutables(gate_seal, sealables, sealing_committee):
    assert (
        gate_seal.get_prolongation_extension_seconds() == PROLONGATION_EXTENSION_SECONDS
    )
    assert gate_seal.get_prolongation_window_seconds() == PROLONGATION_WINDOW_SECONDS
    assert gate_seal.get_pre_expiration_offset() == PRE_EXPIRATION_OFFSET
    assert gate_seal.get_sealing_committee() == sealing_committee
    assert gate_seal.get_sealables() == sealables


def test_seal_fails_with_broken_pause_contracts(
    deploy_gate_seal, normal_sealable, sealable_with_broken_pause, sealing_committee
):
    sealables = [normal_sealable.address, sealable_with_broken_pause.address]
    gate_seal = deploy_gate_seal(sealables_=sealables)

    # Index 1 (sealable_with_broken_pause) should fail, bitmap = 1 << 1 = 2
    with pytest.raises(VirtualMachineError, match="reason string '2'"):
        gate_seal.seal_all(sender=sealing_committee)

    assert not gate_seal.is_expired()


def test_seal_fails_with_reverting_contracts(
    deploy_gate_seal, normal_sealable, reverting_sealable, sealing_committee
):
    sealables = [normal_sealable.address, reverting_sealable.address]
    gate_seal = deploy_gate_seal(sealables_=sealables)

    # Index 1 (reverting_sealable) should fail, bitmap = 1 << 1 = 2
    with pytest.raises(VirtualMachineError, match="reason string '2'"):
        gate_seal.seal_all(sender=sealing_committee)

    assert not gate_seal.is_expired()


def test_seal_fails_with_multiple_failed_contracts_bitmap_encoding(
    deploy_gate_seal,
    normal_sealable,
    sealable_with_broken_pause,
    reverting_sealable,
    sealing_committee,
):
    sealables = [
        normal_sealable.address,
        sealable_with_broken_pause.address,
        reverting_sealable.address,
    ]

    gate_seal = deploy_gate_seal(sealables_=sealables)

    # Failed indexes: 1 and 2
    # Bitmap: (1 << 1) | (1 << 2) = 2 | 4 = 6
    with pytest.raises(VirtualMachineError, match="reason string '6'"):
        gate_seal.seal_all(sender=sealing_committee)

    assert not gate_seal.is_expired()


def test_seal_some_with_subset(
    project, sealing_committee, generate_sealables, deploy_gate_seal
):
    test_sealables = generate_sealables(4)
    gate_seal = deploy_gate_seal(sealables_=test_sealables)

    assert not gate_seal.is_expired()

    subset_to_seal = test_sealables[:2]
    remaining_sealables = test_sealables[2:]

    tx = gate_seal.seal_some(subset_to_seal, sender=sealing_committee)

    assert len(tx.events) == len(subset_to_seal)

    for i, sealable_addr in enumerate(subset_to_seal):
        sealed_event = tx.events[i]
        assert sealed_event.sealed_by == sealing_committee
        assert sealed_event.sealed_for == gate_seal.get_seal_duration_seconds()
        assert sealed_event.sealable == sealable_addr

    assert gate_seal.is_expired()

    for addr in subset_to_seal:
        assert project.SealableMock.at(
            addr
        ).isPaused(), f"Sealable {addr} should be paused"

    for addr in remaining_sealables:
        assert not project.SealableMock.at(
            addr
        ).isPaused(), f"Sealable {addr} should NOT be paused"


def test_seal_some_with_empty_list(gate_seal, sealing_committee):
    with pytest.raises(VirtualMachineError, match="sealables: empty subset"):
        gate_seal.seal_some([], sender=sealing_committee)


def test_seal_some_with_duplicates(gate_seal, sealables, sealing_committee):
    duplicates = [sealables[0], sealables[0]]
    with pytest.raises(VirtualMachineError, match="sealables: includes duplicates"):
        gate_seal.seal_some(duplicates, sender=sealing_committee)


def test_seal_some_with_non_sealable(gate_seal, sealing_committee, stranger):
    non_sealable = [stranger.address]
    with pytest.raises(VirtualMachineError, match="sealables: includes a non-sealable"):
        gate_seal.seal_some(non_sealable, sender=sealing_committee)
