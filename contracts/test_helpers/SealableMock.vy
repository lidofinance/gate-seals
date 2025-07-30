# @version 0.4.2

resumed_timestamp: uint256
unpausable: bool
reverts: bool

@deploy
def __init__(_unpausable: bool, _reverts: bool):
    # _unpausable used for imitating cases where the contract failed
    # to pause without reverting
    self.unpausable = _unpausable
    # _reverts used for imitating cases where the contract reverts on pause
    self.reverts = _reverts
    self.resumed_timestamp = 0  # Initialize to 0 to indicate not paused

@external
@view
def isPaused() -> bool:
    return block.timestamp < self.resumed_timestamp

@external
def force_pause_for(_duration: uint256):
    # pause ignoring any checks
    # required to simulate cases where Sealable is already paused but the seal() reverts
    self.resumed_timestamp = block.timestamp + _duration

@external
def pauseFor(_duration: uint256):
    assert not self.reverts, "simulating revert"
    if not self.unpausable:
        self.resumed_timestamp = block.timestamp + _duration