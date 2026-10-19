import os

import pandas as pd

import streamlit as st
import cryptocompare

# Function to fetch market cap data from Binance
def get_market_caps():

    # Assuming we have a dictionary with market caps for the sake of this example
    market_caps = {
        'BTC': 1000000000,
        'ETH': 200000000,
        'BNB': 50000000,
        'ADA': 30000000,
        'SOL': 25000000,
        'XRP': 23000000,
        'DOT': 22000000,
        'DOGE':20000000,
        'UNI': 19000000,
        'LTC': 18000000
    }

    sorted_symbols = sorted(market_caps, key=market_caps.get, reverse=True)[:10]
    return sorted_symbols



# Yahoo Finance tickers used when CryptoCompare is unavailable
YAHOO_TICKERS = {"UNI": "UNI7083-USD"}


def _from_yahoo(symbol, limit):
    import yfinance as yf
    ticker = YAHOO_TICKERS.get(symbol, f"{symbol}-USD")
    df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True,
                     multi_level_index=False, progress=False)
    if df.empty:
        return pd.DataFrame()
    df = df.rename(columns=str.lower)[["close"]].iloc[-(limit + 1):]
    df.index.name = "time"
    return df


# Function to fetch historical data (CryptoCompare if an API key is set, else Yahoo Finance)
@st.cache_data(ttl=3600, show_spinner=False)
def get_historical_data(symbol, end_date, limit=365):
    # CryptoCompare (now CoinDesk Data) requires an API key since 2025. Read it from the
    # environment instead of hard-coding it; without a key, fall back to Yahoo Finance.
    key = os.environ.get("CRYPTOCOMPARE_API_KEY")
    if key:
        cryptocompare.cryptocompare._set_api_key_parameter(key)
        try:
            data = cryptocompare.get_historical_price_day(symbol, currency='USD', toTs=end_date, limit=limit)
        except Exception:
            data = None
        if data:
            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df.attrs["source"] = "CryptoCompare"
            return df
    df = _from_yahoo(symbol, limit)
    df.attrs["source"] = "Yahoo Finance"
    return df

def get_trend_val(_data):
    _data['SMA_Trend'] = 0
    for i in range(2, len(_data)):
        if _data['SMA_25'].iloc[i] > _data['SMA_25'].iloc[i-1] > _data['SMA_25'].iloc[i-2]:
            _data.loc[_data.index[i], 'SMA_Trend'] = 1
        elif _data['SMA_25'].iloc[i] < _data['SMA_25'].iloc[i-1] < _data['SMA_25'].iloc[i-2]:
            _data.loc[_data.index[i], 'SMA_Trend'] = -1
            
    return _data['SMA_Trend']