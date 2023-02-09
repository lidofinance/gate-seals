def test_happy_path(
    gate_seal, dao_agent, sealable_mock, seal_committee, seal_duration, expiry_period
):
    assert gate_seal.get_initializer() == dao_agent, "dao_agent is not initializer"

    tx = gate_seal.initialize(
        sealable_mock, seal_committee, seal_duration, expiry_period, sender=dao_agent
    )

    assert "Initialized" in tx.events[0], "'Initialized' emitted"
