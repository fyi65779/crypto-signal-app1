import streamlit as st
import requests
import pandas as pd
import numpy as np
import talib

# TwelveData API Key
API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'

# Internet connection check
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# Fetch data from TwelveData API
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
            return df
        else:
            st.error(f"❌ API Error: {data.get('message', 'Unknown error')}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Fetch error: {e}")
        return pd.DataFrame()

# Calculate indicators
def calculate_indicators(df):
    df['RSI'] = talib.RSI(df['close'], timeperiod=14)
    df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
    df['EMA9'] = talib.EMA(df['close'], timeperiod=9)
    df['EMA21'] = talib.EMA(df['close'], timeperiod=21)
    df['UpperBand'], df['MiddleBand'], df['LowerBand'] = talib.BBANDS(df['close'], timeperiod=20)
    return df

# Generate signal
def generate_signal(df):
    latest = df.iloc[-1]

    rsi_signal = 'Buy (RSI < 30)' if latest['RSI'] < 30 else 'Sell (RSI > 70)' if latest['RSI'] > 70 else 'Neutral'
    macd_signal = 'Bullish (MACD > Signal)' if latest['MACD'] > latest['MACD_signal'] else 'Bearish'
    ema_signal = 'Bullish (EMA9 > EMA21)' if latest['EMA9'] > latest['EMA21'] else 'Bearish'
    bb_signal = 'Buy (Below Lower Band)' if latest['close'] < latest['LowerBand'] else 'Sell (Above Upper Band)' if latest['close'] > latest['UpperBand'] else 'Neutral'

    # Strength logic
    buy_signals = sum(['Buy' in s or 'Bullish' in s for s in [rsi_signal, macd_signal, ema_signal, bb_signal]])
    sell_signals = sum(['Sell' in s or 'Bearish' in s for s in [rsi_signal, macd_signal, ema_signal, bb_signal]])

    if buy_signals >= 3:
        combined = '✅ Strong Buy'
    elif sell_signals >= 3:
        combined = '❌ Strong Sell'
    else:
        combined = '⚠️ Neutral / Weak Signal'

    return {
        'RSI': rsi_signal,
        'MACD': macd_signal,
        'EMA': ema_signal,
        'Bollinger': bb_signal,
        'Combined': combined
    }

# Streamlit app
def main():
    st.set_page_config(page_title="Crypto Signal Generator", layout="centered")
    st.title("📈 Crypto Signal Generator")
    st.markdown("Analyze **crypto trading signals** using real-time indicators (RSI, MACD, EMA, Bollinger Bands).")

    if not is_connected():
        st.error("❌ No internet connection.")
        return

    symbol = st.text_input("Enter crypto symbol (e.g., BTC/USD, ETH/USD):", "BTC/USD")

    if st.button("🔍 Generate Signal"):
        df = fetch_data(symbol)
        if df.empty:
            st.warning("⚠️ No data found.")
            return

        df = calculate_indicators(df)
        signal = generate_signal(df)

        st.subheader(f"📊 Signal for {symbol}")
        st.write(f"**RSI:** {signal['RSI']}")
        st.write(f"**MACD:** {signal['MACD']}")
        st.write(f"**EMA Crossover:** {signal['EMA']}")
        st.write(f"**Bollinger Bands:** {signal['Bollinger']}")
        st.markdown(f"### Final Signal: {signal['Combined']}")

if __name__ == "__main__":
    main()
