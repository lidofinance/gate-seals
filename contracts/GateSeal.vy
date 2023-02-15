# @version 0.3.7

"""
@title GateSeal
@author mymphe
@notice A one-time panic button for pausable contracts
@dev The gate seal is meant to be used as an emergency pause for pausable contracts.
     It must be operated by a multisig committee, though the code does not
     perform any such checks. Bypassing the DAO vote, the gate seal pauses 
     the contract(s) immediately for a set duration, e.g. one week, which gives
     the DAO some time to analyze the situation, decide on the course of action,
     hold a vote, implement fixes, etc. A gate seal can only be used once.
     Gate seals assume that they have the permission to pause the contracts.

     Gate seals are only a temporary solution and will be deprecated in the future,
     as it is undesireable for the protocol to rely on a multisig. This is why
     each gate seal has an expiry date. Once expired, the gate seal is no longer
     usable and a new gate seal must be set up with a new multisig committee. This
     works as a kind of difficulty bomb, a device that encourages the protocol
     to get rid of gate seals sooner rather than later.

     In the context of gate seals, sealing is synonymous with pausing the contracts,
     sealables are pausable contracts that implement `pause(duration)` interface.
"""


event Sealed:
    gate_seal: address
    sealed_by: address
    sealed_for: uint256
    sealable: address


interface IPausableUntil:
    def pause(_duration: uint256): nonpayable
    def isPaused() -> bool: view


# The maximum allowed seal duration is 14 days.
# Anything higher than that may be too long of a disruption for the protocol.
# Keep in mind, that the DAO still retains the ability to resume the contracts
# (or, in this context, "break the seal") prematurely.
SECONDS_PER_DAY: constant(uint256) = 60 * 60 * 24
MAX_SEAL_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * 14

# The maximum number of sealables is 8.
# Gate seals were originally designed to pause WithdrawalQueue and ValidatorExitBus,
# however, there is a non-zero chance that there might be more in the future, which
# is why we've opted to use a dynamic-size array.
MAX_SEALABLES: constant(uint256) = 8

# To simplify the code, we chose not to implement committees in gate seals.
# Instead, gate seals are operated by a single account which must be a multisig.
# The code does not performs any checks but we pinky-promise that
# the sealing committee will always be a multisig. 
SEALING_COMMITTEE: immutable(address)

# The duration of the seal in seconds. As mentioned earlier, it cannot be longer
# than 14 days. This period is applied for all sealables and can never be changed.
SEAL_DURATION_SECONDS: immutable(uint256)

# The addresses of pausable contracts. The gate seal must have the permission to
# pause these contract at the time of the sealing. This means that the permissions
# can be given in the same transaction as the sealing and revoked immediately after.
sealables: DynArray[address, MAX_SEALABLES]

# A unix epoch timestamp starting from which the gate seal is completely unusable
# and a new gate seal will have to be set up. This timestamp will be changed
# upon sealing to expire the gate seal immediately and prevent multiple sealings.
expiry_timestamp: uint256


@external
def __init__(
    _sealing_committee: address,
    _seal_duration_seconds: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _expiry_period_seconds: uint256
):
    assert _sealing_committee != empty(address), "sealing committee: zero address"
    assert _seal_duration_seconds != 0, "seal duration: zero"
    assert _seal_duration_seconds <= MAX_SEAL_DURATION_SECONDS, "seal duration: exceeds max"
    assert len(_sealables) > 0, "sealables: empty list"
    assert _expiry_period_seconds != 0, "expiry period: zero"

    SEALING_COMMITTEE = _sealing_committee
    SEAL_DURATION_SECONDS = _seal_duration_seconds

    for sealable in _sealables:
        assert sealable != empty(address), "sealables: includes zero address"
        self.sealables.append(sealable)
    
    self.expiry_timestamp = block.timestamp + _expiry_period_seconds


@external
@view
def get_sealing_committee() -> address:
    return SEALING_COMMITTEE


@external
@view
def get_seal_duration_seconds() -> uint256:
    return SEAL_DURATION_SECONDS


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
def seal(_sealables: DynArray[address, MAX_SEALABLES]):
    """
    @notice Seal the contract(s).
    @dev    Immediately expires the gate seal and, thus, can only
            be executed once during the entire gate seal lifecycle.
    @param _sealables an array of sealable contracts which must be present
                       in the list stored on the gate seal.
    """
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "gate seal: expired"

    self._expire_immediately()
    
    for sealable in _sealables:
        assert sealable in self.sealables, "sealables: includes a non-sealable"

        pausable: IPausableUntil = IPausableUntil(sealable)
        pausable.pause(SEAL_DURATION_SECONDS)
        assert pausable.isPaused(), "sealables: failed to seal"

        log Sealed(self, SEALING_COMMITTEE, SEAL_DURATION_SECONDS, sealable)


@internal
@view
def _is_expired() -> bool:
    return block.timestamp > self.expiry_timestamp


@internal
def _expire_immediately():
    self.expiry_timestamp = block.timestamp - 1