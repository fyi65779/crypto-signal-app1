import streamlit as st
import requests
import pandas as pd
import numpy as np

# ------------------- Utilities -------------------
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

@st.cache_data(ttl=120)
def fetch_top_coins(limit=30):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': limit,
        'page': 1,
        'sparkline': 'false',
        'price_change_percentage': '1h,24h,7d'
    }
    try:
        res = requests.get(url, params=params)
        coins = res.json()
        # Add extra meme coins if not in top list
        for extra in ["official-trump", "zerebro"]:
            if not any(c['id'] == extra for c in coins):
                coin = fetch_specific_coin(extra)
                if coin: coins.append(coin)
        return coins
    except:
        st.error("❌ Error fetching coins.")
        return []

@st.cache_data(ttl=120)
def fetch_specific_coin(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    try:
        res = requests.get(url)
        data = res.json()
        market = data.get("market_data", {})
        return {
            'id': coin_id,
            'symbol': data['symbol'],
            'current_price': market.get('current_price', {}).get('usd', 0),
            'price_change_percentage_1h_in_currency': market.get('price_change_percentage_1h_in_currency', {}).get('usd', 0),
            'price_change_percentage_24h_in_currency': market.get('price_change_percentage_24h_in_currency', {}).get('usd', 0),
            'price_change_percentage_7d_in_currency': market.get('price_change_percentage_7d_in_currency', {}).get('usd', 0),
        }
    except:
        return None

# ------------------- Signal Logic -------------------
def generate_signal(coin):
    price = coin['current_price']
    ch1h = coin.get('price_change_percentage_1h_in_currency', 0)
    ch24h = coin.get('price_change_percentage_24h_in_currency', 0)
    ch7d = coin.get('price_change_percentage_7d_in_currency', 0)

    # Weighted score
    score = 0
    score += 0.5 if ch1h > 0 else -0.5
    score += 1 if ch24h > 0 else -1
    score += 1 if ch7d > 0 else -1

    momentum = (
        'Strong Bullish 🔼' if ch1h > 1 and ch24h > 1 else
        'Bullish ⬆️' if ch24h > 0 else
        'Bearish 🔽' if ch24h < 0 else 'Flat ⚖️'
    )

    direction = '📈 Buy (Long)' if score >= 1 else '📉 Sell (Short)'
    confidence = min(95, max(55, abs(score) * 20 + abs(ch24h)))  # adaptive confidence
    expected_move = round(price * (ch24h / 100), 2)

    profitability = '✅ High chance of profit' if abs(expected_move) > 5 else '⚠️ Low profit expected'
    prediction = '🚀 Likely to go up' if ch24h > 0 else '📉 Likely to go down'
    up_prob = min(85, 60 + ch24h) if ch24h > 0 else 100 - abs(ch24h)
    down_prob = 100 - up_prob
    max_up = round(price * (1 + abs(ch24h / 100)), 4)
    max_down = round(price * (1 - abs(ch24h / 100)), 4)
    only_max = f"🔼 Max Up Prediction: ${max_up}" if ch24h > 0 else f"🔽 Max Down Prediction: ${max_down}"

    return {
        'symbol': coin['symbol'].upper(),
        'id': coin['id'],
        'direction': direction,
        'entry_point': round(price, 4),
        'confidence': round(confidence, 2),
        'prediction': prediction,
        'profitability': profitability,
        'up_probability': round(up_prob),
        'down_probability': round(down_prob),
        'only_max': only_max,
        'momentum': momentum
    }

# ------------------- Streamlit App -------------------
def main():
    st.set_page_config(page_title="Crypto Signal Generator", layout="centered")
    st.title("📊 Crypto Signal Generator")
    st.write("Real-time predictions based on CoinGecko data (No Neutral Signals)")

    if st.button("🔄 Refresh"):
        st.rerun()

    if not is_connected():
        st.error("❌ No Internet. Please connect and try again.")
        return

    coins = fetch_top_coins()
    if not coins:
        st.warning("⚠️ Coin list unavailable.")
        return

    coin_options = [f"{c['symbol'].upper()} - ${c['current_price']}" for c in coins]
    choice = st.selectbox("📥 Select a Coin", coin_options)
    selected = coins[coin_options.index(choice)]

    signal = generate_signal(selected)
    st.subheader(f"🔔 Signal for {signal['symbol']}")
    st.write(f"**Direction:** {signal['direction']}")
    st.write(f"**Entry Point:** ${signal['entry_point']}")
    st.write(f"**Confidence:** {signal['confidence']}%")
    st.write(f"**Momentum:** {signal['momentum']}")
    st.write(f"**Prediction:** {signal['prediction']}")
    st.write(f"**Profitability:** {signal['profitability']}")
    st.write(f"**Up Probability:** {signal['up_probability']}%")
    st.write(f"**Down Probability:** {signal['down_probability']}%")
    st.write(f"{signal['only_max']}")

if __name__ == "__main__":
    main()
