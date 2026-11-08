"""LinkedIn launch poster -> docs/assets/linkedin_poster.png (1440 x 1800, 4:5).

Every number is read from data/processed/facts_*.json and onchain_snapshot.csv; the chart is USDT supply on
Ethereum and Tron from Coin Metrics Community Data (real data). The page is laid out in HTML and rendered by
headless Chrome. Usage: python scripts/make_poster.py
"""
from __future__ import annotations

import base64
import io
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from shadowdollars.collectors import public as P  # noqa: E402
from shadowdollars.config import DATA_PROCESSED, PALETTE, ROOT  # noqa: E402

OUT = ROOT / "docs" / "assets" / "linkedin_poster.png"
W, H = 1440, 1800
CHROME = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome", "chromium"]
DOI = "10.5281/zenodo.24050717"


def chart_png() -> str:
    """Stacked USDT supply, Ethereum below and Tron glowing on top; transparent, no text."""
    eth = P.coinmetrics("usdt_eth")["SplyCur"].loc["2018-01-01":] / 1e9
    tron = P.coinmetrics("usdt_trx")["SplyCur"].reindex(eth.index).fillna(0) / 1e9
    eth, tron = eth.rolling(7, min_periods=1).mean(), tron.rolling(7, min_periods=1).mean()
    fig = plt.figure(figsize=(W / 100, 5.4), dpi=200)
    fig.patch.set_alpha(0)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.patch.set_alpha(0)
    x = eth.index
    ax.fill_between(x, 0, eth, color=PALETTE["eth"], alpha=0.75, lw=0)
    ax.fill_between(x, eth, eth + tron, color=PALETTE["tron"], alpha=0.9, lw=0)
    for lw, a in ((14, 0.05), (7, 0.12), (2.6, 0.95)):
        ax.plot(x, eth + tron, color="#ffb08a", lw=lw, alpha=a, solid_capstyle="round")
    ax.plot(x, eth, color="#9db8e0", lw=1.2, alpha=0.6)
    ax.set_xlim(x[0], x[-1])
    ax.set_ylim(0, (eth + tron).max() * 1.08)
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def facts() -> dict:
    r = json.loads((DATA_PROCESSED / "facts_real.json").read_text())
    s = json.loads((DATA_PROCESSED / "facts_sim.json").read_text())
    snap = pd.read_csv(DATA_PROCESSED / "onchain_snapshot.csv").set_index("series")
    tr, et = r["two_rails"]["USDT · Tron"], r["two_rails"]["USDT · Ethereum"]
    ev = [e["p_calibrated"] for e in r["event_results"]]
    und = list(s["pak"]["undirected_2hop"].values())
    best = [max(s["pak"][k][m] for k in ("iforest_all", "iforest_behaviour")) for m in s["pak"]["iforest_all"]]
    return dict(
        sanc=round(100 * r["ofac_usdt_trx_tron_share"]),
        tron_bn=r["tron_supply_bn"], eth_bn=r["eth_supply_bn"], share=round(100 * r["tron_share_last"]),
        holders_t=tr["holders_m"], holders_e=et["holders_m"],
        bal_t=round(snap.loc["USDT on Tron", "mean_bal"], -2), bal_e=round(snap.loc["USDT on Ethereum", "mean_bal"], -2),
        tpm_t=tr["tfr_per_m_med_2024_26"], tpm_e=et["tfr_per_m_med_2024_26"],
        intensity=r["ratio_intensity_tron_over_eth"],
        placebo=round(100 * r["placebo_overreject"]), placebo_n=r["placebo_n"], pmin=min(ev), pmax=max(ev),
        und_lo=round(100 * min(und)), und_hi=round(100 * max(und)),
        best_lo=round(100 * min(best)), best_hi=round(100 * max(best)),
        power=round(100 * s["bunch_power"]["0.02"]), last=r["supply_last_date"],
    )


def bar(label: str, t: float, e: float, t_txt: str, e_txt: str, note: str) -> str:
    m = max(t, e)
    return f"""
    <div class="cmp">
      <div class="cmp-h"><span>{label}</span><em>{note}</em></div>
      <div class="row"><i class="b tron" style="width:{100 * t / m:.1f}%"></i><b class="tron-t">{t_txt}</b></div>
      <div class="row"><i class="b eth" style="width:{100 * e / m:.1f}%"></i><b class="eth-t">{e_txt}</b></div>
    </div>"""


