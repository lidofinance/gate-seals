resumed_timestamp: uint256

@external
@view
def is_paused() -> bool:
    return self.resumed_timestamp > block.timestamp

@external
def pause(_duration: uint256):
    self.resumed_timestamp = block.timestamp + _duration