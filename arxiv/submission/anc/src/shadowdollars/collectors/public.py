"""Collectors for the public data used in the paper.

Every download is written to ``data/raw`` and logged in ``MANIFEST.json`` with
its URL, retrieval timestamp (UTC), byte size and SHA-256, so that results can
be audited and re-run against the exact same inputs.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from ..config import (COINMETRICS_RAW, DATA_RAW, FX_DAILY_RAW, OFAC_RAW, OFAC_TICKERS,
                      REFERENCE_ASSETS, STABLE_ASSETS, WB_CPI_RAW)

MANIFEST = DATA_RAW / "MANIFEST.json"


def _log(url: str, path: Path) -> None:
    entry = {
        "url": url,
        "file": path.name,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    manifest[path.name] = entry
    MANIFEST.write_text(json.dumps(manifest, indent=2))


def download(url: str, path: Path, retries: int = 3, timeout: int = 120) -> Path:
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            path.write_bytes(r.content)
            _log(url, path)
            return path
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return path


def fetch_all(force: bool = False) -> None:
    jobs = []
    for a in STABLE_ASSETS + REFERENCE_ASSETS:
        jobs.append((COINMETRICS_RAW.format(asset=a), DATA_RAW / f"cm_{a}.csv"))
    jobs.append((FX_DAILY_RAW, DATA_RAW / "fx_daily.csv"))
    jobs.append((WB_CPI_RAW, DATA_RAW / "wb_cpi.csv"))
    (DATA_RAW / "ofac").mkdir(exist_ok=True)
    for t in OFAC_TICKERS:
        jobs.append((OFAC_RAW.format(ticker=t), DATA_RAW / "ofac" / f"{t}.txt"))
    for url, path in jobs:
        if force or not path.exists():
            try:
                download(url, path)
                print(f"ok   {path.relative_to(DATA_RAW)}")
            except requests.RequestException as exc:  # keep going; report at end
                print(f"FAIL {url}: {exc}")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def coinmetrics(asset: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_RAW / f"cm_{asset}.csv", parse_dates=["time"]).set_index("time")
    return df.sort_index()


def fx_daily() -> pd.DataFrame:
    """FRED H.10 noon buying rates, wide format (one column per country).

    Quotation convention differs across series (most are local currency per
    USD; a few such as the euro, pound, AUD and NZD are USD per unit). Log
    returns are therefore sign-agnostic for volatility, which is what we use.
    """
    fx = pd.read_csv(DATA_RAW / "fx_daily.csv", parse_dates=["Date"])
    wide = fx.pivot_table(index="Date", columns="Country", values="Exchange rate")
    return wide.sort_index()


def cpi_inflation() -> pd.DataFrame:
    path = DATA_RAW / "wb_cpi.csv"
    if not path.exists():  # backwards compatibility with the original file name
        path = DATA_RAW / "wb_inflation_gdp.csv"
    return pd.read_csv(path)


def ofac_addresses() -> pd.DataFrame:
    rows = []
    for f in sorted((DATA_RAW / "ofac").glob("*.txt")):
        for line in f.read_text().splitlines():
            a = line.strip()
            if a:
                rows.append({"ticker": f.stem, "address": a})
    df = pd.DataFrame(rows)
    df["format"] = df["address"].map(address_format)
    return df


def address_format(a: str) -> str:
    """Classify an address string by its encoding (not by its owner)."""
    if a.startswith("0x") and len(a) == 42:
        return "EVM (0x…)"
    if a.startswith("T") and len(a) == 34:
        return "Tron (T…)"
    if a.startswith(("bc1", "1", "3")) and 26 <= len(a) <= 62:
        return "Bitcoin"
    return "Other"


if __name__ == "__main__":
    fetch_all()
