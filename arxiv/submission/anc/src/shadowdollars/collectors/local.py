"""Collectors meant to be run on the researcher's own machine.

These could NOT be executed in the environment where the paper was compiled
(exchange and explorer domains were not reachable), so they are provided as
tested-by-design code paths. Verify endpoints and terms of service before use.

Tier 3 data (account-level records from exchanges or regulators) must be
pseudonymised by the data provider and handled under the Thai PDPA.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import pandas as pd
import requests

from ..config import USDT_TRC20

TRONGRID = "https://api.trongrid.io/v1/accounts/{address}/transactions/trc20"


def tron_trc20_transfers(address: str, api_key: str | None = None,
                         min_ts_ms: int | None = None, max_ts_ms: int | None = None,
                         contract: str = USDT_TRC20, max_pages: int = 500,
                         sleep_s: float = 0.25) -> pd.DataFrame:
    """Page through TRC-20 transfers of one address (USDT by default).

    Returns one row per transfer with UTC timestamps and amounts in token
    units (USDT has 6 decimals).
    """
    headers = {"TRON-PRO-API-KEY": api_key} if api_key else {}
    params = {"limit": 200, "contract_address": contract, "order_by": "block_timestamp,asc"}
    if min_ts_ms:
        params["min_timestamp"] = min_ts_ms
    if max_ts_ms:
        params["max_timestamp"] = max_ts_ms
    rows, url = [], TRONGRID.format(address=address)
    for _ in range(max_pages):
        r = requests.get(url, headers=headers, params=params, timeout=60)
        r.raise_for_status()
        payload = r.json()
        for t in payload.get("data", []):
            dec = int(t.get("token_info", {}).get("decimals", 6))
            rows.append({
                "tx": t["transaction_id"],
                "ts": pd.to_datetime(t["block_timestamp"], unit="ms", utc=True),
                "from": t["from"], "to": t["to"],
                "amount": int(t["value"]) / 10 ** dec,
            })
        fp = payload.get("meta", {}).get("fingerprint")
        if not fp:
            break
        params["fingerprint"] = fp
        time.sleep(sleep_s)
    return pd.DataFrame(rows)


def ccxt_ohlcv(exchange_id: str, symbol: str, timeframe: str = "1d",
               since_ms: int | None = None, limit: int = 1000) -> pd.DataFrame:
    """OHLCV from any exchange supported by the optional ``ccxt`` package."""
    import ccxt  # optional dependency

    ex = getattr(ccxt, exchange_id)({"enableRateLimit": True})
    data = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
    df = pd.DataFrame(data, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.set_index("ts")


@dataclass(frozen=True)
class LedgerSchema:
    """Minimal account-level schema expected by ``metrics`` and ``detectors``.

    One row per *cycle*: a fiat deposit, the purchase it funded and (if any)
    the on-chain withdrawal that followed. Times are UTC; amounts in THB.
    """
    columns: tuple = (
        "account_id",          # pseudonymous
        "account_open_ts",     # account creation time
        "funding_source_id",   # pseudonymous bank-account id of the depositor
        "deposit_ts", "deposit_thb",
        "asset",               # e.g. USDT, BTC, ETH
        "buy_ts",
        "withdraw_ts",         # NaT if not withdrawn
        "withdraw_network",    # TRC20, ERC20, ...
        "dest_address",        # destination address (hash it if required)
    )


def validate_ledger(df: pd.DataFrame) -> list[str]:
    missing = [c for c in LedgerSchema().columns if c not in df.columns]
    return missing
