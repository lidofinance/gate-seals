from ape import reverts  # type: ignore (some issue fro)
from ape.logging import logger
from ape.exceptions import VirtualMachineError
from utils.constants import ZERO_ADDRESS


def test_factory_blueprint_cannot_be_zero_address(project, deployer):
    with reverts("blueprint: zero address"):
        project.GateSealFactory.deploy(ZERO_ADDRESS, sender=deployer)


def test_blueprint_uncallable(project, blueprint_address):
    blueprint = project.GateSeal.at(blueprint_address)
    try:
        blueprint.get_sealing_committee()
        assert False, "did not crash"
    except VirtualMachineError:
        assert True


def test_blueprint_address_matches(blueprint_address, gate_seal_factory):
    assert (
        gate_seal_factory.get_blueprint() == blueprint_address
    ), "blueprint address does not match"