def page(f: dict, chart: str) -> str:
    bars = (
        bar("Funded addresses", f["holders_t"], f["holders_e"], f"{f['holders_t']:.1f} M", f"{f['holders_e']:.1f} M",
            f"{f['holders_t'] / f['holders_e']:.1f}×")
        + bar("Transfers per US$1 M a day", f["tpm_t"], f["tpm_e"], f"{f['tpm_t']:.0f}", f"{f['tpm_e']:.1f}",
              f"{f['intensity']:.1f}×")
        + bar("Mean balance", f["bal_t"], f["bal_e"], f"US${f['bal_t']:,.0f}", f"US${f['bal_e']:,.0f}",
              f"{f['bal_e'] / f['bal_t']:.0f}× smaller")
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: {W}px; height: {H}px; }}
body {{ background: radial-gradient(1100px 700px at 85% 55%, #141c33 0%, #070a14 55%, #04060c 100%);
  color: #f4f1ea; font-family: -apple-system, "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
  position: relative; overflow: hidden; -webkit-font-smoothing: antialiased; }}
.abs {{ position: absolute; }}
.brand {{ left: 94px; top: 62px; font-weight: 800; letter-spacing: .06em; color: #ff7a4d; font-size: 28px; }}
.tag {{ left: 400px; top: 66px; color: #9aa3b8; font-size: 25px; }}
.hero {{ left: 86px; top: 112px; font-size: 250px; font-weight: 800; color: #ff7a4d; letter-spacing: -.04em;
  line-height: 1; }}
.hero sup {{ font-size: 120px; vertical-align: 0; margin-left: 6px; }}
.lede {{ left: 100px; top: 382px; width: 560px; font-size: 33px; line-height: 1.38; color: #f4f1ea; }}
.lede b {{ color: #ffb08a; font-weight: 700; }}
.hook {{ left: 100px; top: 590px; width: 560px; font-size: 29px; line-height: 1.4; color: #ffb08a; font-weight: 650; }}
.panel {{ left: 770px; top: 150px; width: 576px; }}
.panel h3 {{ font-size: 23px; color: #9aa3b8; font-weight: 500; margin-bottom: 26px; letter-spacing: .02em; }}
.panel h3 .t {{ color: #ff9a73; font-weight: 700; }} .panel h3 .e {{ color: #9db8e0; font-weight: 700; }}
.cmp {{ margin-bottom: 34px; }}
.cmp-h {{ display: flex; justify-content: space-between; align-items: baseline; font-size: 23px; color: #d9dce6;
  margin-bottom: 12px; }}
.cmp-h em {{ font-style: normal; font-weight: 800; color: #ff7a4d; font-size: 30px; }}
.row {{ display: flex; align-items: center; gap: 14px; height: 30px; margin-bottom: 8px; }}
.b {{ display: block; height: 22px; border-radius: 4px; min-width: 6px; max-width: 440px; }}
.row .b {{ flex: none; }}
.tron {{ background: linear-gradient(90deg, #e4572e, #ff9a73); box-shadow: 0 0 18px rgba(255,122,77,.45); }}
.eth {{ background: #3d5a80; }}
.tron-t {{ color: #ffb08a; font-size: 22px; font-weight: 700; }} .eth-t {{ color: #9db8e0; font-size: 22px; font-weight: 600; }}
.chart {{ left: 0; top: 760px; width: {W}px; height: 540px; }}
.chart img {{ width: 100%; height: 100%; display: block; }}
.legend {{ left: 100px; top: 800px; font-size: 22px; color: #9aa3b8; line-height: 1.7; }}
.legend .k {{ font-size: 40px; font-weight: 800; color: #f4f1ea; line-height: 1.15; display: block; margin-bottom: 6px; }}
.legend .t {{ color: #ff9a73; font-weight: 700; }} .legend .e {{ color: #9db8e0; font-weight: 700; }}
.yr {{ top: 1268px; font-size: 18px; color: rgba(244,241,234,.55); }}
.rule {{ left: 94px; top: 1330px; width: 1252px; height: 1px; background: #26314d; }}
.stats {{ left: 94px; top: 1362px; width: 1260px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 34px; }}
.stat .n {{ font-size: 62px; font-weight: 800; color: #ff7a4d; letter-spacing: -.02em; line-height: 1.05; }}
.stat .n.sm {{ font-size: 54px; }}
.stat .l {{ margin-top: 12px; font-size: 21px; line-height: 1.42; color: #aab2c5; }}
.stat .l b {{ color: #f4f1ea; font-weight: 600; }}
.box {{ left: 86px; top: 1556px; width: 1268px; height: 168px; border: 1.5px solid #26314d; border-radius: 18px;
  background: rgba(13,19,36,.85); padding: 30px 44px; }}
.links {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }}
.links small {{ display: block; font-size: 19px; color: #9aa3b8; margin-bottom: 8px; }}
.links div {{ font-size: 25px; color: #f4f1ea; letter-spacing: .01em; }}
.note {{ margin-top: 22px; font-size: 17px; color: #9aa3b8; }}
.foot {{ left: 94px; top: 1752px; font-size: 19px; color: #c9cedb; }}
.credit {{ right: 94px; top: 1755px; font-size: 15px; color: #7d869c; }}
</style></head><body>
<div class="abs brand">SHADOW-DOLLARS</div>
<div class="abs tag">open research on stablecoins and scam finance in Thailand</div>
<div class="abs hero">{f['sanc']}<sup>%</sup></div>
<div class="abs lede">of U.S.-sanctioned crypto addresses tagged USDT, TRX or USDC sit on <b>one blockchain: Tron.</b></div>
<div class="abs hook">shadow-dollars tests what public data can, and cannot, prove about scam money in Thailand.</div>
<div class="abs panel">
  <h3>Two USDT rails: <span class="t">Tron</span> vs <span class="e">Ethereum</span>, 23 May 2026</h3>
  {bars}
</div>
<div class="abs chart"><img src="data:image/png;base64,{chart}" alt=""></div>
<div class="abs legend">
  <span class="k">US${f['tron_bn'] + f['eth_bn']:.0f} bn of USDT on two rails</span>
  <span class="t">Tron</span> {f['share']}% (US${f['tron_bn']:.0f} bn) &nbsp;·&nbsp; <span class="e">Ethereum</span> US${f['eth_bn']:.0f} bn<br>
  USDT supply, 2018 to May 2026
</div>
<div class="abs yr" style="left:24px">2018</div>
<div class="abs yr" style="right:24px">2026</div>
<div class="abs rule"></div>
<div class="abs stats">
  <div class="stat"><div class="n">{f['placebo']}%</div><div class="l">of <b>random dates</b> look like a crackdown effect under naive 95% tests</div></div>
  <div class="stat"><div class="n sm">{f['pmin']:.2f}–{f['pmax']:.2f}</div><div class="l">calibrated p-values for <b>three Thai crackdowns</b>: none detectable on-chain</div></div>
  <div class="stat"><div class="n">{f['und_lo']}–{f['und_hi']}%</div><div class="l">precision of the <b>common two-hop rule</b>; multi-signal scoring reaches {f['best_lo']}–{f['best_hi']}%*</div></div>
  <div class="stat"><div class="n">{f['power']}%</div><div class="l">power of a <b>bunching test</b> at the 50,000-baht threshold, 2% mule share*</div></div>
</div>
<div class="abs box">
  <div class="links">
    <div><small>Code + paper</small>github.com/thanatchon36/shadow-dollars</div>
    <div><small>Dataset</small>hf.co/datasets/thanatchon36/shadow-dollars</div>
  </div>
  <div class="note">* Simulated, with planted mule accounts: validates methods, not real accounts. No individual is accused of wrongdoing.</div>
</div>
<div class="abs foot">Thanatchon Chongmankhong &nbsp;·&nbsp; views are my own &nbsp;·&nbsp; DOI {DOI}</div>
<div class="abs credit">USDT supply: Coin Metrics Community Data · sanctions: OFAC SDN list</div>
</body></html>"""


def main() -> None:
    chrome = next((c for c in CHROME if shutil.which(c) or Path(c).exists()), None)
    if chrome is None:
        raise RuntimeError("Chrome or Chromium not found")
    html = page(facts(), chart_png())
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "poster.html"
        src.write_text(html, encoding="utf-8")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", f"--window-size={W},{H}",
                        f"--screenshot={OUT}", src.as_uri()], check=True, capture_output=True)
    print("poster ->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
