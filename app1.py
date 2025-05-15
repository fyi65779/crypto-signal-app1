import streamlit as st
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime

# --- Utility: Internet Check ---
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# --- CoinGecko: Fetch Top 50 Coins + Meme Coins ---
@st.cache_data(ttl=300)
def fetch_coins():
    base_url = "https://api.coingecko.com/api/v3"
    try:
        market_resp = requests.get(f"{base_url}/coins/markets", params={
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 50,
            'page': 1,
            'sparkline': False
        })
        market_resp.raise_for_status()
        coins = market_resp.json()

        # Ensure TRUMP and ZEREBRO included
        for cid in ['official-trump', 'zerebro']:
            if not any(c['id'] == cid for c in coins):
                r = requests.get(f"{base_url}/coins/{cid}").json()
                coins.append({
                    'id': r['id'],
                    'symbol': r['symbol'],
                    'name': r['name'],
                    'current_price': r['market_data']['current_price']['usd']
                })
        return coins
    except:
        return []

# --- CoinGecko: Fetch Historical OHLC Data ---
def fetch_ohlc(coin_id, days):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    try:
        resp = requests.get(url, params={
            'vs_currency': 'usd',
            'days': days
        })
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except:
        return pd.DataFrame()

# --- Technical Indicators ---
def add_indicators(df):
    df['EMA12'] = df['close'].ewm(span=12).mean()
    df['EMA26'] = df['close'].ewm(span=26).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9).mean()
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# --- Signal Generation ---
def generate_signal(df):
    latest = df.iloc[-1]
    score = 0

    # RSI
    rsi = latest['RSI']
    if rsi < 30:
        rsi_signal = "✅ Buy (RSI < 30)"
        score += 1
    elif rsi > 70:
        rsi_signal = "❌ Sell (RSI > 70)"
        score -= 1
    else:
        rsi_signal = "⚠️ Neutral"

    # MACD
    if latest['MACD'] > latest['Signal']:
        macd_signal = "✅ Bullish"
        score += 1
    else:
        macd_signal = "❌ Bearish"
        score -= 1

    # EMA Trend
    trend = "📈 Uptrend" if latest['EMA12'] > latest['EMA26'] else "📉 Downtrend"
    score += 1 if trend == "📈 Uptrend" else -1

    final_signal = "✅ Strong Buy" if score >= 2 else "❌ Strong Sell" if score <= -2 else "⚠️ Caution"

    return {
        'RSI': round(rsi, 2),
        'RSI Signal': rsi_signal,
        'MACD Signal': macd_signal,
        'Trend': trend,
        'Final Signal': final_signal,
        'Score': score,
        'Entry Price': round(latest['close'], 4)
    }

# --- Chart Rendering ---
def plot_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df['open'], high=df['high'],
                                 low=df['low'], close=df['close'],
                                 name='Price'))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA12'], line=dict(color='blue'), name='EMA12'))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA26'], line=dict(color='red'), name='EMA26'))
    fig.update_layout(title='Candlestick Chart with EMA', xaxis_title='Time', yaxis_title='Price')
    return fig

# --- Streamlit App ---
def main():
    st.set_page_config(page_title="Crypto Signal Generator", layout="wide")
    st.title("📊 Crypto Signal Generator")
    st.markdown("Get real-time signals with live chart & indicators")

    if not is_connected():
        st.error("❌ No internet connection.")
        return

    coins = fetch_coins()
    if not coins:
        st.warning("⚠️ Failed to load coins.")
        return

    selected = st.selectbox("Select Coin:", [f"{c['symbol'].upper()} ({c['id']}) - ${c['current_price']}" for c in coins])
    coin_id = selected.split('(')[-1].split(')')[0].strip()

    timeframe = st.selectbox("Select Timeframe:", ['1', '7', '30'], format_func=lambda x: {'1': '1 Day', '7': '1 Week', '30': '1 Month'}[x])
    df = fetch_ohlc(coin_id, days=timeframe)

    if df.empty:
        st.warning(f"⚠️ No historical data for {coin_id}")
        return

    df = add_indicators(df)
    signal = generate_signal(df)

    st.subheader(f"📈 Signal for {coin_id.upper()}")
    st.write(f"**Direction:** {signal['Trend']}")
    st.write(f"**MACD:** {signal['MACD Signal']}")
    st.write(f"**RSI:** {signal['RSI']} ({signal['RSI Signal']})")
    st.write(f"**Entry Price:** ${signal['Entry Price']}")
    st.write(f"**Signal Score:** {signal['Score']}")
    st.success(f"**Final Signal:** {signal['Final Signal']}")

    st.plotly_chart(plot_chart(df), use_container_width=True)

if __name__ == "__main__":
    main()
