# @version 0.3.7

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
     as it is undesireable for the protocol to rely on a multisig. This is why
     each GateSeal has an expiry date. Once expired, GateSeal is no longer
     usable and a new GateSeal must be set up with a new multisig committee. This
     works as a kind of difficulty bomb, a device that encourages the protocol
     to get rid of GateSeals sooner rather than later.

     In the context of GateSeals, sealing is synonymous with pausing the contracts,
     sealables are pausable contracts that implement `pauseFor(duration)` interface.
"""


event Sealed:
    gate_seal: address
    sealed_by: address
    sealed_for: uint256
    sealable: address


event ExpiredPrematurely:
    expired_timestamp: uint256


interface IPausableUntil:
    def pauseFor(_duration: uint256): nonpayable
    def isPaused() -> bool: view

SECONDS_PER_DAY: constant(uint256) = 60 * 60 * 24

# The minimum allowed seal duration is 4 days. This is because it takes at least
# 3 days to pass and enact. Additionally, we want to include a 1-day padding.
MIN_SEAL_DURATION_DAYS: constant(uint256) = 4
MIN_SEAL_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * MIN_SEAL_DURATION_DAYS

# The maximum allowed seal duration is 14 days.
# Anything higher than that may be too long of a disruption for the protocol.
# Keep in mind, that the DAO still retains the ability to resume the contracts
# (or, in the GateSeal terms, "break the seal") prematurely.
MAX_SEAL_DURATION_DAYS: constant(uint256) = 14
MAX_SEAL_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * MAX_SEAL_DURATION_DAYS

# The maximum number of sealables is 8.
# GateSeals were originally designed to pause WithdrawalQueue and ValidatorExitBus,
# however, there is a non-zero chance that there might be more in the future, which
# is why we've opted to use a dynamic-size array.
MAX_SEALABLES: constant(uint256) = 8

# The maximum GateSeal expiry duration is 1 year.
MAX_EXPIRY_PERIOD_DAYS: constant(uint256) = 365
MAX_EXPIRY_PERIOD_SECONDS: constant(uint256) = SECONDS_PER_DAY * MAX_EXPIRY_PERIOD_DAYS

# To simplify the code, we chose not to implement committees in GateSeals.
# Instead, GateSeals are operated by a single account which must be a multisig.
# The code does not perform any such checks but we pinky-promise that
# the sealing committee will always be a multisig. 
SEALING_COMMITTEE: immutable(address)

# The duration of the seal in seconds. This period cannot exceed 14 days. 
# The DAO may decide to resume the contracts prematurely via the DAO voting process.
SEAL_DURATION_SECONDS: immutable(uint256)

# The addresses of pausable contracts. The gate seal must have the permission to
# pause these contracts at the time of the sealing.
# Sealing can be partial, meaning the committee may decide to pause only a subset of this list,
# though GateSeal will still expire immediately.
sealables: DynArray[address, MAX_SEALABLES]

# A unix epoch timestamp starting from which GateSeal is completely unusable
# and a new GateSeal will have to be set up. This timestamp will be changed
# upon sealing to expire GateSeal immediately which will revert any consecutive sealings.
expiry_timestamp: uint256


@external
def __init__(
    _sealing_committee: address,
    _seal_duration_seconds: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _expiry_timestamp: uint256
):
    assert _sealing_committee != empty(address), "sealing committee: zero address"
    assert _seal_duration_seconds >= MIN_SEAL_DURATION_SECONDS, "seal duration: too short"
    assert _seal_duration_seconds <= MAX_SEAL_DURATION_SECONDS, "seal duration: exceeds max"
    assert len(_sealables) > 0, "sealables: empty list"
    assert _expiry_timestamp > block.timestamp, "expiry timestamp: must be in the future"
    assert _expiry_timestamp <= block.timestamp + MAX_EXPIRY_PERIOD_SECONDS, "expiry timestamp: exceeds max expiry period"

    SEALING_COMMITTEE = _sealing_committee
    SEAL_DURATION_SECONDS = _seal_duration_seconds

    for sealable in _sealables:
        assert sealable != empty(address), "sealables: includes zero address"
        assert not sealable in self.sealables, "sealables: includes duplicates"
        self.sealables.append(sealable)
    
    self.expiry_timestamp = _expiry_timestamp


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
    @dev    Immediately expires GateSeal and, thus, can only be called once.
    @param _sealables a proper/improper subset of sealables.
    """
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "gate seal: expired"
    assert len(_sealables) > 0, "sealables: empty subset"

    self._expire_immediately()
    
    # Create a new list to store unique addresses.
    # We iterate over `_sealables` and check if each sealable is not already in the new list.
    # If not, we append it to the new list, ensuring that only unique addresses are stored.
    # If a duplicate is found, we stop execution as the new list serves as a flag for duplicates.
    non_duplicates: DynArray[address, MAX_SEALABLES] = []

    # Instead of reverting the transaction as soon as one of the sealables fails,
    # we iterate through the entire list and collect the indexes of those that failed
    # and report them in the dynamically-generated error message.
    # This will make it easier for us to debug in a hectic situation.
    failed_indexes: DynArray[uint256, MAX_SEALABLES] = []
    sealable_index: uint256 = 0

    for sealable in _sealables:
        assert sealable in self.sealables, "sealables: includes a non-sealable"
        assert sealable not in non_duplicates, "sealables: includes duplicates"

        non_duplicates.append(sealable)

        pausable: IPausableUntil = IPausableUntil(sealable)
        pausable.pauseFor(SEAL_DURATION_SECONDS)
        
        if pausable.isPaused():
            log Sealed(self, SEALING_COMMITTEE, SEAL_DURATION_SECONDS, sealable)
        else:
            failed_indexes.append(sealable_index)
    
        sealable_index += 1

    self.assert_all_sealed(failed_indexes)

    log ExpiredPrematurely(block.timestamp)


@internal
def assert_all_sealed(_failed_indexes: DynArray[uint256, MAX_SEALABLES]):
    """
    @notice reverts if `_failed_indexes` is not empty and report the indexes
            in the error message.
    @dev    If `_failed_indexes` is not empty, the function reverts with the error message.
            The error message is a decimal number where each digit represent the index of the
            sealable that failed to be sealed (not paused after `seal()` was called).

            Note that the indexes in the error message are given in the descending order to avoid
            losing leading zeros when casting to string,

            e.g. [0, 2, 3, 6] -> "6320"
    @param _failed_indexes a list of sealable indexes that failed to seal 
    """
    indexes_as_decimal: uint256 = 0
    loop_index: uint256 = 0

    # convert failed indexes to a decimal representation
    for failed_index in _failed_indexes:
        indexes_as_decimal += failed_index * 10 ** loop_index
        loop_index += 1

    # generate error message with indexes as a decimal string
    error_message: String[78] = uint2str(indexes_as_decimal)

    # assert that there are no failed indexes, else revert with error message
    assert len(_failed_indexes) == 0, error_message

@internal
@view
def _is_expired() -> bool:
    return block.timestamp > self.expiry_timestamp


@internal
def _expire_immediately():
    self.expiry_timestamp = 0