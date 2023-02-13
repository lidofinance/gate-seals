# @version 0.3.7

event GateSealCreated:
    gate_seal: address

EIP5202_CODE_OFFSET: constant(uint256) = 3
MAX_SEALABLES: constant(uint256) = 8

BLUEPRINT: immutable(address)

@external
def __init__(_blueprint: address):
    assert _blueprint != empty(address), "blueprint: zero address"
    BLUEPRINT = _blueprint


@external
@view
def get_blueprint() -> address:
    return BLUEPRINT


@external
def create_gate_seal(
    _sealing_committee: address,
    _seal_duration: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _expiry_period: uint256
):
    gate_seal: address = create_from_blueprint(
        BLUEPRINT,
        _sealing_committee,
        _seal_duration,
        _sealables,
        _expiry_period,
        code_offset=EIP5202_CODE_OFFSET,
        salt=convert(_sealing_committee, bytes32)
    )

    log GateSealCreated(gate_seal)