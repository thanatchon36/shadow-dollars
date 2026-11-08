"""Figures and tables built from real public data (Section 5 of the paper)."""
from __future__ import annotations

import json
import warnings

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from shadowdollars import style
from shadowdollars.collectors import public as P
from shadowdollars.config import (DATA_PROCESSED, EVENT_STUDY_DATES, EVENTS, LANE_COLORS,
                                  PALETTE, TABLES)
from shadowdollars.detectors import causal as C

warnings.filterwarnings("ignore")
style.apply()
W = style.TEXT_WIDTH_IN
FACTS: dict = {}


def roll(s, w=30):
    return s.rolling(w, min_periods=w // 2).median()


# ---------------------------------------------------------------------------
# 1. USDT supply by chain
# ---------------------------------------------------------------------------

def fig_supply():
    chains = [("usdt_eth", "Ethereum", PALETTE["eth"]),
              ("usdt_trx", "Tron", PALETTE["tron"]),
              ("usdt_avaxc", "Avalanche", PALETTE["avax"]),
              ("usdt_omni", "Omni", PALETTE["omni"])]
    sp = pd.concat({lab: P.coinmetrics(a)["SplyCur"] for a, lab, _ in chains}, axis=1, sort=True)
    sp = sp.loc["2018-01-01":].fillna(0) / 1e9
    share = sp["Tron"] / sp.sum(axis=1)
    last = sp.index[-1]
    FACTS.update(supply_last_date=str(last.date()), tron_supply_bn=float(sp["Tron"].iloc[-1]),
                 eth_supply_bn=float(sp["Ethereum"].iloc[-1]),
                 tron_share_last=float(share.iloc[-1]),
                 tron_share_2019=float(share.asof(pd.Timestamp("2019-12-31"))),
                 tron_share_2023=float(share.asof(pd.Timestamp("2023-12-31"))),
                 covered_supply_bn=float(sp.sum(axis=1).iloc[-1]),
                 usdt_aggregate_bn=float(P.coinmetrics("usdt")["SplyCur"].dropna().iloc[-1] / 1e9))

    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(W, 3.9), sharex=True,
                                  gridspec_kw=dict(height_ratios=[2.6, 1], hspace=0.12))
    order = ["Omni", "Avalanche", "Tron", "Ethereum"]
    cols = {lab: c for _, lab, c in chains}
    ax.stackplot(sp.index, [sp[o] for o in order], colors=[cols[o] for o in order],
                 alpha=0.92, linewidth=0)
    cum = sp[order].cumsum(axis=1).iloc[-1]
    prev = 0
    for o in order:
        mid = (prev + cum[o]) / 2
        if sp[o].iloc[-1] > 5:
            style.end_label(ax, last, mid, f"{o}  ${sp[o].iloc[-1]:.0f}bn", cols[o])
        prev = cum[o]
    ax.set_ylabel("US$ billions")
    ax.set_ylim(0, None)
    ax.margins(x=0)

    ax2.plot(share.index, 100 * share, color=PALETTE["tron"], lw=1.4)
    ax2.hlines(50, share.index[0], share.index[-1], color=PALETTE["faint"], lw=0.7, ls=(0, (3, 3)))
    ax2.text(sp.index[40], 52, "50%", color=PALETTE["muted"], fontsize=6.5, va="bottom")
    ax2.set_ylim(0, 70)
    ax2.set_ylabel("Tron share, %")
    style.end_label(ax2, last, 100 * share.iloc[-1], f"{100 * share.iloc[-1]:.0f}%", PALETTE["tron"])
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    style.headline(fig, "Tron now carries close to half of all USDT",
                   f"USDT supply by blockchain, US$ bn (top); Tron's share of the covered supply (bottom). Daily, Jan 2018 to {last:%b %Y}.",
                   y=0.9)
    style.source(fig, "Source: Coin Metrics Community Data (usdt_eth, usdt_trx, usdt_avaxc, usdt_omni). "
                      "Chains absent from the community files (e.g. TON, Solana, BNB Chain) are excluded.", y=0.02)
    style.save(fig, "fig_rails_supply")


