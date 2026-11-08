# Shadow Dollars

**Stablecoin Rails, Scam Finance and the Limits of Detection in Thailand**

Thanatchon Chongmankhong · Preprint · November 2026 · [**Read the paper (PDF)**](paper/paper.pdf)

---

## Abstract

Thailand combines low inflation, a licensed and identity-verified crypto exchange sector, and a long border with the
scam-compound economy of Myanmar, Cambodia and Laos. I ask whether Thai stablecoin behaviour is anomalous, whether
USDT is a plausible channel for laundering transnational fraud proceeds, and how either claim can be tested credibly.
Public on-chain data through May 2026 show that USDT on Tron is a retail dollar rail distinct from USDT on Ethereum: it
carries 47% of the covered USDT supply, 74.5 million funded addresses (5.3 times Ethereum), mean balances about six
times smaller and 9.3 times the transfer intensity per dollar. Ninety-five per cent of U.S. sanctions-list addresses
tagged USDT, TRX or USDC are Tron addresses. Thailand itself has little macroeconomic reason to hold dollars on-chain
(2019–2023 inflation of 1.7% a year, fourth lowest of 23 comparators), unlike neighbouring Laos and Myanmar.
Chain-wide data cannot evaluate national enforcement: nominal 95% bands reject at 58% of 149 placebo dates, and
placebo-calibrated p-values for three crackdowns range from 0.69 to 1.00. I therefore develop a pre-registered design
with four estimators—a difference-in-bunching test at the 50,000-baht face-verification threshold, dwell-time
mixtures, direction-aware graph exposure and synthetic control—and validate them in an agent-based simulation with
planted mule accounts. The common undirected two-hop exposure rule attains 2–6% precision among top-ranked accounts;
multi-signal scoring reaches 78–92%; the bunching-difference test has close-to-nominal size and 88% power at a 2%
mule share. A channel-choice model explains why enforcement that displaces flows leaves chain-wide totals unchanged.

## Key findings

1. **A distinct rail.** USDT on Tron is a high-turnover, small-balance dollar rail: 47% of covered USDT supply,
   74.5 million funded addresses and 9.3 times the transfer intensity of USDT on Ethereum.
2. **A weak macro motive.** Thai inflation and exchange-rate volatility do not explain heavy stablecoin use; the same
   is not true of neighbouring Laos and Myanmar, whose legitimate dollar demand can flow through Thai channels.
3. **Aggregate data mislead.** Chain-level event studies over-reject at 58% of random dates; with placebo-calibrated
   inference no crackdown is detectable, as a displacement model predicts.
4. **Detect differences, follow direction.** Structuring is identified by the *difference* in bunching between USDT
   and other assets, not by bunching itself; graph exposure must follow the direction of funds.
5. **A ready design.** Six pre-registered hypotheses, decision rules and open code make the Thai question testable as
   soon as exchange or regulator data are available under the PDPA.

## Selected figures

| | |
|---|---|
| ![USDT supply by chain](figures/fig_rails_supply.png) | ![Two rails, two clienteles](figures/fig_two_rails.png) |
| ![Placebo-calibrated event study](figures/fig_event_study.png) | ![Monte Carlo summary (simulated)](figures/fig_power.png) |

Figures built from simulated data are marked *SIMULATED DATA · METHOD VALIDATION ONLY*. Every figure passes an
automated check for overlapping text (`figures/qa_overlaps.json`).

## Repository layout

| Path | Content |
|---|---|
| `paper/` | arXiv-style LaTeX source (`main.tex`, `arxiv.sty`, sections, `refs.bib`, `main.bbl`), figures, tables and the compiled `paper.pdf` |
| `src/shadowdollars/` | Python package: data collectors, detectors (bunching, dwell-time mixtures, graph exposure, anomaly scoring, synthetic control, event study), agent-based simulator, Monte Carlo, figure style and overlap QA |
| `scripts/` | `figures_real.py` (public-data figures and tables), `figures_sim.py` (simulation figures and tables), `run_mc.py` (Monte Carlo in resumable chunks) |
| `tests/` | Unit tests for the estimators |
| `data/raw/` | Raw public data as retrieved on 8 November 2026, with `MANIFEST.json` (URL, retrieval time, size, SHA-256) |
| `data/processed/` | Derived series, Monte Carlo results and `facts_*.json` holding every number quoted in the paper |
| `figures/` | All figures as vector PDF and PNG |
| `arxiv/` | Upload-ready arXiv files in `arxiv/submission/`, form metadata (`arxiv_metadata.txt`) and `make_arxiv_zip.sh`, which packs them into `arxiv/arxiv_submission.zip` for upload |

## Reproduce

```bash
pip install -e ".[dev]"
pytest -q            # unit tests, a few seconds
bash run_all.sh      # data -> figures -> Monte Carlo (~10 min on one core) -> tests -> paper
```

Building the paper needs a TeX distribution with `pdflatex` and `bibtex`. Random seeds are fixed, so simulation
results reproduce exactly. The collectors download only missing files; some sources update daily, so deleting
`data/raw/` and re-downloading yields a later data vintage than the one recorded in the manifest.

To create the arXiv upload (`arxiv/arxiv_submission.zip`), including after editing the paper: `bash arxiv/make_arxiv_zip.sh`.

## Data sources

| Source | Content | Terms |
|---|---|---|
| [Coin Metrics Community Data](https://github.com/coinmetrics/data) | Daily on-chain metrics by asset and chain | See the repository licence (CC BY-NC 4.0 at retrieval); attribution required, non-commercial |
| Federal Reserve H.10, via [`datasets/exchange-rates`](https://github.com/datasets/exchange-rates) | Daily noon buying rates | U.S. public data |
| World Bank FP.CPI.TOTL.ZG, via [`datasets/inflation`](https://github.com/datasets/inflation) | Annual CPI inflation | World Bank terms (CC BY 4.0) |
| OFAC SDN list, via [`0xB10C/ofac-sanctioned-digital-currency-addresses`](https://github.com/0xB10C/ofac-sanctioned-digital-currency-addresses) | Sanctioned digital-currency addresses | U.S. government data |

Note: in the `datasets/inflation` mirror the CPI and GDP-deflator file labels are transposed; the code uses the
corrected file, as documented in Appendix A of the paper.

## Citation

```bibtex
@misc{chongmankhong2026shadowdollars,
  author = {Chongmankhong, Thanatchon},
  title  = {Shadow Dollars: Stablecoin Rails, Scam Finance and the Limits of Detection in Thailand},
  year   = {2026},
  note   = {Preprint}
}
```

GitHub also reads `CITATION.cff` and shows a "Cite this repository" button.

## Important notes

* Simulated results validate methods against planted ground truth; they are not evidence about real markets.
* `src/shadowdollars/collectors/local.py` (exchange OHLCV via ccxt, TronGrid transfers) was not executed in the build
  environment; verify endpoints and terms of service before use.
* Some references and institutional dates are flagged in the paper for verification against primary sources.
* No individual is accused of wrongdoing, and no address of a private person is de-anonymised.
* AI assistance: the paper, code and figures were prepared with the assistance of Claude (Anthropic); see the
  disclosure section of the paper.

## Licence

Code: [MIT](LICENSE). The arXiv template `paper/arxiv.sty` is from
[kourgeorge/arxiv-style](https://github.com/kourgeorge/arxiv-style) (MIT). Paper text and figures: © 2026 Thanatchon
Chongmankhong. Data: subject to each provider's terms listed above.
