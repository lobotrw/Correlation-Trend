import os

import numpy as np
import pandas as pd
import requests

import streamlit as st
import cryptocompare

# Coins shown if the live market-cap ranking is unavailable (no market caps are shown then)
FALLBACK_COINS = ["BTC", "ETH", "BNB", "ADA", "SOL", "XRP", "DOT", "DOGE", "UNI", "LTC"]

# Pegged / wrapped / staked tokens: their "correlation" or "trend" is meaningless here
EXCLUDE = {"USDT", "USDC", "USDS", "USDE", "DAI", "USD1", "FDUSD", "PYUSD", "TUSD", "USDD", "FRAX",
           "USDTB", "BSC-USD", "SUSDE", "BUIDL", "USDF", "RLUSD", "USD0", "WBTC", "WETH", "STETH",
           "WSTETH", "WEETH", "CBBTC", "WBETH", "RETH", "METH", "EZETH", "XAUT", "PAXG", "FIGR_HELOC"}


@st.cache_data(ttl=3600, show_spinner=False)
def get_market_caps(n=10, candidates=40):
    """Real market caps from CoinGecko's public /coins/markets endpoint (no key needed).

    Returns (DataFrame[symbol, name, market_cap] ordered by market cap, source label).
    Pegged/wrapped tokens are excluded. On any failure returns the fallback coin list
    WITHOUT market caps (never invented numbers).
    """
    try:
        r = requests.get("https://api.coingecko.com/api/v3/coins/markets",
                         params={"vs_currency": "usd", "order": "market_cap_desc",
                                 "per_page": candidates, "page": 1}, timeout=15)
        r.raise_for_status()
        rows = [{"symbol": c["symbol"].upper(), "name": c["name"], "market_cap": float(c["market_cap"] or 0)}
                for c in r.json()]
        df = pd.DataFrame(rows)
        df = df[~df["symbol"].isin(EXCLUDE)].drop_duplicates("symbol")
        return df.reset_index(drop=True), "CoinGecko (live)"
    except Exception:
        return pd.DataFrame({"symbol": FALLBACK_COINS, "name": FALLBACK_COINS,
                             "market_cap": np.nan}), "fixed list (live market caps unavailable)"


# Yahoo Finance tickers used when CryptoCompare is unavailable
YAHOO_TICKERS = {"UNI": "UNI7083-USD", "SUI": "SUI20947-USD", "HYPE": "HYPE32196-USD"}


def _from_yahoo(symbol, limit):
    import yfinance as yf
    ticker = YAHOO_TICKERS.get(symbol, f"{symbol}-USD")
    df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True,
                     multi_level_index=False, progress=False)
    if df.empty:
        return pd.DataFrame()
    df = df.rename(columns=str.lower)[["close"]].iloc[-(limit + 2):]
    df.index.name = "time"
    return df


def drop_incomplete_daily_bar(df, now=None):
    """Remove today's (UTC) daily candle: it is still forming and would make the trend repaint."""
    if df.empty:
        return df
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    today = now.tz_convert("UTC").normalize().tz_localize(None) if now.tzinfo else now.normalize()
    idx = df.index.tz_localize(None) if getattr(df.index, "tz", None) is not None else df.index
    return df[idx.normalize() < today]


# Function to fetch historical data (CryptoCompare if an API key is set, else Yahoo Finance)
@st.cache_data(ttl=3600, show_spinner=False)
def get_historical_data(symbol, end_date, limit=365):
    # CryptoCompare (now CoinDesk Data) requires an API key since 2025. Read it from the
    # environment instead of hard-coding it; without a key, fall back to Yahoo Finance.
    key = os.environ.get("CRYPTOCOMPARE_API_KEY")
    if key:
        cryptocompare.cryptocompare._set_api_key_parameter(key)
        try:
            data = cryptocompare.get_historical_price_day(symbol, currency='USD', toTs=end_date, limit=limit + 1)
        except Exception:
            data = None
        if data:
            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df = drop_incomplete_daily_bar(df).iloc[-limit:]
            df.attrs["source"] = "CryptoCompare"
            return df
    df = drop_incomplete_daily_bar(_from_yahoo(symbol, limit)).iloc[-limit:]
    df.attrs["source"] = "Yahoo Finance"
    return df


def get_trend_val(_data, n=5, band=0.01):
    """SMA25 trend with hysteresis (causal: each value uses only that bar and earlier ones).

    slope = SMA25 change over the last ``n`` bars, relative to SMA25.
    +1 once slope > +band, -1 once slope < -band. Inside the band the previous state is kept
    as long as the slope still points the same way; otherwise the trend is 0 (flat).
    """
    sma = _data['SMA_25']
    slope = sma / sma.shift(n) - 1
    state, out = 0, []
    for s in slope:
        if np.isnan(s):
            state = 0
        elif s > band:
            state = 1
        elif s < -band:
            state = -1
        elif state * s <= 0:          # slope no longer agrees with the held state
            state = 0
        out.append(state)
    _data['SMA_Trend'] = out
    return _data['SMA_Trend']


def return_correlation(price_data):
    """Correlation of daily (simple) returns, not of price levels."""
    return price_data.pct_change().corr()


def market_trend(own_trends, market_caps=None):
    """Average of each coin's OWN trend; market-cap weighted when real caps are given."""
    t = pd.Series(own_trends, dtype=float)
    eq = float(t.mean())
    if market_caps is None:
        return eq, None
    w = pd.Series(market_caps, dtype=float).reindex(t.index)
    if w.isna().any() or w.sum() <= 0:
        return eq, None
    return eq, float((t * w).sum() / w.sum())
