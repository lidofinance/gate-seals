from ape.logging import logger
from datetime import datetime
from utils.blueprint import deploy_blueprint, construct_blueprint_deploy_bytecode


def test_happy_path(networks, chain, project, accounts):
    DEPLOYER = accounts[0]

    # Step 1. Get the GateSeal bytecode
    gate_seal_bytecode = project.GateSeal.contract_type.deployment_bytecode.bytecode

    # Step 2. Generate the GateSeal initcode with preamble which will be stored onchain
    #         and will be used as the blueprint for the factory to create new GateSeals
    gate_seal_deploy_code = construct_blueprint_deploy_bytecode(gate_seal_bytecode)

    # Step 3. Deploy initcode
    blueprint_address = deploy_blueprint(DEPLOYER, gate_seal_deploy_code)

    # Step 4. Deploy the GateSeal factory and pass the address of the GateSeal blueprint
    gate_seal_factory = project.GateSealFactory.deploy(
        blueprint_address, sender=DEPLOYER
    )

    assert (
        gate_seal_factory.get_blueprint() == blueprint_address
    ), "blueprint doesn't match"

    # Step 5. Set up the GateSeal config
    SEALING_COMMITTEE = accounts[1]
    SEAL_DURATION_SECONDS = 60 * 60 * 24 * 7  # one week
    SEALABLES = []
    for _ in range(8):
        SEALABLES.append(project.SealableMock.deploy(False, False, sender=DEPLOYER))

    now = chain.pending_timestamp

    EXPIRY_DURATION = 60 * 60 * 24 * 365  # 1 year

    # Step 6. Create a GateSeal using the factory
    transaction = gate_seal_factory.create_gate_seal(
        SEALING_COMMITTEE,
        SEAL_DURATION_SECONDS,
        SEALABLES,
        now + EXPIRY_DURATION,
        sender=DEPLOYER,
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
    gate_seal.seal([SEALABLE], sender=SEALING_COMMITTEE)
    assert project.SealableMock.at(SEALABLE).isPaused(), "failed to seal"

    assert gate_seal.is_expired(), "must be expired after sealing all"