# ---------------------------------------------------------------------------
# 2. Two rails, two clienteles
# ---------------------------------------------------------------------------

def fig_two_rails():
    series = [("usdt_trx", "USDT · Tron", PALETTE["tron"]),
              ("usdt_eth", "USDT · Ethereum", PALETTE["eth"]),
              ("usdc_eth", "USDC · Ethereum", PALETTE["usdc_eth"])]
    data = {lab: P.coinmetrics(a).loc["2020-01-01":] for a, lab, _ in series}
    fig, axes = plt.subplots(1, 3, figsize=(W, 2.55), gridspec_kw=dict(wspace=0.42))
    titles = ["Addresses holding a balance\nmillions",
              "Mean balance per holding address\nUS$, log scale",
              "Transfers per US$1m of supply\nper day, log scale"]
    stats = {}
    for lab, col in [(s[1], s[2]) for s in series]:
        d = data[lab]
        holders = d["AdrBalCnt"] / 1e6
        bal = roll(d["SplyCur"] / d["AdrBalCnt"])
        inten = roll(d["TxTfrCnt"] / d["SplyCur"] * 1e6)
        for ax, y in zip(axes, [holders, bal, inten]):
            ax.plot(y.index, y, color=col, lw=1.4)
        stats[lab] = dict(holders_m=float(holders.dropna().iloc[-1]), mean_bal=float(bal.dropna().iloc[-1]),
                          tfr_per_m=float(inten.dropna().iloc[-1]),
                          tfr_per_m_med_2024_26=float((d["TxTfrCnt"] / d["SplyCur"] * 1e6).loc["2024-01-01":].median()))
    axes[1].set_yscale("log")
    axes[2].set_yscale("log")
    for ax, t in zip(axes, titles):
        ax.set_title(t, loc="left", fontsize=7.5, color=PALETTE["ink"], fontweight="bold", pad=6, linespacing=1.3)
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[1].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    axes[2].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    # direct labels on the first panel (stacked key in the empty upper-left corner)
    last = data["USDT · Tron"].index[-1]
    for k, (lab, col) in enumerate([(s_[1], s_[2]) for s_ in series]):
        axes[0].text(0.04, 0.95 - 0.09 * k, lab, transform=axes[0].transAxes, fontsize=6.6,
                     color=col, fontweight="bold", va="top")
    FACTS["two_rails"] = stats
    ratio_bal = stats["USDT · Ethereum"]["mean_bal"] / stats["USDT · Tron"]["mean_bal"]
    ratio_tfr = stats["USDT · Tron"]["tfr_per_m_med_2024_26"] / stats["USDT · Ethereum"]["tfr_per_m_med_2024_26"]
    FACTS.update(ratio_mean_balance_eth_over_tron=float(ratio_bal), ratio_intensity_tron_over_eth=float(ratio_tfr))
    style.headline(fig, "On Tron, USDT behaves like a retail payment rail",
                   f"More holders, smaller balances, {ratio_tfr:.0f}x the transfer intensity of USDT on Ethereum. 30-day rolling medians, 2020 to {last:%b %Y}.",
                   y=0.93)
    style.source(fig, "Source: Coin Metrics Community Data (AdrBalCnt, SplyCur, TxTfrCnt). Author's calculations.", y=-0.04)
    style.save(fig, "fig_two_rails")


# ---------------------------------------------------------------------------
# 3. Circle leaves Tron
# ---------------------------------------------------------------------------

