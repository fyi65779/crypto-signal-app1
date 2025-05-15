import streamlit as st
import requests
import pandas as pd
import numpy as np

# --- API Key ---
TWELVE_API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'  # Replace with your TwelveData API Key

# --- Check Internet Connection ---
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

# --- Fetch Top 50 Coins ---
@st.cache_data(ttl=300)
def fetch_top_50_coins():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 50,
            'page': 1,
            'sparkline': False
        }
        coins = requests.get(url, params=params).json()
        extra_ids = ['official-trump', 'zerebro']
        for coin_id in extra_ids:
            coin_data = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}").json()
            coins.append({
                'id': coin_data['id'],
                'symbol': coin_data['symbol'],
                'name': coin_data['name'],
                'current_price': coin_data['market_data']['current_price']['usd']
            })
        return coins
    except:
        return []

# --- Streamlit App ---
def main():
    st.set_page_config(page_title="Crypto Signal Generator", layout="centered")
    st.title("📊 Crypto Signal Generator")
    st.markdown("🔍 **Trading Signals for Top 50 Coins**")

    if not is_connected():
        st.error("❌ No internet connection.")
        return

    coins = fetch_top_50_coins()
    if not coins:
        st.warning("⚠️ Failed to fetch coin list.")
        return

    coin_names = [f"{c['symbol'].upper()} - {c['name']}" for c in coins]
    selected_name = st.selectbox("Select a coin:", coin_names)
    selected_coin = coins[coin_names.index(selected_name)]

    coin_id = selected_coin['id']
    coin_symbol = selected_coin['symbol'].upper()
    coin_name = selected_coin['name']

    st.write(f"🪙 **{coin_name} ({coin_symbol})**")

    symbol = f"{coin_symbol}/USD"
    df = fetch_data(symbol)

    if df.empty:
        price = fetch_coin_price(coin_id)
        if price > 0:
            st.success(f"📈 Real-time price: ${price}")
            st.info("ℹ️ Signal not generated (TwelveData does not support this coin).")
        else:
            st.error("❌ Failed to fetch price.")
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
