"""Causal designs for policy shocks.

synthetic_control
    Abadie, Diamond and Hainmueller (2010): convex weights on donor units that
    reproduce the treated unit's pre-treatment path; inference by in-space
    placebos ranked on the post/pre RMSPE ratio (Abadie, 2021).

event_study
    Aggregate abnormal activity around a dated shock. The counterfactual is a
    log-linear trend with day-of-week effects estimated on a clean window
    before the event; uncertainty comes from a moving-block bootstrap of the
    estimation residuals, which respects serial correlation.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize


# ---------------------------------------------------------------------------
# Synthetic control
# ---------------------------------------------------------------------------

def synth_weights(y1_pre: np.ndarray, Y0_pre: np.ndarray) -> np.ndarray:
    J = Y0_pre.shape[1]
    w0 = np.full(J, 1.0 / J)

    def loss(w):
        r = y1_pre - Y0_pre @ w
        return r @ r

    def grad(w):
        return -2 * Y0_pre.T @ (y1_pre - Y0_pre @ w)

    res = minimize(loss, w0, jac=grad, method="SLSQP", bounds=[(0, 1)] * J,
                   constraints=({"type": "eq", "fun": lambda w: w.sum() - 1,
                                 "jac": lambda w: np.ones_like(w)},),
                   options={"maxiter": 500, "ftol": 1e-10})
    w = np.clip(res.x, 0, None)
    return w / w.sum()


@dataclass
class SynthResult:
    weights: np.ndarray
    gap: np.ndarray            # treated minus synthetic, all periods
    ratio: float               # post/pre RMSPE
    placebo_gaps: np.ndarray   # (J, T)
    placebo_ratios: np.ndarray
    p_value: float
    att: float                 # mean post-treatment gap


def synthetic_control(Y: np.ndarray, treated: int, t0: int, placebos: bool = True) -> SynthResult:
    """Y is (units, periods); periods < t0 are pre-treatment."""
    n, T = Y.shape

    def fit(i):
        donors = [j for j in range(n) if j != i]
        w = synth_weights(Y[i, :t0], Y[donors, :t0].T)
        synth = Y[donors].T @ w
        gap = Y[i] - synth
        pre = np.sqrt(np.mean(gap[:t0] ** 2))
        post = np.sqrt(np.mean(gap[t0:] ** 2))
        return w, gap, post / max(pre, 1e-12)

    w, gap, ratio = fit(treated)
    pg, pr = [], []
    if placebos:
        for j in range(n):
            if j == treated:
                continue
            _, g, r = fit(j)
            pg.append(g)
            pr.append(r)
    pr = np.array(pr)
    p = (1 + np.sum(pr >= ratio)) / (1 + len(pr)) if len(pr) else np.nan
    return SynthResult(w, gap, ratio, np.array(pg), pr, float(p), float(gap[t0:].mean()))


# ---------------------------------------------------------------------------
# Aggregate event study
# ---------------------------------------------------------------------------

@dataclass
class EventStudyResult:
    rel_day: np.ndarray
    abnormal: np.ndarray       # actual - predicted, log points
    car: np.ndarray            # cumulative abnormal from day 0
    car_lo: np.ndarray
    car_hi: np.ndarray
    car_30: float              # CAR over [0, 30]
    car_30_ci: tuple


def _design(idx: pd.DatetimeIndex, t_ref: pd.Timestamp) -> np.ndarray:
    trend = (idx - t_ref).days.to_numpy(float) / 365.0
    dow = np.zeros((len(idx), 6))
    for k in range(6):
        dow[:, k] = (idx.dayofweek == k + 1).astype(float)
    return np.column_stack([np.ones(len(idx)), trend, dow])


def event_study(series: pd.Series, event: str, est=(-150, -31), win=(-30, 60),
                block: int = 14, reps: int = 2000, seed: int = 0) -> EventStudyResult:
    s = np.log(series.dropna())
    t = pd.Timestamp(event)
    est_idx = s.loc[t + pd.Timedelta(days=est[0]): t + pd.Timedelta(days=est[1])].index
    win_idx = s.loc[t + pd.Timedelta(days=win[0]): t + pd.Timedelta(days=win[1])].index
    Xe, ye = _design(est_idx, t), s.loc[est_idx].to_numpy()
    beta, *_ = np.linalg.lstsq(Xe, ye, rcond=None)
    resid = ye - Xe @ beta
    Xw = _design(win_idx, t)
    ab = s.loc[win_idx].to_numpy() - Xw @ beta
    rel = (win_idx - t).days.to_numpy()
    post = rel >= 0
    car = np.where(post, np.cumsum(np.where(post, ab, 0.0)), np.nan)

    # Null distribution of the CAR that includes (i) future shocks and (ii) the
    # sampling error of the extrapolated trend: re-draw estimation residuals by
    # moving blocks, refit, and add block-resampled future errors.
    rng = np.random.default_rng(seed)
    n_post, n_est, n_win = int(post.sum()), len(resid), len(win_idx)
    starts_max = n_est - block

    def blocks(m):
        st = rng.integers(0, starts_max + 1, size=int(np.ceil(m / block)))
        return np.concatenate([resid[s0:s0 + block] for s0 in st])[:m]

    sims = np.empty((reps, n_post))
    fitted_e = Xe @ beta
    for r in range(reps):
        b_star, *_ = np.linalg.lstsq(Xe, fitted_e + blocks(n_est), rcond=None)
        ab_star = Xw @ (beta - b_star) + blocks(n_win)
        sims[r] = np.cumsum(ab_star[post])
    lo = np.full(len(rel), np.nan)
    hi = np.full(len(rel), np.nan)
    lo[post] = np.percentile(sims, 2.5, axis=0)
    hi[post] = np.percentile(sims, 97.5, axis=0)
    i30 = np.where(rel == 30)[0]
    c30 = float(car[i30[0]]) if len(i30) else np.nan
    ci30 = (float(lo[i30[0]]), float(hi[i30[0]])) if len(i30) else (np.nan, np.nan)
    return EventStudyResult(rel, ab, car, lo, hi, c30, ci30)
