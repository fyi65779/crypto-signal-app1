import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# --- API Keys ---
TWELVE_API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'  # Replace with your TwelveData API key

# --- Check Internet ---
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# --- Fetch Historical Data ---
def fetch_data(symbol, interval='1h', limit=100):
    url = f"https://api.twelvedata.com/time_series"
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': TWELVE_API_KEY,
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
    delta = df['close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    avg_gain = up.rolling(window=14).mean()
    avg_loss = down.rolling(window=14).mean()
    rs = avg_gain / avg_loss
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

    rsi = latest['RSI']
    if rsi < 30:
        rsi_sig = 'Buy (RSI Oversold)'
        score += 1
    elif rsi > 70:
        rsi_sig = 'Sell (RSI Overbought)'
        score -= 1
    else:
        rsi_sig = 'Neutral'

    macd = latest['MACD']
    macd_sig = latest['MACD_signal']
    if macd > macd_sig:
        macd_result = 'Bullish (MACD > Signal)'
        score += 1
    else:
        macd_result = 'Bearish (MACD < Signal)'
        score -= 1

    if latest['EMA9'] > latest['EMA21']:
        ema_result = 'Bullish (EMA9 > EMA21)'
        score += 1
    else:
        ema_result = 'Bearish (EMA9 < EMA21)'
        score -= 1

    if latest['close'] < latest['LowerBand']:
        bb_result = 'Buy (Below Lower Band)'
        score += 1
    elif latest['close'] > latest['UpperBand']:
        bb_result = 'Sell (Above Upper Band)'
        score -= 1
    else:
        bb_result = 'Neutral'

    if latest['close'] > latest['EMA200']:
        trend = 'Uptrend'
        score += 1
    else:
        trend = 'Downtrend'
        score -= 1

    if score >= 3:
        final = '✅ Strong Buy'
    elif score <= -3:
        final = '❌ Strong Sell'
    else:
        final = '⚠️ Neutral / Caution'

    return {
        'RSI': rsi_sig,
        'MACD': macd_result,
        'EMA': ema_result,
        'Bollinger': bb_result,
        'Trend': trend,
        'Score': score,
        'Final': final,
        'Entry': latest['close']
    }

# --- Get Top Coins ---
@st.cache_data(ttl=300)
def fetch_top_coins(limit=30):
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        full_list = requests.get(url).json()
        ids_to_include = ['bitcoin', 'ethereum', 'binancecoin', 'ripple', 'cardano', 'dogecoin', 'solana', 'tron', 'polkadot', 'litecoin', 'official-trump', 'zerebro']
        top_coins = []
        for coin in full_list:
            if coin['id'] in ids_to_include:
                price = fetch_coin_price(coin['id'])
                top_coins.append({
                    'id': coin['id'],
                    'symbol': coin['symbol'],
                    'name': coin['name'],
                    'current_price': price
                })
        return top_coins
    except:
        return []

# --- Streamlit App ---
def main():
    st.set_page_config(page_title="Crypto Signal Generator", layout="centered")
    st.title("📊 Crypto Signal Generator")

    if not is_connected():
        st.error("❌ Internet not available. Please check connection.")
        return

    coins = fetch_top_coins()
    if not coins:
        st.warning("⚠️ Could not load coins from CoinGecko.")
        return

    coin_choice = st.selectbox("📥 Select a coin:", [f"{c['symbol'].upper()} - ${c['current_price']}" for c in coins])
    selected = coins[[f"{c['symbol'].upper()} - ${c['current_price']}" for c in coins].index(coin_choice)]

    unsupported_symbols = ['official-trump', 'zerebro']
    coin_id = selected['id']
    symbol = None if coin_id in unsupported_symbols else selected['symbol'].upper() + "/USD"

    df = fetch_data(symbol) if symbol else pd.DataFrame()

    if df.empty:
        st.warning(f"⚠️ No data for {selected['symbol'].upper()} from TwelveData.")
        price = fetch_coin_price(coin_id)
        if price > 0:
            st.success(f"📡 Real-time price: ${price}")
            st.info("⚠️ Only real-time data available. No signal generated.")
        else:
            st.error("❌ Coin price not available from CoinGecko.")
        return

    df = calculate_indicators(df)
    signal = generate_signal(df)

    st.subheader(f"📈 Signal for {selected['name']} ({selected['symbol'].upper()})")
    st.write(f"**RSI:** {signal['RSI']}")
    st.write(f"**MACD:** {signal['MACD']}")
    st.write(f"**EMA Crossover:** {signal['EMA']}")
    st.write(f"**Bollinger Bands:** {signal['Bollinger']}")
    st.write(f"**Trend (EMA200):** {signal['Trend']}")
    st.write(f"**Confidence Score:** {signal['Score']}")
    st.write(f"**Combined Signal:** {signal['Final']}")
    st.write(f"**Entry Point:** ${round(signal['Entry'], 4)}")

if __name__ == "__main__":
    main()
