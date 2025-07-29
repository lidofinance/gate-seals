import pytest
from ape.exceptions import VirtualMachineError
from utils.constants import (
    PROLONGATION_PERIOD_SECONDS,
    PROLONGATION_WINDOW_SECONDS,
    DAO_RESERVE_SECONDS,
    MIN_INITIAL_LIFETIME_SECONDS,
    MAX_INITIAL_LIFETIME_SECONDS,
    SECONDS_PER_DAY,
)


def test_deploy_and_seal_all(
    project, deploy_gate_seal, sealing_committee, generate_sealables
):
    sealables = generate_sealables(2)
    gate_seal = deploy_gate_seal(
        sealing_committee,
        sealables,
        PROLONGATION_PERIOD_SECONDS,
        1,
    )

    gate_seal.seal(sender=sealing_committee)
    assert gate_seal.is_expired()
    for addr in sealables:
        assert project.SealableMock.at(addr).isPaused()


def test_prolongation_in_window(
    networks,
    deploy_gate_seal,
    sealing_committee,
    generate_sealables,
):
    gate_seal = deploy_gate_seal(
        sealing_committee,
        generate_sealables(1),
        PROLONGATION_PERIOD_SECONDS,
        1,
    )

    expiry = gate_seal.get_expiry_timestamp()
    networks.active_provider.set_timestamp(
        expiry - (DAO_RESERVE_SECONDS + PROLONGATION_WINDOW_SECONDS) + 1
    )
    networks.active_provider.mine()
    tx = gate_seal.prolongLifetime(sender=sealing_committee)
    assert tx.events[0].prolongations_remaining == 0
    assert tx.events[0].new_expiry == expiry + PROLONGATION_PERIOD_SECONDS
    assert gate_seal.get_expiry_timestamp() == expiry + PROLONGATION_PERIOD_SECONDS
    assert gate_seal.get_prolongations_remaining() == 0


def test_prolongation_too_early(
    networks,
    deploy_gate_seal,
    sealing_committee,
    generate_sealables,
):
    gate_seal = deploy_gate_seal(
        sealing_committee,
        generate_sealables(1),
        PROLONGATION_PERIOD_SECONDS,
        1,
    )

    expiry = gate_seal.get_expiry_timestamp()
    too_early = (
        expiry
        - (DAO_RESERVE_SECONDS + PROLONGATION_WINDOW_SECONDS)
        - PROLONGATION_WINDOW_SECONDS
    )
    networks.active_provider.set_timestamp(too_early)
    networks.active_provider.mine()
    with pytest.raises(VirtualMachineError, match="prolongation window: too early"):
        gate_seal.prolongLifetime(sender=sealing_committee)


def test_prolongation_too_late(
    networks,
    deploy_gate_seal,
    sealing_committee,
    generate_sealables,
):
    gate_seal = deploy_gate_seal(
        sealing_committee,
        generate_sealables(1),
        PROLONGATION_PERIOD_SECONDS,
        1,
    )

    expiry = gate_seal.get_expiry_timestamp()
    too_late = expiry - DAO_RESERVE_SECONDS + 1
    networks.active_provider.set_timestamp(too_late)
    networks.active_provider.mine()
    with pytest.raises(VirtualMachineError, match="prolongation window: expired"):
        gate_seal.prolongLifetime(sender=sealing_committee)


def test_total_lifetime_limit(
    deploy_gate_seal, sealing_committee, generate_sealables
):
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(
            sealing_committee,
            generate_sealables(1),
            PROLONGATION_PERIOD_SECONDS * 2,
            4,
        )


def test_initial_lifetime_too_short(
    deploy_gate_seal, sealing_committee, generate_sealables
):
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(
            sealing_committee,
            generate_sealables(1),
            MIN_INITIAL_LIFETIME_SECONDS - 1,
            1,
        )


def test_initial_lifetime_too_long(
    deploy_gate_seal, sealing_committee, generate_sealables
):
    with pytest.raises(VirtualMachineError):
        deploy_gate_seal(
            sealing_committee,
            generate_sealables(1),
            MAX_INITIAL_LIFETIME_SECONDS + 1,
            1,
        )


def test_cannot_prolong_twice(
    networks,
    deploy_gate_seal,
    sealing_committee,
    generate_sealables,
):
    gate_seal = deploy_gate_seal(
        sealing_committee,
        generate_sealables(1),
        PROLONGATION_PERIOD_SECONDS,
        2,
    )

    expiry = gate_seal.get_expiry_timestamp()
    networks.active_provider.set_timestamp(
        expiry - (DAO_RESERVE_SECONDS + PROLONGATION_WINDOW_SECONDS) + 1
    )
    networks.active_provider.mine()
    gate_seal.prolongLifetime(sender=sealing_committee)
    with pytest.raises(VirtualMachineError, match="prolongation window: too early"):
        gate_seal.prolongLifetime(sender=sealing_committee)


def test_prolongation_view_functions(
    networks,
    deploy_gate_seal,
    sealing_committee,
    generate_sealables,
):
    gate_seal = deploy_gate_seal(
        sealing_committee,
        generate_sealables(1),
        PROLONGATION_PERIOD_SECONDS,
        1,
    )

    start, end = gate_seal.get_prolongation_window()
    networks.active_provider.set_timestamp(start + 1)
    networks.active_provider.mine()
    assert gate_seal.is_in_prolongation_window()
    gate_seal.prolongLifetime(sender=sealing_committee)
