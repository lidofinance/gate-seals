from ape.logging import logger


def test_happy_path(
    project, gate_seal, sealing_committee, sealable_mock, sealable_mock_2
):
    assert (
        gate_seal.get_sealing_committee() == sealing_committee.address
    ), "committee address does not match"

    assert len(gate_seal.get_sealables()) == 2, "incorrect number of sealables"

    gate_seal.seal(sealable_mock, sender=sealing_committee)
    assert project.SealableMock.at(sealable_mock).isPaused(), "failed to seal"

    gate_seal.seal_all(sender=sealing_committee)
    assert project.SealableMock.at(sealable_mock_2).isPaused(), "failed to seal all"
