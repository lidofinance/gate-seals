from utils.blueprint import deploy_blueprint, construct_blueprint_deploy_bytecode
from utils.constants import (
    PROLONGATION_PERIOD_SECONDS,
    TOTAL_LIFETIME_SECONDS,
    SECONDS_PER_DAY,
)


def test_happy_path(networks, chain, project, accounts):
    DEPLOYER = accounts[0]

    # Step 1. Get the GateSealV2 bytecode
    gate_seal_bytecode = project.GateSealV2.contract_type.deployment_bytecode.bytecode

    # Step 2. Generate the GateSealV2 initcode with preamble which will be stored onchain
    #         and will be used as the blueprint for the factory to create new GateSealV2s
    gate_seal_deploy_code = construct_blueprint_deploy_bytecode(gate_seal_bytecode)

    # Step 3. Deploy initcode
    blueprint_address = deploy_blueprint(DEPLOYER, gate_seal_deploy_code)

    # Step 4. Deploy the GateSealV2 factory and pass the address of the GateSealV2 blueprint
    gate_seal_factory = project.GateSealFactoryV2.deploy(
        blueprint_address, sender=DEPLOYER
    )

    assert (
        gate_seal_factory.get_blueprint() == blueprint_address
    ), "blueprint doesn't match"

    # Step 5. Set up the GateSealV2 config
    SEALING_COMMITTEE = accounts[1]
    SEAL_DURATION_SECONDS = SECONDS_PER_DAY * 11
    SEALABLES = []
    for _ in range(8):
        SEALABLES.append(project.SealableMock.deploy(False, False, sender=DEPLOYER))

    now = chain.pending_timestamp

    LIFETIME_DURATION = PROLONGATION_PERIOD_SECONDS

    # Step 6. Create a GateSealV2 using the factory
    PROLONGATIONS = (TOTAL_LIFETIME_SECONDS // LIFETIME_DURATION) - 1
    transaction = gate_seal_factory.create_gate_seal(
        SEALING_COMMITTEE,
        SEAL_DURATION_SECONDS,
        SEALABLES,
        LIFETIME_DURATION,
        PROLONGATIONS,
        sender=DEPLOYER,
    )

    gate_seal_address = transaction.events[0].gate_seal
    gate_seal = project.GateSealV2.at(gate_seal_address)

    assert (
        gate_seal.get_sealing_committee() == SEALING_COMMITTEE
    ), "committee address does not match"

    assert len(gate_seal.get_sealables()) == len(
        SEALABLES
    ), "incorrect number of sealables"

    # Step 7. Seal one of the sealables
    SEALABLE = SEALABLES[0]
    gate_seal.seal(sender=SEALING_COMMITTEE)
    assert project.SealableMock.at(SEALABLE).isPaused(), "failed to seal"

    assert gate_seal.is_expired(), "must be expired after sealing all"
