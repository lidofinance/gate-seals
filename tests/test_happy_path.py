from ape.logging import logger

from utils.blueprint import get_blueprint_address, get_blueprint_initcode


def test_happy_path(project, accounts):
    DEPLOYER = accounts[0]

    # Step 1. Get the GateSeal bytecode
    gate_seal_bytecode = project.GateSeal.contract_type.deployment_bytecode.bytecode

    # Step 2. Generate the GateSeal initcode with preamble which will be stored onchain
    #         and will be used as the blueprint for the factory to create new GateSeals
    gate_seal_initcode = get_blueprint_initcode(gate_seal_bytecode)

    # Step 3. Deploy initcode
    blueprint_address = get_blueprint_address(DEPLOYER, gate_seal_initcode)

    # Step 4. Deploy the GateSeal factory and pass the address of the GateSeal blueprint
    gate_seal_factory = project.GateSealFactory.deploy(
        blueprint_address, sender=DEPLOYER
    )

    assert (
        gate_seal_factory.get_blueprint() == blueprint_address
    ), "blueprint doesn't match"

    # Step 5. Set up the GateSeal config
    SEALING_COMMITTEE = accounts[1]
    SEAL_DURATION = 60 * 60 * 24 * 7  # one week
    SEALABLES = []
    for i in range(8):
        SEALABLES.append(project.SealableMock.deploy(sender=DEPLOYER))
    EXPIRY_TIMESTAMP = 60 * 60 * 24 * 365  # one year

    # Step 6. Create a GateSeal using the factory
    transaction = gate_seal_factory.create_gate_seal(
        SEALING_COMMITTEE, SEAL_DURATION, SEALABLES, EXPIRY_TIMESTAMP, sender=DEPLOYER
    )

    gate_seal_address = transaction.events[0].gate_seal
    gate_seal = project.GateSeal.at(gate_seal_address)

    assert (
        gate_seal.get_sealing_committee() == SEALING_COMMITTEE
    ), "committee address does not match"

    assert len(gate_seal.get_sealables()) == len(
        SEALABLES
    ), "incorrect number of sealables"

    # Step 7. Seal one of the sealables
    SEALABLE = SEALABLES[0]
    gate_seal.seal(SEALABLE, sender=SEALING_COMMITTEE)
    assert project.SealableMock.at(SEALABLE).isPaused(), "failed to seal"

    # Step 8. Seal the rest of the sealables
    gate_seal.seal_all(sender=SEALING_COMMITTEE)
    for sealable in SEALABLES:
        assert project.SealableMock.at(sealable).isPaused(), "failed to seal all"

    assert gate_seal.is_expired(), "must be expired after sealing all"
