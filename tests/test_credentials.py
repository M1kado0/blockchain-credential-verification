import pytest
from src.credentials import commitment, leaf, MerkleTree, verify_proof


def test_salted_commitment_detects_changes():
    assert commitment(b'diploma', b'a' * 32) != commitment(b'diploma!', b'a' * 32)
    assert commitment(b'diploma', b'a' * 32) != commitment(b'diploma', b'b' * 32)
    with pytest.raises(ValueError):
        commitment(b'diploma', b'short')


@pytest.mark.parametrize('size', [1, 2, 3, 7, 8, 31, 32, 129])
def test_all_merkle_proofs(size):
    issuer = '0x' + '11' * 20
    leaves = [leaf(issuer, b'b' * 32, i.to_bytes(32, 'big'), b'h' * 32) for i in range(size)]
    tree = MerkleTree(leaves)
    for i, value in enumerate(leaves):
        assert verify_proof(tree.root, value, tree.proof(i))
        assert not verify_proof(tree.root, b'x' * 32, tree.proof(i))
    with pytest.raises(IndexError):
        tree.proof(size)


def test_empty_tree_rejected():
    with pytest.raises(ValueError):
        MerkleTree([])
