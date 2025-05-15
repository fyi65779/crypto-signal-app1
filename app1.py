import streamlit as st
import requests

# Check internet connection
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# Fetch top coins
@st.cache_data(ttl=120)
def fetch_top_coins(limit=50):
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
        return response.json()
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return []

# Generate trading signal
def generate_signal(coin):
    price = coin['current_price']
    change_1h = coin.get('price_change_percentage_1h_in_currency', 0)
    change_24h = coin.get('price_change_percentage_24h_in_currency', 0)

    direction = '📈 Buy (Long)' if change_24h > 0 else '📉 Sell (Short)'
    momentum = 'Bullish 🔼' if change_1h > 0 and change_24h > 0 else 'Bearish 🔽' if change_1h < 0 and change_24h < 0 else 'Mixed ⚖️'
    confidence = min(max((abs(change_1h) + abs(change_24h)) * 1.6, 15), 88)
    prediction = '🚀 Likely to go up' if change_24h > 0 else '📉 May go down'
    up_prob = min(65 + change_24h, 90) if change_24h > 0 else 25
    down_prob = 100 - up_prob
    expected_move = change_24h / 100
    max_up = round(price * (1 + abs(expected_move)), 4)
    max_down = round(price * (1 - abs(expected_move)), 4)
    only_max = f"🔼 Max Up Prediction: ${max_up}" if up_prob > down_prob else f"🔽 Max Down Prediction: ${max_down}"
    profitability = '✅ High Profit Chance' if abs(expected_move) > 0.05 else '⚠️ Low Profit Range'

    return {
        'symbol': coin['symbol'].upper(),
        'direction': direction,
        'entry_point': round(price, 4),
        'confidence': round(confidence),
        'momentum': momentum,
        'prediction': prediction,
        'profitability': profitability,
        'up_probability': round(up_prob),
        'down_probability': round(down_prob),
        'only_max': only_max
    }

# Streamlit App
st.set_page_config(page_title="📊 CoinGecko Signal Generator", layout="centered")
st.title("📊 Crypto Signal Generator (Most Probable Using CoinGecko)")
st.markdown("🌐 Powered by CoinGecko – no candles or 3rd party APIs used.")

if not is_connected():
    st.error("❌ No internet connection.")
    st.stop()

coins = fetch_top_coins()
if not coins:
    st.error("❌ Unable to fetch coins.")
    st.stop()

coin_options = [f"{c['symbol'].upper()} - ${c['current_price']}" for c in coins]
choice = st.selectbox("📥 Select Coin:", coin_options)

selected = coins[coin_options.index(choice)]
signal = generate_signal(selected)

# Display signal
st.subheader(f"🔔 Signal for {signal['symbol']}")
st.write(f"**Direction:** {signal['direction']}")
st.write(f"**Entry Point:** ${signal['entry_point']}")
st.write(f"**Confidence:** {signal['confidence']}%")
st.write(f"**Momentum:** {signal['momentum']}")
st.write(f"**Prediction:** {signal['prediction']}")
st.write(f"**Profitability:** {signal['profitability']}")
st.write(f"**Up Probability:** {signal['up_probability']}%")
st.write(f"**Down Probability:** {signal['down_probability']}%")
st.write(signal['only_max'])
