import streamlit as st
import requests
import pandas as pd
import numpy as np

TWELVE_API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'  # Replace with your TwelveData API Key

def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

def fetch_data(symbol, interval='1h', limit=100):
    url = f"https://api.twelvedata.com/time_series"
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': TWELVE_API_KEY,
        'limit': limit
    }
    try:
        response = requests.get(url, params=params).json()
        if "values" in response:
            df = pd.DataFrame(response['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df = df.astype(float)
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def fetch_coin_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        res = requests.get(url).json()
        return res[coin_id]['usd'] if coin_id in res else 0
    except:
        return 0

def calculate_indicators(df):
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (df['close'].diff() > 0).rolling(14).mean() / (df['close'].diff() < 0).rolling(14).mean()))
    df['UpperBand'] = df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std()
    df['LowerBand'] = df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std()
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def generate_signal(df):
    latest = df.iloc[-1]
    score = 0

    # RSI
    rsi = latest['RSI']
    if rsi < 30:
        rsi_sig = 'Buy (RSI Oversold)'
        score += 1
    elif rsi > 70:
        rsi_sig = 'Sell (RSI Overbought)'
        score -= 1
    else:
        rsi_sig = 'Neutral'

    # MACD
    macd = latest['MACD']
    macd_sig = latest['MACD_signal']
    if macd > macd_sig:
        macd_result = 'Bullish (MACD > Signal)'
        score += 1
    else:
        macd_result = 'Bearish (MACD < Signal)'
        score -= 1

    # EMA crossover
    if latest['EMA9'] > latest['EMA21']:
        ema_result = 'Bullish (EMA9 > EMA21)'
        score += 1
    else:
        ema_result = 'Bearish (EMA9 < EMA21)'
        score -= 1

    # Bollinger
    if latest['close'] < latest['LowerBand']:
        bb_result = 'Buy (Below Lower Band)'
        score += 1
    elif latest['close'] > latest['UpperBand']:
        bb_result = 'Sell (Above Upper Band)'
        score -= 1
    else:
        bb_result = 'Neutral'

    # Trend
    if latest['close'] > latest['EMA200']:
        trend = 'Uptrend'
        score += 1
    else:
        trend = 'Downtrend'
        score -= 1

    # Final Signal
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

@st.cache_data(ttl=300)
def fetch_all_coins():
    try:
        url = "https://api.coingecko.com/api/v3/coins/list"
        coins = requests.get(url).json()
        return sorted(coins, key=lambda x: x['symbol'])
    except:
        return []

def main():
    st.set_page_config(page_title="Crypto Signal Generator", layout="centered")
    st.title("📊 Crypto Signal Generator")
    st.markdown("🔍 **All coins supported via CoinGecko + TwelveData**")

    if not is_connected():
        st.error("❌ No internet connection.")
        return

    coin_list = fetch_all_coins()
    if not coin_list:
        st.warning("⚠️ Coin list not loaded.")
        return

    coin_names = [f"{c['symbol'].upper()} - {c['name']}" for c in coin_list]
    selected_name = st.selectbox("Select a coin:", coin_names)
    selected_coin = coin_list[coin_names.index(selected_name)]

    coin_id = selected_coin['id']
    coin_symbol = selected_coin['symbol'].upper()
    coin_name = selected_coin['name']

    st.write(f"🪙 **{coin_name} ({coin_symbol})**")

    symbol = f"{coin_symbol}/USD"
    df = fetch_data(symbol)

    if df.empty:
        price = fetch_coin_price(coin_id)
        if price > 0:
            st.success(f"📈 Real-time Price: ${price}")
            st.info("ℹ️ Signal generation not available (TwelveData does not support this coin).")
        else:
            st.error("❌ Could not fetch price.")
        return

    df = calculate_indicators(df)
    signal = generate_signal(df)

    st.subheader("📈 Signal Analysis")
    st.write(f"**RSI:** {signal['RSI']}")
    st.write(f"**MACD:** {signal['MACD']}")
    st.write(f"**EMA Crossover:** {signal['EMA']}")
    st.write(f"**Bollinger Bands:** {signal['Bollinger']}")
    st.write(f"**Trend:** {signal['Trend']}")
    st.write(f"**Score:** {signal['Score']}")
    st.write(f"**Signal:** {signal['Final']}")
    st.write(f"**Entry Point:** ${round(signal['Entry'], 4)}")

if __name__ == "__main__":
    main()
