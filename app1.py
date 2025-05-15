import streamlit as st
import requests
import pandas as pd
import numpy as np

# ---------------------- CONFIG ----------------------
st.set_page_config(page_title="📈 Crypto Signal Generator", layout="centered")

COINGECKO_MARKET_URL = "https://api.coingecko.com/api/v3/coins/markets"

# ---------------------- FUNCTIONS ----------------------
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

@st.cache_data(ttl=600)
def fetch_top_coins():
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 50,
        'page': 1,
        'sparkline': 'false'
    }
    response = requests.get(COINGECKO_MARKET_URL, params=params)
    data = response.json()

    extra_ids = ['official-trump', 'zerebro']
    for coin_id in extra_ids:
        if not any(coin.get('id') == coin_id for coin in data):
            try:
                coin_data = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}").json()
                market_data = coin_data.get("market_data", {})
                data.append({
                    'id': coin_id,
                    'symbol': coin_data.get('symbol', '').upper(),
                    'name': coin_data.get('name', coin_id),
                    'current_price': market_data.get('current_price', {}).get('usd', 0)
                })
            except:
                continue
    return data

def fetch_price_data(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {'vs_currency': 'usd', 'days': '7', 'interval': 'hourly'}
        response = requests.get(url, params=params)
        data = response.json()
        prices = data.get("prices", [])
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("datetime", inplace=True)
        df.drop("timestamp", axis=1, inplace=True)
        return df
    except:
        return pd.DataFrame()

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_signal(df):
    df['EMA12'] = df['price'].ewm(span=12).mean()
    df['EMA26'] = df['price'].ewm(span=26).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
    df['RSI'] = compute_rsi(df['price'])

    latest = df.dropna().iloc[-1]

    score = 0
    notes = []

    if latest['EMA12'] > latest['EMA26']:
        score += 1
        notes.append("✅ EMA12 > EMA26 (Bullish)")

    if latest['MACD'] > latest['MACD_signal']:
        score += 1
        notes.append("✅ MACD > Signal (Momentum Up)")

    if latest['RSI'] < 30:
        score += 1
        notes.append("✅ RSI < 30 (Oversold)")
    elif latest['RSI'] > 70:
        score -= 1
        notes.append("❌ RSI > 70 (Overbought)")
    else:
        notes.append("⚠️ RSI Neutral")

    if score >= 1:
        signal = "✅ Strong Buy"
    else:
        signal = "❌ Strong Sell"

    return signal, notes, latest['price']

# ---------------------- MAIN APP ----------------------
def main():
    st.title("📈 Crypto Signal Generator (Most Probable)")
    
    if not is_connected():
        st.error("❌ No internet connection.")
        return

    coins = fetch_top_coins()
    coin_options = [f"{c['symbol'].upper()} - {c['name']}" for c in coins]
    selected = st.selectbox("Select a Coin", coin_options)
    coin = coins[coin_options.index(selected)]

    df = fetch_price_data(coin['id'])

    st.markdown(f"**Current Price:** ${round(coin['current_price'], 4)}")

    if df.empty or len(df) < 50:
        st.warning("⚠️ No candle data available for this coin. Using real-time price only.")
        st.info("⚠️ Cannot generate chart or signal due to lack of data.")
    else:
        st.line_chart(df['price'], use_container_width=True)
        signal, notes, entry_price = calculate_signal(df)
        st.subheader("📊 Signal Prediction")
        st.write(f"**Signal:** {signal}")
        st.write(f"**Entry Price:** ${round(entry_price, 4)}")
        st.markdown("**Analysis Notes:**")
        for note in notes:
            st.markdown(f"- {note}")

if __name__ == "__main__":
    main()
