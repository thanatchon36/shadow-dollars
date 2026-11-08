"""Monte Carlo evaluation of the detectors against planted ground truth."""
from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd

from .config import DATA_PROCESSED
from .detectors import accounts as A
from .detectors import bunching as B
from .detectors import causal as C
from .detectors import flows as Fl
from .simulate import LedgerConfig, country_panel, simulate_ledger

warnings.filterwarnings("ignore")

BEHAVIOUR = [f for f in A.FEATURES if f != "directed_exposure"]


def ledger_replicate(share: float, seed: int, n_accounts: int = 8_000) -> dict:
    sim = simulate_ledger(LedgerConfig(n_accounts=n_accounts, illicit_share=share, seed=seed))
    cy = sim.cycles
    out = {"share": share, "seed": seed, "n_mules": int(sim.accounts["illicit"].sum())}
    d = B.difference_in_bunching(cy.loc[cy.asset == "USDT", "deposit_thb"].to_numpy(),
                                 cy.loc[cy.asset != "USDT", "deposit_thb"].to_numpy(),
                                 reps=200, seed=seed)
    out.update(b_usdt=d.b_usdt, b_other=d.b_other, delta_b=d.delta, se_delta=d.se,
               p_bunch=d.p_one_sided, reject_bunch=d.p_one_sided < 0.05)
    if out["n_mules"] == 0:
        return out
    truth = sim.accounts.set_index("account_id")["illicit"]
    ds = Fl.account_dwell_score(cy, seed=seed)
    dd = Fl.distance_to_flagged(sim.edges, sim.n_nodes, sim.flagged, directed=True)
    du = Fl.distance_to_flagged(sim.edges, sim.n_nodes, sim.flagged, directed=False)
    ex_dir = Fl.account_exposure(cy, dd, 3)
    ex_und = Fl.account_exposure(cy, du, 2)
    feat = A.build_features(cy, ds, ex_dir)
    scores = {
        "dwell_only": ds,
        "undirected_2hop": ex_und,
        "directed_3hop": ex_dir,
        "composite_behaviour": A.composite_score(feat[BEHAVIOUR]),
        "composite_all": A.composite_score(feat),
        "iforest_behaviour": A.isolation_score(feat[BEHAVIOUR], seed=seed),
        "iforest_all": A.isolation_score(feat, seed=seed),
    }
    for name, s in scores.items():
        ev = A.evaluate(s.reindex(truth.index).fillna(0.0), truth)
        out[f"auc_{name}"] = ev["auc"]
        out[f"p@k_{name}"] = ev["precision_at_k"]
    return out


def scm_replicate(effect: float, seed: int, n_donors: int = 19) -> dict:
    Y = country_panel(n_donors=n_donors, effect=-effect, seed=seed)
    r = C.synthetic_control(Y, treated=0, t0=104)
    return {"effect": effect, "seed": seed, "att": r.att, "p": r.p_value,
            "reject": r.p_value <= 0.05, "pre_rmspe": float(np.sqrt(np.mean(r.gap[:104] ** 2)))}


def run(shares=(0.0, 0.0025, 0.005, 0.01, 0.02, 0.04), reps: int = 40,
        effects=(0.0, 0.05, 0.10, 0.15, 0.20, 0.30), scm_reps: int = 60) -> None:
    t0 = time.time()
    rows = [ledger_replicate(s, 1000 + r) for s in shares for r in range(reps)]
    pd.DataFrame(rows).to_csv(DATA_PROCESSED / "mc_ledger.csv", index=False)
    print(f"ledger MC: {len(rows)} replicates in {time.time() - t0:.0f}s")
    t1 = time.time()
    rows = [scm_replicate(e, 5000 + r) for e in effects for r in range(scm_reps)]
    pd.DataFrame(rows).to_csv(DATA_PROCESSED / "mc_scm.csv", index=False)
    print(f"SCM MC: {len(rows)} replicates in {time.time() - t1:.0f}s")


if __name__ == "__main__":
    run()
