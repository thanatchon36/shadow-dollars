#!/usr/bin/env bash
# Monte Carlo in resumable chunks (about 10 minutes on one core).
set -euo pipefail
export PYTHONPATH=src
python scripts/run_mc.py ledger 0 200
for s in 0.0025 0.005 0.01 0.02 0.04; do python scripts/run_mc.py ledger $s 50; done
for e in 0 0.05 0.1 0.15 0.2 0.3; do python scripts/run_mc.py scm $e 200; done
python - << 'PY'
import glob, pandas as pd
pd.concat(pd.read_csv(f) for f in sorted(glob.glob("data/processed/mc/ledger_*.csv"))).to_csv("data/processed/mc_ledger.csv", index=False)
pd.concat(pd.read_csv(f) for f in sorted(glob.glob("data/processed/mc/scm_*.csv"))).to_csv("data/processed/mc_scm.csv", index=False)
PY
