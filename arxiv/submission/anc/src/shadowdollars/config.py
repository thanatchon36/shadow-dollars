"""Central configuration for the Shadow Dollars project.

All paths are relative to the repository root so that the whole pipeline can be
re-run with ``python -m shadowdollars.run_all`` or ``bash run_all.sh``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures"
TABLES = ROOT / "paper" / "tables"

for _p in (DATA_RAW, DATA_PROCESSED, FIGURES, TABLES):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Public data sources that are fetched by ``collectors`` (all verified to be
# reachable when the paper was compiled). Every source is versioned by the
# retrieval date written to ``data/raw/MANIFEST.json``.
# ---------------------------------------------------------------------------
COINMETRICS_RAW = "https://raw.githubusercontent.com/coinmetrics/data/master/csv/{asset}.csv"
FX_DAILY_RAW = "https://raw.githubusercontent.com/datasets/exchange-rates/main/data/daily.csv"
# NOTE: in the `datasets/inflation` mirror the two file labels are transposed.
# `inflation-gdp.csv` holds World Bank FP.CPI.TOTL.ZG (consumer prices) and
# `inflation-consumer.csv` holds the GDP deflator. We validated this against
# known CPI prints (e.g. Thailand 2022 = 6.1%, United States 2022 = 8.0%).
WB_CPI_RAW = "https://raw.githubusercontent.com/datasets/inflation/main/data/inflation-gdp.csv"
OFAC_RAW = (
    "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/"
    "lists/sanctioned_addresses_{ticker}.txt"
)

STABLE_ASSETS = [
    "usdt", "usdt_trx", "usdt_eth", "usdt_omni", "usdt_avaxc",
    "usdc", "usdc_eth", "usdc_trx", "dai", "pyusd_eth", "fdusd_eth", "usde_eth",
]
REFERENCE_ASSETS = ["btc", "eth", "trx"]
OFAC_TICKERS = ["XBT", "ETH", "USDT", "TRX", "USDC", "XMR", "LTC", "ZEC", "DASH",
                "BCH", "BSC", "ARB", "SOL", "ETC", "BSV", "BTG", "XVG"]

# USDT token contracts (public, widely documented).
USDT_TRC20 = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_ERC20 = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
USDC_ERC20 = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

# ---------------------------------------------------------------------------
# Institutional parameters (Thailand). Approximate; verify before use.
# ---------------------------------------------------------------------------
BIOMETRIC_TX_THRESHOLD_THB = 50_000      # face verification per transfer
BIOMETRIC_DAY_THRESHOLD_THB = 200_000    # face verification, cumulative per day


@dataclass(frozen=True)
class Event:
    date: str            # ISO date; month-level events use the 1st of month
    label: str
    lane: str            # "thai", "enforcement", "global", "border"
    precise: bool        # True if the day is known with confidence


EVENTS = [
    Event("2022-04-01", "SEC bars crypto-payment facilitation", "thai", True),
    Event("2023-03-17", "Tech-crime decree: mule accounts criminalised", "thai", True),
    Event("2023-11-01", "AOC 1441 anti-scam centre opens", "thai", True),
    Event("2024-01-15", "UNODC report on USDT-Tron & underground banking", "enforcement", False),
    Event("2024-02-01", "Circle ends USDC minting on Tron", "global", False),
    Event("2024-06-30", "EU MiCA stablecoin titles apply", "global", True),
    Event("2024-09-01", "T3 Financial Crime Unit formed", "enforcement", False),
    Event("2025-02-05", "Thailand cuts power to border scam hubs", "enforcement", True),
    Event("2025-03-16", "USDT & USDC approved as quote assets", "thai", False),
    Event("2025-04-01", "Amended tech-crime decree (CASPs liable)", "thai", False),
    Event("2025-05-01", "Telegram removes major guarantee markets", "enforcement", False),
    Event("2025-06-28", "Unlicensed offshore exchanges blocked", "thai", True),
    Event("2025-07-18", "US GENIUS Act signed", "global", True),
    Event("2025-07-24", "Thai-Cambodian border clashes", "border", True),
    Event("2025-08-01", "Hong Kong stablecoin ordinance in force", "global", True),
    Event("2025-10-14", "US/UK sanction Prince Group; FinCEN acts on Huione", "enforcement", True),
]

# Events used in the aggregate on-chain event study: only those whose day is
# known with confidence.
EVENT_STUDY_DATES = {
    "Border power cut (2025-02-05)": "2025-02-05",
    "Offshore exchanges blocked (2025-06-28)": "2025-06-28",
    "Prince Group sanctions (2025-10-14)": "2025-10-14",
}

# ---------------------------------------------------------------------------
# Visual identity
# ---------------------------------------------------------------------------
PALETTE = {
    "ink": "#1d2330",
    "muted": "#6b7280",
    "faint": "#9ca3af",
    "grid": "#e6e8ec",
    "paper": "#ffffff",
    "thai": "#b5172b",
    "neighbour": "#e09f3e",
    "peer": "#a3aab5",
    "tron": "#e4572e",
    "eth": "#3d5a80",
    "usdc_eth": "#2a9d8f",
    "usdc_trx": "#f4a261",
    "omni": "#9aa5b1",
    "avax": "#8d6cab",
    "legit": "#94a3b8",
    "illicit": "#b5172b",
    "bridge": "#3d5a80",
    "remit": "#2a9d8f",
}
LANE_COLORS = {
    "thai": PALETTE["thai"],
    "enforcement": PALETTE["eth"],
    "global": PALETTE["usdc_eth"],
    "border": PALETTE["neighbour"],
}
