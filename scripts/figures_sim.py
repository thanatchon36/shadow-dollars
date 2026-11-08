"""Figures and tables from the simulation study (Section 6 of the paper).

Every figure carries a SIMULATED DATA marker above its source note: these figures validate
methods against planted ground truth and say nothing about real markets.
"""
from __future__ import annotations

import json
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import gaussian_kde
from sklearn.metrics import roc_curve

from shadowdollars import style
from shadowdollars.config import DATA_PROCESSED, PALETTE, TABLES
from shadowdollars.detectors import accounts as A
from shadowdollars.detectors import bunching as B
from shadowdollars.detectors import causal as C
from shadowdollars.detectors import flows as Fl
from shadowdollars.montecarlo import BEHAVIOUR
from shadowdollars.simulate import LedgerConfig, country_panel, simulate_ledger

warnings.filterwarnings("ignore")
style.apply()
W = style.TEXT_WIDTH_IN
FACTS: dict = {}
SHOWCASE = LedgerConfig(illicit_share=0.02, seed=11)


# ---------------------------------------------------------------------------
# 1. Bunching: USDT versus other assets
# ---------------------------------------------------------------------------

def fig_bunching(sim):
    cy = sim.cycles
    d = B.difference_in_bunching(cy.loc[cy.asset == "USDT", "deposit_thb"].to_numpy(),
                                 cy.loc[cy.asset != "USDT", "deposit_thb"].to_numpy(), reps=300)
    FACTS.update(showcase_b_usdt=d.b_usdt, showcase_b_other=d.b_other, showcase_delta=d.delta,
                 showcase_se=d.se, showcase_p=d.p_one_sided)
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.6), gridspec_kw=dict(wspace=0.22))
    for ax, res, lab, col in [(axes[0], d.usdt, "Deposits funding USDT", PALETTE["illicit"]),
                              (axes[1], d.other, "Deposits funding other assets", PALETTE["eth"])]:
        x = res.centers / 1000
        keep = (x >= 20) & (x <= 90)
        ax.bar(x[keep], res.counts[keep], width=0.9, color=PALETTE["peer"], alpha=0.55, lw=0)
        ax.plot(x[keep], res.counterfactual[keep], color=PALETTE["ink"], lw=1.1, ls=(0, (3, 2)))
        zl, zu = res.window[0] / 1000, res.window[1] / 1000
        below = keep & (x >= zl) & (x < 50)
        ax.bar(x[below], res.counts[below], width=0.9, color=col, alpha=0.9, lw=0)
        ax.axvline(50, color=PALETTE["ink"], lw=0.8)
        ax.axvspan(zl, zu, color=PALETTE["grid"], alpha=0.5, lw=0, zorder=0)
        ax.set_title(lab, loc="left", fontsize=7.6, fontweight="bold", pad=4)
        ax.text(0.98, 0.70, f"responding share\n$\\hat\\beta$ = {res.b:.2f} (s.e. {res.se:.2f})",
                transform=ax.transAxes, ha="right", va="top", fontsize=6.8, color=col, linespacing=1.3)
        ax.set_xlabel("deposit amount, thousand THB (1,000-baht bins)", fontsize=6.6, color=PALETTE["muted"])
        if ax is axes[0]:
            ax.text(50.6, ax.get_ylim()[1] * 0.97, "50,000 THB\nface-scan threshold", fontsize=6, va="top",
                    color=PALETTE["muted"], linespacing=1.2)
    axes[0].set_ylabel("deposits per bin")
    style.headline(fig, "Structuring shows up as a difference in bunching, not as bunching itself",
                   f"Both channels bunch below the threshold because honest users dislike the face scan. "
                   f"The USDT excess over other assets is the signal: difference = {d.delta:.2f} "
                   f"(s.e. {d.se:.2f}, one-sided p = {d.p_one_sided:.3f}). One simulated exchange-year, 2% mule accounts.")
    style.source(fig, simulated=True, text="Dashed line: Poisson-GLM counterfactual in log-amount with round-number effects, fitted outside the "
                      "shaded exclusion window. Coloured bars: excess mass below the threshold.")
    style.save(fig, "fig_bunching")


# ---------------------------------------------------------------------------
# 2. Dwell-time ridgeline and ROC curves
# ---------------------------------------------------------------------------

