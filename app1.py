import streamlit as st
import requests
import pandas as pd
import numpy as np

# Your TwelveData API key
API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'

# Check Internet connection
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
            st.warning(f"⚠️ Error fetching {symbol} from TwelveData.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error fetching data: {e}")
        return pd.DataFrame()

# Fetch real-time price from CoinGecko
def fetch_coin_price(symbol):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if symbol in data:
            return data[symbol]['usd']
        return 0
    except Exception as e:
        st.error(f"Error fetching {symbol} price: {e}")
        return 0

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

    # Entry point calculation based on most recent data
    entry_point = latest_data['close']  # Simplified entry point as the latest closing price
    
    return {
        'rsi_signal': rsi_signal,
        'macd_signal': macd_signal,
        'ema_signal': ema_signal,
        'bb_signal': bb_signal,
        'combined_signal': combined_signal,
        'entry_point': entry_point
    }

# Fetch top coins from CoinGecko and add Trump and Zerebro
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

        # Adding Trump and Zerebro (real-time data if available)
        # If Trump and Zerebro are not found on CoinGecko, you can add fake prices here.
        trump = {
            'symbol': 'official-trump',
            'current_price': fetch_coin_price('official-trump'),
            'name': 'Trump Coin'
        }
        zerebro = {
            'symbol': 'zerebro',
            'current_price': fetch_coin_price('zerebro'),
            'name': 'Zerebro Coin'
        }

        coins.append(trump)
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
        st.warning(f"⚠️ No data found for {symbol}. Trying CoinGecko...")
        price = fetch_coin_price(selected['symbol'])
        if price > 0:
            st.write(f"🔹 **Price for {selected['name']}**: ${price}")
            signal = {
                'combined_signal': '❌ No data (Using CoinGecko price)',
                'entry_point': price
            }
            st.write(f"**Entry Point:** {signal['entry_point']}")
        else:
            st.warning("⚠️ No valid data for this coin.")
        st.stop()

    df = calculate_indicators(df)

    signal = generate_signal(df)

    st.subheader(f"🔔 Signal for {symbol}")
    st.write(f"**RSI Signal:** {signal['rsi_signal']}")
    st.write(f"**MACD Signal:** {signal['macd_signal']}")
    st.write(f"**EMA Crossover Signal:** {signal['ema_signal']}")
    st.write(f"**Bollinger Bands Signal:** {signal['bb_signal']}")
    st.write(f"**Combined Signal:** {signal['combined_signal']}")
    st.write(f"**Entry Point:** {signal['entry_point']}")

if __name__ == "__main__":
    main()
