# @version 0.4.2

"""
@title GateSealV2
@author alex.k@lido.fi
@notice A one-time panic button for pausable contracts
@dev GateSeal is an one-time immediate emergency pause for pausable contracts.
     It must be operated by a multisig committee, though the code does not
     perform any such checks. Bypassing the DAO vote, GateSeal pauses 
     the contract(s) immediately for a set duration, e.g. one week, which gives
     the DAO the time to analyze the situation, decide on the course of action,
     hold a vote, implement fixes, etc. GateSeal can only be used once.
     GateSeal assumes that they have the permission to pause the contracts.

     Initially introduced as an emergency 'circuit breaker', GateSeals have evolved in version 2 to function as a long-term safety mechanism.
     A committee ensures the GateSeal remains viable by prolonging its duration periodically.
     Should they fail to do so, the GateSeal will automatically expire, necessitating the deployment of a new one.
     This approach maintains the multisig's limitations in terms of power and duration, while allowing the DAO to bypass the need for an annual full vote.

     In the context of GateSeals, sealing is synonymous with pausing the contracts,
     sealables are pausable contracts that implement `pauseFor(duration)` interface.
"""


event Sealed:
    sealed_by: address
    sealed_for: uint256

event Prolonged:
    prolonged_by: address
    prolongations_remaining: uint256
    new_expiry: uint256

interface IPausableUntil:
    def pauseFor(_duration: uint256): nonpayable
    def isPaused() -> bool: view


# Basic time unit
SECONDS_PER_DAY: constant(uint256) = 60 * 60 * 24

# === SEALABLE CONTRACTS LIMITS ===
# The maximum number of sealables is 8.
# GateSeals were originally designed to pause WithdrawalQueue and ValidatorExitBus,
# however, there is a non-zero chance that there might be more in the future.
MAX_SEALABLES: constant(uint256) = 8

# === PROLONGATION SYSTEM ===
# Each prolongation extends the GateSeal by exactly one year.
PROLONGATION_PERIOD_DAYS: constant(uint256) = 365
PROLONGATION_PERIOD_SECONDS: constant(uint256) = SECONDS_PER_DAY * PROLONGATION_PERIOD_DAYS

# Timeline: Now → [PROLONGATION_WINDOW] → [DAO_RESERVE] → Expiry
# PROLONGATION_WINDOW is the period during which the committee can prolong
PROLONGATION_WINDOW_DAYS: constant(uint256) = 14
PROLONGATION_WINDOW_SECONDS: constant(uint256) = SECONDS_PER_DAY * PROLONGATION_WINDOW_DAYS

# DAO_RESERVE ensures the DAO can deploy a new GateSeal if prolongation fails
DAO_RESERVE_DAYS: constant(uint256) = 60
DAO_RESERVE_SECONDS: constant(uint256) = SECONDS_PER_DAY * DAO_RESERVE_DAYS

# === LIFETIME LIMITS ===
# Initial lifetime must be at least DAO_RESERVE + prolongation window
MIN_INITIAL_LIFETIME_SECONDS: constant(uint256) = DAO_RESERVE_SECONDS + PROLONGATION_WINDOW_SECONDS

# Initial lifetime cannot exceed two prolongation periods
MAX_INITIAL_LIFETIME_SECONDS: constant(uint256) = PROLONGATION_PERIOD_SECONDS * 2

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

# The sealing committee extends the GateSeal to attest that the multisig is still active.

# The time window before expiry during which prolongation is allowed.
# The initial lifetime in seconds, set at deployment to align the first
# expiration with the chosen prolongation window.
INITIAL_LIFETIME_SECONDS: immutable(uint256)

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
    _initial_lifetime_seconds: uint256,
    _prolongations: uint256
):
    assert _sealing_committee != empty(address), "sealing committee: zero address"
    assert len(_sealables) > 0, "sealables: empty list"
    assert _initial_lifetime_seconds >= MIN_INITIAL_LIFETIME_SECONDS, "initial lifetime: too short"
    assert _initial_lifetime_seconds <= MAX_INITIAL_LIFETIME_SECONDS, "initial lifetime: exceeds max"
    assert _initial_lifetime_seconds + PROLONGATION_PERIOD_SECONDS * _prolongations <= TOTAL_LIFETIME_SECONDS, "total lifetime: exceeds max"
    assert _seal_duration_seconds > 0, "seal duration: must be positive"
    
    for sealable: address in _sealables:
        assert sealable != empty(address), "sealables: includes zero address"
    assert not self._has_duplicates(_sealables), "sealables: includes duplicates"

    SEALING_COMMITTEE = _sealing_committee
    SEAL_DURATION_SECONDS = _seal_duration_seconds
    INITIAL_LIFETIME_SECONDS = _initial_lifetime_seconds
    self.sealables = _sealables
    self.expiry_timestamp = block.timestamp + _initial_lifetime_seconds
    self.prolongations_remaining = _prolongations


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
def get_initial_lifetime_seconds() -> uint256:
    return INITIAL_LIFETIME_SECONDS


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
def get_prolongation_window_start() -> uint256:
    return self._get_prolongation_window_start()


@external
@view
def get_prolongation_window_end() -> uint256:
    return self._get_prolongation_window_end()


@external
@view
def is_in_prolongation_window() -> bool:
    start: uint256 = self._get_prolongation_window_start()
    end: uint256 = self._get_prolongation_window_end()
    return block.timestamp >= start and block.timestamp <= end

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
    start: uint256 = self._get_prolongation_window_start()
    end: uint256 = self._get_prolongation_window_end()
    assert block.timestamp >= start, "prolongation window: too early"
    assert block.timestamp <= end, "prolongation window: expired"

    self.expiry_timestamp += PROLONGATION_PERIOD_SECONDS
    self.prolongations_remaining -= 1
    log Prolonged(
        prolonged_by=SEALING_COMMITTEE,
        prolongations_remaining=self.prolongations_remaining,
        new_expiry=self.expiry_timestamp,
    )


@external
def seal():
    """
    @notice Seal the contract(s).
    @dev    Immediately expires GateSeal and, thus, can only be called once.
    @dev Seals all predefined sealables.
    """
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "gate seal: expired"

    self._expire_immediately()

    # Instead of reverting the transaction as soon as one of the sealables fails,
    # we iterate through the entire list and collect the indexes of those that failed
    # and report them in the dynamically-generated error message.
    # This will make it easier for us to debug in a hectic situation.
    failed_indexes: DynArray[uint256, MAX_SEALABLES] = []
    sealable_index: uint256 = 0

    for sealable: address in self.sealables:

        success: bool = raw_call(
            sealable,
            abi_encode(SEAL_DURATION_SECONDS, method_id=method_id("pauseFor(uint256)")),
            revert_on_failure=False
        )
        
        if success and staticcall IPausableUntil(sealable).isPaused():
            log Sealed(
                sealed_by=SEALING_COMMITTEE,
                sealed_for=SEAL_DURATION_SECONDS,
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
    return self.expiry_timestamp - DAO_RESERVE_SECONDS - PROLONGATION_WINDOW_SECONDS


@internal
@view
def _get_prolongation_window_end() -> uint256:
    return self.expiry_timestamp - DAO_RESERVE_SECONDS


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
