# Validation of the baseline code

Executed while preparing the baseline on 30 September 2026 UTC:

- Compiled all contracts using solc-js 0.8.24, Shanghai target, optimizer 200.
- Python unit and PyEVM integration tests: **18 passed**.
- Foundry 1.7.1 tests: **7 passed**, including **256 fuzz cases** in the tampering
  test. Since the native Solidity binary download was unavailable, Foundry used
  a temporary standard-JSON wrapper around the same pinned solc-js compiler.
  The wrapper was validation tooling, not a project dependency. The ordinary
  `forge test` command downloads the pinned native compiler on your machine.
- Self-contained demo: valid credential accepted; byte-modified document and
  revoked credentials rejected; individual and batch paths exercised.
- Local Anvil RPC workflow: CLI deploy, authorize, package, issue, verify, revoke
  and re-verify exercised. Verification returns `VALID` before revocation and
  `INVALID` after it, with exit codes 0 and 1 respectively.
- Benchmark: seed 42, sizes 1/8/32/128, three repeats, twenty timed verification
  queries per method and repeat; **24 measured rows**. All valid generated
  credentials and the configured tampered/revoked examples passed assertions.
- Figure script: generated three vector PDFs and a summary CSV from those rows.
- Dependencies installed in a clean Python 3.12 environment; exact resolved
  package versions recorded in `requirements-lock.txt`.

Not executed: Docker build (Docker unavailable), GitHub-hosted CI, public-testnet
deployment, production security audit, institutional/identity integrations, legal
compliance assessment or any real student-data experiment. The CI workflow and
Dockerfile are provided for subsequent runs.

The included experiment values are local measurements. For example, a batch of
128 credentials used mean issuance gas of about 573 gas units per credential in
the batch registry, versus about 73,309 in the individual registry. That is an
amortized issuance comparison, not a complete operational-cost estimate. See the
raw CSV and protocol for excluded setup costs and the added proof requirements.

Run commands and exact metric definitions are in README.md and
EXPERIMENT_PROTOCOL.md. Timings will vary between machines. Small gas variation
between repeats arises from different zero bytes in deterministic random calldata.