def fig_dwell_roc(sim):
    cy, acc = sim.cycles, sim.accounts.set_index("account_id")
    w = cy.dropna(subset=["dwell_min"]).copy()
    w["group"] = w["kind"]
    camo = acc["camo"].reindex(w["account_id"]).to_numpy()
    arb = acc["arb"].reindex(w["account_id"]).to_numpy()
    w.loc[(w["kind"] == "mule") & camo, "group"] = "mule_camo"
    w.loc[(w["kind"] == "bridge") & arb, "group"] = "arbitrage"
    groups = [("retail", "Domestic traders", PALETTE["legit"]),
              ("remit", "Cross-border remitters", PALETTE["remit"]),
              ("bridge", "Offshore bridge traders", PALETTE["bridge"]),
              ("arbitrage", "Arbitrageurs", PALETTE["bridge"]),
              ("merchant", "Honest P2P merchants", PALETTE["neighbour"]),
              ("mule_camo", "Mules, camouflaged", PALETTE["illicit"]),
              ("mule", "Mules", PALETTE["illicit"])]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 3.1), gridspec_kw=dict(width_ratios=[1.35, 1], wspace=0.28))
    grid = np.linspace(-0.5, 5.2, 400)
    for k, (g, lab, col) in enumerate(groups):
        x = np.log10(w.loc[w["group"] == g, "dwell_min"].to_numpy())
        if len(x) < 10:
            continue
        dens = gaussian_kde(x, bw_method=0.18)(grid)
        dens = dens / dens.max() * 0.85
        base = len(groups) - 1 - k
        a1.fill_between(grid, base, base + dens, color=col, alpha=0.35 if "mule" not in g else 0.75, lw=0)
        a1.plot(grid, base + dens, color=col, lw=0.9)
        a1.text(-0.55, base + 0.12, lab, ha="right", va="bottom", fontsize=6.6, color=col if "mule" in g else PALETTE["ink"],
                fontweight="bold" if "mule" in g else "normal")
    for v, lab in [(0, "1 min"), (1, "10 min"), (np.log10(60), "1 hour"), (np.log10(1440), "1 day"),
                   (np.log10(7 * 1440), "1 week")]:
        a1.vlines(v, -0.1, len(groups) - 0.3, color=PALETTE["grid"], lw=0.7, zorder=0)
        a1.text(v, len(groups) - 0.05, lab, ha="center", va="bottom", fontsize=6, color=PALETTE["muted"])
    a1.set_yticks([])
    a1.set_xlim(-0.5, 5.2)
    a1.set_xticks([])
    a1.grid(False)
    a1.spines["left"].set_visible(False)
    a1.set_xlabel("time from deposit to on-chain withdrawal (log scale)", fontsize=6.6, color=PALETTE["muted"])
    a1.set_title("(a) Dwell time by population", loc="left", fontsize=7.6, fontweight="bold", pad=14)

    truth = acc["illicit"]
    ds = Fl.account_dwell_score(cy)
    dd = Fl.distance_to_flagged(sim.edges, sim.n_nodes, sim.flagged, directed=True)
    du = Fl.distance_to_flagged(sim.edges, sim.n_nodes, sim.flagged, directed=False)
    ex_dir, ex_und = Fl.account_exposure(cy, dd, 3), Fl.account_exposure(cy, du, 2)
    feat = A.build_features(cy, ds, ex_dir)
    scores = [("Undirected 2-hop exposure", ex_und, PALETTE["faint"], (0, (2, 2))),
              ("Dwell time only", ds, PALETTE["neighbour"], "-"),
              ("Directed 3-hop exposure", ex_dir, PALETTE["remit"], "-"),
              ("Red-flag composite", A.composite_score(feat), PALETTE["bridge"], "-"),
              ("Isolation forest", A.isolation_score(feat), PALETTE["illicit"], "-")]
    for lab, s, col, ls in scores:
        s = s.reindex(truth.index).fillna(0.0)
        fpr, tpr, _ = roc_curve(truth.astype(int), s)
        a2.plot(fpr, tpr, color=col, lw=1.3, ls=ls, label=lab)
    a2.set_xscale("symlog", linthresh=0.01)
    a2.set_xlim(0, 1)
    a2.set_ylim(0, 1.01)
    a2.set_xticks([0, 0.01, 0.1, 1])
    a2.set_xticklabels(["0", "1%", "10%", "100%"])
    a2.set_xlabel("false-positive rate (honest accounts flagged)", fontsize=6.6, color=PALETTE["muted"])
    a2.set_ylabel("share of mules caught", fontsize=6.8)
    a2.legend(loc="upper left", bbox_to_anchor=(-0.02, -0.2), ncol=2, fontsize=6.0, handlelength=1.6,
              columnspacing=1.0)
    a2.set_title("(b) Detection trade-off", loc="left", fontsize=7.6, fontweight="bold", pad=14)
    style.headline(fig, "Speed alone cannot separate mules from arbitrageurs and honest dealers",
                   "Panel (a): kernel densities of withdrawal speed. Panel (b): ROC curves at low false-positive rates "
                   "(symmetric log x-axis). One simulated exchange-year with 2% mule accounts.")
    style.source(fig, simulated=True, text="Mules draw their own tradecraft: exit speeds from 3 to 90 minutes, 40% camouflaged with rented aged "
                      "accounts. Blacklists cover 70% of layering wallets within two hops.")
    style.save(fig, "fig_dwell_roc")


