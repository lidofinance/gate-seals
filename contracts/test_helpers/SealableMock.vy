resumed_timestamp: uint256
unpausable: bool

@external
def __init__(_unpausable: bool):
    # _unpausable used for imitating cases where the contract failed
    # to pause without reverting
    self.unpausable = _unpausable

@external
@view
def isPaused() -> bool:
    return self._is_paused()


@external
def pauseFor(_duration: uint256):
    if not self.unpausable and not self._is_paused():
        self.resumed_timestamp = block.timestamp + _duration

@internal
@view
def _is_paused() -> bool:
    return block.timestamp < self.resumed_timestamp
