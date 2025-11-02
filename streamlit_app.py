import streamlit as st
import requests
import datetime
import random
import numpy as np

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide")

# === HELPERS ===
def get_crypto_price(symbol):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd&include_24hr_change=true"
        res = requests.get(url, timeout=10).json()
        data = res[symbol]
        return data["usd"], data["usd_24h_change"]
    except Exception:
        return 0, 0

def detect_fx_session_volatility(current_hour):
    """Automatically determine FX session and volatility based on given UTC hour."""
    if 22 <= current_hour or current_hour < 7:
        session, vol = "Sydney Session", random.randint(30, 45)
    elif 0 <= current_hour < 9:
        session, vol = "Tokyo Session", random.randint(50, 70)
    elif 7 <= current_hour < 16:
        session, vol = "London Session", random.randint(80, 120)
    else:
        session, vol = "New York Session", random.randint(90, 130)
    return session, vol

def interpret_fx_volatility(vol):
    if vol < 20:
        return "⚪ Flat Market – Low Volatility, Avoid or Reduce Risk"
    elif 40 <= vol <= 60:
        return "🟡 Room to Move – Good for Breakouts"
    elif vol >= 100:
        return "🔴 Overextended – Beware of Reversals"
    else:
        return "🟢 Moderate Activity – Normal Volatility"

def motivational_quote():
    quotes = [
        "Discipline beats impulse — trade the plan, not emotions.",
        "Patience is also a position.",
        "Focus on setups, not outcomes.",
        "Stay consistent — every small win builds your edge.",
        "Success in trading comes from calm execution, not speed."
    ]
    return np.random.choice(quotes)

# === SIDEBAR ===
st.sidebar.title("📊 Market Context Panel")

# BTC/ETH prices
btc_price, btc_change = get_crypto_price("bitcoin")
eth_price, eth_change = get_crypto_price("ethereum")

st.sidebar.metric("BTC Price (USD)", f"${btc_price:,.2f}", f"{btc_change:.2f}%")
st.sidebar.metric("ETH Price (USD)", f"${eth_price:,.2f}", f"{eth_change:.2f}%")

# === TIMEZONE SELECTOR ===
st.sidebar.markdown("### 🌍 Select Timezone (UTC)")
offset = st.sidebar.slider("Choose UTC Offset (Hours)", -12, 12, 0)
user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset)
st.sidebar.write(f"🕒 Local Time: {user_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC{offset:+d})")

# === FX SESSION ===
session, vol = detect_fx_session_volatility(user_time.hour)
st.sidebar.markdown(f"### 💹 {session}")
st.sidebar.info(interpret_fx_volatility(vol))

# === MAIN CONTENT ===
st.title(" AI Trading Chatbot – Market Overview")

st.write(
    f"""
    Welcome! This assistant automatically tracks **global FX market sessions**, 
    shows **real-time BTC/ETH benchmarks**, and adapts volatility analysis based on your timezone.

    Use the sidebar to:
    - View live crypto benchmark prices  
    - Adjust your timezone (UTC-based)  
    - Understand current FX session activity  
    """
)

st.markdown("### 💬 Trading Motivation")
st.success(motivational_quote())
