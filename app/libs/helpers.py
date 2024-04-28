import hashlib

import base58

__all__ = (
    'is_tron_address',
)


class TronConfig:
    ADDRESS_SIZE = 34
    ADDRESS_PREFIX_BYTE = 0x41


def is_tron_address(address: str) -> str | bool:
    if len(address) != TronConfig.ADDRESS_SIZE:
        return False

    decode_addr = base58.b58decode(address)
    if len(decode_addr) != 25:
        return False

    if decode_addr[0] != TronConfig.ADDRESS_PREFIX_BYTE:
        return False

    checksum = decode_addr[21:]
    decode_addr = decode_addr[:21]

    hash0 = hashlib.sha256(decode_addr).digest()
    hash1 = hashlib.sha256(hash0).digest()
    checksum1 = hash1[:4]

    if not all([
        checksum[0] == checksum1[0], checksum[1] == checksum1[1],
        checksum[2] == checksum1[2], checksum[3] == checksum1[3]
    ]):
        return False
    return address
