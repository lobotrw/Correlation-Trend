import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timezone

import matplotlib.dates as mdates
import numpy as np
from matplotlib.collections import LineCollection
import time
from functions import get_market_caps, get_historical_data, get_trend_val, market_trend, return_correlation

# Set Page Configurations
st.set_page_config(
    page_title="Correlation Trend",
    page_icon="📊",
    layout="wide"
)
[_, c, _] = st.columns([1, 15, 1])

# WELCOME (animated only on the first run of a session, not on every rerun)
if not st.session_state.get("welcomed"):
    for t in ["***:blue[Welcome] to Crypto Correlation App***", "***Welcome :blue[to] Crypto Correlation App***",
              "***Welcome to :blue[Crypto] Correlation App***", "***Welcome to Crypto :blue[Correlation] App***",
              "***Welcome to Crypto Correlation :blue[App]***"]:
        welcome = c.title(t)
        time.sleep(.5)
        welcome.empty()
    st.session_state["welcomed"] = True
c.title("***:blue[Crypto] Correlation App***")

about = open("components/about.txt", "r")

# Real market caps (CoinGecko); falls back to a fixed coin list without caps
caps_df, caps_source = get_market_caps()

# Define the date range: up to now (the incomplete current daily candle is dropped)
end_date = datetime.now(timezone.utc)

# Fetch daily closes; take the 10 largest coins that have daily price data
price_data = pd.DataFrame()
missing, coins = [], []
for symbol in caps_df["symbol"]:
    if len(coins) == 10:
        break
    data = get_historical_data(symbol, end_date)
    if data.empty or 'close' not in data:
        missing.append(symbol)
        continue
    price_data[symbol] = data['close']
    coins.append(symbol)
caps = caps_df.set_index("symbol")["market_cap"].reindex(coins)
has_caps = caps.notna().all()

if 'BTC' not in price_data:
    c.error(f"Could not load price data for {', '.join(missing) or 'BTC'}. "
            "Set CRYPTOCOMPARE_API_KEY or check your network connection.")
    st.stop()

option = c.selectbox("Which Coin would you like to be ploted?", coins)

if missing:
    c.warning(f"No daily price data for {', '.join(missing)}; skipped (next-largest coins used instead).")
c.caption(f"Daily closes, last {len(price_data)} complete UTC days (today's forming candle excluded). "
          f"Prices: {data.attrs.get('source', 'unknown')}. Ranking and market caps: {caps_source}. "
          "Stablecoins and wrapped/staked tokens excluded.")

# Correlation of daily RETURNS (price-level correlation is inflated by common trends)
correlation_matrix = return_correlation(price_data)

# Create a heatmap of the correlation matrix
fig1 = plt.figure(figsize=(10, 8))
sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap='coolwarm', linewidths=0.5, linecolor='black')
plt.title("Correlation of daily returns")

# Each coin's own SMA25 trend
own_trend = {}
for symbol in coins:
    d = price_data[[symbol]].rename(columns={symbol: "close"}).dropna()
    d['SMA_25'] = d['close'].rolling(window=25).mean()
    own_trend[symbol] = int(get_trend_val(d).iloc[-1])

_data = price_data[[option]].rename(columns={option: "close"}).dropna()
_data['SMA_25'] = _data['close'].rolling(window=25).mean()
_data['SMA_Trend'] = get_trend_val(_data)

# Plot close price and SMA coloured by trend (one LineCollection instead of 365 plot calls)
fig2, ax = plt.subplots(figsize=(14, 7))
ax.plot(_data.index, _data['close'], label=f'{option} Close Price', color='black', linewidth=1)
x = mdates.date2num(_data.index.to_pydatetime())
pts = np.column_stack([x, _data['SMA_25'].to_numpy()])
segs = np.stack([pts[:-1], pts[1:]], axis=1)
colors = ['red' if t == -1 else ('#5396ec' if t == 1 else 'gray') for t in _data['SMA_Trend'].iloc[:-1]]
ax.add_collection(LineCollection(segs, colors=colors, linewidths=3, label='SMA 25 (blue up / red down / gray flat)'))
ax.xaxis_date()
ax.set_title(f'{option} Close Price with SMA 25')
ax.legend()

btc_trend = own_trend["BTC"]
corr_btc = correlation_matrix['BTC']
trend_table = pd.DataFrame({
    'Coin': coins,
    'Own trend': [own_trend[s] for s in coins],
    'Return corr. with BTC': [round(float(corr_btc[s]), 2) for s in coins],
    'BTC trend × corr.': [round(float(corr_btc[s]) * btc_trend, 2) if s != "BTC" else None for s in coins],
})
if has_caps:
    trend_table.insert(1, 'Market cap (USD bn)', [round(caps[s] / 1e9, 1) for s in coins])

avg_eq, avg_cap = market_trend(own_trend, caps if has_caps else None)

with c:
    [c1, c2] = st.columns([1.2, 2])

    c1.subheader("Correlation Top :blue[10]" if has_caps else "Correlation: :blue[selected coins]")
    c1.pyplot(fig1, width='stretch')
    c2.subheader(f":orange[{option}] TREND")
    c2.pyplot(fig2, width='stretch')
    c1.divider()
    c2.divider()
    c1.subheader("Trend values")
    c1.dataframe(trend_table, width='stretch', hide_index=True)
    c1.caption("Own trend: +1 up, −1 down, 0 flat (SMA25 5-day slope beyond ±1 %, with hysteresis). "
               "'BTC trend × corr.' is a BTC-beta view, not the coin's own trend.")
    if avg_cap is not None:
        c2.metric(label="Market trend (market-cap-weighted avg of each coin's own trend)", value=round(avg_cap, 2))
    c2.metric(label="Market trend (equal-weight avg of each coin's own trend)", value=round(avg_eq, 2))

    with c2.expander("DESCRIPTION:"):
        st.markdown(about.read())

    st.divider()
    st.write('''Crypto Correlation App 2024\n
             This site is for informational purposes only. The information on our website is not financial advice, and you should not consider it to be financial advice.''')

    st.write("@VanHes1ng")

    st.write('''TradingView: https://www.tradingview.com/u/VanHe1sing/\n 
Telegram: https://t.me/IvanKocherzhat\n 
GitHub: https://github.com/VanHes1ng\n
X: https://x.com/Van_He1sing           
''')

     
