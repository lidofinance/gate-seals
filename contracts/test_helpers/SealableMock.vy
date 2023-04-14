resumed_timestamp: uint256
unpausable: bool
reverts: bool

@external
def __init__(_unpausable: bool, _reverts: bool):
    # _unpausable used for imitating cases where the contract failed
    # to pause without reverting
    self.unpausable = _unpausable
    # _reverts used for imitating cases where the contract reverts on pause
    self.reverts = _reverts

@external
@view
def isPaused() -> bool:
    return self._is_paused()


@external
def __force_pause_for(_duration: uint256):
    # pause ignoring any checks
    # required to simulate cases where Sealable is already paused but the seal() reverts
    self.resumed_timestamp = block.timestamp + _duration


@external
def pauseFor(_duration: uint256):
    assert not self.reverts, "simulating revert"
    if not self.unpausable and not self._is_paused():
        self.resumed_timestamp = block.timestamp + _duration

@internal
@view
def _is_paused() -> bool:
    return block.timestamp < self.resumed_timestamp