# ---------------------------------------------------------------------------
# 3. Network 'galaxy': direction matters
# ---------------------------------------------------------------------------

def fig_galaxy(sim):
    rng = np.random.default_rng(3)
    kinds = sim.node_kind
    dd = Fl.distance_to_flagged(sim.edges, sim.n_nodes, sim.flagged, directed=True)
    du = Fl.distance_to_flagged(sim.edges, sim.n_nodes, sim.flagged, directed=False)
    # sample of nodes to draw
    pick = []
    for k, n in [("flagged", 60), ("layering", 400), ("exchange", 20), ("p2p", 200), ("consolidation", 240)]:
        idx = np.where(kinds == k)[0]
        pick += list(rng.choice(idx, min(n, len(idx)), replace=False))
    pers = np.where(kinds == "personal")[0]
    linked = np.unique(sim.edges[np.isin(sim.edges[:, 1], np.where(kinds == "p2p")[0]), 0])
    pick += list(rng.choice(np.intersect1d(pers, linked), 150, replace=False))
    pick = np.array(pick)
    ring = np.where(np.isfinite(dd[pick]), np.minimum(dd[pick], 4), 5).astype(int)
    radius = {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0, 4: 3.8, 5: 4.5}
    sector = {"flagged": 0, "layering": 0.6, "consolidation": 2.0, "p2p": 3.3, "personal": 4.4, "exchange": 5.5}
    pos = {}
    for node, rg in zip(pick, ring):
        k = kinds[node]
        th = sector[k] + rng.uniform(-0.45, 0.45)
        rr = radius[rg] + rng.uniform(-0.18, 0.18)
        if rg == 0:
            rr = rng.uniform(0, 0.45)
            th = rng.uniform(0, 2 * np.pi)
        pos[node] = (rr * np.cos(th), rr * np.sin(th))
    fig, ax = plt.subplots(figsize=(W, 4.6))
    ax.set_aspect("equal")
    for r, lab in [(1, "1 hop"), (2, "2 hops"), (3, "3 hops")]:
        ax.add_patch(plt.Circle((0, 0), r, fill=False, ec=PALETTE["grid"], lw=0.8))
        ax.text(r * np.cos(2.65), r * np.sin(2.65), lab, fontsize=6, color=PALETTE["muted"], ha="center",
                va="center", bbox=dict(fc="white", ec="none", pad=0.5), zorder=10)
    ax.add_patch(plt.Circle((0, 0), 4.0, fill=False, ec=PALETTE["grid"], lw=0.8, ls=(0, (3, 3))))
    ax.text(4.0 * np.cos(2.65), 4.0 * np.sin(2.65), "4+ hops", fontsize=6, color=PALETTE["muted"],
            ha="center", va="center", bbox=dict(fc="white", ec="none", pad=0.5), zorder=10)
    ax.text(4.75 * np.cos(2.65), 4.75 * np.sin(2.65), "no forward path", fontsize=6, color=PALETTE["muted"],
            ha="center", va="center", bbox=dict(fc="white", ec="none", pad=0.5), zorder=10)
    ps = set(pick.tolist())
    for a, b in sim.edges:
        if a in ps and b in ps:
            (x0, y0), (x1, y1) = pos[a], pos[b]
            into_x = kinds[b] == "exchange"
            ax.plot([x0, x1], [y0, y1], lw=0.35 if not into_x else 0.5,
                    color=PALETTE["eth"] if into_x else PALETTE["faint"], alpha=0.25 if not into_x else 0.45, zorder=1)
    colors = {"flagged": PALETTE["ink"], "layering": "#6b7280", "consolidation": PALETTE["illicit"],
              "p2p": PALETTE["neighbour"], "personal": PALETTE["remit"], "exchange": PALETTE["eth"]}
    sizes = {"flagged": 10, "layering": 5, "consolidation": 7, "p2p": 8, "personal": 4, "exchange": 38}
    labels = {"flagged": "Flagged (sanctioned or frozen)", "layering": "Layering wallets",
              "consolidation": "Mule consolidation wallets", "p2p": "P2P merchants (neighbouring countries)",
              "personal": "Remitters' wallets", "exchange": "Exchange hot wallets"}
    for k in ["layering", "personal", "p2p", "consolidation", "flagged", "exchange"]:
        sel = [n for n in pick if kinds[n] == k]
        xy = np.array([pos[n] for n in sel])
        ax.scatter(xy[:, 0], xy[:, 1], s=sizes[k], color=colors[k], edgecolor="white", linewidth=0.3,
                   zorder=3 if k != "exchange" else 4, label=labels[k])
    ex = np.where(kinds == "exchange")[0]
    FACTS.update(galaxy_exchange_undirected_mean=float(np.mean(du[ex])),
                 galaxy_exchange_directed_reachable=float(np.mean(np.isfinite(dd[ex]))))
    ax.annotate("Exchange hubs: two hops from a flagged\naddress if direction is ignored; four or\nmore, or none, if funds are followed forward",
                xy=pos[ex[0]], xytext=(4.7, -3.7), fontsize=6.6, color=PALETTE["eth"], ha="left",
                arrowprops=dict(arrowstyle="-", lw=0.6, color=PALETTE["eth"]))
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=6.4, markerscale=1.3, handletextpad=0.3,
              labelspacing=0.7)
    ax.set_xlim(-5.0, 5.0)
    ax.set_ylim(-5.0, 5.0)
    ax.axis("off")
    style.headline(fig, "Direction matters: hop counts that ignore the flow of funds flag the wrong hubs",
                   "Nodes are placed on rings by their forward (directed) distance to the nearest flagged address. "
                   "Blue lines: payments into exchange hot wallets, which make every exchange look two hops from a "
                   "flagged address on the undirected graph.")
    style.source(fig, simulated=True, text="One simulated exchange-year with 2% mule accounts; a random sample of 1,070 "
                                           "nodes and the payments among them. Source: author's simulation.")
    style.save(fig, "fig_galaxy")


