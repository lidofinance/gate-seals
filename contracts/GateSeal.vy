# @version 0.3.7

interface IPausableUntil:
    def pause(_duration: uint256): nonpayable

MAX_SEALABLES: constant(uint256) = 8
EXPIRY_TIMESTAMP: immutable(uint256)
SEALING_COMMITEE: immutable(address)
SEAL_DURATION: immutable(uint256)
sealables: DynArray[address, MAX_SEALABLES]

@external
def __init__(
    _expiry_period: uint256,
    _sealing_committee: address,
    _seal_duration: uint256,
    _sealables: DynArray[address, MAX_SEALABLES]
):
    assert _sealing_committee != empty(address), "_sealing_committee: zero address"

    for sealable in _sealables:
        assert sealable != empty(address), "_sealables: includes zero address"

    EXPIRY_TIMESTAMP = block.timestamp + _expiry_period
    SEALING_COMMITEE = _sealing_committee
    SEAL_DURATION = _seal_duration
    self.sealables = _sealables


@view
@external
def get_expiry_timestamp() -> uint256:
    return EXPIRY_TIMESTAMP


@view
@external
def is_expired() -> bool:
    return self._is_expired()


@view
@external
def get_sealing_commitee() -> address:
    return SEALING_COMMITEE


@view
@external
def get_seal_duration() -> uint256:
    return SEAL_DURATION


@view    
@external
def get_sealables() -> DynArray[address, MAX_SEALABLES]:
    return self._get_sealables()


@view
@external
def is_sealable(_address: address) -> bool:
    return self._is_sealable(_address)


@external
def seal_gate(_address: address):
    assert msg.sender == SEALING_COMMITEE, "sender: not SEALING_COMMITEE"
    assert not self._is_expired(), "state: expired"

    IPausableUntil(_address).pause(SEAL_DURATION)



@view
@internal
def _is_expired() -> bool:
    return block.timestamp < EXPIRY_TIMESTAMP


@view
@internal
def _is_sealable(_address: address) -> bool:
    return _address in self.sealables


@view
@internal
def _get_sealables() -> DynArray[address, MAX_SEALABLES]:
    return self.sealables


@view
@internal
def _get_sealable(index: uint256) -> address:
    return self.sealables[index]

