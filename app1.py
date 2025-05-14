import streamlit as st
import requests
import pandas as pd
import numpy as np
import talib

API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'

def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

@st.cache_data(ttl=60)
def get_coin_list():
    return ['BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD', 'DOGE/USD', 'BNB/USD']

def fetch_data(symbol, interval='1h', limit=100):
    url = "https://api.twelvedata.com/time_series"
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': API_KEY,
        'limit': limit
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if "values" in data:
            df = pd.DataFrame(data['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df = df.astype(float)
            return df.sort_index()
        else:
            st.error(f"❌ Error fetching data: {data.get('message', 'Unknown error')}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return pd.DataFrame()

def calculate_indicators(df):
    df['RSI'] = talib.RSI(df['close'], timeperiod=14)
    df['MACD'], df['MACD_signal'], _ = talib.MACD(df['close'], 12, 26, 9)
    df['EMA9'] = talib.EMA(df['close'], timeperiod=9)
    df['EMA21'] = talib.EMA(df['close'], timeperiod=21)
    df['Upper'], df['Middle'], df['Lower'] = talib.BBANDS(df['close'], timeperiod=20)
    return df

def generate_signal(df):
    latest = df.iloc[-1]
    rsi_sig = 'Buy (RSI < 30)' if latest['RSI'] < 30 else 'Sell (RSI > 70)' if latest['RSI'] > 70 else 'Neutral'
    macd_sig = 'Bullish' if latest['MACD'] > latest['MACD_signal'] else 'Bearish'
    ema_sig = 'Bullish' if latest['EMA9'] > latest['EMA21'] else 'Bearish'
    bb_sig = 'Buy (Below Band)' if latest['close'] < latest['Lower'] else 'Sell (Above Band)' if latest['close'] > latest['Upper'] else 'Neutral'
    signals = [rsi_sig, macd_sig, ema_sig, bb_sig]
    buy_count = sum('Buy' in s or 'Bullish' in s for s in signals)
    combined = '✅ Strong Buy' if buy_count >= 3 else '❌ Weak/Neutral'
    return {
        'RSI': rsi_sig,
        'MACD': macd_sig,
        'EMA': ema_sig,
        'Bollinger': bb_sig,
        'Combined': combined
    }

def main():
    st.set_page_config(page_title="Crypto Signal App", layout="centered")
    st.title("📊 Real-time Crypto Signal Generator")

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

    if not is_connected():
        st.error("❌ Internet connection issue.")
        st.stop()

    coin_list = get_coin_list()
    symbol = st.selectbox("🔍 Select a coin pair:", coin_list)

    df = fetch_data(symbol)
    if df.empty:
        st.warning("⚠️ No data received.")
        st.stop()

    df = calculate_indicators(df)
    signal = generate_signal(df)

    st.subheader(f"📈 Signal Summary for {symbol}")
    st.write(f"**RSI Signal:** {signal['RSI']}")
    st.write(f"**MACD Signal:** {signal['MACD']}")
    st.write(f"**EMA Crossover:** {signal['EMA']}")
    st.write(f"**Bollinger Band:** {signal['Bollinger']}")
    st.write(f"### {signal['Combined']}")

if __name__ == "__main__":
    main()
