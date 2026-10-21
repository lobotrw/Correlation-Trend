### Correlation Trend Application

![plot](components/main.png)
This Streamlit app compares the 10 largest cryptocurrencies (by live market cap, excluding stablecoins and wrapped/staked tokens) with Bitcoin, using daily data for the last 365 complete UTC days.

#### What is calculated

1. **Ranking and market caps:** live from CoinGecko. If CoinGecko is unavailable, the app uses a fixed coin list and shows **no** market caps.
2. **Prices:** daily closes from CryptoCompare (if `CRYPTOCOMPARE_API_KEY` is set) or Yahoo Finance. Today's still-forming daily candle is excluded.
3. **Correlation:** of daily **returns**. Correlating price levels inflates the values, because any two trending series look correlated.
4. **Own trend per coin:** from the 25-day SMA. The slope over the last 5 days is +1 when it is above +1 %, −1 when it is below −1 %, and 0 when the SMA is flat. Hysteresis stops it flipping on daily noise. Each value uses only past data.
5. **Market trend:** the average of each coin's **own** trend, market-cap-weighted (when live caps are available) and equal-weight.
6. **BTC trend × corr.:** a BTC-beta view of where a coin "should" go if it follows BTC. It is not the coin's own trend.

This is descriptive information, not financial advice.

![plot](components/heatmap.png)
