"""Run the Monte Carlo in resumable chunks: one CSV per design point.

Usage: python scripts/run_mc.py ledger 0.01 50
       python scripts/run_mc.py scm 0.15 200
"""
import sys
import time

import pandas as pd

from shadowdollars import montecarlo as M
from shadowdollars.config import DATA_PROCESSED

kind, value, reps = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
out = DATA_PROCESSED / "mc"
out.mkdir(exist_ok=True)
t = time.time()
if kind == "ledger":
    rows = [M.ledger_replicate(value, 1000 + r) for r in range(reps)]
else:
    rows = [M.scm_replicate(value, 5000 + r) for r in range(reps)]
pd.DataFrame(rows).to_csv(out / f"{kind}_{value:g}.csv", index=False)
print(f"{kind} {value:g}: {reps} reps in {time.time() - t:.0f}s")
