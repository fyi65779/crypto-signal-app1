import streamlit as st
import requests
import pandas as pd
import numpy as np

# ---------------------- CONFIG ----------------------
COINGECKO_MARKET_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINGECKO_SIMPLE_URL = "https://api.coingecko.com/api/v3/simple/price"

# ---------------------- UTILITIES ----------------------
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

@st.cache_data(ttl=600)
def fetch_top_coins():
    try:
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 50,
            'page': 1,
            'sparkline': 'false'
        }
        response = requests.get(COINGECKO_MARKET_URL, params=params)
        data = response.json()

        # Extra meme coins
        extra_ids = ['official-trump', 'zerebro']
        for coin_id in extra_ids:
            if not any(coin.get('id') == coin_id for coin in data):
                coin_data = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}").json()
                market_data = coin_data.get("market_data", {})
                data.append({
                    'id': coin_id,
                    'symbol': coin_data.get('symbol', '').upper(),
                    'name': coin_data.get('name', coin_id),
                    'current_price': market_data.get('current_price', {}).get('usd', 0)
                })

        return data
    except Exception as e:
        st.error(f"Error fetching coins: {e}")
        return []

def fetch_price_data(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {'vs_currency': 'usd', 'days': 7, 'interval': 'hourly'}
        response = requests.get(url, params=params)
        data = response.json()

        prices = data.get('prices', [])
        df = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        df.drop('timestamp', axis=1, inplace=True)
        return df
    except:
        return pd.DataFrame()

def calculate_signals(df):
    df['EMA12'] = df['price'].ewm(span=12).mean()
    df['EMA26'] = df['price'].ewm(span=26).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9).mean()

    df['RSI'] = compute_rsi(df['price'], 14)
    latest = df.iloc[-1]

    score = 0
    if latest['EMA12'] > latest['EMA26']:
        score += 1  # Bullish crossover
    if latest['MACD'] > latest['Signal']:
        score += 1
    if latest['RSI'] < 30:
        score += 1  # Oversold
    elif latest['RSI'] > 70:
        score -= 1  # Overbought

    # Force a decision
    if score >= 1:
        return "✅ Strong Buy"
    else:
        return "❌ Strong Sell"

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ---------------------- MAIN APP ----------------------
st.set_page_config(page_title="Crypto Signal Generator", layout="centered")

def main():
    st.title("📈 Crypto Signal Generator (Most Probable)")

    if not is_connected():
        st.error("❌ No internet connection.")
        return

    coins = fetch_top_coins()
    if not coins:
        st.warning("⚠️ Could not load coins.")
        return

    coin_options = [f"{coin['symbol'].upper()} - {coin['name']}" for coin in coins]
    selected = st.selectbox("Select a Coin", coin_options)
    coin_id = coins[coin_options.index(selected)]['id']

    # Price display
    price = fetch_price_data(coin_id)
    if price.empty:
        st.warning("⚠️ No price history available. Showing basic info only.")
        st.write(f"Current Price: ${coins[coin_options.index(selected)]['current_price']}")
        st.write("❌ Unable to generate signal without price history.")
    else:
        st.line_chart(price['price'])
        signal = calculate_signals(price)
        st.subheader("📊 Signal Prediction")
        st.success(signal)

if __name__ == "__main__":
    main()
