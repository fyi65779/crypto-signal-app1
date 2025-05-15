import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import datetime

TWELVE_API_KEY = "6cbc54ad9e114dbea0ff7d8a7228188b"

# -------- Helper functions -----------

@st.cache_data(ttl=600)
def fetch_coingecko_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 50,
        "page": 1,
        "sparkline": "false"
    }
    r = requests.get(url, params=params)
    data = r.json()
    # Add meme coins manually if missing
    meme_coins = ['official-trump', 'zerebro']
    for mc in meme_coins:
        if not any(c['id'] == mc for c in data):
            try:
                mc_data = requests.get(f"https://api.coingecko.com/api/v3/coins/{mc}").json()
                price = mc_data.get("market_data", {}).get("current_price", {}).get("usd", None)
                if price:
                    data.append({
                        "id": mc,
                        "symbol": mc_data["symbol"],
                        "name": mc_data["name"],
                        "current_price": price
                    })
            except:
                pass
    return data

def check_twelvedata_symbol(coin_symbol):
    # TwelveData crypto symbols = e.g. BTC/USD, ETH/USD
    # We'll test if symbol/USD exists on TwelveData by calling time_series API with limit=1
    symbol = coin_symbol.upper() + "/USD"
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": "1day",
        "outputsize": 1,
        "apikey": TWELVE_API_KEY
    }
    r = requests.get(url, params=params).json()
    if "status" in r and r["status"] == "error":
        return None
    if "values" in r:
        return symbol
    return None

@st.cache_data(ttl=300)
def fetch_candle_data(symbol, interval="1h", outputsize=100):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": TWELVE_API_KEY
    }
    r = requests.get(url, params=params).json()
    if "values" not in r:
        return pd.DataFrame()
    df = pd.DataFrame(r["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)
    # convert columns to float
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.sort_index(inplace=True)
    return df

# -------- Technical Indicators -----------

def calculate_indicators(df):
    # EMA
    df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
    # MACD
    df['macd'] = df['ema12'] - df['ema26']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    # RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    # Bollinger Bands
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['std20'] = df['close'].rolling(window=20).std()
    df['upper_band'] = df['ma20'] + (df['std20'] * 2)
    df['lower_band'] = df['ma20'] - (df['std20'] * 2)
    return df

def generate_signal(df):
    # Use last row for signal generation
    last = df.iloc[-1]
    prev = df.iloc[-2]

    signals = []

    # EMA crossover
    if last['ema12'] > last['ema26'] and prev['ema12'] <= prev['ema26']:
        signals.append("buy")
    elif last['ema12'] < last['ema26'] and prev['ema12'] >= prev['ema26']:
        signals.append("sell")

    # MACD crossover
    if last['macd'] > last['signal'] and prev['macd'] <= prev['signal']:
        signals.append("buy")
    elif last['macd'] < last['signal'] and prev['macd'] >= prev['signal']:
        signals.append("sell")

    # RSI overbought/oversold
    if last['rsi'] < 30:
        signals.append("buy")
    elif last['rsi'] > 70:
        signals.append("sell")

    # Bollinger bands touch
    if last['close'] < last['lower_band']:
        signals.append("buy")
    elif last['close'] > last['upper_band']:
        signals.append("sell")

    # Majority voting
    buy_signals = signals.count("buy")
    sell_signals = signals.count("sell")

    if buy_signals > sell_signals:
        final_signal = "BUY"
    elif sell_signals > buy_signals:
        final_signal = "SELL"
    else:
        final_signal = "HOLD"

    confidence = max(buy_signals, sell_signals) / 4  # max 4 signals checked

    # Entry price for BUY is last close, for SELL also last close
    entry_price = last['close']

    return {
        "final": final_signal,
        "confidence": round(confidence * 100, 2),
        "entry": entry_price,
        "rsi": round(last['rsi'], 2),
        "macd": round(last['macd'], 4),
        "ema12": round(last['ema12'], 4),
        "ema26": round(last['ema26'], 4),
        "bollinger_upper": round(last['upper_band'], 4),
        "bollinger_lower": round(last['lower_band'], 4),
    }

# -------- Plotting Chart ------------

def plot_candlestick(df, coin_name):
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=coin_name
    )])
    fig.update_layout(
        title=f"{coin_name} Candlestick Chart",
        xaxis_rangeslider_visible=False,
        template='plotly_dark'
    )
    return fig

# -------- Main App -----------

def main():
    st.title("📈 Crypto Signal Generator with Candle Data")

    # 1. Fetch coins from CoinGecko
    coins = fetch_coingecko_coins()
    coin_options = [f"{c['symbol'].upper()} - {c['name']}" for c in coins]
    selected = st.selectbox("Select a Coin", coin_options)
    selected_coin = coins[coin_options.index(selected)]

    # Show current price from CoinGecko
    st.markdown(f"### Current Price: ${selected_coin['current_price']}")

    # 2. Check if TwelveData has candle data for this coin
    td_symbol = check_twelvedata_symbol(selected_coin['symbol'])
    if td_symbol:
        st.success(f"This coin is available on TwelveData as `{td_symbol}`")
        # 3. Fetch candle data and show chart + signals
        interval = st.selectbox("Select Timeframe", ["15min", "1h", "4h", "1day"], index=1)
        df = fetch_candle_data(td_symbol, interval=interval)
        if df.empty:
            st.warning("No candle data found for this coin/timeframe.")
        else:
            df = calculate_indicators(df)
            fig = plot_candlestick(df, selected_coin['name'])
            st.plotly_chart(fig, use_container_width=True)
            signal = generate_signal(df)
            st.markdown("### 🔔 Signal Summary")
            st.write(f"**Final Signal:** {signal['final']}")
            st.write(f"**Confidence:** {signal['confidence']}%")
            st.write(f"**Entry Price:** ${signal['entry']:.4f}")
            st.write(f"**RSI:** {signal['rsi']}")
            st.write(f"**MACD:** {signal['macd']}")
            st.write(f"**EMA12:** {signal['ema12']}")
            st.write(f"**EMA26:** {signal['ema26']}")
            st.write(f"**Bollinger Bands:** Upper {signal['bollinger_upper']}, Lower {signal['bollinger_lower']}")
    else:
        st.info("This coin is NOT available on TwelveData for candle data.")
        st.info("Showing only current price from CoinGecko.")

if __name__ == "__main__":
    main()
