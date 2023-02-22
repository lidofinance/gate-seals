from ape import project

# Blueprint utils
# https://eips.ethereum.org/EIPS/eip-5202

def get_blueprint_address(deployer, initcode):
    transaction = project.provider.network.ecosystem.create_transaction(
        chain_id=project.provider.chain_id,
        data=initcode,
        gas_price=project.provider.gas_price,
        nonce=deployer.nonce,
    )

    transaction.gas_limit = project.provider.estimate_gas_cost(transaction)
    signed_transaction = deployer.sign_transaction(transaction)
    receipt = project.provider.send_transaction(signed_transaction)
    return receipt.contract_address


def get_blueprint_initcode(bytecode):
    if isinstance(bytecode, str):
        bytecode = bytes.fromhex(bytecode[2:])
    initcode = b"\xfe\x71\x00" + bytecode  # eip-5202 preamble version 0
    initcode = (
        b"\x61"
        + len(initcode).to_bytes(2, "big")
        + b"\x3d\x81\x60\x0a\x3d\x39\xf3"
        + initcode
    )
    return initcode


def verify_preamble(initcode):
    assert initcode[0] == int("FE", 16), "blueprint must start with magic byte: 0xFE"
    assert initcode[1] == int("71", 16), "blueprint's second byte must be 0x71"
    n_length_bytes = initcode[2] & 0b11
    assert n_length_bytes != 0b11, "reserved bits are set, not an EIP5202 preamble"