def fig_usdc_exit():
    u = P.coinmetrics("usdc_trx")["SplyCur"].loc["2021-01-01":] / 1e6
    u = u[u.index >= u[u > 5].index.min()]
    t = P.coinmetrics("usdt_trx")["SplyCur"].loc["2021-01-01":] / 1e6
    peak_d, peak_v = u.idxmax(), u.max()
    FACTS.update(usdc_trx_peak_date=str(peak_d.date()), usdc_trx_peak_m=float(peak_v),
                 usdc_trx_last_m=float(u.dropna().iloc[-1]))
    fig, ax = plt.subplots(figsize=(W, 2.3))
    ax.plot(t.index, t, color=PALETTE["tron"], lw=1.5)
    ax.plot(u.index, u, color=PALETTE["usdc_trx"], lw=1.5)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:,.0f}bn" if v >= 1000 else f"${v:,.0f}m"))
    ax.axvspan(pd.Timestamp("2024-02-01"), pd.Timestamp("2025-02-28"), color=PALETTE["grid"], alpha=0.7, lw=0)
    ax.set_ylim(5, 4e5)
    ax.text(pd.Timestamp("2024-02-20"), 6e3, "Circle winds down\nUSDC on Tron\n(approx. Feb 2024 to Feb 2025)",
            fontsize=6.5, color=PALETTE["muted"], va="center", linespacing=1.25)
    style.end_label(ax, t.index[-1], t.iloc[-1], "USDT on Tron", PALETTE["tron"])
    style.end_label(ax, u.dropna().index[-1], u.dropna().iloc[-1], "USDC on Tron", PALETTE["usdc_trx"])
    ax.scatter([peak_d], [peak_v], s=10, color=PALETTE["usdc_trx"], zorder=4)
    ax.annotate(f"peak ${peak_v/1000:.1f}bn, {peak_d:%b %Y}", xy=(peak_d, peak_v), xytext=(0, 6),
                textcoords="offset points", fontsize=6.5, color=PALETTE["ink"], va="bottom", ha="center")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.margins(x=0)
    style.headline(fig, "When Circle left Tron, USDT kept the cheapest rail to itself",
                   "Token supply on the Tron blockchain, US$, log scale, 2021 to 2026.", y=0.9)
    style.source(fig, "Source: Coin Metrics Community Data (usdc_trx, usdt_trx). Wind-down dates approximate.", y=0.0)
    style.save(fig, "fig_usdc_exit")


# ---------------------------------------------------------------------------
# 4. Macro motives
# ---------------------------------------------------------------------------
MEKONG = {"Cambodia", "Myanmar", "Lao PDR"}
COUNTRIES = ["Thailand", "Viet Nam", "Philippines", "Indonesia", "Malaysia", "Cambodia", "Myanmar",
             "Lao PDR", "China", "Korea, Rep.", "Japan", "Singapore", "India", "Pakistan", "Turkiye",
             "Argentina", "Nigeria", "Brazil", "Russian Federation", "Ukraine", "United States",
             "Euro area", "Egypt, Arab Rep.", "Ghana"]
SHORT = {"Korea, Rep.": "Korea", "Russian Federation": "Russia", "Egypt, Arab Rep.": "Egypt",
         "Viet Nam": "Vietnam", "Lao PDR": "Laos", "United States": "United States"}


