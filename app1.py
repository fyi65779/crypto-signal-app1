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
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 50,
            'page': 1,
            'sparkline': 'false'
        }
        response = requests.get(url, params=params)
        data = response.json()

        # Include meme coins if missing
        extra_ids = ['official-trump', 'zerebro']
        for coin_id in extra_ids:
            if coin_id not in [coin['id'] for coin in data]:
                coin_data = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}").json()
                market_data = coin_data.get("market_data", {})
                data.append({
                    'id': coin_id,
                    'symbol': coin_data.get('symbol', '').upper(),
                    'name': coin_data.get('name', ''),
                    'current_price': market_data.get('current_price', {}).get('usd', 0)
                })

        return data
    except Exception as e:
        st.error(f"Error fetching top coins: {e}")
        return []


def fetch_realtime_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(url).json()
        return response[coin_id]['usd'] if coin_id in response else 0
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
        response = requests.get(url, params=params)
        data = response.json()
        if "values" not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data['values'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        df = df.astype(float)
        df.sort_index(inplace=True)
        return df
    except:
        return pd.DataFrame()


def calculate_indicators(df):
    df['EMA9'] = df['close'].ewm(span=9).mean()
    df['EMA21'] = df['close'].ewm(span=21).mean()
    df['EMA200'] = df['close'].ewm(span=200).mean()

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
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

    # RSI
    if latest['RSI'] < 30:
        rsi = "Buy (Oversold)"; score += 1
    elif latest['RSI'] > 70:
        rsi = "Sell (Overbought)"; score -= 1
    else:
        rsi = "Neutral"

    # MACD
    if latest['MACD'] > latest['MACD_signal']:
        macd = "Bullish"; score += 1
    else:
        macd = "Bearish"; score -= 1

    # EMA
    if latest['EMA9'] > latest['EMA21']:
        ema = "Bullish EMA"; score += 1
    else:
        ema = "Bearish EMA"; score -= 1

    # Bollinger
    if latest['close'] < latest['LowerBand']:
        bb = "Buy (Low Band)"; score += 1
    elif latest['close'] > latest['UpperBand']:
        bb = "Sell (High Band)"; score -= 1
    else:
        bb = "Neutral"

    # Trend
    trend = "Uptrend" if latest['close'] > latest['EMA200'] else "Downtrend"
    score += 1 if trend == "Uptrend" else -1

    # Final
    if score >= 3:
        signal = "✅ Strong Buy"
    elif score <= -3:
        signal = "❌ Strong Sell"
    else:
        signal = "⚠️ Neutral"

    return {
        'rsi': rsi,
        'macd': macd,
        'ema': ema,
        'bollinger': bb,
        'trend': trend,
        'confidence': score,
        'final': signal,
        'entry': latest['close']
    }


def plot_chart(df, coin_name):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Candlestick'))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], line=dict(color='orange'), name='EMA9'))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA21'], line=dict(color='blue'), name='EMA21'))
    fig.update_layout(title=f'{coin_name} Price Chart', xaxis_title='Date', yaxis_title='Price', height=500)
    return fig

# ---------------------- MAIN APP ----------------------
st.set_page_config(page_title="Crypto Signal Generator", layout="centered")

def main():
    st.title("📊 Crypto Signal Generator")

    if not is_connected():
        st.error("❌ No internet connection.")
        return

    coins = fetch_top_coins()
    if not coins:
        st.warning("⚠️ Unable to fetch coins.")
        return

    options = [f"{coin['symbol'].upper()} ({coin['id']}) - ${coin['current_price']}" for coin in coins]
    selected_option = st.selectbox("Select Coin:", options)
    selected_id = selected_option.split("(")[1].split(")")[0]
    selected_coin = next(coin for coin in coins if coin['id'] == selected_id)

    symbol = selected_coin['symbol'].upper() + "/USD" if selected_id not in ['official-trump', 'zerebro'] else None

    timeframe = st.selectbox("Select Timeframe:", ['15min', '1h', '4h', '1day'])
    df = fetch_twelvedata(symbol, interval=timeframe) if symbol else pd.DataFrame()

    if df.empty:
        st.warning(f"⚠️ No historical data for {selected_coin['name']}. Showing real-time price only.")
        price = fetch_realtime_price(selected_id)
        if price:
            st.write(f"🔹 Price: ${price}")
        else:
            st.error("❌ Price not available.")
        return

    df = calculate_indicators(df)
    signal = generate_signal(df)
    chart = plot_chart(df, selected_coin['name'])

    st.plotly_chart(chart)
    st.subheader("📋 Signal Summary")
    st.write(f"**RSI**: {signal['rsi']}")
    st.write(f"**MACD**: {signal['macd']}")
    st.write(f"**EMA Crossover**: {signal['ema']}")
    st.write(f"**Bollinger Bands**: {signal['bollinger']}")
    st.write(f"**Trend**: {signal['trend']}")
    st.write(f"**Confidence Score**: {signal['confidence']} / 5")
    st.write(f"**Final Signal**: {signal['final']}")
    st.write(f"**Entry Price**: ${round(signal['entry'], 4)}")

if __name__ == "__main__":
    main()
