import streamlit as st
import requests
import pandas as pd
import numpy as np

# --- API Key ---
TWELVE_API_KEY = '6cbc54ad9e114dbea0ff7d8a7228188b'  # یہاں اپنا TwelveData API کلید درج کریں

# --- انٹرنیٹ کنکشن چیک کریں ---
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# --- تاریخی ڈیٹا حاصل کریں ---
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

# --- حقیقی وقت کی قیمت حاصل کریں ---
def fetch_coin_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        res = requests.get(url).json()
        return res[coin_id]['usd'] if coin_id in res else 0
    except:
        return 0

# --- تکنیکی اشاریے کا حساب لگائیں ---
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

# --- سگنل تیار کریں ---
def generate_signal(df):
    latest = df.iloc[-1]
    score = 0

    # RSI
    rsi = latest['RSI']
    if rsi < 30:
        rsi_sig = 'خریداری (RSI کم)'
        score += 1
    elif rsi > 70:
        rsi_sig = 'فروخت (RSI زیادہ)'
        score -= 1
    else:
        rsi_sig = 'غیر جانبدار'

    # MACD
    macd = latest['MACD']
    macd_sig = latest['MACD_signal']
    if macd > macd_sig:
        macd_result = 'بلش (MACD > سگنل)'
        score += 1
    else:
        macd_result = 'بئیرش (MACD < سگنل)'
        score -= 1

    # EMA کراس اوور
    if latest['EMA9'] > latest['EMA21']:
        ema_result = 'بلش (EMA9 > EMA21)'
        score += 1
    else:
        ema_result = 'بئیرش (EMA9 < EMA21)'
        score -= 1

    # Bollinger Bands
    if latest['close'] < latest['LowerBand']:
        bb_result = 'خریداری (نیچے کی بینڈ سے کم)'
        score += 1
    elif latest['close'] > latest['UpperBand']:
        bb_result = 'فروخت (اوپر کی بینڈ سے زیادہ)'
        score -= 1
    else:
        bb_result = 'غیر جانبدار'

    # رجحان
    if latest['close'] > latest['EMA200']:
        trend = 'اوپر کا رجحان'
        score += 1
    else:
        trend = 'نیچے کا رجحان'
        score -= 1

    # حتمی سگنل
    if score >= 3:
        final = '✅ مضبوط خریداری'
    elif score <= -3:
        final = '❌ مضبوط فروخت'
    else:
        final = '⚠️ احتیاط / غیر جانبدار'

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

# --- ٹاپ 50 کوائنز حاصل کریں ---
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
        # مخصوص meme کوائنز شامل کریں اگر وہ ٹاپ 50 میں نہیں ہیں
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

# --- Streamlit ایپ ---
def main():
    st.set_page_config(page_title="Crypto Signal Generator", layout="centered")
    st.title("📊 Crypto Signal Generator")
    st.markdown("🔍 **ٹاپ 50 کوائنز کے لیے تجارتی سگنلز**")

    if not is_connected():
        st.error("❌ انٹرنیٹ کنکشن دستیاب نہیں۔")
        return

    coins = fetch_top_50_coins()
    if not coins:
        st.warning("⚠️ کوائنز کی فہرست حاصل نہیں ہو سکی۔")
        return

    coin_names = [f"{c['symbol'].upper()} - {c['name']}" for c in coins]
    selected_name = st.selectbox("کوائن منتخب کریں:", coin_names)
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
            st.success(f"📈 حقیقی وقت کی قیمت: ${price}")
            st.info("ℹ️ سگنل تیار نہیں کیا جا سکتا (TwelveData اس کوائن کو سپورٹ نہیں کرتا)۔")
        else:
            st.error("❌ قیمت حاصل نہیں کی جا سکی۔")
        return

    df = calculate_indicators(df)
    signal = generate_signal(df)

    st.subheader("📈 سگنل تجزیہ")
    st.write(f"**RSI:** {signal['RSI']}")
    st.write(f"**MACD:** {signal['MACD']}")
    st.write(f"**EMA کراس اوور:** {signal['EMA']}")
    st.write(f"**Bollinger Bands:** {signal['Bollinger']}")
    st.write(f"**رجحان:** {signal['Trend']}")
    st.write(f"**سکور:** {signal['Score']}")
    st.write(f"**سگنل:** {signal['Final']}")
    st.write(f"**انٹری پوائنٹ:** ${round(signal['Entry'], 4)}")

if __name__ == "__main__":
    main()