def fig_macro():
    cpi = P.cpi_inflation()
    c = cpi[cpi["Country"].isin(COUNTRIES) & cpi["Year"].between(2019, 2024)]
    agg = c.groupby("Country")["Inflation"].agg(["mean", "min", "max", "count"]).sort_values("mean")
    agg.to_csv(DATA_PROCESSED / "cpi_2019_2024.csv")
    fx = P.fx_daily().loc["2021-01-01":]
    fx = fx.drop(columns=["Venezuela"], errors="ignore")
    ret = np.log(fx).diff()
    vol = (ret.std() * np.sqrt(252) * 100).sort_values()
    vol.to_csv(DATA_PROCESSED / "fx_vol_2021_2026.csv")
    FACTS.update(cpi_thailand_mean=float(agg.loc["Thailand", "mean"]),
                 cpi_rank_thailand=int(list(agg.index).index("Thailand") + 1), cpi_n=len(agg),
                 fx_vol_thailand=float(vol["Thailand"]),
                 fx_vol_rank_thailand=int(list(vol.index).index("Thailand") + 1), fx_n=len(vol),
                 fx_last_date=str(fx.dropna(how="all").index[-1].date()),
                 cpi_mekong={k: float(agg.loc[k, "mean"]) for k in MEKONG if k in agg.index})

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 3.9), gridspec_kw=dict(width_ratios=[1.25, 1], wspace=0.55))
    y = np.arange(len(agg))
    for i, (name, r) in enumerate(agg.iterrows()):
        col = PALETTE["thai"] if name == "Thailand" else (PALETTE["neighbour"] if name in MEKONG else PALETTE["peer"])
        a1.plot([r["min"], r["max"]], [i, i], color=col, lw=1.2, alpha=0.55, solid_capstyle="butt")
        sparse = r["count"] < 3
        a1.scatter(r["mean"], i, s=26 if name == "Thailand" else 16, zorder=3,
                   color="white" if sparse else col, edgecolor=col, linewidth=1.0 if sparse else 0.5)
    a1.set_xscale("symlog", linthresh=5)
    a1.set_xlim(-3, 90)
    a1.set_xticks([-2, 0, 2, 5, 10, 20, 50])
    a1.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    a1.set_yticks(y)
    a1.set_yticklabels([SHORT.get(n, n) + (" \u2020" if agg.loc[n, "count"] < 3 else "")
                        for n in agg.index], fontsize=6.6)
    for lbl in a1.get_yticklabels():
        n = lbl.get_text()
        if n == "Thailand":
            lbl.set_color(PALETTE["thai"]); lbl.set_fontweight("bold")
        elif n.rstrip(" \u2020") in {"Cambodia", "Myanmar", "Laos"}:
            lbl.set_color(PALETTE["neighbour"]); lbl.set_fontweight("bold")
    a1.grid(axis="x", color=PALETTE["grid"]); a1.grid(axis="y", visible=False)
    a1.set_title("(a) CPI inflation, % per year\nmean 2019-2024 (dot) and range (bar)", loc="left",
                 fontsize=7.5, fontweight="bold", pad=6)
    a1.set_xlabel("symmetric log scale", fontsize=6.5, color=PALETTE["muted"])

    y2 = np.arange(len(vol))
    cols = [PALETTE["thai"] if n == "Thailand" else PALETTE["peer"] for n in vol.index]
    a2.barh(y2, vol.values, color=cols, height=0.65)
    a2.set_yticks(y2)
    a2.set_yticklabels(vol.index, fontsize=6.6)
    for lbl in a2.get_yticklabels():
        if lbl.get_text() == "Thailand":
            lbl.set_color(PALETTE["thai"]); lbl.set_fontweight("bold")
    for i, v in enumerate(vol.values):
        a2.text(v + 0.2, i, f"{v:.1f}", va="center", fontsize=6, color=PALETTE["muted"])
    a2.grid(axis="x", color=PALETTE["grid"]); a2.grid(axis="y", visible=False)
    a2.set_title("(b) Volatility against the US dollar\n% annualised, Jan 2021 to Oct 2026", loc="left",
                 fontsize=7.5, fontweight="bold", pad=6)
    style.headline(fig, "Thailand has little macroeconomic reason to hold dollars on-chain",
                   "Low inflation and a mid-volatility currency, next to neighbours with strong legitimate demand for dollars.",
                   y=0.93)
    style.source(fig, "Sources: World Bank FP.CPI.TOTL.ZG (via datasets/inflation, file labels corrected); "
                      "Federal Reserve H.10 noon rates (via datasets/exchange-rates). \u2020 Hollow marker: fewer than "
                      "three annual observations (Myanmar: 2019 only). Argentina and Venezuela are not reported in "
                      "this World Bank series. Author's calculations.", y=0.0)
    style.save(fig, "fig_macro")


# ---------------------------------------------------------------------------
# 5. Timeline of shocks (editorial leader-line layout)
# ---------------------------------------------------------------------------

