import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objs as go

# ---------------------- CONFIG ----------------------
TWELVE_API_KEY = "6cbc54ad9e114dbea0ff7d8a7228188b"

# ---------------------- UTILITIES ----------------------
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
        'sparkline': 'false'
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()

        extra_ids = ['official-trump', 'zerebro']
        for coin_id in extra_ids:
            if not any(c['id'] == coin_id for c in data):
                coin_data = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}").json()
                market = coin_data.get("market_data", {})
                price = market.get('current_price', {}).get('usd', 0)
                if price:
                    data.append({
                        'id': coin_id,
                        'symbol': coin_data.get('symbol', '').upper(),
                        'name': coin_data.get('name', coin_id),
                        'current_price': price
                    })
        return data
    except:
        return []

def fetch_realtime_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        return requests.get(url).json().get(coin_id, {}).get('usd', 0)
    except:
        return 0

def fetch_twelvedata(symbol, interval="1h", limit=100):
    try:
        url = f"https://api.twelvedata.com/time_series"
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": limit,
            "apikey": TWELVE_API_KEY
        }
        data = requests.get(url, params=params).json()
        if "values" not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data['values'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.sort_index(inplace=True)
        return df
    except:
        return pd.DataFrame()

def calculate_indicators(df):
    df['EMA9'] = df['close'].ewm(span=9).mean()
    df['EMA21'] = df['close'].ewm(span=21).mean()
    df['EMA200'] = df['close'].ewm(span=200).mean()

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['MACD'] = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
    df['MACD_signal'] = df['MACD'].ewm(span=9).mean()

    df['UpperBand'] = df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std()
    df['LowerBand'] = df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std()

    return df

def generate_signal(df):
    latest = df.iloc[-1]
    score = 0
    rsi_score = 1 if latest['RSI'] < 30 else (-1 if latest['RSI'] > 70 else 0)
    macd_score = 1 if latest['MACD'] > latest['MACD_signal'] else -1
    ema_score = 1 if latest['EMA9'] > latest['EMA21'] else -1
    bb_score = 1 if latest['close'] < latest['LowerBand'] else (-1 if latest['close'] > latest['UpperBand'] else 0)
    trend_score = 1 if latest['close'] > latest['EMA200'] else -1

    score = rsi_score + macd_score + ema_score + bb_score + trend_score
    confidence = int(((score + 5) / 10) * 100)

    if confidence >= 70:
        final = "✅ Strong Buy" if score > 0 else "❌ Strong Sell"
    elif confidence >= 40:
        final = "⚠️ Neutral"
    else:
        final = "❌ Strong Sell" if score < 0 else "✅ Strong Buy"

    return {
        'rsi': latest['RSI'],
        'macd': latest['MACD'],
        'macd_signal': latest['MACD_signal'],
        'ema9': latest['EMA9'],
        'ema21': latest['EMA21'],
        'bb_upper': latest['UpperBand'],
        'bb_lower': latest['LowerBand'],
        'price': latest['close'],
        'trend': 'Uptrend' if latest['close'] > latest['EMA200'] else 'Downtrend',
        'confidence': confidence,
        'final': final
    }

def soft_signal(price):
    return {
        'rsi': '-',
        'macd': '-',
        'macd_signal': '-',
        'ema9': '-',
        'ema21': '-',
        'bb_upper': '-',
        'bb_lower': '-',
        'price': price,
        'trend': '-',
        'confidence': 50,
        'final': "⚠️ Estimated Neutral (Fallback)"
    }

def plot_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name='Candlestick'))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], line=dict(color='orange'), name='EMA9'))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA21'], line=dict(color='blue'), name='EMA21'))
    fig.update_layout(title='Price Chart', xaxis_title='Date', yaxis_title='Price')
    return fig

# ---------------------- MAIN APP ----------------------
st.set_page_config(page_title="Crypto Signal Generator", layout="centered")

def main():
    st.title("📈 Crypto Signal Generator with Candle Data")

    if not is_connected():
        st.error("❌ No internet connection.")
        return

    coins = fetch_top_coins()
    options = [f"{c['symbol'].upper()} - {c['name']} (${c['current_price']})" for c in coins]
    selected = st.selectbox("Select a Coin", options)
    selected_coin = next(c for c in coins if c['symbol'].upper() in selected)

    twelved_symbol = st.text_input("Enter symbol in TwelveData format (e.g., BTC/USD):", f"{selected_coin['symbol'].upper()}/USD")
    timeframe = st.selectbox("Select Timeframe", ['15min', '1h', '4h', '1day'])

    df = fetch_twelvedata(twelved_symbol, interval=timeframe)

    if not df.empty:
        st.success(f"TwelveData available for {twelved_symbol}")
        df = calculate_indicators(df)
        signal = generate_signal(df)
        st.plotly_chart(plot_chart(df))
    else:
        st.warning("No candle data found on TwelveData, using fallback")
        price = fetch_realtime_price(selected_coin['id'])
        signal = soft_signal(price)

    st.subheader("📋 Signal Summary")
    st.write(f"**Final Signal:** {signal['final']}")
    st.write(f"**Confidence:** {signal['confidence']}%")
    st.write(f"**Price:** ${round(signal['price'], 4)}")
    if signal['rsi'] != '-':
        st.write(f"**RSI:** {round(signal['rsi'], 2)}")
        st.write(f"**MACD:** {round(signal['macd'], 4)} vs Signal {round(signal['macd_signal'], 4)}")
        st.write(f"**EMA9 vs EMA21:** {round(signal['ema9'], 4)} / {round(signal['ema21'], 4)}")
        st.write(f"**Bollinger Bands:** {round(signal['bb_lower'], 4)} - {round(signal['bb_upper'], 4)}")
        st.write(f"**Trend:** {signal['trend']}")

if __name__ == "__main__":
    main()
