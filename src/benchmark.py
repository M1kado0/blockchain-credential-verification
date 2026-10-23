"""Deterministic inputs, real transaction receipt gas, fresh contracts per repeat.

Gas is deterministic for this EVM/compiler/input configuration. Wall-clock
eth_call timings are machine dependent and do not measure public-chain latency.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import itertools
import json
import math
import platform
import random
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from .chain import ROOT, setup, transact, artifact
from .credentials import commitment, leaf, MerkleTree


def expect(condition, message):
    if not condition:
        raise RuntimeError(f"benchmark outcome wrong: {message}")


def validate(sizes, fractions, repeats, queries):
    if any(n < 1 or n > 4096 for n in sizes) or repeats < 1 or queries < 1:
        raise ValueError('sizes must be 1..4096; repeats and queries must be positive')
    if any(not 0 <= r <= 1 for r in fractions):
        raise ValueError('fractions must be between 0 and 1')


def run(sizes, fractions, repeats, queries, seed, output):
    validate(sizes, fractions, repeats, queries)
    random.seed(seed)
    np.random.seed(seed)
    rng = random.Random(seed)
    rows = []
    for n, fraction in itertools.product(sizes, fractions):
        k = math.floor(fraction * n + 1e-9)  # guard float error, e.g. 0.29 * 100
        for repeat in range(repeats):
            w3, admin, issuer, attacker, single, batch = setup()
            batch_id = rng.randbytes(32)
            ids = [rng.randbytes(32) for _ in range(n)]
            salts = [rng.randbytes(32) for _ in range(n)]
            # Synthetic documents only. Identical workload for both methods.
            documents = [json.dumps({"student": i, "degree": "BSc CS", "year": 2026,
                                     "synthetic": True}, sort_keys=True).encode() for i in range(n)]
            digests = [commitment(d, s) for d, s in zip(documents, salts)]
            start = time.perf_counter_ns()
            tree = MerkleTree([leaf(issuer, batch_id, cid, h) for cid, h in zip(ids, digests)])
            tree_build_ms = (time.perf_counter_ns() - start) / 1e6
            proof = tree.proof(0)
            revoked = set(rng.sample(range(n), k))
            for method, contract in (("individual", single), ("merkle_batch", batch)):
                gas, calldata_bytes = 0, 0
                if method == "individual":
                    for cid, h in zip(ids, digests):
                        fn = contract.functions.issue(cid, h)
                        receipt = transact(w3, fn, issuer)
                        gas += receipt.gasUsed
                        calldata_bytes += len(bytes.fromhex(fn._encode_transaction_data()[2:]))
                    vf = contract.functions.verify(ids[0], digests[0])
                    bad = contract.functions.verify(ids[0], commitment(documents[0] + b'X', salts[0]))
                else:
                    fn = contract.functions.issueBatch(batch_id, tree.root)
                    gas = transact(w3, fn, issuer).gasUsed
                    calldata_bytes = len(bytes.fromhex(fn._encode_transaction_data()[2:]))
                    vf = contract.functions.verify(batch_id, ids[0], digests[0], proof)
                    bad = contract.functions.verify(batch_id, ids[0], commitment(documents[0] + b'X', salts[0]), proof)
                expect(vf.call() is True and bad.call() is False, "valid or tampered check")
                # execute every generated valid credential, not just the timed one
                for i in range(n):
                    f = (contract.functions.verify(ids[i], digests[i]) if method == "individual" else
                         contract.functions.verify(batch_id, ids[i], digests[i], tree.proof(i)))
                    expect(f.call() is True, f"credential {i} fails before revocation")
                # eth_estimateGas includes transaction overhead and estimator slack;
                # this is a simulated transaction, not the fee for ordinary eth_call.
                estimate = vf.estimate_gas({"from": attacker})
                for _ in range(3):
                    vf.call()  # warm-up, excluded from timing
                timings = []
                for _ in range(queries):
                    start = time.perf_counter_ns()
                    expect(vf.call() is True, "timed verification")
                    timings.append((time.perf_counter_ns() - start) / 1e6)
                revoke_total_gas = 0
                for i in sorted(revoked):
                    fn = (contract.functions.revoke(ids[i]) if method == "individual" else
                          contract.functions.revokeCredential(batch_id, ids[i]))
                    revoke_total_gas += transact(w3, fn, issuer).gasUsed
                for i in range(n):
                    f = (contract.functions.verify(ids[i], digests[i]) if method == "individual" else
                         contract.functions.verify(batch_id, ids[i], digests[i], tree.proof(i)))
                    expect(f.call() is (i not in revoked), f"credential {i} wrong outcome after revocation")
                rows.append({"method": method, "batch_size": n, "repeat": repeat,
                    "seed": seed, "issue_total_gas": gas, "issue_gas_per_credential": gas / n,
                    "issue_tx_count": n if method == "individual" else 1,
                    "issue_calldata_bytes": calldata_bytes, "verify_estimate_gas": estimate,
                    "verify_calldata_bytes": len(bytes.fromhex(vf._encode_transaction_data()[2:])),
                    "proof_bytes": 0 if method == "individual" else 32 * len(proof),
                    "verify_call_median_ms": statistics.median(timings),
                    "verify_call_p95_ms": float(np.percentile(timings, 95)),
                    "verify_queries": queries, "revocation_fraction": fraction, "revoked_count": k,
                    "revoke_total_gas": revoke_total_gas,
                    "revoke_mean_gas": revoke_total_gas / k if k else 0,
                    "tree_build_ms": 0 if method == "individual" else tree_build_ms,
                    "valid_checked": n, "tampered_rejected": 1, "revoked_rejected": k})
            print(f"completed n={n}, repeat={repeat + 1}/{repeats}", flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metadata = {"created_utc": datetime.now(timezone.utc).isoformat(), "seed": seed,
        "sizes": sizes, "fractions": fractions, "repeats": repeats, "queries": queries,
        "backend": "EthereumTester/PyEVM", "platform": platform.platform(),
        "python": platform.python_version(), "compiler": artifact('CredentialRegistry')['compiler'],
        "compiler_settings": artifact('CredentialRegistry')['settings'],
        "packages": {k: importlib.metadata.version(k) for k in ['web3', 'eth-tester', 'py-evm', 'numpy']},
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / 'src').rglob('*')) if p.suffix in ['.py', '.sol']},
        "csv_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    output.with_suffix('.metadata.json').write_text(json.dumps(metadata, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sizes', nargs='+', type=int, default=[1, 8, 32, 128])
    p.add_argument('--fractions', nargs='+', type=float, default=[0.1])
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--queries', type=int, default=20)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--output', type=Path, default=ROOT / 'data/raw/benchmark.csv')
    args = p.parse_args()
    try:
        validate(args.sizes, args.fractions, args.repeats, args.queries)
    except ValueError as e:
        p.error(str(e))
    run(args.sizes, args.fractions, args.repeats, args.queries, args.seed, args.output)


if __name__ == '__main__':
    main()
