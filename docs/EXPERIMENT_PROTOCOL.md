# Captions-first measurement protocol

Question: For a fixed compiler, EVM and issuer/revocation model, how does
Merkle-batched issuance change issuance gas, proof size and verification cost
relative to storing each credential separately?

Hypothesis (not a prior result): amortized batch issuance gas decreases with
batch size, while proof length and verification work increase. The experiment
does not claim to establish a previously unstudied research gap.

## Fixed inputs and configuration

- Solidity 0.8.24; optimizer enabled, 200 runs; Shanghai bytecode target.
- Local EthereumTester/PyEVM; fresh chain and deployments for each repeat.
- Synthetic documents, salted SHA-256 commitments, random 32-byte identifiers.
- Seed 42 for Python and NumPy; deterministic generation for synthetic inputs.
  Actual document packaging uses cryptographic randomness.
- Batch sizes 1, 8, 32 and 128; three independent deployments per size.
- Twenty valid verification calls per method per repeat, after three warm-ups.
- Both methods issue exactly the same set of credentials under the same issuer.
- All valid generated credentials are checked; one byte-modified document and
  every revoked credential (k = floor(r * n), same seeded set for both methods)
  are checked per method per repeat. A wrong outcome aborts the run before the
  CSV is written.

Deployment and issuer-authorization gas are excluded from issuance totals. These
are amortized setup operations. Each method's authorization and deployment are
performed before its measured issuance workload. Different transaction histories
can change timestamps but timestamps are not used by these contracts.

## Exact metrics

- Issuance gas: sum of mined transaction `receipt.gasUsed`; includes transaction
  intrinsic cost and execution, excludes deployment/setup.
- Gas per credential: issuance total divided by batch size.
- Issuance calldata bytes: ABI-encoded input size summed across issuance txs.
- Verification gas: `eth_estimateGas` for a hypothetical transaction invoking the
  view function; includes intrinsic cost and estimator slack. Ordinary `eth_call`
  does not charge a transaction fee.
- Local verification duration: `perf_counter_ns` around one `eth_call`, milliseconds.
  Includes local provider/serialization/EVM overhead, excludes public network,
  finality, document hashing and off-chain proof retrieval.
- Revocation gas: `revoke_total_gas` is the sum of the actual revoke transaction
  receipts for the k revoked credentials, `revoke_mean_gas` is that sum divided
  by k (0 when k is 0). `revocation_fraction` and `revoked_count` (k) are
  recorded per row. These replace the earlier single-revocation `revoke_gas`.
  Batch-wide revocation cost is not measured by this experiment.
- Proof bytes: number of 32-byte sibling hashes, excluding ABI overhead.
- Tree construction time: leaves + complete Merkle tree, milliseconds.

## Figure and table definitions, established before the experiment

**Table 1.** Individual and Merkle-batch credential registration on a local EVM.
For each batch size, report mean total issuance gas (gas units), mean issuance gas
per credential (gas units), mean simulated verification transaction estimate (gas
units), mean individual revocation gas (gas units), and proof size (bytes).
Generated from `data/raw/benchmark.csv` by `src/generate_figures.py` as
`figures/summary.csv`. Precision/recall are not reported: the synthetic lifecycle
checks are functional assertions, not a labeled fraud-detection dataset.

**Figure 1.** Issuance gas per credential versus credentials per batch.
X: batch size, credential count, log2 scale. Y: gas units per credential, log scale.
Lines: individual records and Merkle batching. Error bars: sample standard
deviation across three fresh-deployment repeats, not confidence intervals.
Script: `src/generate_figures.py`; output `figures/issuance_scaling.pdf`.

**Figure 2.** Simulated verification transaction gas versus batch size.
X: credentials per batch, count, log2 scale. Y: `eth_estimateGas`, gas units,
linear scale. Same lines/error bars as Figure 1. Script: `src/generate_figures.py`;
output `figures/verification_gas.pdf`.

**Supplementary Figure.** Local PyEVM verification call duration versus batch
size. X: count, log2 scale. Y: mean of repeat-level median call durations, ms.
Error bars: sample standard deviation of these repeat medians.
Output `figures/local_call_latency.pdf`.

## Threats to validity

Synthetic records do not model real registrars or document delivery. SHA-256
document commitments and Keccak Merkle hashing serve distinct purposes. Proof
generation and availability are a real extra burden of batching. Input bytes
affect calldata gas; random seeds and source/CSV hashes are recorded. Repeating
deterministic gas measurements is not evidence about internet variability.
PyEVM may execute a newer fork than the Shanghai compiler target; exact package
versions are recorded, and claims apply to that execution environment only.

The experiment measures one valid proof path per batch for gas and timing.
Odd trees duplicate final siblings; test coverage includes non-power-of-two sizes.
The default benchmark sizes are powers of two. Scaling to thousands of records,
external wallets, permissioned networks, RPC load, malicious institutions, key
rotation, real identity validation and national adoption remain unmeasured.

No external data API is used, so API rate limiting does not apply. The RPC CLI
sets a 15-second HTTP timeout and transactions use a 120-second receipt timeout.
Transactions are not automatically retried: a retry after an ambiguous response
could accidentally resubmit an already mined operation.
