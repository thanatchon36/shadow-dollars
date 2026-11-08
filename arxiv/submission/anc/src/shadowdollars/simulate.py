"""Agent-based simulator of a Thai-style exchange ledger and its on-chain graph.

PURPOSE. The simulator is a *method-validation* device: it plants known
laundering accounts among realistic legitimate populations so that the power,
size and failure modes of each detector can be measured against ground truth.
Its outputs are never presented as evidence about real markets.

Legitimate populations (the four motives of the paper):
  retail    - domestic traders, mostly non-stablecoin assets, rarely withdraw
  bridge    - buy USDT to trade derivatives offshore; fast withdrawals to
              exchange hot wallets (15% are latency-sensitive arbitrageurs)
  remit     - small, regular USDT purchases forwarded to P2P merchants in
              neighbouring countries
  holder    - buy USDT and keep it on the platform
  merchant  - legitimate OTC/P2P dealers: many counterparties (fan-in), USDT
              only, fast withdrawals to exchange P2P desks. They are the
              hardest false positives and, in practice, the usual victims of
              "triangle" fraud.
Illicit population:
  mule      - young accounts funded by many bank accounts, deposits structured
              below the face-verification threshold, USDT only, withdrawals
              within minutes to fresh consolidation wallets that forward to
              layering wallets near flagged clusters. A share of mules is
              *camouflaged*: rented aged accounts, pre-layered funding from
              one or two bank accounts, little structuring, slower exits and
              partial cash-out through exchange hot wallets.
Parameters are stylised, chosen to make the detection problem *hard* rather
than to match any proprietary dataset.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TYPES = {
    #          share  cycles  median THB  sigma  P(USDT) P(wd|USDT) P(wd|other) dwell(min) dsig  peak hour
    "retail": (0.55, 10, 4_000, 1.00, 0.15, 0.15, 0.08, 3 * 1440, 1.2, 20),
    "bridge": (0.22, 20, 20_000, 0.90, 0.90, 0.95, 0.30, 20, 1.0, 21),
    "remit": (0.10, 10, 6_000, 0.60, 0.95, 0.95, 0.10, 360, 0.8, 19),
    "holder": (0.13, 5, 15_000, 1.00, 0.80, 0.03, 0.05, 30 * 1440, 1.0, 20),
    "merchant": (0.03, 40, 30_000, 0.80, 1.00, 0.95, 0.00, 15, 0.9, 15),
    "mule": (None, 35, 20_000, 0.90, 1.00, 0.98, 0.00, 7, 0.7, 13),
}


@dataclass
class LedgerConfig:
    n_accounts: int = 8_000
    illicit_share: float = 0.01
    start: str = "2025-01-01"
    days: int = 365
    threshold: float = 50_000
    hassle_share: float = 0.35      # legit deposits in [T, 1.25T) moved just below T
    structured_share: float = 0.65  # mule deposits structured into [0.8T, T)
    arb_share: float = 0.15         # bridge accounts that withdraw within minutes
    camouflage: float = 0.40        # share of mules that are camouflaged
    seed: int = 0
    graph: dict = field(default_factory=lambda: dict(n_F=60, n_L=400, n_X=20, n_P=200))


@dataclass
class Simulation:
    cycles: pd.DataFrame
    accounts: pd.DataFrame
    edges: np.ndarray
    n_nodes: int
    flagged: np.ndarray
    node_kind: np.ndarray


def simulate_ledger(cfg: LedgerConfig) -> Simulation:
    rng = np.random.default_rng(cfg.seed)
    T0 = pd.Timestamp(cfg.start)
    n_mule = int(round(cfg.illicit_share * cfg.n_accounts))
    n_legit = cfg.n_accounts - n_mule
    legit_types = ["retail", "bridge", "remit", "holder", "merchant"]
    shares = np.array([TYPES[t][0] for t in legit_types])
    kinds = list(rng.choice(legit_types, size=n_legit, p=shares / shares.sum())) + ["mule"] * n_mule
    kinds = np.array(kinds)
    acc = pd.DataFrame({"account_id": np.arange(cfg.n_accounts), "kind": kinds})
    acc["illicit"] = acc["kind"].eq("mule")
    acc["arb"] = acc["kind"].eq("bridge") & (rng.random(cfg.n_accounts) < cfg.arb_share)
    acc["camo"] = acc["illicit"] & (rng.random(cfg.n_accounts) < cfg.camouflage)

    # Activity windows and opening dates -----------------------------------
    open_days = np.where(acc["illicit"], 0.0, rng.uniform(-3 * 365, 0.8 * cfg.days, cfg.n_accounts))
    act_lo = np.maximum(open_days, 0.0)
    act_hi = np.full(cfg.n_accounts, float(cfg.days))
    mule_start = rng.uniform(0, cfg.days - 45, cfg.n_accounts)
    is_m = acc["illicit"].to_numpy()
    act_lo[is_m] = mule_start[is_m]
    act_hi[is_m] = mule_start[is_m] + 45
    open_days[is_m] = mule_start[is_m] - rng.uniform(0, 20, is_m.sum())
    camo = acc["camo"].to_numpy()
    open_days[camo] = rng.uniform(-3 * 365, 0, camo.sum())          # rented aged accounts
    # Mule-specific heterogeneity: each mule draws its own tradecraft.
    m_dwell = np.exp(rng.uniform(np.log(3), np.log(90), cfg.n_accounts))
    m_struct = np.where(camo, rng.uniform(0.0, 0.4, cfg.n_accounts),
                        rng.uniform(0.2, 0.9, cfg.n_accounts))
    m_fan = np.where(camo, 0.0, rng.uniform(0.4, 0.95, cfg.n_accounts))

    lam = np.array([TYPES[k][1] for k in kinds], float)
    n_cyc = rng.poisson(lam) + 1
    aid = np.repeat(acc["account_id"].to_numpy(), n_cyc)
    k_c = np.repeat(kinds, n_cyc)
    n = len(aid)
    par = {name: np.array([TYPES[k][i] for k in k_c], float)
           for i, name in [(2, "med"), (3, "sig"), (4, "p_usdt"), (5, "pw_u"), (6, "pw_o"),
                           (7, "dwell"), (8, "dsig"), (9, "peak")]}
    illicit_c = k_c == "mule"

    # Timestamps -------------------------------------------------------------
    day = rng.uniform(np.repeat(act_lo, n_cyc), np.repeat(act_hi, n_cyc))
    peaked = rng.random(n) < 0.6
    hour = np.where(peaked, rng.normal(par["peak"], np.where(illicit_c, 3.0, 2.5)),
                    rng.uniform(0, 24, n)) % 24
    deposit_ts = T0 + pd.to_timedelta(np.floor(day) * 86400 + hour * 3600, unit="s")

    # Amounts -----------------------------------------------------------------
    amt = np.exp(rng.normal(np.log(par["med"]), par["sig"]))
    r = rng.random(n)
    amt = np.where(r < 0.30, np.round(amt, -3), amt)                       # heaping 1,000
    amt = np.where((r >= 0.30) & (r < 0.42), np.round(amt / 5000) * 5000, amt)  # heaping 5,000
    T = cfg.threshold
    hassle = (~illicit_c) & (amt >= T) & (amt < 1.25 * T) & (rng.random(n) < cfg.hassle_share)
    amt = np.where(hassle, rng.uniform(0.95 * T, 0.999 * T, n), amt)
    camo_c = np.repeat(acc["camo"].to_numpy(), n_cyc)
    struct_p = np.repeat(m_struct, n_cyc) * cfg.structured_share / 0.65
    struct = illicit_c & (rng.random(n) < struct_p)
    amt = np.where(struct, rng.uniform(0.80 * T, 0.999 * T, n), amt)
    amt = np.maximum(amt, 100.0)

    # Asset, withdrawal, dwell --------------------------------------------------
    asset = np.where(rng.random(n) < par["p_usdt"], "USDT", "BTC")
    pw = np.where(asset == "USDT", par["pw_u"], par["pw_o"])
    withdrawn = rng.random(n) < pw
    arb_c = np.repeat(acc["arb"].to_numpy(), n_cyc)
    dmed = np.where(arb_c, 5.0, par["dwell"])
    dmed = np.where(illicit_c, np.repeat(m_dwell, n_cyc), dmed)
    dmed = np.where(camo_c, np.maximum(dmed, 30.0), dmed)
    dwell = np.exp(rng.normal(np.log(dmed), par["dsig"]))
    dwell = np.where(withdrawn, dwell, np.nan)

    # Funding sources (fan-in) ----------------------------------------------------
    own = aid * 10 + rng.integers(0, 2, n)
    fresh = 10 * cfg.n_accounts + np.arange(n)
    is_merch_c = k_c == "merchant"
    fan_p = np.where(illicit_c, np.repeat(m_fan, n_cyc), np.where(is_merch_c, 0.70, 0.0))
    funding = np.where(rng.random(n) < fan_p, fresh, own)

    cyc = pd.DataFrame({
        "account_id": aid, "kind": k_c, "illicit": illicit_c,
        "account_open_ts": T0 + pd.to_timedelta(np.repeat(open_days, n_cyc), unit="D"),
        "funding_source_id": funding, "deposit_ts": deposit_ts, "deposit_thb": amt,
        "asset": asset, "dwell_min": dwell,
        "network": np.where(withdrawn, np.where(rng.random(n) < np.where(illicit_c, 0.97, 0.85),
                                                 "TRC20", "ERC20"), None),
    })

    # Graph -------------------------------------------------------------------------
    g = cfg.graph
    nF, nL, nX, nP = g["n_F"], g["n_L"], g["n_X"], g["n_P"]
    F = np.arange(0, nF)
    L = np.arange(nF, nF + nL)
    X = np.arange(nF + nL, nF + nL + nX)
    P = np.arange(nF + nL + nX, nF + nL + nX + nP)
    nxt = nF + nL + nX + nP
    W = np.arange(nxt, nxt + cfg.n_accounts)            # one personal wallet per account
    nxt += cfg.n_accounts
    C = np.arange(nxt, nxt + 3 * n_mule).reshape(max(n_mule, 0), 3) if n_mule else np.empty((0, 3), int)
    nxt += 3 * n_mule
    kind_node = np.empty(nxt, dtype=object)
    kind_node[F], kind_node[L], kind_node[X], kind_node[P], kind_node[W] = (
        "flagged", "layering", "exchange", "p2p", "personal")
    if n_mule:
        kind_node[C.ravel()] = "consolidation"

    edges = []
    # Blacklists are incomplete: half of the layering wallets pay a flagged
    # address directly, a fifth do so through another layering wallet, and
    # the rest belong to criminal infrastructure nobody has flagged yet.
    u = rng.random(nL)
    direct, second = u < 0.5, (u >= 0.5) & (u < 0.7)
    edges += list(zip(L[direct], rng.choice(F, direct.sum())))
    edges += list(zip(L[second], rng.choice(L[direct], second.sum())))
    cashout = rng.random(nL) < 0.4                                  # layering -> exchange
    edges += list(zip(L[cashout], rng.choice(X, cashout.sum())))
    edges += list(zip(np.repeat(X, 25), rng.choice(W, 25 * nX)))     # exchange -> users
    tainted = rng.random(nP) < 0.10                                  # some merchants pay layering
    edges += list(zip(P[tainted], rng.choice(L, tainted.sum())))
    edges += list(zip(P, rng.choice(W, nP)))
    is_remit = acc["kind"].eq("remit").to_numpy()
    merchant_of = rng.choice(P, cfg.n_accounts)
    edges += list(zip(W[is_remit], merchant_of[is_remit]))
    stray = (acc["kind"].eq("retail").to_numpy()) & (rng.random(cfg.n_accounts) < 0.05)
    edges += list(zip(W[stray], rng.choice(P, stray.sum())))
    if n_mule:
        edges += list(zip(C.ravel(), rng.choice(L, C.size)))
    edges = np.array(edges, dtype=np.int64)

    # Destinations ----------------------------------------------------------------------
    fav_x = rng.choice(X, cfg.n_accounts)
    dest = np.full(n, -1, dtype=np.int64)
    kc = cyc["kind"].to_numpy()
    w_of = W[aid]
    dest = np.where(np.isin(kc, ["retail", "remit", "holder"]), w_of, dest)
    dest = np.where(np.isin(kc, ["bridge", "merchant"]), fav_x[aid], dest)
    if n_mule:
        mule_rank = np.full(cfg.n_accounts, -1)
        mule_rank[is_m] = np.arange(n_mule)
        cidx = C[np.maximum(mule_rank[aid], 0), rng.integers(0, 3, n)]
        dest = np.where(kc == "mule", cidx, dest)
        via_x = (kc == "mule") & (rng.random(n) < np.where(camo_c, 0.5, 0.2))  # cash-out via CEX
        dest = np.where(via_x, fav_x[aid], dest)
    dest = np.where(withdrawn, dest, -1)
    cyc["dest_node"] = np.where(dest >= 0, dest, np.nan)
    cyc["dest_kind"] = np.where(dest >= 0, kind_node[np.maximum(dest, 0)], None)
    return Simulation(cyc, acc, edges, nxt, F, kind_node)


# ---------------------------------------------------------------------------
# Country panel for synthetic-control experiments
# ---------------------------------------------------------------------------

def country_panel(n_donors: int = 16, T: int = 130, t0: int = 104, effect: float = 0.0,
                  noise: float = 0.04, seed: int = 0) -> np.ndarray:
    """Weekly log index of stablecoin net outflows, unit 0 = 'Thailand'.

    Two persistent common factors with heterogeneous loadings; the treated
    unit's loadings are a convex combination of 4 donors plus small noise so
    that a good synthetic match exists, as SCM requires.
    """
    rng = np.random.default_rng(seed)
    f = np.zeros((T, 2))
    for t in range(1, T):
        f[t] = 0.92 * f[t - 1] + rng.normal(0, [0.08, 0.05])
    f[:, 0] += np.linspace(0, 0.6, T)                       # common growth
    lam = rng.normal(1.0, 0.45, size=(n_donors, 2))
    mu = rng.normal(0.0, 0.3, size=n_donors)
    idx = rng.choice(n_donors, 4, replace=False)
    w = rng.dirichlet(np.ones(4))
    lam_t = w @ lam[idx] + rng.normal(0, 0.03, 2)
    mu_t = w @ mu[idx]
    lam_all = np.vstack([lam_t, lam])
    mu_all = np.concatenate([[mu_t], mu])
    Y = mu_all[:, None] + lam_all @ f.T + rng.normal(0, noise, size=(n_donors + 1, T))
    Y[0, t0:] += effect
    return Y
