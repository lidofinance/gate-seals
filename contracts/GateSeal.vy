# @version 0.3.7

event Sealed:
    gate_seal: address
    sealed_by: address
    sealable: address
    seal_duration: uint256

interface IPausableUntil:
    def pause(_duration: uint256): nonpayable
    def isPaused() -> bool: view

struct Sealable:
    location: address
    is_sealed: bool

MAX_SEALABLES: constant(uint256) = 8
INVALID_INDEX: constant(uint256) = MAX_SEALABLES

SEALING_COMMITTEE: immutable(address)
SEAL_DURATION: immutable(uint256)
sealables: DynArray[Sealable, MAX_SEALABLES]
sealables_unsealed: uint256
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
        self.sealables.append(Sealable({ location: sealable, is_sealed: False }))

    self.sealables_unsealed = len(_sealables)
    
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
    return self._get_sealables()


@external
@view
def get_expiry_timestamp() -> uint256:
    return self.expiry_timestamp


@external
def seal(_sealable: address):
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "gate seal: expired"
    
    sealable_index: uint256 = self._get_sealable_index(_sealable)
    assert self._is_sealable(sealable_index), "sealable: not a sealable"

    sealable: Sealable = self.sealables[sealable_index]

    assert not sealable.is_sealed, "sealable: cannot to be sealed more than once"
    sealable.is_sealed = True
    self.sealables_unsealed -= 1

    if (self.sealables_unsealed == 0):
        self.expiry_timestamp = block.timestamp

    pausable: IPausableUntil = IPausableUntil(sealable.location)
    pausable.pause(SEAL_DURATION)
    assert pausable.isPaused(), "sealable: failed to seal"

    log Sealed(self, SEALING_COMMITTEE, _sealable, SEAL_DURATION)


@external
def seal_all():
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "gate seal: expired"

    self.sealables_unsealed = 0
    self.expiry_timestamp = block.timestamp

    for sealable in self.sealables:
        if not sealable.is_sealed:
            pausable: IPausableUntil = IPausableUntil(sealable.location)
            pausable.pause(SEAL_DURATION)
            assert pausable.isPaused(), "sealable: failed to seal"

            log Sealed(self, SEALING_COMMITTEE, sealable.location, SEAL_DURATION)


@internal
@view
def _get_sealables() -> DynArray[address, MAX_SEALABLES]:
    sealables: DynArray[address, MAX_SEALABLES] = []
    for sealable in self.sealables:
        sealables.append(sealable.location)

    return sealables


@internal
@view
def _is_sealable(_sealable_index: uint256) -> bool:
    return _sealable_index < INVALID_INDEX


@internal
@view
def _get_sealable_index(_sealable: address) -> uint256:
    sealable_index: uint256 = INVALID_INDEX
    sealables_length: uint256 = len(self.sealables)

    for i in range(MAX_SEALABLES):
        if i < sealables_length and _sealable == self.sealables[i].location:
            sealable_index = i
            break 

    return sealable_index


@internal
@view
def _is_expired() -> bool:
    return block.timestamp > self.expiry_timestamp
