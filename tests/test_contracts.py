import pytest
from eth_tester.exceptions import TransactionFailed
from src.chain import setup, transact
from src.credentials import leaf, MerkleTree


@pytest.fixture
def env():
    return setup()


def test_single_full_lifecycle(env):
    w3, admin, issuer, attacker, registry, _ = env
    cid, digest = b'i' * 32, b'h' * 32
    with pytest.raises(TransactionFailed):
        transact(w3, registry.functions.issue(cid, digest), attacker)
    transact(w3, registry.functions.issue(cid, digest), issuer)
    assert registry.functions.verify(cid, digest).call()
    assert not registry.functions.verify(cid, b'x' * 32).call()
    assert not registry.functions.verify(b'z' * 32, digest).call()
    with pytest.raises(TransactionFailed):
        transact(w3, registry.functions.issue(cid, digest), issuer)
    with pytest.raises(TransactionFailed):
        transact(w3, registry.functions.revoke(cid), attacker)
    transact(w3, registry.functions.revoke(cid), issuer)
    assert not registry.functions.verify(cid, digest).call()
    with pytest.raises(TransactionFailed):
        transact(w3, registry.functions.revoke(cid), issuer)


@pytest.mark.parametrize('size', [1, 3, 8])
def test_batch_proofs_and_revocation(env, size):
    w3, admin, issuer, attacker, _, registry = env
    batch_id, digest = b'b' * 32, b'h' * 32
    ids = [(i + 1).to_bytes(32, 'big') for i in range(size)]
    tree = MerkleTree([leaf(issuer, batch_id, cid, digest) for cid in ids])
    assert registry.functions.leaf(issuer, batch_id, ids[0], digest).call() == leaf(issuer, batch_id, ids[0], digest)
    with pytest.raises(TransactionFailed):
        transact(w3, registry.functions.issueBatch(batch_id, tree.root), attacker)
    transact(w3, registry.functions.issueBatch(batch_id, tree.root), issuer)
    for i, cid in enumerate(ids):
        assert registry.functions.verify(batch_id, cid, digest, tree.proof(i)).call()
        assert not registry.functions.verify(batch_id, cid, b'x' * 32, tree.proof(i)).call()
        assert not registry.functions.verify(b'z' * 32, cid, digest, tree.proof(i)).call()
    with pytest.raises(TransactionFailed):
        transact(w3, registry.functions.revokeCredential(batch_id, ids[0]), attacker)
    transact(w3, registry.functions.revokeCredential(batch_id, ids[0]), issuer)
    assert not registry.functions.verify(batch_id, ids[0], digest, tree.proof(0)).call()
    if size > 1:
        assert registry.functions.verify(batch_id, ids[1], digest, tree.proof(1)).call()
    transact(w3, registry.functions.revokeBatch(batch_id), admin)
    assert not registry.functions.verify(batch_id, ids[-1], digest, tree.proof(size - 1)).call()


def test_issuer_suspension_and_disabled_issuer_can_revoke(env):
    w3, admin, issuer, attacker, registry, _ = env
    cid, digest = b'i' * 32, b'h' * 32
    transact(w3, registry.functions.issue(cid, digest), issuer)
    transact(w3, registry.functions.setIssuer(issuer, False), admin)
    assert not registry.functions.verify(cid, digest).call()
    with pytest.raises(TransactionFailed):
        transact(w3, registry.functions.issue(b'j' * 32, digest), issuer)
    transact(w3, registry.functions.revoke(cid), issuer)
    transact(w3, registry.functions.setIssuer(issuer, True), admin)
    assert not registry.functions.verify(cid, digest).call()


def test_authority_and_two_step_admin(env):
    w3, admin, issuer, attacker, registry, _ = env
    with pytest.raises(TransactionFailed):
        transact(w3, registry.functions.setIssuer(attacker, True), issuer)
    with pytest.raises(TransactionFailed):
        transact(w3, registry.functions.proposeAdmin(attacker), issuer)
    transact(w3, registry.functions.proposeAdmin(issuer), admin)
    with pytest.raises(TransactionFailed):
        transact(w3, registry.functions.acceptAdmin(), attacker)
    transact(w3, registry.functions.acceptAdmin(), issuer)
    assert registry.functions.admin().call() == issuer
    with pytest.raises(TransactionFailed):
        transact(w3, registry.functions.setIssuer(attacker, True), admin)


def test_zero_inputs_and_unknown_revocation(env):
    w3, admin, issuer, attacker, single, batch = env
    for fn in [single.functions.issue(bytes(32), b'h' * 32),
               single.functions.issue(b'i' * 32, bytes(32)),
               batch.functions.issueBatch(bytes(32), b'r' * 32),
               batch.functions.issueBatch(b'b' * 32, bytes(32)),
               single.functions.revoke(b'z' * 32),
               batch.functions.revokeBatch(b'z' * 32)]:
        with pytest.raises(TransactionFailed):
            transact(w3, fn, issuer)


def test_batch_proof_cannot_be_replayed_under_another_issuer(env):
    w3, admin, issuer, attacker, _, registry = env
    bid, cid, digest = b'b' * 32, b'i' * 32, b'h' * 32
    tree = MerkleTree([leaf(issuer, bid, cid, digest)])
    transact(w3, registry.functions.setIssuer(attacker, True), admin)
    # Even reusing the exact root under a different issuer cannot authenticate this leaf.
    transact(w3, registry.functions.issueBatch(bid, tree.root), attacker)
    assert not registry.functions.verify(bid, cid, digest, []).call()
