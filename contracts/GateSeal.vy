# @version 0.3.7

event Sealed:
    gate_seal: address
    sealed_by: address
    sealable: address
    seal_duration: uint256

interface IPausableUntil:
    def pause(_duration: uint256): nonpayable
    def isPaused() -> bool: view

MAX_SEALABLES: constant(uint256) = 8

SEALING_COMMITTEE: immutable(address)
SEAL_DURATION: immutable(uint256)
sealables: DynArray[address, MAX_SEALABLES]
sealed: HashMap[address, bool]
unsealed_count: uint256
expiry_timestamp: uint256


@external
def __init__(
    _sealing_committee: address,
    _seal_duration: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _expiry_period: uint256
):
    assert _sealing_committee != empty(address), "sealing committee: zero address"
    assert _seal_duration != 0, "seal duration: zero"
    assert _expiry_period != 0, "expiry period: zero"

    SEALING_COMMITTEE = _sealing_committee
    SEAL_DURATION = _seal_duration

    for sealable in _sealables:
        assert sealable != empty(address), "sealables: includes zero address"
        self.sealables.append(sealable)
        self.sealed[sealable] = False

    self.unsealed_count = len(_sealables)
    
    self.expiry_timestamp = block.timestamp + _expiry_period


@external
@view
def get_sealing_committee() -> address:
    return SEALING_COMMITTEE


@external
@view
def get_seal_duration() -> uint256:
    return SEAL_DURATION


@external
@view
def get_sealables() -> DynArray[address, MAX_SEALABLES]:
    return self.sealables


@external
@view
def get_expiry_timestamp() -> uint256:
    return self.expiry_timestamp


@external
@view
def is_expired() -> bool:
    return self._is_expired()


@external
def seal(_sealable: address):
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "gate seal: expired"
    assert not self.sealed[_sealable], "sealable: already been sealed once"

    self.unsealed_count -= 1
    if self.unsealed_count == 0:
        self._expire_immediately()

    self._seal(_sealable)


@external
def seal_all():
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "gate seal: expired"

    self.unsealed_count = 0
    self._expire_immediately()

    for sealable in self.sealables:
        if not self.sealed[sealable]:
            self._seal(sealable)


@internal
@view
def _is_expired() -> bool:
    return block.timestamp > self.expiry_timestamp


@internal
def _seal(_sealable: address):
    self.sealed[_sealable] = True

    pausable: IPausableUntil = IPausableUntil(_sealable)
    pausable.pause(SEAL_DURATION)
    assert pausable.isPaused(), "sealable: failed to seal"

    log Sealed(self, SEALING_COMMITTEE, _sealable, SEAL_DURATION)


@internal
def _expire_immediately():
    self.expiry_timestamp = block.timestamp - 1