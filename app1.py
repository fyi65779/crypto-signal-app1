import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- API KEY ---
TWELVE_API_KEY = "6cbc54ad9e114dbea0ff7d8a7228188b"

# --- Connectivity Check ---
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

# --- Fetch Historical Data ---
def fetch_data(symbol, interval='1h', limit=100):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "apikey": TWELVE_API_KEY,
        "limit": limit
    }
    try:
        r = requests.get(url, params=params).json()
        if "values" not in r:
            return pd.DataFrame()
        df = pd.DataFrame(r["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        df = df.astype(float)
        return df.sort_index()
    except:
        return pd.DataFrame()

# --- Fallback Real-time Price from CoinGecko ---
def fetch_price_coingecko(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        r = requests.get(url).json()
        return r[coin_id]['usd'] if coin_id in r else 0
    except:
        return 0

# --- Calculate Indicators ---
def calculate_indicators(df):
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['UpperBand'] = df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std()
    df['LowerBand'] = df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std()
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
    if latest['close'] < latest['LowerBand']:
        score += 1
    elif latest['close'] > latest['UpperBand']:
        score -= 1
    if latest['close'] > latest['EMA200']:
        score += 1
    else:
        score -= 1

    if score >= 3:
        final = '✅ Strong Buy'
    elif score <= -3:
        final = '❌ Strong Sell'
    else:
        final = '⚠️ Neutral'

    confidence = round(abs(score) / 5 * 100, 1)

    return final, confidence, latest['close']

# --- Plot Chart ---
def plot_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df['open'],
                                 high=df['high'],
                                 low=df['low'],
                                 close=df['close'],
                                 name='Candles'))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], mode='lines', name='EMA9'))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA21'], mode='lines', name='EMA21'))
    fig.update_layout(title="Candlestick Chart with EMAs", xaxis_title="Date", yaxis_title="Price")
    return fig

# --- Get Top Coins ---
@st.cache_data(ttl=300)
def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 50,
        "page": 1
    }
    coins = requests.get(url, params=params).json()
    extra_ids = ['official-trump', 'zerebro']
    for eid in extra_ids:
        price = fetch_price_coingecko(eid)
        if price:
            coins.append({"id": eid, "symbol": eid, "name": eid.title().replace('-', ' '), "current_price": price})
    return coins

# --- Streamlit App ---
def main():
    st.set_page_config(page_title="Crypto Signal Generator", layout="centered")
    st.title("📊 Crypto Signal Generator")

    if not is_connected():
        st.error("No internet connection.")
        return

    coins = get_top_coins()
    options = [f"{c['name']} ({c['symbol'].upper()}) - ${c['current_price']}" for c in coins]
    selected = st.selectbox("Select Coin:", options)

    selected_coin = coins[options.index(selected)]
    coin_symbol = selected_coin['symbol'].upper()
    coin_id = selected_coin['id']

    st.write(f"Fetching data for **{selected_coin['name']}**")

    symbol = None if coin_id in ['official-trump', 'zerebro'] else coin_symbol + "/USD"

    timeframe = st.selectbox("Select Timeframe:", ["1h", "4h", "1day"])
    df = fetch_data(symbol, interval=timeframe) if symbol else pd.DataFrame()

    if df.empty:
        st.warning("No historical data found. Using CoinGecko price only.")
        price = fetch_price_coingecko(coin_id)
        if price:
            st.success(f"Price: ${price}")
        else:
            st.error("CoinGecko also failed.")
        return

    df = calculate_indicators(df)

    fig = plot_chart(df)
    st.plotly_chart(fig)

    signal, confidence, entry = generate_signal(df)
    st.subheader("📈 Signal")
    st.write(f"**Recommendation:** {signal}")
    st.write(f"**Confidence:** {confidence}%")
    st.write(f"**Entry Point:** ${round(entry, 4)}")

if __name__ == '__main__':
    main()
