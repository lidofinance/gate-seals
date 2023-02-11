def test_happy_path(gate_seal, sealing_committee):
    assert (
        gate_seal.get_sealing_commitee() == sealing_committee.address
    ), "does not match"
