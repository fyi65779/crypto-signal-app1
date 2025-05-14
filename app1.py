import streamlit as st
import requests
import pandas as pd
import numpy as np

# Your TwelveData API key
API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'

# Internet check
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# Fetch historical data from TwelveData API
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
            return df
        else:
            st.error(f"Error fetching data: {data.get('message', 'Unknown error')}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error fetching data: {e}")
        return pd.DataFrame()

# Calculate technical indicators
def calculate_indicators(df):
    df['RSI'] = 100 - (100 / (1 + (df['close'].diff() > 0).rolling(window=14).mean() / (df['close'].diff() < 0).rolling(window=14).mean()))
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['UpperBand'] = df['close'].rolling(window=20).mean() + 2 * df['close'].rolling(window=20).std()
    df['LowerBand'] = df['close'].rolling(window=20).mean() - 2 * df['close'].rolling(window=20).std()
    
    # MACD calculation
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df

# Generate signal based on indicators
def generate_signal(df):
    latest_data = df.iloc[-1]
    
    # RSI condition
    if latest_data['RSI'] < 30:
        rsi_signal = 'Buy (RSI oversold)'
    elif latest_data['RSI'] > 70:
        rsi_signal = 'Sell (RSI overbought)'
    else:
        rsi_signal = 'Neutral (RSI normal)'

    # MACD condition
    if latest_data['MACD'] > latest_data['MACD_signal']:
        macd_signal = 'Bullish (MACD positive)'
    else:
        macd_signal = 'Bearish (MACD negative)'

    # EMA Crossover condition
    if latest_data['EMA9'] > latest_data['EMA21']:
        ema_signal = 'Bullish (EMA9 > EMA21)'
    else:
        ema_signal = 'Bearish (EMA9 < EMA21)'

    # Bollinger Bands condition
    if latest_data['close'] < latest_data['LowerBand']:
        bb_signal = 'Buy (Price below Lower Band)'
    elif latest_data['close'] > latest_data['UpperBand']:
        bb_signal = 'Sell (Price above Upper Band)'
    else:
        bb_signal = 'Neutral (Price within Bands)'

    # Combine signals
    signals = [rsi_signal, macd_signal, ema_signal, bb_signal]
    combined_signal = '✅ Strong Buy' if 'Buy' in [s.split(' ')[0] for s in signals] else '❌ Strong Sell'

    return {
        'rsi_signal': rsi_signal,
        'macd_signal': macd_signal,
        'ema_signal': ema_signal,
        'bb_signal': bb_signal,
        'combined_signal': combined_signal
    }

# Fetch top coins
@st.cache_data(ttl=120)  # Cache for 2 minutes
def fetch_top_coins(limit=35):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': limit,
        'page': 1,
        'sparkline': 'false',
        'price_change_percentage': '1h,24h'
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        coins = response.json()

        if not any(c['symbol'].lower() == 'trump' for c in coins):
            trump = fetch_specific_coin("official-trump")
            if trump:
                coins.append(trump)

        if not any(c['symbol'].lower() == 'zerebro' for c in coins):
            zerebro = fetch_specific_coin("zerebro")
            if zerebro:
                coins.append(zerebro)

        return coins
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Error fetching coins: {e}")
        return []
    except Exception as e:
        st.error(f"❌ Unknown error fetching coins: {e}")
        return []

# Main Streamlit app
def main():
    st.title("📊 Crypto Signal Generator")

    st.write("🔄 Real-time data from CoinGecko")

    if st.button("🔁 Refresh"):
        st.rerun()

    if not is_connected():
        st.error("❌ Internet connection nahi hai. Please check and try again.")
        st.stop()

    coins = fetch_top_coins()
    if not coins:
        st.warning("⚠️ Coins load nahi ho rahe.")
        st.stop()

    coin_options = [f"{c['symbol'].upper()} - ${c['current_price']}" for c in coins]
    choice = st.selectbox("📥 Coin select karein:", coin_options)

    selected_index = coin_options.index(choice)
    selected = coins[selected_index]
    symbol = selected['symbol'].upper() + "/USD"
    
    df = fetch_data(symbol)
    if df.empty:
        st.warning("⚠️ No data found. Try again.")
        st.stop()

    df = calculate_indicators(df)

    signal = generate_signal(df)

    st.subheader(f"🔔 Signal for {symbol}")
    st.write(f"**RSI Signal:** {signal['rsi_signal']}")
    st.write(f"**MACD Signal:** {signal['macd_signal']}")
    st.write(f"**EMA Crossover Signal:** {signal['ema_signal']}")
    st.write(f"**Bollinger Bands Signal:** {signal['bb_signal']}")
    st.write(f"**Combined Signal:** {signal['combined_signal']}")

if __name__ == "__main__":
    main()
