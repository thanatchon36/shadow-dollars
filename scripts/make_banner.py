"""README banner -> docs/assets/banner.png: USDT supply on Tron and Ethereum, 2018 to the data vintage.

Real data (Coin Metrics Community Data, data/raw/cm_usdt_*.csv), drawn as two rails on a dark ground.
Usage: python scripts/make_banner.py
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from shadowdollars.collectors import public as P  # noqa: E402
from shadowdollars.config import PALETTE, ROOT  # noqa: E402

BG = "#0b1020"
OUT = ROOT / "docs" / "assets" / "banner.png"


def main() -> None:
    supply = {name: P.coinmetrics(asset)["SplyCur"].loc["2018-01-01":] / 1e9
              for asset, name in (("usdt_eth", "Ethereum"), ("usdt_trx", "Tron"))}
    eth, tron = supply["Ethereum"], supply["Tron"].reindex(supply["Ethereum"].index).fillna(0)
    eth, tron = eth.rolling(7, min_periods=1).mean(), tron.rolling(7, min_periods=1).mean()

    fig = plt.figure(figsize=(16.8, 6.24), dpi=100, facecolor=BG)
    ax = fig.add_axes((0.0, 0.0, 1.0, 0.86), facecolor=BG)
    x = eth.index
    ax.fill_between(x, 0, eth, color=PALETTE["eth"], alpha=0.55, lw=0)
    ax.fill_between(x, eth, eth + tron, color=PALETTE["tron"], alpha=0.85, lw=0)
    for lw, a in ((9, 0.06), (5, 0.12), (2.2, 0.9)):  # glow on the Tron rail
        ax.plot(x, eth + tron, color="#ffb08a", lw=lw, alpha=a, solid_capstyle="round")
    ax.set_xlim(x[0], x[-1])
    ax.set_ylim(0, (eth + tron).max() * 1.02)
    ax.axis("off")

    fig.text(0.035, 0.80, "shadow-dollars", color="#f4f1ea", fontsize=54, fontweight="bold",
             family="DejaVu Sans", va="top")
    fig.text(0.037, 0.655, "Stablecoin rails, scam finance and the limits of detection in Thailand",
             color="#c9cedb", fontsize=21, va="top")
    pieces = [("USDT supply on ", "#8f98ad", "normal"), ("Ethereum", "#8fb0db", "bold"),
              (" and ", "#8f98ad", "normal"), ("Tron", "#ff9a73", "bold"),
              (f"  \u00b7  2018 to {x[-1]:%B %Y}", "#8f98ad", "normal")]
    renderer = fig.canvas.get_renderer()
    left = 0.037
    for text, color, weight in pieces:  # one line in several colours: place each piece after the last
        t = fig.text(left, 0.565, text, color=color, fontsize=15, fontweight=weight, va="top")
        left += t.get_window_extent(renderer).width / fig.bbox.width
    fig.text(0.99, 0.02, "Data: Coin Metrics Community Data", color="#c9cedb", alpha=0.75, fontsize=11,
             ha="right", va="bottom")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=BG)
    print("banner ->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
