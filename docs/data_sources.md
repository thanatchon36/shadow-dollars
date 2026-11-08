# Data sources

Every input is public. `make data` (`python -m shadowdollars.collectors.public`) downloads only the files missing from
`data/raw/` and records each one in [`data/raw/MANIFEST.json`](../data/raw/MANIFEST.json): URL, retrieval time, size and
SHA-256. The vintage used in the paper was retrieved on 8 November 2026. Some sources update daily, so deleting
`data/raw/` and downloading again gives a later vintage than the one in the manifest.

| Source | Content | Files | Terms |
|---|---|---|---|
| [Coin Metrics Community Data](https://github.com/coinmetrics/data) | Daily on-chain metrics by asset and chain: supply, addresses with a balance, active addresses, transfer counts | `data/raw/cm_*.csv` | See the repository licence (CC BY-NC 4.0 at retrieval); attribution required, non-commercial |
| Federal Reserve H.10, via [`datasets/exchange-rates`](https://github.com/datasets/exchange-rates) | Daily noon buying rates for 22 currencies including the baht | `data/raw/fx_daily.csv` | U.S. public data |
| World Bank FP.CPI.TOTL.ZG, via [`datasets/inflation`](https://github.com/datasets/inflation) | Annual consumer-price inflation | `data/raw/wb_*.csv` | World Bank terms (CC BY 4.0) |
| OFAC SDN list, via [`0xB10C/ofac-sanctioned-digital-currency-addresses`](https://github.com/0xB10C/ofac-sanctioned-digital-currency-addresses) | Sanctioned digital-currency addresses under 17 currency tags | `data/raw/ofac/` | U.S. government data |
| Author's event compilation | 16 dated policy and enforcement events, 2022–2025 | `src/shadowdollars/config.py` (`EVENTS`) | — |

**CPI label swap.** In the `datasets/inflation` mirror the CPI and GDP-deflator file labels are transposed:
`inflation-gdp.csv` holds consumer prices. The code uses the corrected file, checked against known prints (Thailand 2022
= 6.1%, United States 2022 = 8.0%), as documented in Appendix A of the paper.

## Not executed: exchange and account-level data

`src/shadowdollars/collectors/local.py` (exchange OHLCV via `ccxt`, TronGrid transfers) and the account-level schema used
by the pre-registered plan (paper §8) were not executed in the build environment. Verify endpoints and terms of service
before use. Account-level Thai exchange data are available only to exchanges and regulators, under the PDPA.

## Simulated data

The detection results (paper §7) come from an agent-based simulator of an exchange-year with planted mule accounts
(`src/shadowdollars/simulate.py`, `scripts/run_mc.py`). Seeds are fixed, so they reproduce exactly. Figures built from
simulated data carry the label *SIMULATED DATA · METHOD VALIDATION ONLY*; they validate methods against planted ground
truth and are not evidence about real markets.
