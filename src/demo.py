"""Run an end-to-end synthetic issuance, tampering and revocation demonstration."""
import json
from .chain import setup, transact
from .credentials import new_credential, commitment, leaf, MerkleTree


def main():
    w3, admin, issuer, attacker, single, batch = setup()
    document = b'SYNTHETIC credential: Example University; CS; 2026. NOT A REAL DIPLOMA.'
    package = new_credential(document)
    cid, salt, digest = [bytes.fromhex(package[k]) for k in ("id", "salt", "commitment")]
    receipt = transact(w3, single.functions.issue(cid, digest), issuer)
    valid = single.functions.verify(cid, commitment(document, salt)).call()
    tampered = single.functions.verify(cid, commitment(document + b' altered', salt)).call()
    transact(w3, single.functions.revoke(cid), issuer)
    revoked = single.functions.verify(cid, digest).call()
    batch_id = bytes.fromhex('01' * 32)
    tree = MerkleTree([leaf(issuer, batch_id, cid, digest)])
    batch_receipt = transact(w3, batch.functions.issueBatch(batch_id, tree.root), issuer)
    batch_valid = batch.functions.verify(batch_id, cid, digest, tree.proof(0)).call()
    transact(w3, batch.functions.revokeCredential(batch_id, cid), issuer)
    batch_revoked = batch.functions.verify(batch_id, cid, digest, tree.proof(0)).call()
    assert valid and not tampered and not revoked and batch_valid and not batch_revoked
    print(json.dumps({"backend": "local PyEVM", "single_registry": single.address,
        "batch_registry": batch.address, "issuer": issuer,
        "valid_document": valid, "tampered_document": tampered,
        "revoked_document": revoked, "batch_valid": batch_valid,
        "batch_after_revocation": batch_revoked,
        "single_issue_gas": receipt.gasUsed,
        "batch_issue_gas": batch_receipt.gasUsed}, indent=2))


if __name__ == '__main__':
    main()
