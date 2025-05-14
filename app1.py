# Enhanced crypto signal generator with trend filtering, confidence score, and better logic
import streamlit as st
import requests
import pandas as pd
import numpy as np

API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'

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
        'apikey': API_KEY,
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
            return df.sort_index()
        else:
            st.warning(f"⚠️ Error fetching {symbol} from TwelveData.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error fetching data: {e}")
        return pd.DataFrame()

def fetch_coin_price(symbol):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data[symbol]['usd'] if symbol in data else 0
    except:
        return 0

def calculate_indicators(df):
    df['close'] = df['close'].astype(float)
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    delta = df['close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14).mean()
    avg_loss = pd.Series(loss).rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['UpperBand'] = df['close'].rolling(window=20).mean() + 2 * df['close'].rolling(window=20).std()
    df['LowerBand'] = df['close'].rolling(window=20).mean() - 2 * df['close'].rolling(window=20).std()
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def generate_signal(df):
    latest = df.iloc[-1]
    confidence = 0
    details = []

    if latest['RSI'] < 30:
        confidence += 1
        details.append("🟢 RSI indicates **Oversold** (Buy)")
    elif latest['RSI'] > 70:
        confidence -= 1
        details.append("🔴 RSI indicates **Overbought** (Sell)")
    else:
        details.append("⚪ RSI is Neutral")

    if latest['MACD'] > latest['MACD_signal']:
        confidence += 1
        details.append("🟢 MACD shows **Bullish momentum**")
    else:
        confidence -= 1
        details.append("🔴 MACD shows **Bearish momentum**")

    if latest['EMA9'] > latest['EMA21']:
        confidence += 1
        details.append("🟢 Short-term trend is **Bullish** (EMA9 > EMA21)")
    else:
        confidence -= 1
        details.append("🔴 Short-term trend is **Bearish** (EMA9 < EMA21)")

    if latest['close'] < latest['LowerBand']:
        confidence += 1
        details.append("🟢 Price is below Bollinger Band ⇒ **Oversold**")
    elif latest['close'] > latest['UpperBand']:
        confidence -= 1
        details.append("🔴 Price is above Bollinger Band ⇒ **Overbought**")
    else:
        details.append("⚪ Price within Bollinger Bands")

    if latest['close'] > latest['EMA200']:
        confidence += 1
        details.append("🟢 Above EMA200 ⇒ **Uptrend**")
    else:
        confidence -= 1
        details.append("🔴 Below EMA200 ⇒ **Downtrend**")

    signal = "✅ STRONG BUY" if confidence >= 3 else "⚠️ CAUTION" if -2 <= confidence < 3 else "❌ STRONG SELL"

    return {
        'confidence': confidence,
        'details': details,
        'signal': signal,
        'entry': latest['close']
    }

@st.cache_data(ttl=120)
def fetch_top_coins(limit=25):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': limit,
        'page': 1,
        'sparkline': 'false'
    }
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        coins = res.json()
        extra = [
            {'symbol': 'official-trump', 'current_price': fetch_coin_price('official-trump'), 'name': 'Trump Coin'},
            {'symbol': 'zerebro', 'current_price': fetch_coin_price('zerebro'), 'name': 'Zerebro Coin'}
        ]
        return coins + extra
    except:
        return []

def main():
    st.set_page_config(page_title="Crypto Signal Generator", layout="wide")
    st.title("📈 AI-Powered Crypto Signal Generator")
    st.markdown("Get **smart signals** based on technical indicators and trend filters.")

    if not is_connected():
        st.error("❌ No Internet connection.")
        return

    if st.button("🔄 Refresh Coins"):
        st.rerun()

    coins = fetch_top_coins()
    if not coins:
        st.warning("⚠️ Failed to load coins.")
        return

    options = [f"{c['name']} ({c['symbol'].upper()}) - ${c['current_price']}" for c in coins]
    choice = st.selectbox("Select a coin:", options)
    selected = coins[options.index(choice)]
    symbol = selected['symbol'].upper() + "/USD"

    df = fetch_data(symbol)
    if df.empty:
        st.warning(f"⚠️ No historical data for {symbol}. Showing price only.")
        st.write(f"**Current Price:** ${selected['current_price']}")
        return

    df = calculate_indicators(df)
    signal = generate_signal(df)

    st.subheader(f"🔍 Signal for {symbol}")
    st.write(f"**Confidence Score:** `{signal['confidence']}`")
    st.write(f"**Final Signal:** {signal['signal']}")
    st.write(f"**Entry Point:** `${signal['entry']:.4f}`")
    st.markdown("---")
    st.markdown("### 📊 Signal Details")
    for d in signal['details']:
        st.write(d)

if __name__ == "__main__":
    main()
