# @version 0.4.2

"""
@title GateSealV2
@author alex.k@lido.fi
@notice A one-time panic button for pausable contracts
@dev GateSealV2 is a one-time immediate emergency pause for pausable contracts.
     It must be operated by a multisig committee, though the code does not
     perform any such checks. Bypassing the DAO vote, GateSeal pauses 
     the contract(s) immediately for a set duration, e.g. one week, which gives
     the DAO time to analyze the situation, decide on the course of action,
     hold a vote, implement fixes, etc. GateSeal can only be used once.
     GateSeal assumes that it has the permission to pause the contracts.

     GateSeals serve as a long-term safety mechanism. 
     A committee ensures the GateSeal remains viable by prolonging its duration periodically.
     Should they fail to do so, the GateSeal will automatically expire, requiring the deployment of a new one.
     This approach maintains the multisig's limitations in terms of power and duration, while streamlining the full DAO vote cadence.

     In the context of GateSeals, sealing is synonymous with pausing the contracts.
     Sealables are pausable contracts that implement the `pauseFor(duration)` interface.
"""


event Sealed:
    sealed_by: address
    sealed_for: uint256
    sealable: indexed(address)

event Prolonged:
    prolonged_by: address
    prolongations_remaining: uint256
    new_expiry: indexed(uint256)

interface IPausableUntil:
    def pauseFor(_duration: uint256): nonpayable
    def isPaused() -> bool: view


# Basic time unit
SECONDS_PER_DAY: constant(uint256) = 60 * 60 * 24

# === SEALABLE CONTRACTS LIMITS ===
# The maximum number of sealables is 10.
# DynArray requires a compile-time limit, and 10 provides sufficient sealable count.
MAX_SEALABLES: constant(uint256) = 10

# === PROLONGATION SYSTEM ===
# Each prolongation extends the GateSeal by the provided period.
PROLONGATION_PERIOD_SECONDS: immutable(uint256)

# Timeline: Now → [PROLONGATION_WINDOW] → [PRE_EXPIRATION_OFFSET] → Expiry
# PROLONGATION_WINDOW is the period during which the committee can prolong
PROLONGATION_WINDOW_SECONDS: immutable(uint256)

# PRE_EXPIRATION_OFFSET ensures the DAO can deploy a new GateSeal if prolongation fails
PRE_EXPIRATION_OFFSET: immutable(uint256)


# Total lifetime across all prolongations is capped at five years
TOTAL_LIFETIME_DAYS: constant(uint256) = 365 * 5
TOTAL_LIFETIME_SECONDS: constant(uint256) = SECONDS_PER_DAY * TOTAL_LIFETIME_DAYS

# NOTE: GateSeal V2 does not enforce any limits on the seal duration.
# The DAO is expected to choose a sensible value during deployment and
# may always resume the contracts early via governance if required.

# To simplify the code, we chose not to implement committees in GateSeals.
# Instead, GateSeals are operated by a single account which must be a multisig.
# The code does not perform any such checks but we pinky-promise that
# the sealing committee will always be a multisig. 
SEALING_COMMITTEE: immutable(address)

# The duration of the seal in seconds. The DAO may resume the contracts
# prematurely via the regular governance process if needed.
SEAL_DURATION_SECONDS: immutable(uint256)


# The addresses of pausable contracts. The GateSeal must have the permission to
# pause these contracts at the time of the sealing.
# Sealing can be partial, meaning the committee may decide to pause only a subset of this list,
# though GateSeal will still expire immediately.
sealables: DynArray[address, MAX_SEALABLES]

# Absolute unix timestamp when the current GateSeal lifetime ends unless it is prolonged.
# Before sealing, this value determines the prolongation window bounds
# (see get_prolongation_window_start/end) and the moment when the GateSeal expires.
# Each successful prolongation increases this value by PROLONGATION_PERIOD_SECONDS.
# On sealing, this value is set to the current block timestamp to expire the GateSeal
# immediately and prevent any further operations. After expiry, a new GateSeal must be set up.
expiry_timestamp: uint256

# The number of prolongations remaining.
prolongations_remaining: uint256