# ---------------------------------------------------------------------------
# 4. Synthetic control with placebo spaghetti
# ---------------------------------------------------------------------------

def fig_synth():
    Y = country_panel(n_donors=19, effect=-0.15, seed=21)
    r = C.synthetic_control(Y, treated=0, t0=104)
    donors = np.arange(1, Y.shape[0])
    synth = Y[donors].T @ r.weights
    FACTS.update(synth_att=r.att, synth_p=r.p_value, synth_ratio=r.ratio,
                 synth_n_donors_used=int((r.weights > 0.01).sum()))
    t = np.arange(Y.shape[1]) - 104
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 2.6), gridspec_kw=dict(wspace=0.28))
    a1.plot(t, synth, color=PALETTE["ink"], lw=1.1, ls=(0, (3, 2)), label="synthetic 'Thailand'")
    a1.plot(t, Y[0], color=PALETTE["thai"], lw=1.4, label="'Thailand'")
    a1.axvline(0, color=PALETTE["muted"], lw=0.7)
    a1.set_title("(a) Treated unit and its synthetic twin", loc="left", fontsize=7.6, fontweight="bold", pad=4)
    a1.set_xlabel("weeks from policy shock", fontsize=6.6, color=PALETTE["muted"])
    a1.set_ylabel("log flow index")
    a1.legend(loc="upper left", fontsize=6.4)
    for g in r.placebo_gaps:
        a2.plot(t, g, color=PALETTE["peer"], lw=0.6, alpha=0.6)
    a2.plot(t, r.gap, color=PALETTE["thai"], lw=1.5)
    a2.axhline(0, color=PALETTE["faint"], lw=0.7)
    a2.axvline(0, color=PALETTE["muted"], lw=0.7)
    a2.set_title("(b) Gap versus 19 placebo units", loc="left", fontsize=7.6, fontweight="bold", pad=4)
    a2.set_xlabel("weeks from policy shock", fontsize=6.6, color=PALETTE["muted"])
    a2.text(0.03, 0.05, f"estimated effect {r.att:+.3f} (true -0.150)\nrank-based p = {r.p_value:.2f}",
            transform=a2.transAxes, fontsize=6.6, color=PALETTE["thai"], va="bottom", linespacing=1.3,
            bbox=dict(fc="white", ec=PALETTE["grid"], lw=0.6, pad=3, alpha=0.95), zorder=10)
    style.headline(fig, "Synthetic control recovers a planted 0.15 log-point drop and ranks it first among placebos",
                   "A weekly flow index for a treated country and 19 donors driven by two persistent common factors.")
    style.source(fig, simulated=True, text="Weights are convex and fitted on 104 pre-shock weeks; inference ranks the post/pre RMSPE ratio "
                      "against in-space placebos (Abadie, Diamond and Hainmueller, 2010).")
    style.save(fig, "fig_synth")


