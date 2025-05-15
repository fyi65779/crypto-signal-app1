import streamlit as st
import requests
import pandas as pd
import numpy as np

# ---------------------- CONFIG ----------------------
st.set_page_config(page_title="📈 Crypto Signal Generator", layout="centered")

def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

@st.cache_data(ttl=600)
def fetch_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 50,
        'page': 1,
        'sparkline': False
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        # Add meme coins manually
        extra = ['official-trump', 'zerebro']
        for eid in extra:
            try:
                edata = requests.get(f"https://api.coingecko.com/api/v3/coins/{eid}").json()
                price = edata.get('market_data', {}).get('current_price', {}).get('usd', None)
                if price:
                    data.append({
                        'id': eid,
                        'symbol': edata['symbol'].upper(),
                        'name': edata['name'],
                        'current_price': price
                    })
            except:
                continue
        return data
    except Exception as e:
        st.error(f"Error fetching coin list: {e}")
        return []

def fetch_price_history(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {'vs_currency': 'usd', 'days': 7, 'interval': 'hourly'}
        res = requests.get(url, params=params).json()
        prices = res.get("prices", [])
        if not prices:
            return pd.DataFrame()
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        df.drop('timestamp', axis=1, inplace=True)
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
    reasons = []

    if latest['EMA12'] > latest['EMA26']:
        score += 1
        reasons.append("✅ EMA12 > EMA26 (Bullish)")

    if latest['MACD'] > latest['MACD_signal']:
        score += 1
        reasons.append("✅ MACD > Signal (Momentum Up)")

    if latest['RSI'] < 30:
        score += 1
        reasons.append("✅ RSI < 30 (Oversold)")
    elif latest['RSI'] > 70:
        score -= 1
        reasons.append("❌ RSI > 70 (Overbought)")
    else:
        reasons.append("⚠️ RSI Neutral")

    signal = "✅ Strong Buy" if score >= 1 else "❌ Strong Sell"
    return signal, reasons, round(latest['price'], 4)

# ---------------------- MAIN ----------------------
def main():
    st.title("📈 Crypto Signal Generator (Most Probable)")

    if not is_connected():
        st.error("❌ No internet connection.")
        return

    coins = fetch_top_coins()
    coin_options = [f"{coin['symbol'].upper()} - {coin['name']} (${coin['current_price']})" for coin in coins]
    selected = st.selectbox("Select a Coin", coin_options)
    selected_coin = coins[coin_options.index(selected)]
    coin_id = selected_coin['id']

    # Show current price
    st.write(f"**Current Price:** ${round(selected_coin['current_price'], 4)}")

    # Try fetching price history
    df = fetch_price_history(coin_id)

    if df.empty or len(df) < 30:
        st.warning("⚠️ No price history available for signal.")
        st.info("⚠️ Showing fallback prediction based on price logic.")
        fallback_price = selected_coin['current_price']
        signal = "✅ Strong Buy" if fallback_price < 5 else "❌ Strong Sell"
        st.subheader("📊 Fallback Signal")
        st.success(signal)
    else:
        signal, reasons, entry = calculate_signal(df)
        st.subheader("📊 Signal Prediction")
        st.success(signal)
        st.write(f"**Entry Price:** ${entry}")
        st.markdown("**Reasoning:**")
        for r in reasons:
            st.markdown(f"- {r}")

if __name__ == "__main__":
    main()