@deploy
def __init__(
    _sealing_committee: address,
    _seal_duration_seconds: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _expiry_timestamp: uint256,
    _prolongation_limit: uint256,
    _prolongation_period_seconds: uint256,
    _prolongation_window_seconds: uint256,
    _pre_expiration_offset: uint256,
):
    assert _sealing_committee != empty(address), "sealing committee: zero address"
    assert len(_sealables) > 0, "sealables: empty list"

    min_prolongation_period_seconds: uint256 = _prolongation_window_seconds + _pre_expiration_offset
    max_lifetime_seconds: uint256 = _prolongation_period_seconds * 2

    assert _prolongation_period_seconds >= min_prolongation_period_seconds, "prolongation period: below minimum"
    
    PROLONGATION_PERIOD_SECONDS = _prolongation_period_seconds
    PROLONGATION_WINDOW_SECONDS = _prolongation_window_seconds
    PRE_EXPIRATION_OFFSET = _pre_expiration_offset
    assert _expiry_timestamp >= block.timestamp, "expiry timestamp: must be in the future"
    lifetime_seconds: uint256 = _expiry_timestamp - block.timestamp
    assert lifetime_seconds >= min_prolongation_period_seconds, "expiry timestamp: below minimum"
    assert lifetime_seconds <= max_lifetime_seconds, "expiry timestamp: exceeds max"
    assert lifetime_seconds + PROLONGATION_PERIOD_SECONDS * _prolongation_limit <= TOTAL_LIFETIME_SECONDS, "total lifetime: exceeds max"
    assert _seal_duration_seconds > 0, "seal duration: must be positive"
    
    for sealable: address in _sealables:
        assert sealable != empty(address), "sealables: includes zero address"
    assert not self._has_duplicates(_sealables), "sealables: includes duplicates"

    SEALING_COMMITTEE = _sealing_committee
    SEAL_DURATION_SECONDS = _seal_duration_seconds
    self.sealables = _sealables
    self.expiry_timestamp = _expiry_timestamp
    self.prolongations_remaining = _prolongation_limit


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
def get_prolongation_period_seconds() -> uint256:
    return PROLONGATION_PERIOD_SECONDS


@external
@view
def get_prolongation_window_seconds() -> uint256:
    return PROLONGATION_WINDOW_SECONDS


@external
@view
def get_pre_expiration_offset() -> uint256:
    return PRE_EXPIRATION_OFFSET


@external
@view
def get_prolongation_window_start() -> uint256:
    return self._get_prolongation_window_start()


@external
@view
def get_prolongation_window_end() -> uint256:
    return self._get_prolongation_window_end()


@external
@view
def is_in_prolongation_window() -> bool:
    return self._is_in_prolongation_window()


@internal
@view
def _is_in_prolongation_window() -> bool:
    start: uint256 = self._get_prolongation_window_start()
    end: uint256 = self._get_prolongation_window_end()
    return block.timestamp >= start and block.timestamp < end

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
def prolong_lifetime():
    """
    @notice Prolong the GateSeal.
    @dev    Can be called only by the sealing committee while the seal hasn't been used and not expired.
    """
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "GateSeal: expired"
    assert self.prolongations_remaining > 0, "prolongations: exhausted"
    assert self._is_in_prolongation_window(), "prolongation window: not active"

    self.expiry_timestamp += PROLONGATION_PERIOD_SECONDS
    self.prolongations_remaining -= 1
    log Prolonged(
        prolonged_by=SEALING_COMMITTEE,
        prolongations_remaining=self.prolongations_remaining,
        new_expiry=self.expiry_timestamp,
    )


@external
def seal_all():
    """
    @notice Seal all the sealables.
    @dev    Immediately expires GateSeal and, thus, can only be called once.
    """
    self._seal(self.sealables)

@external
def seal_some(_sealables: DynArray[address, MAX_SEALABLES]):
    """
    @notice Seal a subset of the sealables.
    @dev    Immediately expires GateSeal and, thus, can only be called once.
    """
    assert len(_sealables) > 0, "sealables: empty subset"
    assert not self._has_duplicates(_sealables), "sealables: includes duplicates"
    for sealable: address in _sealables:
        assert sealable in self.sealables, "sealables: includes a non-sealable"
    self._seal(_sealables)

@internal
def _seal(_sealables: DynArray[address, MAX_SEALABLES]):
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "GateSeal: expired"

    self._expire_immediately()

    # Instead of reverting the transaction as soon as one of the sealables fails,
    # we iterate through the entire list and collect the indexes of those that failed
    # and report them in the dynamically-generated error message.
    # This will make it easier for us to debug in a hectic situation.
    failed_indexes: DynArray[uint256, MAX_SEALABLES] = []
    sealable_index: uint256 = 0

    for sealable: address in _sealables:
        success: bool = raw_call(
            sealable,
            abi_encode(SEAL_DURATION_SECONDS, method_id=method_id("pauseFor(uint256)")),
            revert_on_failure=False
        )
        
        if success and staticcall IPausableUntil(sealable).isPaused():
            log Sealed(
                sealed_by=SEALING_COMMITTEE,
                sealed_for=SEAL_DURATION_SECONDS,
                sealable=sealable,
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
@view
def _get_prolongation_window_start() -> uint256:
    if self._is_expired():
        return 0

    return self.expiry_timestamp - PRE_EXPIRATION_OFFSET - PROLONGATION_WINDOW_SECONDS


@internal
@view
def _get_prolongation_window_end() -> uint256:
    if self._is_expired():
        return 0

    return self.expiry_timestamp - PRE_EXPIRATION_OFFSET


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
    @dev    The indexes are encoded as a bitmap where each bit represents
            a failed index. For example,

            [0, 2, 3, 6] -> 77 (0b1001101)
    @param _failed_indexes a list of sealable indexes that failed to seal 
    """
    bitmap: uint256 = 0

    # convert failed indexes to a bitmap representation
    for failed_index: uint256 in _failed_indexes:
        bitmap |= 1 << failed_index

    # generate error message with indexes as a decimal string of the bitmap
    # return type of `uint2str` is String[78] because 2^256 has 78 digits
    error_message: String[78] = uint2str(bitmap)

    return error_message
