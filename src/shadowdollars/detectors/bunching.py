"""Bunching estimator for structuring below a verification threshold.

We follow the notch logic of Kleven (2016): fit a flexible counterfactual
density to binned amounts *outside* an exclusion window around the threshold
T, then measure the excess mass just below T.

Two choices matter for retail payment amounts and are tested in the paper:
* the counterfactual is a Poisson GLM whose log-mean is a polynomial in
  log(amount/T). Payment amounts are close to log-normal, whose log-density is
  quadratic in log-amount, so a low-order polynomial extrapolates stably
  across the exclusion window (a polynomial in levels does not);
* round-number heaping is multiplicative (a fixed *proportion* of users pick
  round amounts), so heaping dummies enter the log-mean.

The identifying contrast of the paper is a *difference in bunching* between
deposits that fund USDT purchases and deposits that fund other assets on the
same platform. Legitimate "hassle avoidance" (users who simply prefer not to do
a face scan) should be asset-invariant (Assumption A1); strategic structuring
by mule accounts is concentrated in the stablecoin channel.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class BunchingResult:
    b: float                 # responding share: excess below T / counterfactual mass in [T, T+R)
    b_density: float         # classic normalisation: excess / counterfactual count per bin below T
    excess: float            # excess count below T
    missing: float           # missing count above T
    centers: np.ndarray
    counts: np.ndarray
    counterfactual: np.ndarray
    window: tuple
    se: float = np.nan


def design(left: np.ndarray, width: float, threshold: float, degree: int,
           round_every: tuple[int, ...]) -> np.ndarray:
    u = np.log((left + width / 2) / threshold)
    cols = [u ** k for k in range(degree + 1)]
    for r in round_every:
        has_round = (np.floor((left + width - 1e-9) / r) * r >= left).astype(float)
        cols.append(has_round)
    return np.column_stack(cols)


def poisson_irls(X: np.ndarray, y: np.ndarray, iters: int = 50, tol: float = 1e-9) -> np.ndarray:
    """Poisson regression with log link by iteratively reweighted least squares."""
    beta = np.zeros(X.shape[1])
    beta[0] = np.log(max(y.mean(), 1e-6))
    for _ in range(iters):
        eta = X @ beta
        mu = np.exp(np.clip(eta, -30, 30))
        z = eta + (y - mu) / np.maximum(mu, 1e-9)
        XtW = X.T * mu
        new = np.linalg.solve(XtW @ X + 1e-8 * np.eye(X.shape[1]), XtW @ z)
        converged = np.max(np.abs(new - beta)) < tol
        beta = new
        if converged:
            break
    return beta


def _fit(left, counts, width, threshold, excl_below, excl_above, degree, round_every):
    X = design(left, width, threshold, degree, round_every)
    zl, zu = threshold - excl_below, threshold + excl_above
    excluded = (left >= zl) & (left < zu)
    beta = poisson_irls(X[~excluded], counts[~excluded])
    cf = np.exp(X @ beta)
    below = (left >= zl) & (left < threshold)
    above = (left >= threshold) & (left < zu)
    excess = float(np.sum(counts[below] - cf[below]))
    missing = float(np.sum(cf[above] - counts[above]))
    # Responding share: the fraction of deposits that would have landed in
    # [T, T+R) but were placed just below T. Unlike the classic per-bin
    # normalisation it does not depend on the local slope of the density, so
    # an asset-invariant propensity to avoid the threshold (A1) implies equal
    # values across assets with differently shaped amount distributions.
    b = excess / max(float(np.sum(cf[above])), 1e-9)
    b_density = excess / max(float(np.mean(cf[below])), 1e-9)
    return BunchingResult(b=b, b_density=b_density, excess=excess, missing=missing,
                          centers=left + width / 2, counts=counts, counterfactual=cf, window=(zl, zu))


def bunching(amounts: np.ndarray, threshold: float = 50_000, width: float = 1_000,
             lo: float = 10_000, hi: float = 110_000, excl_below: float = 5_000,
             excl_above: float = 15_000, degree: int = 3,
             round_every: tuple[int, ...] = (5_000, 10_000)) -> BunchingResult:
    edges = np.arange(lo, hi + width, width)
    counts, _ = np.histogram(amounts, bins=edges)
    return _fit(edges[:-1], counts.astype(float), width, threshold, excl_below, excl_above,
                degree, round_every)


def poisson_bootstrap(res: BunchingResult, width: float = 1_000, threshold: float = 50_000,
                      excl_below: float = 5_000, excl_above: float = 15_000, degree: int = 3,
                      round_every: tuple[int, ...] = (5_000, 10_000), reps: int = 200,
                      rng: np.random.Generator | None = None) -> np.ndarray:
    """Bootstrap distribution of b, redrawing each bin count from Poisson.

    A Poisson redraw of every bin is a multinomial bootstrap with a random
    total; it avoids resampling the raw amounts.
    """
    rng = rng or np.random.default_rng(0)
    left = res.centers - width / 2
    out = np.empty(reps)
    for i in range(reps):
        draw = rng.poisson(np.maximum(res.counts, 0)).astype(float)
        out[i] = _fit(left, draw, width, threshold, excl_below, excl_above, degree, round_every).b
    return out


@dataclass
class DiffResult:
    b_usdt: float
    b_other: float
    delta: float
    se: float
    z: float
    p_one_sided: float
    usdt: BunchingResult
    other: BunchingResult


def difference_in_bunching(usdt_amounts: np.ndarray, other_amounts: np.ndarray,
                           reps: int = 200, seed: int = 0, **kw) -> DiffResult:
    rng = np.random.default_rng(seed)
    r1 = bunching(usdt_amounts, **kw)
    r0 = bunching(other_amounts, **kw)
    boot_kw = {k: v for k, v in kw.items() if k in
               ("width", "threshold", "excl_below", "excl_above", "degree", "round_every")}
    d1 = poisson_bootstrap(r1, reps=reps, rng=rng, **boot_kw)
    d0 = poisson_bootstrap(r0, reps=reps, rng=rng, **boot_kw)
    r1.se, r0.se = float(np.std(d1, ddof=1)), float(np.std(d0, ddof=1))
    delta = r1.b - r0.b
    se = float(np.sqrt(r1.se ** 2 + r0.se ** 2))
    z = delta / se if se > 0 else np.nan
    return DiffResult(r1.b, r0.b, delta, se, z, float(1 - stats.norm.cdf(z)), r1, r0)