# ---------------------------------------------------------------------------
# 5. Monte Carlo summary
# ---------------------------------------------------------------------------
DETECTORS = [("undirected_2hop", "Undirected 2-hop exposure"),
             ("dwell_only", "Dwell time only"),
             ("directed_3hop", "Directed 3-hop exposure"),
             ("composite_behaviour", "Red-flag composite, behaviour"),
             ("composite_all", "Red-flag composite, all"),
             ("iforest_behaviour", "Isolation forest, behaviour"),
             ("iforest_all", "Isolation forest, all")]


def fig_power():
    L = pd.read_csv(DATA_PROCESSED / "mc_ledger.csv")
    S = pd.read_csv(DATA_PROCESSED / "mc_scm.csv")
    g = L[L["share"] > 0].groupby("share")
    shares = sorted(L.loc[L["share"] > 0, "share"].unique())
    M = np.array([[g[f"p@k_{k}"].mean().loc[s] for s in shares] for k, _ in DETECTORS])
    Aauc = np.array([[g[f"auc_{k}"].mean().loc[s] for s in shares] for k, _ in DETECTORS])
    pw = L.groupby("share")["reject_bunch"].mean()
    nreps = L.groupby("share").size()
    sp = S.groupby("effect")["reject"].mean()
    FACTS.update(mc_reps_per_share=int(nreps.iloc[-1]), mc_reps_null=int(nreps.loc[0.0]),
                 bunch_size=float(pw.loc[0.0]), bunch_power={str(k): float(v) for k, v in pw.items()},
                 scm_power={str(k): float(v) for k, v in sp.items()},
                 pak={k: {str(s): float(M[i, j]) for j, s in enumerate(shares)} for i, (k, _) in enumerate(DETECTORS)},
                 auc={k: {str(s): float(Aauc[i, j]) for j, s in enumerate(shares)} for i, (k, _) in enumerate(DETECTORS)})
    fig = plt.figure(figsize=(W, 3.3))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.55, 1], hspace=0.9, wspace=0.5)
    ax = fig.add_subplot(gs[:, 0])
    cmap = LinearSegmentedColormap.from_list("p", ["#f7f7f8", "#f3c4c9", PALETTE["illicit"]])
    ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=6.4,
                    color="white" if M[i, j] > 0.7 else PALETTE["ink"])
    ax.set_xticks(range(len(shares)))
    ax.set_xticklabels([f"{100 * s:g}%" for s in shares])
    ax.set_yticks(range(len(DETECTORS)))
    ax.set_yticklabels([d[1] for d in DETECTORS], fontsize=6.6)
    ax.set_xlabel("share of accounts that are mules", fontsize=6.6, color=PALETTE["muted"])
    ax.grid(False)
    for sp_ in ax.spines.values():
        sp_.set_visible(False)
    ax.set_title("(a) Precision among the top-k flagged accounts\n(k = number of mules)", loc="left",
                 fontsize=7.6, fontweight="bold", pad=5)
    b1 = fig.add_subplot(gs[0, 1])
    b1.plot([100 * s for s in pw.index], pw.values, color=PALETTE["illicit"], marker="o", ms=3, lw=1.3)
    b1.axhline(0.05, color=PALETTE["faint"], lw=0.7, ls=(0, (3, 3)))
    b1.set_xscale("symlog", linthresh=0.25)
    b1.set_xticks([0, 0.25, 0.5, 1, 2, 4])
    b1.set_xticklabels(["0", ".25", ".5", "1", "2", "4"])
    b1.set_ylim(0, 1.05)
    b1.set_title("(b) Bunching-difference test:\nrejection rate", loc="left", fontsize=7.2, fontweight="bold", pad=4)
    b1.set_xlabel("mule share, %", fontsize=6.4, color=PALETTE["muted"])
    b2 = fig.add_subplot(gs[1, 1])
    b2.plot(100 * sp.index, sp.values, color=PALETTE["thai"], marker="o", ms=3, lw=1.3)
    b2.axhline(0.05, color=PALETTE["faint"], lw=0.7, ls=(0, (3, 3)))
    b2.set_ylim(0, 1.05)
    b2.set_title("(c) Synthetic control: rejection rate", loc="left", fontsize=7.2, fontweight="bold", pad=4)
    b2.set_xlabel("true effect, log points x 100", fontsize=6.4, color=PALETTE["muted"])
    style.headline(fig, "Single heuristics fail at low prevalence; layered evidence holds up",
                   f"Monte Carlo over {int(nreps.iloc[-1])} simulated exchange-years per mule share "
                   f"({int(nreps.loc[0.0])} under the null) and 200 country panels per effect size. "
                   "Dashed lines mark the 5% nominal level.")
    style.source(fig, simulated=True, text="Absolute levels depend on simulator parameters; the ranking of methods and their failure modes are "
                      "the transferable result. Source: author's simulations.")
    style.save(fig, "fig_power")

    # LaTeX table
    lines = [r"\begin{tabular}{l" + "c" * len(shares) + "}", r"\toprule",
             r" & \multicolumn{" + str(len(shares)) + r"}{c}{Share of accounts that are mules} \\",
             r"\cmidrule(lr){2-" + str(len(shares) + 1) + "}",
             "Detector & " + " & ".join(f"{100 * s:g}\\%" for s in shares) + r" \\", r"\midrule",
             r"\multicolumn{" + str(len(shares) + 1) + r"}{l}{\emph{Panel A. Area under the ROC curve}} \\"]
    for i, (_, lab) in enumerate(DETECTORS):
        lines.append(lab + " & " + " & ".join(f"{v:.3f}" for v in Aauc[i]) + r" \\")
    lines += [r"\addlinespace", r"\multicolumn{" + str(len(shares) + 1) + r"}{l}{\emph{Panel B. Precision at $k$}} \\"]
    for i, (_, lab) in enumerate(DETECTORS):
        lines.append(lab + " & " + " & ".join(f"{v:.2f}" for v in M[i]) + r" \\")
    lines += [r"\addlinespace", r"\multicolumn{" + str(len(shares) + 1) + r"}{l}{\emph{Panel C. Bunching-difference test}} \\"]
    lines.append(r"Rejection rate at 5\% & " + " & ".join(f"{pw.loc[s]:.2f}" for s in shares) + r" \\")
    dmean = L.groupby("share")["delta_b"].mean()
    lines.append(r"Mean $\hat\beta_{\mathrm{USDT}}-\hat\beta_{\mathrm{other}}$ & " +
                 " & ".join(f"{dmean.loc[s]:.3f}" for s in shares) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "tab_mc.tex").write_text("\n".join(lines))
    lines = [r"\begin{tabular}{l" + "c" * len(sp) + "}", r"\toprule",
             "True effect (log points $\\times$ 100) & " + " & ".join(f"{100 * e:g}" for e in sp.index) + r" \\", r"\midrule",
             "Rejection rate ($p \\le 0.05$) & " + " & ".join(f"{v:.3f}" for v in sp.values) + r" \\",
             "Mean estimated effect & " + " & ".join(f"{v:+.3f}" for v in S.groupby('effect')['att'].mean().values) + r" \\",
             r"\bottomrule", r"\end{tabular}"]
    (TABLES / "tab_scm.tex").write_text("\n".join(lines))


if __name__ == "__main__":
    sim = simulate_ledger(SHOWCASE)
    fig_bunching(sim)
    fig_dwell_roc(sim)
    fig_galaxy(sim)
    fig_synth()
    fig_power()
    (DATA_PROCESSED / "facts_sim.json").write_text(json.dumps(FACTS, indent=2, default=str))
    print(json.dumps({k: v for k, v in FACTS.items() if k not in ("pak", "auc")}, indent=1, default=str))
