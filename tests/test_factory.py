from ape import reverts
from ape.logging import logger
from ape.exceptions import VirtualMachineError
from utils.blueprint import verify_eip522_blueprint
from utils.constants import ZERO_ADDRESS


def test_factory_blueprint_cannot_be_zero_address(project, deployer):
    with reverts("blueprint: zero address"):
        project.GateSealFactory.deploy(ZERO_ADDRESS, sender=deployer)


def test_blueprint_uncallable(project, blueprint_address):
    blueprint = project.GateSeal.at(blueprint_address)
    # using try-except because ape.reverts doesn't catch VirtualMachineError for some reason
    try:
        blueprint.get_sealing_committee()
        assert False, "did not crash"
    except VirtualMachineError:
        assert True


def test_blueprint_address_matches(blueprint_address, gate_seal_factory):
    assert (
        gate_seal_factory.get_blueprint() == blueprint_address
    ), "blueprint address does not match"


def test_compliance_with_eip_5202(project, blueprint_address):
    blueprint = project.provider.get_code(blueprint_address)
    verify_eip522_blueprint(blueprint)
