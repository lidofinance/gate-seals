# @version 0.4.1

"""
@title GateSeal
@author mymphe
@notice A one-time panic button for pausable contracts
@dev GateSeal is an one-time immediate emergency pause for pausable contracts.
     It must be operated by a multisig committee, though the code does not
     perform any such checks. Bypassing the DAO vote, GateSeal pauses 
     the contract(s) immediately for a set duration, e.g. one week, which gives
     the DAO the time to analyze the situation, decide on the course of action,
     hold a vote, implement fixes, etc. GateSeal can only be used once.
     GateSeal assumes that they have the permission to pause the contracts.

     GateSeals are only a temporary solution and will be deprecated in the future,
     as it is undesirable for the protocol to rely on a multisig. This is why
     each GateSeal has an expiry date. Once expired, GateSeal is no longer
     usable and a new GateSeal must be set up with a new multisig committee. This
     works as a kind of difficulty bomb, a device that encourages the protocol
     to get rid of GateSeals sooner rather than later.

     In the context of GateSeals, sealing is synonymous with pausing the contracts,
     sealables are pausable contracts that implement `pauseFor(duration)` interface.
"""

interface IPausableUntil:
    def pauseFor(_duration: uint256): nonpayable
    def isPaused() -> bool: view


event Sealed:
    gate_seal: address
    sealed_by: address
    sealed_for: uint256
    sealable: address
    sealed_at: uint256

SECONDS_PER_DAY: constant(uint256) = 60 * 60 * 24

# The lifetime of GateSeal must be between 1 month and 1 year.
MIN_LIFETIME_DURATION_DAYS: constant(uint256) = 30
MIN_LIFETIME_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * MIN_LIFETIME_DURATION_DAYS

MAX_LIFETIME_DURATION_DAYS: constant(uint256) = 365
MAX_LIFETIME_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * MAX_LIFETIME_DURATION_DAYS

# Prolongation window during which the committee may extend the lifetime.
MIN_PROLONGATION_WINDOW_DAYS: constant(uint256) = 7
MIN_PROLONGATION_WINDOW_SECONDS: constant(uint256) = SECONDS_PER_DAY * MIN_PROLONGATION_WINDOW_DAYS

MAX_PROLONGATION_WINDOW_DAYS: constant(uint256) = 30
MAX_PROLONGATION_WINDOW_SECONDS: constant(uint256) = SECONDS_PER_DAY * MAX_PROLONGATION_WINDOW_DAYS

# The minimum allowed seal duration is 6 days. This is because it takes at least
# 5 days to pass and enact (3 days main phase, 2 days objection phase).
# Additionally, we want to include a 1-day padding.
MIN_SEAL_DURATION_DAYS: constant(uint256) = 6
MIN_SEAL_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * MIN_SEAL_DURATION_DAYS

# The maximum allowed seal duration is 21 days.
# Anything higher than that may be too long of a disruption for the protocol.
# Keep in mind, that the DAO still retains the ability to resume the contracts
# (or, in the GateSeal terms, "break the seal") prematurely.
MAX_SEAL_DURATION_DAYS: constant(uint256) = 21
MAX_SEAL_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * MAX_SEAL_DURATION_DAYS

# The maximum number of sealables is 8.
# GateSeals were originally designed to pause WithdrawalQueue and ValidatorExitBus,
# however, there is a non-zero chance that there might be more in the future, which
# is why we've opted to use a dynamic-size array.
MAX_SEALABLES: constant(uint256) = 8

# Maximum number of prolongations allowed
MAX_PROLONGATIONS: constant(uint256) = 5

# To simplify the code, we chose not to implement committees in GateSeals.
# Instead, GateSeals are operated by a single account which must be a multisig.
# The code does not perform any such checks but we pinky-promise that
# the sealing committee will always be a multisig. 
SEALING_COMMITTEE: immutable(address)

# The duration of the seal in seconds. This period cannot exceed 21 days.
# The DAO may decide to resume the contracts prematurely via the DAO voting process.
SEAL_DURATION_SECONDS: immutable(uint256)

# The sealing committee extends the GateSeal to attest that the multisig is still active.

# The time window before expiry during which prolongation is allowed.
PROLONGATION_WINDOW_SECONDS: immutable(uint256)

# Initial lifetime duration in seconds.
LIFETIME_DURATION_SECONDS: immutable(uint256)

# The addresses of pausable contracts. The gate seal must have the permission to
# pause these contracts at the time of the sealing.
# Sealing can be partial, meaning the committee may decide to pause only a subset of this list,
# though GateSeal will still expire immediately.
sealables: DynArray[address, MAX_SEALABLES]

# A unix epoch timestamp starting from which GateSeal is completely unusable
# and a new GateSeal will have to be set up. This timestamp will be changed
# upon sealing to expire GateSeal immediately which will revert any consecutive sealings.
expiry_timestamp: uint256

# The number of prolongations remaining.
prolongations_remaining: uint256