def fig_timeline():
    ev = sorted(EVENTS, key=lambda e: e.date)
    n = len(ev)
    fig, ax = plt.subplots(figsize=(W, 5.6))
    t0, t1 = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-01-01")
    span = (t1 - t0).days

    def ty(d):  # time runs downwards on the left axis, 0 at top
        return (pd.Timestamp(d) - t0).days / span

    x_axis, x_lab = 0.16, 0.36
    ax.plot([x_axis, x_axis], [0, 1], color=PALETTE["faint"], lw=0.8)
    for yr in range(2022, 2027):
        yy = ty(f"{yr}-01-01")
        ax.plot([x_axis - 0.012, x_axis], [yy, yy], color=PALETTE["faint"], lw=0.8)
        ax.text(x_axis - 0.02, yy, str(yr), ha="right", va="center", fontsize=7.5, color=PALETTE["muted"],
                fontweight="bold")
    # 2025 cluster band
    a, b = ty("2025-02-01"), ty("2025-10-31")
    ax.add_patch(plt.Rectangle((x_axis - 0.006, a), 0.012, b - a, color=PALETTE["thai"], alpha=0.12, lw=0))
    ax.text(x_axis - 0.02, (a + b) / 2, "9 shocks\nin 9 months", ha="right", va="center", fontsize=6.5,
            color=PALETTE["thai"], fontweight="bold", linespacing=1.2)
    label_y = np.linspace(0.02, 0.98, n)
    for i, e in enumerate(ev):
        yy = ty(e.date)
        col = LANE_COLORS[e.lane]
        ax.scatter([x_axis], [yy], s=22, color=col, zorder=3, edgecolor="white", linewidth=0.6)
        xm = x_lab - 0.06
        ax.plot([x_axis, xm, x_lab - 0.01], [yy, label_y[i], label_y[i]], color=col, lw=0.6, alpha=0.7)
        date_txt = pd.Timestamp(e.date).strftime("%d %b %Y" if e.precise else "%b %Y")
        ax.text(x_lab, label_y[i], date_txt, ha="left", va="center", fontsize=6.6, color=PALETTE["muted"])
        ax.text(x_lab + 0.13, label_y[i], e.label, ha="left", va="center", fontsize=7, color=PALETTE["ink"])
    ax.set_xlim(0, 1)
    ax.set_ylim(1.02, -0.02)
    ax.axis("off")
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, markersize=5) for c in LANE_COLORS.values()]
    ax.legend(handles, ["Thai policy and market", "Enforcement and reports", "Global stablecoin rules",
                        "Border security"], loc="lower left", bbox_to_anchor=(0.0, -0.06), ncol=4,
              fontsize=6.6, handletextpad=0.3, columnspacing=1.2)
    style.headline(fig, "Policy shocks overlap: 9 of 16 fall between February and October 2025",
                   "Events relevant to Thai stablecoin flows, 2022-2025. Left: true dates; right: events in order. "
                   "Month-level dates shown without a day.", y=0.95)
    style.source(fig, "Source: author's compilation from public announcements; dates to be verified against primary sources.", y=0.0)
    style.save(fig, "fig_timeline")


# ---------------------------------------------------------------------------
# 6. Aggregate event study with placebo calibration
# ---------------------------------------------------------------------------

