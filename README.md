# Blockchain credential verification for Kazakhstan education

CSCI 435 Research Track, Nazarbayev University

## Current status

Planning checkpoint prepared during Week 9. This repository contains the Stage 3
proposal and implementation plan. The team's annotated bibliography exists outside
this repository.

## Research question

How do batch size and revocation workload affect the gas trade-off between
individual and Merkle-batched credential registration under the same issuer policy?

The intended output is a tested command-line prototype and reproducible comparison,
not a national deployment. The novelty claim is provisional until checked against
the required course readings. See [two-page proposal](docs/proposal.pdf)
## Where everything belongs

| Path | Purpose | Status |
|---|---|---|
| `docs/proposal.tex`, `docs/proposal.pdf` | Two-page Stage 3 proposal | Draft for instructor review |
| `docs/TEAM_PLAN.md` | Two-person work plan and acceptance criteria | Suggested allocation |
| `docs/PROGRESS.md` | Honest checkpoint record | Planning only |
| `paper/` | Final 10-15-page LaTeX paper and bibliography | Not written yet |
| `src/` | Contracts, synthetic data and experiment scripts | Implemented (T-1) |
| `tests/` | Functional/security tests | Implemented (T-1) |
| `data/` | Synthetic inputs, raw CSV and environment metadata | Implemented (T-1) |
| `figures/` | Script-generated vector figures | Implemented (T-1) |
| `notebooks/` | Optional exploratory analysis | Implemented (T-1) |

## Build the proposal

Requires a LaTeX installation with article, geometry, lmodern, enumitem, booktabs,
tabularx and hyperref (a normal TeX Live or MacTeX installation).

```bash
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=docs docs/proposal.tex
```

Alternatively upload `docs/proposal.tex` to Overleaf and compile using pdfLaTeX.
The proposed Python 3.12 / Solidity 0.8.24 runtime is not installed by this commit.
Pinned experiment dependencies and exact run commands will accompany the baseline.

Run from a clean clone (Python 3.12, Node.js 20 or newer):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
npm ci --ignore-scripts
npm run compile
python -m pytest tests -q
python -m src.demo
```

## Next contribution

We gonna find out.

## Contributions and attribution

Each person commits real work through their own account using the actual date.
