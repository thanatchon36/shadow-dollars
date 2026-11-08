"""Flow-based detectors: dwell-time mixtures and graph exposure.

Dwell time
    Time between a fiat deposit and the on-chain withdrawal of the asset it
    bought. Pass-through accounts have a short, tight dwell distribution. A
    Gaussian mixture on log-dwell recovers a 'fast' component; we score each
    account by its mean posterior membership in that component.

Graph exposure
    Practitioners often flag an account if its withdrawal destinations lie
    within k hops of a sanctioned or frozen address. Counting hops on the
    *undirected* graph is fragile: large hubs (exchange hot wallets) are a
    few hops from almost everything. We compare it with a *directed*,
    value-weighted exposure that follows funds forward from the destination.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from sklearn.mixture import GaussianMixture


# ---------------------------------------------------------------------------
# Dwell time
# ---------------------------------------------------------------------------

def dwell_mixture(log_dwell: np.ndarray, max_components: int = 4, seed: int = 0):
    """Fit 1..max_components mixtures, keep the BIC-best (at least 2)."""
    x = np.asarray(log_dwell, float).reshape(-1, 1)
    best, best_bic = None, np.inf
    for k in range(2, max_components + 1):
        gm = GaussianMixture(k, random_state=seed, n_init=2).fit(x)
        bic = gm.bic(x)
        if bic < best_bic:
            best, best_bic = gm, bic
    fast = int(np.argmin(best.means_.ravel()))
    post_fast = best.predict_proba(x)[:, fast]
    return best, fast, post_fast


def account_dwell_score(cycles: pd.DataFrame, seed: int = 0) -> pd.Series:
    w = cycles.dropna(subset=["dwell_min"])
    _, _, post = dwell_mixture(np.log(w["dwell_min"].to_numpy()), seed=seed)
    return pd.Series(post, index=w.index).groupby(w["account_id"]).mean()


# ---------------------------------------------------------------------------
# Graph exposure
# ---------------------------------------------------------------------------

def _csr(edges: np.ndarray, n: int) -> csr_matrix:
    data = np.ones(len(edges))
    return csr_matrix((data, (edges[:, 0], edges[:, 1])), shape=(n, n))


def distance_to_flagged(edges: np.ndarray, n_nodes: int, flagged: np.ndarray,
                        directed: bool = True, limit: int = 6) -> np.ndarray:
    """Hop distance from every node to the nearest flagged node.

    Directed: distance along the direction of fund flow (node -> ... -> F),
    computed as a multi-source search from F on the transposed graph.
    """
    A = _csr(edges, n_nodes)
    G = A.T.tocsr() if directed else (A + A.T).tocsr()
    d = dijkstra(G, directed=directed, indices=flagged, min_only=True, limit=limit,
                 unweighted=True)
    return d


def account_exposure(withdrawals: pd.DataFrame, dist: np.ndarray, k: int) -> pd.Series:
    """Value share of each account's withdrawals sent to nodes within k hops."""
    w = withdrawals.dropna(subset=["dest_node"])
    near = dist[w["dest_node"].astype(int).to_numpy()] <= k
    val = w["deposit_thb"].to_numpy()
    num = pd.Series(val * near, index=w.index).groupby(w["account_id"]).sum()
    den = pd.Series(val, index=w.index).groupby(w["account_id"]).sum()
    return (num / den).fillna(0.0)
