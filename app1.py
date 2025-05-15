import streamlit as st
import requests

# ---------------- INTERNET CHECK ----------------
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# ---------------- COIN FETCHING ----------------
@st.cache_data(ttl=120)
def fetch_top_coins(limit=30):
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

        # Add TRUMP and ZEREBRO
        for extra_id in ['official-trump', 'zerebro']:
            if not any(c['id'] == extra_id for c in coins):
                coin = fetch_specific_coin(extra_id)
                if coin:
                    coins.append(coin)

        return coins
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            st.error("❌ CoinGecko rate limit exceeded. Try again shortly.")
        else:
            st.error(f"❌ Error fetching coins: {e}")
        return []
    except Exception as e:
        st.error(f"❌ Unknown error: {e}")
        return []

@st.cache_data(ttl=120)
def fetch_specific_coin(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {
            'id': data['id'],
            'symbol': data['symbol'],
            'current_price': data['market_data']['current_price']['usd'],
            'price_change_percentage_1h_in_currency': data['market_data']['price_change_percentage_1h_in_currency'].get('usd', 0),
            'price_change_percentage_24h_in_currency': data['market_data']['price_change_percentage_24h_in_currency'].get('usd', 0)
        }
    except Exception:
        return None

# ---------------- SIGNAL GENERATION ----------------
def generate_signal(coin):
    price = coin['current_price']
    change_1h = coin.get('price_change_percentage_1h_in_currency', 0)
    change_24h = coin.get('price_change_percentage_24h_in_currency', 0)

    momentum = 'Bullish 🔼' if change_1h > 0 and change_24h > 0 else 'Bearish 🔽' if change_1h < 0 and change_24h < 0 else 'Mixed ⚖️'
    direction = '📈 Buy (Long)' if change_24h > 0 else '📉 Sell (Short)'
    confidence = min(max((abs(change_1h) + abs(change_24h)) * 1.5, 10), 95)

    predicted_move = round(price * (change_24h / 100), 2)
    profitability = '✅ High chance of profit' if abs(predicted_move) > 5 else '⚠️ Profit < $5'
    prediction = '🚀 Likely to go up' if change_24h > 0 else '📉 May go down'

    up_prob = min(60 + change_24h, 85) if change_24h > 0 else 20
    down_prob = 100 - up_prob

    max_up = round(price * (1 + abs(change_24h / 100)), 4)
    max_down = round(price * (1 - abs(change_24h / 100)), 4)
    only_max = f"🔼 Max Up Prediction: ${max_up}" if up_prob > down_prob else f"🔽 Max Down Prediction: ${max_down}"

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

# ---------------- MAIN APP ----------------
def main():
    st.set_page_config(page_title="Crypto Signal Generator", layout="centered")
    st.title("📊 Crypto Signal Generator")
    st.markdown("**Most probable signal using CoinGecko live data**")
    st.write("🌐 Powered by [CoinGecko](https://coingecko.com)")

    if not is_connected():
        st.error("❌ No internet. Check your connection.")
        return

    if st.button("🔁 Refresh Data"):
        st.rerun()

    coins = fetch_top_coins()
    if not coins:
        st.warning("⚠️ Unable to load coins.")
        return

    coin_options = [f"{c['symbol'].upper()} - ${c['current_price']}" for c in coins]
    choice = st.selectbox("📥 Select Coin:", coin_options)

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
