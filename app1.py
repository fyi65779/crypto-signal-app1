import streamlit as st
import requests
import pandas as pd
import ta

# TwelveData API Key
API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'

# Internet check
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

@st.cache_data(ttl=60)
def get_coin_list():
    return ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD', 'XRP/USD', 'DOGE/USD']

def fetch_data(symbol, interval='1h', limit=100):
    url = "https://api.twelvedata.com/time_series"
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': API_KEY,
        'outputsize': limit,
        'format': 'JSON'
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if 'values' in data:
            df = pd.DataFrame(data['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df = df.astype(float)
            return df.sort_index()
        else:
            st.error(f"❌ Error: {data.get('message', 'No data found.')}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return pd.DataFrame()

def calculate_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close']).rsi()
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['ema9'] = ta.trend.EMAIndicator(close=df['close'], window=9).ema_indicator()
    df['ema21'] = ta.trend.EMAIndicator(close=df['close'], window=21).ema_indicator()
    bb = ta.volatility.BollingerBands(close=df['close'])
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    return df

def generate_signal(df):
    latest = df.iloc[-1]
    rsi_sig = 'Buy (RSI < 30)' if latest['rsi'] < 30 else 'Sell (RSI > 70)' if latest['rsi'] > 70 else 'Neutral'
    macd_sig = 'Bullish' if latest['macd'] > latest['macd_signal'] else 'Bearish'
    ema_sig = 'Bullish' if latest['ema9'] > latest['ema21'] else 'Bearish'
    bb_sig = 'Buy (Below Band)' if latest['close'] < latest['bb_lower'] else 'Sell (Above Band)' if latest['close'] > latest['bb_upper'] else 'Neutral'
    
    score = sum([
        'Buy' in rsi_sig or 'Bullish' in rsi_sig,
        'Buy' in macd_sig or 'Bullish' in macd_sig,
        'Buy' in ema_sig or 'Bullish' in ema_sig,
        'Buy' in bb_sig or 'Bullish' in bb_sig
    ])

    combined = '✅ Strong Buy' if score >= 3 else '❌ Weak or Neutral'
    return {
        'RSI': rsi_sig,
        'MACD': macd_sig,
        'EMA': ema_sig,
        'Bollinger': bb_sig,
        'Combined': combined
    }

def main():
    st.set_page_config("Crypto Signal App", layout="centered")
    st.title("📈 Real-Time Crypto Signal Generator")

    if st.button("🔄 Refresh Now"):
        st.cache_data.clear()

    if not is_connected():
        st.error("❌ Internet connection issue.")
        st.stop()

    coins = get_coin_list()
    symbol = st.selectbox("Select Coin Pair:", coins)

    df = fetch_data(symbol)
    if df.empty:
        st.warning("⚠️ Data unavailable. Try again later.")
        return

    df = calculate_indicators(df)
    signal = generate_signal(df)

    st.subheader(f"📊 Signals for {symbol}")
    st.write(f"**RSI Signal:** {signal['RSI']}")
    st.write(f"**MACD Signal:** {signal['MACD']}")
    st.write(f"**EMA Crossover:** {signal['EMA']}")
    st.write(f"**Bollinger Bands:** {signal['Bollinger']}")
    st.markdown(f"### {signal['Combined']}")

if __name__ == "__main__":
    main()
