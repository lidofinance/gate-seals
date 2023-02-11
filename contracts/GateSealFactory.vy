# @version 0.3.7

event GateSealCreated:
    gate_seal: address

EIP5202_CODE_OFFSET: constant(uint256) = 3
MAX_SEALABLES: constant(uint256) = 8

BLUEPRINT: immutable(address)

@external
def __init__(_blueprint: address):
    BLUEPRINT = _blueprint

@external
def create_gate_seal(
    _expiry_period: uint256,
    _sealing_committee: address,
    _seal_duration: uint256,
    _sealables: DynArray[address, MAX_SEALABLES]
):
    gate_seal: address = create_from_blueprint(
        BLUEPRINT,
        _expiry_period,
        _sealing_committee,
        _seal_duration,
        _sealables,
        code_offset=EIP5202_CODE_OFFSET,
        salt=keccak256("hello")
    )

    log GateSealCreated(gate_seal)