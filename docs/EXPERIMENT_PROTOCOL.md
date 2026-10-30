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
- Write cost per credential: `write_gas_per_credential` is
  C_write(n, k) = (`issue_total_gas` + `revoke_total_gas`) / n, where n is the
  batch size and k the revoked count. It is computed from the two raw gas columns
  and is exact for every row.
- Setup gas: `deploy_gas` (contract deployment receipt) and `authorize_gas`
  (the admin's `setIssuer` receipt) are recorded per method in their own columns.
  They are never added into `issue_total_gas` or C_write.
- Proof bytes: number of 32-byte sibling hashes, excluding ABI overhead.
- Tree construction time: leaves + complete Merkle tree, milliseconds.

## Figure and table definitions, established before the experiment

**Table 1.** Individual versus batch registration by n and actual k: issuance
gas per credential, revocation gas, verification gas estimate and proof bytes;
mean and sample standard deviation over repeats. One row per method, batch size
n and revoked count k. Columns: `issue_gas_per_credential`, `revoke_total_gas`
(all k revocations), `revoke_mean_gas` (per revocation), `verify_estimate_gas`
and `proof_bytes`, each as `_mean` and `_std` in gas units or bytes, rounded to
one decimal. `_std` is the sample standard deviation (n - 1 denominator) over
the rows in the group and is 0 for a single row. `revoke_mean_gas` is blank when
k = 0 because no revocation happened. Fractions that give the same k (for
example r = 0 and r = 0.01 at n = 8) share one row, so a row can pool more than
five repeats: `repeats` counts the pooled rows and `revocation_fractions` lists
the fractions pooled.
Generated from `data/raw/benchmark.csv` by `src/generate_figures.py` as
`figures/summary.csv`. Precision/recall are not reported: the synthetic lifecycle
checks are functional assertions, not a labeled fraud-detection dataset.

**Figure 1.** Write gas per credential (gas units, vertical axis) against batch
size (credential count, horizontal axis); method and revocation-fraction curves,
with repeat variation.
X: batch size n, log2 scale, ticks at the measured sizes. Y: C_write(n, k)
(`write_gas_per_credential`), log scale. One line per method and revocation
fraction r: colour and line style give the method, the hollow marker gives r.
Points are the mean over repeats; error bars are the sample standard deviation
(n - 1 denominator), not confidence intervals. Lines group by r, not by k, so
r = 0 and r = 0.01 draw on top of each other wherever k = 0 (every n below 100).
Script: `src/generate_figures.py`; output `figures/write_gas.pdf`. It replaces
the earlier `figures/issuance_scaling.pdf`, which plotted issuance gas only.

**Figure 2.** Simulated verification transaction gas versus batch size.
X: credentials per batch, count, log2 scale. Y: `eth_estimateGas`, gas units,
linear scale. Lines: individual records and Merkle batching. Error bars: sample
standard deviation over repeats. Script: `src/generate_figures.py`;
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