def fig_event_study():
    s = P.coinmetrics("usdt_trx")["TxTfrCnt"]
    events = {k: C.event_study(s, d) for k, d in EVENT_STUDY_DATES.items()}
    # placebo dates: every 7 days, avoiding +/-45 days around the real events
    cand = pd.date_range("2022-06-01", "2025-12-31", freq="7D")
    real = [pd.Timestamp(d) for d in EVENT_STUDY_DATES.values()]
    cand = [d for d in cand if all(abs((d - r).days) > 45 for r in real)]
    plac = []
    for d in cand:
        r = C.event_study(s, str(d.date()), reps=400)
        if np.isfinite(r.car_30):
            plac.append((d, r.car_30, r.car_30_ci[0], r.car_30_ci[1]))
    pl = pd.DataFrame(plac, columns=["date", "car30", "lo", "hi"])
    pl["outside"] = (pl["car30"] < pl["lo"]) | (pl["car30"] > pl["hi"])
    pl.to_csv(DATA_PROCESSED / "event_placebos.csv", index=False)
    res = []
    for k, r in events.items():
        p_cal = float((1 + np.sum(np.abs(pl["car30"]) >= abs(r.car_30))) / (1 + len(pl)))
        res.append(dict(event=k, car30=r.car_30, lo=r.car_30_ci[0], hi=r.car_30_ci[1], p_calibrated=p_cal))
    res = pd.DataFrame(res)
    res.to_csv(DATA_PROCESSED / "event_study_results.csv", index=False)
    FACTS.update(placebo_n=len(pl), placebo_overreject=float(pl["outside"].mean()),
                 event_results=res.to_dict(orient="records"))

    fig = plt.figure(figsize=(W, 3.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.25, 1], hspace=0.75, wspace=0.32)
    for j, (k, r) in enumerate(events.items()):
        ax = fig.add_subplot(gs[0, j])
        post = r.rel_day >= 0
        ax.fill_between(r.rel_day[post], r.car_lo[post], r.car_hi[post], color=PALETTE["grid"], lw=0)
        ax.axhline(0, color=PALETTE["faint"], lw=0.7)
        ax.axvline(0, color=PALETTE["muted"], lw=0.7, ls=(0, (2, 2)))
        ax.plot(r.rel_day[~post], np.cumsum(r.abnormal[~post][::-1])[::-1] * 0, alpha=0)  # keep x-range
        ax.scatter(r.rel_day[~post], r.abnormal[~post], s=3, color=PALETTE["peer"])
        ax.plot(r.rel_day[post], r.car[post], color=PALETTE["thai"], lw=1.4)
        ax.set_title(k.replace(" (", "\n("), loc="left", fontsize=7, fontweight="bold", pad=4, linespacing=1.2)
        ax.set_xlabel("days from event", fontsize=6.5, color=PALETTE["muted"])
        if j == 0:
            ax.set_ylabel("cumulative abnormal\nlog transfers", fontsize=6.8)
        ax.set_xlim(-30, 60)
    ax = fig.add_subplot(gs[1, :])
    ax.hist(pl["car30"], bins=40, color=PALETTE["peer"], alpha=0.85)
    short = {"Border": "Border power cut", "Offshore": "Offshore block", "Prince": "Prince Group sanctions"}
    ymax = ax.get_ylim()[1]
    ax.set_ylim(0, ymax * 1.18)
    key = []
    for k, (_, r) in enumerate(res.sort_values("car30").iterrows()):
        tag = "ABC"[k]
        ax.axvline(r["car30"], ymax=1 / 1.18, color=PALETTE["thai"], lw=1.2)
        ax.text(r["car30"], ymax * 1.03, tag, ha="center", va="bottom", fontsize=6.8, fontweight="bold",
                color=PALETTE["thai"])
        key.append(f"{tag}  {short[r['event'].split(' ')[0]]}: p = {r['p_calibrated']:.2f}")
    ax.text(0.01, 0.97, "\n".join(key), transform=ax.transAxes, ha="left", va="top", fontsize=6.3,
            color=PALETTE["thai"], linespacing=1.35)
    ax.set_xlabel(f"30-day cumulative abnormal log transfers. Grey: {len(pl)} placebo dates; red: the three shocks; "
                  "p = share of placebos at least as extreme", fontsize=6.5, color=PALETTE["muted"])
    ax.set_ylabel("placebo dates", fontsize=6.8)
    style.headline(fig, "Chain-wide data cannot see a national crackdown",
                   f"Tron USDT transfer counts. Nominal 95% bands reject at {100 * pl['outside'].mean():.0f}% of random dates; "
                   "placebo-calibrated p-values are the honest test.", y=0.93)
    style.source(fig, "Source: Coin Metrics Community Data (usdt_trx TxTfrCnt). Counterfactual: log-linear trend with "
                      "day-of-week effects fitted on days -150 to -31; moving-block bootstrap bands.", y=0.0)
    style.save(fig, "fig_event_study")


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def tables():
    of = P.ofac_addresses()
    tab = of.pivot_table(index="ticker", columns="format", values="address", aggfunc="count", fill_value=0)
    tab["Total"] = tab.sum(axis=1)
    tab = tab.sort_values("Total", ascending=False)
    tab.to_csv(DATA_PROCESSED / "ofac_by_format.csv")
    stable = of[of["ticker"].isin(["USDT", "TRX", "USDC"])]
    FACTS.update(ofac_total=int(len(of)), ofac_tron_format=int((of["format"] == "Tron (T…)").sum()),
                 ofac_usdt=int((of["ticker"] == "USDT").sum()), ofac_trx=int((of["ticker"] == "TRX").sum()),
                 ofac_usdt_trx_tron_share=float((stable["format"] == "Tron (T…)").mean()))
    top = tab.head(8)
    lines = [r"\begin{tabular}{l" + "r" * len(top.columns) + "}", r"\toprule",
             "Listed under & " + " & ".join(c.replace("…", r"\ldots{}") for c in top.columns) + r" \\", r"\midrule"]
    for k, r in top.iterrows():
        lines.append(k + " & " + " & ".join(f"{int(v):,}" for v in r.values) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "tab_ofac.tex").write_text("\n".join(lines))

    rows = []
    for a, lab in [("usdt_trx", "USDT on Tron"), ("usdt_eth", "USDT on Ethereum"), ("usdc_eth", "USDC on Ethereum"),
                   ("usdc_trx", "USDC on Tron")]:
        d = P.coinmetrics(a)
        last = d.dropna(subset=["SplyCur"]).iloc[-1]
        prev = d["SplyCur"].asof(last.name - pd.Timedelta(days=365))
        h_prev = d["AdrBalCnt"].asof(last.name - pd.Timedelta(days=365))
        rows.append(dict(series=lab, supply=last.SplyCur / 1e9, supply_g=100 * (last.SplyCur / prev - 1),
                         holders=last.AdrBalCnt / 1e6, holders_g=100 * (last.AdrBalCnt / h_prev - 1),
                         active=last.AdrActCnt / 1e3, transfers=last.TxTfrCnt / 1e3,
                         mean_bal=last.SplyCur / last.AdrBalCnt))
    df = pd.DataFrame(rows)
    df.to_csv(DATA_PROCESSED / "onchain_snapshot.csv", index=False)
    lines = [r"\begin{tabular}{lrrrrrrr}", r"\toprule",
             r" & Supply & 1-yr & Holders & 1-yr & Active & Transfers & Mean \\",
             r" & US\$bn & \% & m & \% & k/day & k/day & balance US\$ \\", r"\midrule"]
    for r in rows:
        lines.append(f"{r['series']} & {r['supply']:,.2f} & {r['supply_g']:+.0f} & {r['holders']:,.2f} & "
                     f"{r['holders_g']:+.0f} & {r['active']:,.0f} & {r['transfers']:,.0f} & {r['mean_bal']:,.0f}" + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "tab_onchain.tex").write_text("\n".join(lines))
    FACTS["snapshot_date"] = str(P.coinmetrics("usdt_trx").dropna(subset=["SplyCur"]).index[-1].date())


if __name__ == "__main__":
    fig_supply()
    fig_two_rails()
    fig_usdc_exit()
    fig_macro()
    fig_timeline()
    tables()
    fig_event_study()
    (DATA_PROCESSED / "facts_real.json").write_text(json.dumps(FACTS, indent=2, default=str))
    print(json.dumps(FACTS, indent=1, default=str)[:3000])
