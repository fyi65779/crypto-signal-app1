import streamlit as st
import pandas as pd
import requests
import plotly.graph_objs as go
import ta

# Set page config at top
st.set_page_config(page_title="📊 Crypto Signal Generator", layout="centered")

# Internet check
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# Fetch top 50 coins with TRUMP and ZEREBRO support
@st.cache_data(ttl=300)
def fetch_top_coins(limit=50):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': limit,
        'page': 1,
        'sparkline': 'false',
        'price_change_percentage': '1h,24h'
    }
    coins = requests.get(url, params=params).json()
    for custom in ["official-trump", "zerebro"]:
        if not any(c['id'] == custom for c in coins):
            try:
                extra = requests.get(f"https://api.coingecko.com/api/v3/coins/{custom}").json()
                coins.append({
                    'id': extra['id'],
                    'symbol': extra['symbol'],
                    'name': extra['name'],
                    'current_price': extra['market_data']['current_price']['usd']
                })
            except:
                continue
    return coins

# Fetch historical OHLC data
def fetch_ohlc_data(coin_id, days="1"):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {'vs_currency': 'usd', 'days': days, 'interval': 'hourly' if days == '1' else 'daily'}
    data = requests.get(url, params=params).json()
    prices = data.get("prices", [])
    df = pd.DataFrame(prices, columns=["timestamp", "price"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["price"]
    df["open"] = df["close"].shift(1).fillna(df["close"])
    df["high"] = df["close"].rolling(3).max().fillna(df["close"])
    df["low"] = df["close"].rolling(3).min().fillna(df["close"])
    return df[["timestamp", "open", "high", "low", "close"]].dropna()

# Generate signal using MACD, RSI, etc.
def generate_signal(df):
    macd = ta.trend.macd(df['close'])
    rsi = ta.momentum.rsi(df['close'])

    macd_signal = "Buy 🔼" if macd.iloc[-1] > 0 else "Sell 🔽"
    rsi_value = rsi.iloc[-1]
    rsi_signal = "Overbought ⚠️" if rsi_value > 70 else "Oversold ✅" if rsi_value < 30 else "Neutral"

    trend = "📈 Uptrend" if df['close'].iloc[-1] > df['close'].iloc[0] else "📉 Downtrend"
    confidence = 70 if macd.iloc[-1] > 0 else 30
    confidence += 10 if rsi_value < 30 else -10 if rsi_value > 70 else 0

    return {
        "macd": round(macd.iloc[-1], 4),
        "rsi": round(rsi_value, 2),
        "signal": macd_signal,
        "rsi_signal": rsi_signal,
        "trend": trend,
        "confidence": min(max(confidence, 10), 95)
    }

# Plot candlestick chart with MACD
def plot_chart(df, coin_symbol):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["timestamp"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Candlestick"
    ))
    fig.update_layout(title=f"📊 Price Chart for {coin_symbol}", xaxis_title="Time", yaxis_title="Price (USD)", height=400)
    st.plotly_chart(fig, use_container_width=True)

# Main App
def main():
    st.title("📊 Crypto Signal Generator")
    if not is_connected():
        st.error("❌ Internet connection error.")
        return

    coins = fetch_top_coins()
    if not coins:
        st.error("Failed to load coins.")
        return

    coin_names = [f"{coin['symbol'].upper()} ({coin['id']}) - ${coin.get('current_price', 'N/A')}" for coin in coins]
    selected_coin = st.selectbox("🔎 Select Coin", coin_names)
    coin_id = selected_coin.split("(")[1].split(")")[0]
    coin_symbol = selected_coin.split()[0]

    timeframe = st.radio("⏱️ Timeframe", ["1 Day", "1 Week", "1 Month"])
    days_map = {"1 Day": "1", "1 Week": "7", "1 Month": "30"}
    df = fetch_ohlc_data(coin_id, days_map[timeframe])

    if df.empty:
        st.error("❌ No historical data found.")
        return

    signal = generate_signal(df)
    st.subheader(f"🔔 Signal for {coin_symbol}")
    st.write(f"**MACD:** {signal['macd']}")
    st.write(f"**RSI:** {signal['rsi']} ({signal['rsi_signal']})")
    st.write(f"**Trend:** {signal['trend']}")
    st.write(f"**Direction:** {signal['signal']}")
    st.write(f"**Confidence:** {signal['confidence']}%")

    with st.expander("📈 View Candlestick Chart"):
        plot_chart(df, coin_symbol)

if __name__ == "__main__":
    main()