@deploy
def __init__(
    _sealing_committee: address,
    _seal_duration_seconds: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _lifetime_duration_seconds: uint256,
    _max_prolongations: uint256,
    _prolongation_window_seconds: uint256
):
    assert _sealing_committee != empty(address), "sealing committee: zero address"
    assert _seal_duration_seconds >= MIN_SEAL_DURATION_SECONDS, "seal duration: too short"
    assert _seal_duration_seconds <= MAX_SEAL_DURATION_SECONDS, "seal duration: exceeds max"
    assert len(_sealables) > 0, "sealables: empty list"
    assert _lifetime_duration_seconds >= MIN_LIFETIME_DURATION_SECONDS, "lifetime duration: too short"
    assert _lifetime_duration_seconds <= MAX_LIFETIME_DURATION_SECONDS, "lifetime duration: exceeds max"
    assert _max_prolongations <= MAX_PROLONGATIONS, "max prolongations: exceeds max"
    assert _max_prolongations >= 0, "max prolongations: must be non-negative"

    assert _prolongation_window_seconds >= MIN_PROLONGATION_WINDOW_SECONDS, "prolongation window: too short"
    assert _prolongation_window_seconds <= MAX_PROLONGATION_WINDOW_SECONDS, "prolongation window: exceeds max"
    assert _prolongation_window_seconds <= _lifetime_duration_seconds, "prolongation window: exceeds lifetime"

    for sealable: address in _sealables:
        assert sealable != empty(address), "sealables: includes zero address"
    assert not self._has_duplicates(_sealables), "sealables: includes duplicates"

    SEALING_COMMITTEE = _sealing_committee
    SEAL_DURATION_SECONDS = _seal_duration_seconds
    PROLONGATION_WINDOW_SECONDS = _prolongation_window_seconds
    LIFETIME_DURATION_SECONDS = _lifetime_duration_seconds
    self.sealables = _sealables
    self.expiry_timestamp = block.timestamp + _lifetime_duration_seconds
    self.prolongations_remaining = _max_prolongations


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
def get_lifetime_duration_seconds() -> uint256:
    return LIFETIME_DURATION_SECONDS


@external
@view
def get_prolongation_window_seconds() -> uint256:
    return PROLONGATION_WINDOW_SECONDS

@external
@view
def get_expiry_timestamp() -> uint256:
    return self.expiry_timestamp



@external
@view
def get_prolongations_remaining() -> uint256:
    return self.prolongations_remaining


@external
@view
def is_expired() -> bool:
    return self._is_expired()


@external
def prolongLifetime():
    """
    @notice Prolong the GateSeal.
    @dev    Can be called only by the sealing committee while the seal hasn't been used and not expired.
    """
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "gate seal: expired"
    assert self.prolongations_remaining > 0, "prolongations: exhausted"
    assert block.timestamp >= self.expiry_timestamp - PROLONGATION_WINDOW_SECONDS, "prolongation window: too early"

    self.expiry_timestamp += LIFETIME_DURATION_SECONDS
    self.prolongations_remaining -= 1


@external
def seal(_sealables: DynArray[address, MAX_SEALABLES]):
    """
    @notice Seal the contract(s).
    @dev    Immediately expires GateSeal and, thus, can only be called once.
    @param _sealables a list of sealables to seal; may include all or only a subset.
    """
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "gate seal: expired"
    assert len(_sealables) > 0, "sealables: empty subset"
    assert not self._has_duplicates(_sealables), "sealables: includes duplicates"

    self._expire_immediately()

    # Instead of reverting the transaction as soon as one of the sealables fails,
    # we iterate through the entire list and collect the indexes of those that failed
    # and report them in the dynamically-generated error message.
    # This will make it easier for us to debug in a hectic situation.
    failed_indexes: DynArray[uint256, MAX_SEALABLES] = []
    sealable_index: uint256 = 0

    for sealable: address in _sealables:
        assert sealable in self.sealables, "sealables: includes a non-sealable"

        success: bool = raw_call(
            sealable,
            abi_encode(SEAL_DURATION_SECONDS, method_id=method_id("pauseFor(uint256)")),
            revert_on_failure=False
        )
        
        if success and staticcall IPausableUntil(sealable).isPaused():
            log Sealed(
                gate_seal=self,
                sealed_by=SEALING_COMMITTEE,
                sealed_for=SEAL_DURATION_SECONDS,
                sealable=sealable,
                sealed_at=block.timestamp
            )
        else:
            failed_indexes.append(sealable_index)
    
        sealable_index += 1

    assert len(failed_indexes) == 0, self._to_error_string(failed_indexes)


@internal
@view
def _is_expired() -> bool:
    return block.timestamp >= self.expiry_timestamp


@internal
def _expire_immediately():
    self.expiry_timestamp = block.timestamp


@internal
@pure
def _has_duplicates(_sealables: DynArray[address, MAX_SEALABLES]) -> bool:
    """
    @notice checks the list for duplicates 
    @param  _sealables list of addresses to check
    """
    unique: DynArray[address, MAX_SEALABLES] = []

    for sealable: address in _sealables:
        if sealable in unique:
            return True
        unique.append(sealable)

    return False


@internal
@pure
def _to_error_string(_failed_indexes: DynArray[uint256, MAX_SEALABLES]) -> String[78]:
    """
    @notice converts a list of indexes into an error message to facilitate debugging
    @dev    The indexes in the error message are given in the descending order to avoid
            losing leading zeros when casting to string,

            e.g. [0, 2, 3, 6] -> "6320"
    @param _failed_indexes a list of sealable indexes that failed to seal 
    """
    indexes_as_decimal: uint256 = 0
    loop_index: uint256 = 0

    # convert failed indexes to a decimal representation
    for failed_index: uint256 in _failed_indexes:
        indexes_as_decimal += failed_index * 10 ** loop_index
        loop_index += 1

    # generate error message with indexes as a decimal string
    # return type of `uint2str` is String[78] because 2^256 has 78 digits
    error_message: String[78] = uint2str(indexes_as_decimal)

    return error_message
