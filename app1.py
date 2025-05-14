import streamlit as st
import requests
import pandas as pd
import numpy as np
import ta

# TwelveData API Key
API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'

# Check internet
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# Fetch historical OHLC data
def fetch_data(symbol, interval='1h', limit=100):
    url = f"https://api.twelvedata.com/time_series"
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': API_KEY,
        'limit': limit,
        'outputsize': limit
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
            st.error(f"Error fetching data: {data.get('message', 'Unknown error')}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return pd.DataFrame()

# Indicators
def calculate_indicators(df):
    df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    macd = ta.trend.MACD(df['close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['EMA9'] = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
    df['EMA21'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()
    bb = ta.volatility.BollingerBands(df['close'], window=20)
    df['UpperBand'] = bb.bollinger_hband()
    df['LowerBand'] = bb.bollinger_lband()
    return df

# Generate Signal
def generate_signal(df):
    latest = df.iloc[-1]

    # RSI
    if latest['RSI'] < 30:
        rsi_signal = 'Buy (RSI oversold)'
    elif latest['RSI'] > 70:
        rsi_signal = 'Sell (RSI overbought)'
    else:
        rsi_signal = 'Neutral (RSI normal)'

    # MACD
    macd_signal = 'Bullish (MACD > Signal)' if latest['MACD'] > latest['MACD_signal'] else 'Bearish (MACD < Signal)'

    # EMA Crossover
    ema_signal = 'Bullish (EMA9 > EMA21)' if latest['EMA9'] > latest['EMA21'] else 'Bearish (EMA9 < EMA21)'

    # Bollinger Bands
    if latest['close'] < latest['LowerBand']:
        bb_signal = 'Buy (Below Lower Band)'
    elif latest['close'] > latest['UpperBand']:
        bb_signal = 'Sell (Above Upper Band)'
    else:
        bb_signal = 'Neutral (Within Bands)'

    # Combined
    buy_signals = sum([
        rsi_signal.startswith("Buy"),
        macd_signal.startswith("Bullish"),
        ema_signal.startswith("Bullish"),
        bb_signal.startswith("Buy")
    ])

    if buy_signals >= 3:
        final = "✅ Strong Buy"
    elif buy_signals <= 1:
        final = "❌ Strong Sell"
    else:
        final = "⚠️ Hold / Weak Signal"

    return {
        'RSI': rsi_signal,
        'MACD': macd_signal,
        'EMA': ema_signal,
        'BB': bb_signal,
        'Combined': final
    }

# Streamlit UI
def main():
    st.set_page_config(page_title="Crypto Signal App", layout="centered")
    st.title("📈 Crypto Signal Generator")

    st.markdown("Real-time crypto signals using **RSI, MACD, EMA, and Bollinger Bands** from **TwelveData**.")

    if not is_connected():
        st.error("No internet connection.")
        st.stop()

    symbol = st.text_input("Enter symbol (e.g. BTC/USD):", value="BTC/USD")

    if symbol:
        df = fetch_data(symbol)
        if df.empty:
            st.warning("No data found. Try another symbol.")
            st.stop()

        df = calculate_indicators(df)
        signal = generate_signal(df)

        st.subheader(f"📊 Signals for {symbol}")
        st.write(f"**RSI Signal:** {signal['RSI']}")
        st.write(f"**MACD Signal:** {signal['MACD']}")
        st.write(f"**EMA Signal:** {signal['EMA']}")
        st.write(f"**Bollinger Bands Signal:** {signal['BB']}")
        st.markdown(f"### 🧠 Final Signal: {signal['Combined']}")

if __name__ == "__main__":
    main()
