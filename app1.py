import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --------- CONFIG ----------
API_KEY = "6cbc54ad9e114dbea0ff7d8a7228188b"  # <-- Apni Twelve Data API key yahan daalein
BASE_URL = "https://api.twelvedata.com"

# --------- UTILS ----------
def fetch_candles(symbol, interval="1h", outputsize=100):
    url = f"{BASE_URL}/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "apikey": API_KEY,
        "format": "JSON",
        "outputsize": outputsize,
        "order": "asc"
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "values" not in data:
        st.error(f"Error fetching candle data: {data.get('message', 'Unknown error')}")
        return pd.DataFrame()
    df = pd.DataFrame(data["values"])
    df['datetime'] = pd.to_datetime(df['datetime'])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.set_index('datetime', inplace=True)
    return df

def compute_indicators(df):
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def generate_signal(df):
    if df.empty or len(df) < 30:
        return "Data insufficient for signal"

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # MACD crossover signal
    macd_bull = (latest['MACD'] > latest['Signal_Line']) and (prev['MACD'] <= prev['Signal_Line'])
    macd_bear = (latest['MACD'] < latest['Signal_Line']) and (prev['MACD'] >= prev['Signal_Line'])

    # RSI overbought/oversold
    rsi = latest['RSI']
    if rsi < 30:
        rsi_signal = "Oversold (Buy)"
    elif rsi > 70:
        rsi_signal = "Overbought (Sell)"
    else:
        rsi_signal = "Neutral"

    # Combine signals to form strong signal
    if macd_bull and rsi < 70:
        signal = "✅ Strong Buy"
        confidence = 90
    elif macd_bear and rsi > 30:
        signal = "❌ Strong Sell"
        confidence = 90
    elif rsi_signal == "Oversold (Buy)":
        signal = "⚠️ Buy"
        confidence = 75
    elif rsi_signal == "Overbought (Sell)":
        signal = "⚠️ Sell"
        confidence = 75
    else:
        # No clear signal but force best guess based on close price change
        price_change = (latest['close'] - prev['close']) / prev['close']
        if price_change > 0:
            signal = "ℹ️ Likely Buy"
            confidence = 60
        else:
            signal = "ℹ️ Likely Sell"
            confidence = 60

    return signal, confidence

# --------- MAIN APP ---------
st.set_page_config(page_title="Twelve Data Crypto Signal Generator", layout="centered")
st.title("📈 Crypto Signal Generator with Twelve Data API")

st.markdown("""
**Instructions:**  
- Enter coin symbol with `/USD` suffix.  
  Example: `BTC/USD`, `ETH/USD`, `SOL/USD`  
- Signal is generated based on MACD and RSI indicators.  
- Confidence score shows the strength of the signal.
""")

symbol = st.text_input("Enter Coin Symbol (e.g. BTC/USD):", value="BTC/USD")

if st.button("Generate Signal"):
    if not symbol or "/" not in symbol:
        st.error("Please enter symbol in format COIN/USD (e.g. BTC/USD)")
    else:
        df = fetch_candles(symbol, interval="1h", outputsize=100)
        if df.empty:
            st.error("Failed to fetch candle data. Check your API key and symbol.")
        else:
            df = compute_indicators(df)
            signal, confidence = generate_signal(df)
            st.subheader(f"Signal: {signal}")
            st.write(f"Confidence: {confidence}%")
            st.line_chart(df['close'])

