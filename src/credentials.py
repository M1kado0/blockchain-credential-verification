"""Byte-exact document commitments and sorted-pair Merkle proofs.

Salt is retained with the credential package, never on-chain. Real issuance uses
secrets.token_bytes; deterministic randomness is only for synthetic experiments.
"""
import hashlib
import secrets
from eth_abi import encode
from web3 import Web3

DOMAIN = b"RK-ACADEMIC-CREDENTIAL-V1\x00"


def commitment(document: bytes, salt: bytes) -> bytes:
    if len(salt) != 32:
        raise ValueError("salt must contain exactly 32 bytes")
    return hashlib.sha256(DOMAIN + salt + document).digest()


def new_credential(document: bytes) -> dict:
    salt = secrets.token_bytes(32)
    return {"id": secrets.token_bytes(32).hex(), "salt": salt.hex(),
            "commitment": commitment(document, salt).hex()}


def leaf(issuer: str, batch_id: bytes, credential_id: bytes, digest: bytes) -> bytes:
    inner = Web3.keccak(encode(["address", "bytes32", "bytes32", "bytes32"],
                              [issuer, batch_id, credential_id, digest]))
    return bytes(Web3.keccak(inner))


def pair(a: bytes, b: bytes) -> bytes:
    return bytes(Web3.keccak(min(a, b) + max(a, b)))


class MerkleTree:
    """Preserves leaf order; sorts node pairs; duplicates odd final nodes."""
    def __init__(self, leaves: list[bytes]):
        if not leaves or any(len(x) != 32 for x in leaves):
            raise ValueError("need at least one 32-byte leaf")
        self.levels = [list(leaves)]
        while len(self.levels[-1]) > 1:
            previous = self.levels[-1]
            self.levels.append([pair(previous[i], previous[min(i + 1, len(previous) - 1)])
                                for i in range(0, len(previous), 2)])

    @property
    def root(self) -> bytes:
        return self.levels[-1][0]

    def proof(self, index: int) -> list[bytes]:
        if not 0 <= index < len(self.levels[0]):
            raise IndexError(index)
        proof = []
        for level in self.levels[:-1]:
            proof.append(level[min(index ^ 1, len(level) - 1)])
            index //= 2
        return proof


def verify_proof(root: bytes, value: bytes, proof: list[bytes]) -> bool:
    for sibling in proof:
        value = pair(value, sibling)
    return value == root
