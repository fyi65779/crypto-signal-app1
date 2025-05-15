import streamlit as st
import requests
import pandas as pd

# --- API Keys ---
TWELVE_API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'  # Replace with your real key

# --- Internet Check ---
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

# --- Fetch Historical Data from TwelveData ---
def fetch_twelvedata(symbol, interval='1h', limit=100):
    url = "https://api.twelvedata.com/time_series"
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': TWELVE_API_KEY,
        'limit': limit
    }
    try:
        r = requests.get(url, params=params)
        data = r.json()
        if 'values' in data:
            df = pd.DataFrame(data['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df = df.astype(float)
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- Real-Time Price from CoinGecko ---
def get_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    try:
        res = requests.get(url).json()
        return res[coin_id]['usd']
    except:
        return 0

# --- Get Top 50 Coins with Trump & Zerebro ---
@st.cache_data(ttl=300)
def fetch_top_50():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 50,
        'page': 1
    }
    try:
        coins = requests.get(url, params=params).json()

        # Ensure Trump and Zerebro are included
        extra_ids = ['official-trump', 'zerebro']
        for eid in extra_ids:
            url2 = f"https://api.coingecko.com/api/v3/coins/{eid}"
            res = requests.get(url2).json()
            price = res['market_data']['current_price']['usd']
            coins.append({
                'id': eid,
                'symbol': res['symbol'],
                'name': res['name'],
                'current_price': price
            })
        return coins
    except:
        return []

# --- Indicators ---
def add_indicators(df):
    df['EMA9'] = df['close'].ewm(span=9).mean()
    df['EMA21'] = df['close'].ewm(span=21).mean()
    df['EMA200'] = df['close'].ewm(span=200).mean()
    df['RSI'] = 100 - (100 / (1 + (df['close'].diff() > 0).rolling(14).mean() / (df['close'].diff() < 0).rolling(14).mean()))
    df['Upper'] = df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std()
    df['Lower'] = df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std()
    df['MACD'] = df['close'].ewm(12).mean() - df['close'].ewm(26).mean()
    df['MACD_sig'] = df['MACD'].ewm(9).mean()
    return df

# --- Signal Logic ---
def generate_signal(df):
    latest = df.iloc[-1]
    score = 0
    if latest['RSI'] < 30:
        rsi = "Buy (Oversold)"
        score += 1
    elif latest['RSI'] > 70:
        rsi = "Sell (Overbought)"
        score -= 1
    else:
        rsi = "Neutral"

    macd = "Bullish" if latest['MACD'] > latest['MACD_sig'] else "Bearish"
    score += 1 if macd == "Bullish" else -1

    ema = "Bullish" if latest['EMA9'] > latest['EMA21'] else "Bearish"
    score += 1 if ema == "Bullish" else -1

    band = "Buy" if latest['close'] < latest['Lower'] else "Sell" if latest['close'] > latest['Upper'] else "Neutral"
    score += 1 if band == "Buy" else -1 if band == "Sell" else 0

    trend = "Uptrend" if latest['close'] > latest['EMA200'] else "Downtrend"
    score += 1 if trend == "Uptrend" else -1

    final = "✅ Strong Buy" if score >= 3 else "❌ Strong Sell" if score <= -3 else "⚠️ Neutral"

    return {
        'RSI': rsi,
        'MACD': macd,
        'EMA': ema,
        'Bollinger': band,
        'Trend': trend,
        'Final': final,
        'Score': score,
        'Entry': latest['close']
    }

# --- Streamlit App ---
def main():
    st.set_page_config("Crypto Signal Generator", layout="centered")
    st.title("📊 Crypto Signal Generator")

    if not is_connected():
        st.error("❌ No internet connection.")
        return

    coins = fetch_top_50()
    options = [f"{c['symbol'].upper()}/USD - ${round(c['current_price'], 4)}" for c in coins]
    choice = st.selectbox("Select Coin:", options)

    selected = coins[options.index(choice)]
    coin_id = selected['id']
    symbol = selected['symbol'].upper() + "/USD"

    df = fetch_twelvedata(symbol)
    if df.empty:
        st.warning(f"⚠️ No historical data for {symbol}. Showing real-time price only.")
        price = get_price(coin_id)
        if price > 0:
            st.success(f"🔹 Real-Time Price: ${price}")
        else:
            st.error("❌ Price not available.")
        return

    df = add_indicators(df)
    signal = generate_signal(df)

    st.subheader(f"📈 Signal for {selected['name']} ({selected['symbol'].upper()})")
    st.write(f"**RSI:** {signal['RSI']}")
    st.write(f"**MACD:** {signal['MACD']}")
    st.write(f"**EMA Crossover:** {signal['EMA']}")
    st.write(f"**Bollinger Band:** {signal['Bollinger']}")
    st.write(f"**Trend:** {signal['Trend']}")
    st.write(f"**Score:** {signal['Score']}")
    st.write(f"**Final Signal:** {signal['Final']}")
    st.write(f"**Entry Point:** ${round(signal['Entry'], 4)}")

if __name__ == "__main__":
    main()
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
