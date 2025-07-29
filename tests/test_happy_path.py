from utils.constants import (
    PROLONGATION_PERIOD_SECONDS,
    TOTAL_LIFETIME_SECONDS,
    MAX_SEALABLES,
    SECONDS_PER_DAY,
)


def test_happy_path(project, deploy_gate_seal, generate_sealables, sealing_committee):
    sealables = generate_sealables(MAX_SEALABLES)
    prolongations = (TOTAL_LIFETIME_SECONDS // PROLONGATION_PERIOD_SECONDS) - 1
    gate_seal = deploy_gate_seal(
        sealing_committee,
        sealables,
        PROLONGATION_PERIOD_SECONDS,
        prolongations,
        SECONDS_PER_DAY * 11,
    )

    assert gate_seal.get_sealing_committee() == sealing_committee
    assert len(gate_seal.get_sealables()) == len(sealables)

    gate_seal.seal(sender=sealing_committee)
    assert project.SealableMock.at(sealables[0]).isPaused()
    assert gate_seal.is_expired()

