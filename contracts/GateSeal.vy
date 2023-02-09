"""
@title GateSeal
@license MIT
@author mymphe
@notice A set-duration one-time pause for a PausableUntil contract
@dev
    This contract is meant to be used as a panic button for a critical contract;
 
    In a state of emergency, the pauser (a multisig committee) can pause (seal the gate)
    the contract for a set duration, e.g. one week, bypassing the DAO voting;
    This will give the DAO some time to analyze the situation, hold a vote, etc.;
 
    To reduce the protocol's reliance on this mechanism,
    GateSeal will expire in a set amount of time;
    and a new GateSeal with a new committee will have to be deployed;
 
    Sealing the gate will also expire the contract immediately.
"""


interface IPausableUntil:
    def pause(_duration: uint256): nonpayable


event Initialized:
    initializer: address
    sealable: address
    sealer: address
    seal_duration: uint256
    expiry_timestamp: uint256

event GateSealed:
    sealable: address
    sealer: address
    seal_duration: uint256

initializer: address
sealable: address
sealer: address
seal_duration: uint256
expiry_timestamp: uint256


@external
def __init__(_initializer: address):
    assert _initializer != empty(address), "_initializer: zero address"
    self.initializer = _initializer


@external
@view
def get_initializer() -> address:
    return self.initializer


@external
@view    
def get_sealable() -> address:
    return self.sealable


@external
@view    
def get_sealer() -> address:
    return self.sealer


@external
@view    
def get_seal_duration() -> uint256:
    return self.seal_duration


@external
@view    
def get_expiry_timestamp() -> uint256:
    return self.expiry_timestamp


@external
@view    
def is_initialized() -> bool:
    return self._is_initialized()


@external
@view    
def is_expired() -> bool:
    return self._is_expired()


@external
def initialize(_sealable: address, _sealer: address, _seal_duration: uint256, _expiry_period: uint256):
    assert not self._is_initialized(), "state: initialized"
    assert msg.sender == self.initializer, "sender: not initializer"
    assert _sealable != empty(address), "_sealable: zero address"
    assert _sealer != empty(address), "_sealer: zero address"

    self.initializer = empty(address)

    self.sealable = _sealable
    self.sealer = _sealer
    self.seal_duration = _seal_duration
    self.expiry_timestamp = block.timestamp + _expiry_period

    log Initialized(msg.sender, _sealable, _sealer, _seal_duration, self.expiry_timestamp)


@external
def seal_gate():
    assert self._is_initialized(), "state: not initialized"
    assert not self._is_expired(), "state: expired"
    assert msg.sender == self.sealer, "sender: not sealer"

    self.expiry_timestamp = block.timestamp - 1
    self.sealer = empty(address)

    IPausableUntil(self.sealable).pause(self.seal_duration)

    log GateSealed(self.sealable, self.sealer, self.seal_duration)


@internal
@view
def _is_initialized() -> bool:
    return self.initializer == empty(address)

@internal
@view
def _is_expired() -> bool:
    return self.expiry_timestamp > block.timestamp