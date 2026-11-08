"""Account-level features and anomaly scores.

Two scorers are compared:
* an Isolation Forest (Liu, Ting and Zhou, 2008) on standardised features,
  which needs no labels but is opaque; and
* a transparent composite: the mean of rank-normalised red flags taken from
  the FATF (2020) virtual-asset red-flag indicators. Each component can be
  explained to a compliance officer or a court.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score

FEATURES = [
    "young_account",       # days from account opening to first cycle (inverted)
    "fan_in",              # distinct funding sources per cycle
    "usdt_value_share",    # share of purchase value in USDT
    "fast_withdrawal",     # mean posterior of the fast dwell component
    "near_threshold",      # share of deposits in [0.8T, T)
    "unlabelled_dest",     # share of withdrawals to non-exchange destinations
    "daytime_share",       # share of deposits 09:00-17:00 ICT
    "directed_exposure",   # value share within k forward hops of flagged nodes
]


def build_features(cycles: pd.DataFrame, dwell_score: pd.Series, exposure: pd.Series,
                   threshold: float = 50_000) -> pd.DataFrame:
    g = cycles.groupby("account_id")
    f = pd.DataFrame(index=g.size().index)
    first = g["deposit_ts"].min()
    opened = g["account_open_ts"].first()
    f["young_account"] = -((first - opened).dt.total_seconds() / 86400.0)
    f["fan_in"] = g["funding_source_id"].nunique() / g.size()
    usdt_val = cycles["deposit_thb"].where(cycles["asset"] == "USDT", 0.0)
    f["usdt_value_share"] = usdt_val.groupby(cycles["account_id"]).sum() / g["deposit_thb"].sum()
    f["fast_withdrawal"] = dwell_score.reindex(f.index).fillna(0.0)
    nt = cycles["deposit_thb"].between(0.8 * threshold, threshold, inclusive="left")
    f["near_threshold"] = nt.groupby(cycles["account_id"]).mean()
    wd = cycles.dropna(subset=["dest_node"])
    unl = (wd["dest_kind"] != "exchange").groupby(wd["account_id"]).mean()
    f["unlabelled_dest"] = unl.reindex(f.index).fillna(0.0)
    hour = cycles["deposit_ts"].dt.hour
    f["daytime_share"] = hour.between(9, 16).groupby(cycles["account_id"]).mean()
    f["directed_exposure"] = exposure.reindex(f.index).fillna(0.0)
    return f[FEATURES]


def composite_score(features: pd.DataFrame) -> pd.Series:
    return features.rank(pct=True).mean(axis=1)


def isolation_score(features: pd.DataFrame, seed: int = 0) -> pd.Series:
    X = (features - features.mean()) / features.std(ddof=0).replace(0, 1)
    model = IsolationForest(n_estimators=300, random_state=seed).fit(X)
    return pd.Series(-model.score_samples(X), index=features.index)


def evaluate(score: pd.Series, truth: pd.Series) -> dict:
    """AUC and precision at k = number of true positives."""
    s, y = score.align(truth, join="inner")
    y = y.astype(int)
    if y.nunique() < 2:
        return {"auc": np.nan, "precision_at_k": np.nan}
    k = int(y.sum())
    top = s.sort_values(ascending=False).index[:k]
    return {"auc": float(roc_auc_score(y, s)), "precision_at_k": float(y.loc[top].mean())}
