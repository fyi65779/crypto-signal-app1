import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- API Keys ---
TWELVE_API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'

# --- Check Internet ---
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# --- Fetch Historical Data ---
def fetch_data(symbol, interval='1h', limit=200):
    url = f"https://api.twelvedata.com/time_series"
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': TWELVE_API_KEY,
        'limit': limit,
        'outputsize': 'full'
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if "values" in data:
            df = pd.DataFrame(data['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df = df.astype(float).sort_index()
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- Fetch Real-time Price ---
def fetch_coin_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        res = requests.get(url).json()
        return res[coin_id]['usd'] if coin_id in res else 0
    except:
        return 0

# --- Calculate Indicators ---
def calculate_indicators(df):
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (df['close'].diff() > 0).rolling(14).mean() / (df['close'].diff() < 0).rolling(14).mean()))
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

# --- Generate Signal ---
def generate_signal(df):
    latest = df.iloc[-1]
    score = 0

    if latest['RSI'] < 30:
        score += 1
    elif latest['RSI'] > 70:
        score -= 1

    if latest['MACD'] > latest['MACD_signal']:
        score += 1
    else:
        score -= 1

    if latest['EMA9'] > latest['EMA21']:
        score += 1
    else:
        score -= 1

    if latest['close'] > latest['EMA200']:
        score += 1
    else:
        score -= 1

    confidence = (score + 4) / 8 * 100
    final_signal = '✅ Strong Buy' if score >= 3 else '❌ Strong Sell' if score <= -3 else '⚠️ Neutral'

    return {
        'Score': score,
        'Confidence': round(confidence, 2),
        'Final': final_signal,
        'Entry': round(latest['close'], 4)
    }

# --- Plot Candlestick Chart ---
def plot_chart(df):
    fig = go.Figure(data=[
        go.Candlestick(x=df.index,
                       open=df['open'],
                       high=df['high'],
                       low=df['low'],
                       close=df['close'],
                       name='Candles'),
        go.Scatter(x=df.index, y=df['EMA9'], mode='lines', name='EMA9'),
        go.Scatter(x=df.index, y=df['EMA21'], mode='lines', name='EMA21'),
        go.Scatter(x=df.index, y=df['EMA200'], mode='lines', name='EMA200')
    ])
    fig.update_layout(title='Candlestick Chart', xaxis_title='Time', yaxis_title='Price')
    return fig

# --- Streamlit App ---
def main():
    st.set_page_config(page_title="Crypto Signal Generator", layout="wide")
    st.title("📊 Crypto Signal Generator with Charts & Confidence Score")

    if not is_connected():
        st.error("❌ Internet connection not available.")
        return

    coin_id = st.text_input("Enter CoinGecko Coin ID (e.g. bitcoin, official-trump, zerebro):", value='bitcoin')
    timeframe = st.selectbox("Select Timeframe:", ['5min', '15min', '1h', '4h', '1day'])

    symbol = coin_id.upper() + "/USD"
    df = fetch_data(symbol, interval=timeframe)

    if df.empty:
        st.warning(f"⚠️ No data found for {symbol} on TwelveData. Trying CoinGecko price only...")
        price = fetch_coin_price(coin_id)
        if price:
            st.info(f"🔹 Real-time price: ${price}")
        else:
            st.error("❌ CoinGecko price also not found.")
        return

    df = calculate_indicators(df)
    signal = generate_signal(df)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("📈 Entry Price", f"${signal['Entry']}")
        st.metric("🔍 Confidence", f"{signal['Confidence']}%")
    with col2:
        st.metric("📊 Signal", signal['Final'])

    st.plotly_chart(plot_chart(df), use_container_width=True)

if __name__ == '__main__':
    main()
