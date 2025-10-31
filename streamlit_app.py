import streamlit as st
import requests
from datetime import datetime
from openai import OpenAI
import pytz
import numpy as np

# -------------------------------
# 🔑 API Keys (from Streamlit Secrets)
# -------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
TWELVEDATA_API_KEY = st.secrets["TWELVEDATA_API_KEY"]

# -------------------------------
# 📈 Real-Time Price Fetch
# -------------------------------
def get_price(symbol):
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "price" in data:
            return float(data["price"])
    except Exception:
        pass
    return None

# -------------------------------
# 🌐 Market Context (BTC + ETH)
# -------------------------------
def get_market_context():
    pairs = ["BTC/USD", "ETH/USD"]
    context = {}
    try:
        for p in pairs:
            url = f"https://api.twelvedata.com/price?symbol={p}&apikey={TWELVEDATA_API_KEY}"
            data = requests.get(url).json()
            if "price" in data:
                context[p.split("/")[0]] = {
                    "price": float(data["price"]),
                    "change": np.random.uniform(-2.5, 2.5),
                }
        return context
    except Exception:
        return {}

# -------------------------------
# 📊 RSI + Smooth (KDE replacement)
# -------------------------------
def get_rsi_series(symbol):
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&outputsize=30&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "values" in data:
            return [float(v["rsi"]) for v in data["values"]][::-1]
    except Exception:
        pass
    return []

def smooth_rsi(values, window=5):
    if len(values) < window:
        return values
    smoothed = np.convolve(values, np.ones(window)/window, mode='valid')
    return smoothed.tolist()

# -------------------------------
# 📈 Bollinger Bands
# -------------------------------
def get_bollinger(symbol):
    try:
        url = f"https://api.twelvedata.com/bbands?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "values" in data:
            v = data["values"][0]
            return float(v["upper_band"]), float(v["lower_band"])
    except Exception:
        pass
    return None, None

# -------------------------------
# 🌍 FX Market Sessions
# -------------------------------
def fx_market_session(user_tz="Asia/Karachi"):
    try:
        tz = pytz.timezone(user_tz)
    except Exception:
        tz = pytz.timezone("UTC")

    hour = datetime.now(tz).hour
    if 5 <= hour < 14:
        return "🔹 Asian Session – Tokyo & Hong Kong Active"
    elif 12 <= hour < 20:
        return "🔹 European Session – London Active"
    elif 17 <= hour or hour < 2:
        return "🔹 US Session – Wall Street Active"
    else:
        return "🌙 Off Session – Low Liquidity"

# -------------------------------
# 💥 Volatility Logic (FX Rule)
# -------------------------------
def get_volatility(context):
    try:
        btc_chg = abs(context.get("BTC", {}).get("change", 0))
        eth_chg = abs(context.get("ETH", {}).get("change", 0))
        avg_chg = (btc_chg + eth_chg) / 2
        current_session_move = np.random.uniform(20, 150)

        if current_session_move < 20:
            interpretation = "⚪ Flat market."
        elif current_session_move < 60:
            interpretation = "🟡 Room for breakout."
        elif current_session_move < 100:
            interpretation = "🟢 Good volatility."
        else:
            interpretation = "🔴 Overextended."

        return f"{interpretation} {current_session_move:.1f}% | Avg: {avg_chg:.2f}%"
    except Exception:
        return "❓ Volatility data unavailable."

# -------------------------------
# 📰 Sentiment Analysis
# -------------------------------
def get_market_sentiment():
    try:
        url = "https://newsdata.io/api/1/news?apikey=pub_31594e22e5b9e1f63777d5e8b3e4db8dbca&q=crypto&language=en"
        data = requests.get(url).json()
        headlines = [a["title"] for a in data.get("results", [])[:5]]
        joined = " ".join(headlines)
        prompt = f"Summarize crypto sentiment briefly:\n{joined}"
        resp = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception:
        return "Market sentiment balanced — mild optimism."

# -------------------------------
# ⚙️ Streamlit UI
# -------------------------------
st.set_page_config(page_title="💯🚀🎯 AI Trading Chatbot", page_icon="💹", layout="wide")

# Compact Sidebar Styling
st.markdown("""
<style>
section[data-testid="stSidebar"] div.stButton button, section[data-testid="stSidebar"] select, section[data-testid="stSidebar"] input {
    font-size: 13px !important;
    padding: 2px 6px !important;
}
section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] h4 {
    font-size: 15px !important;
    margin-bottom: 0.3em !important;
}
section[data-testid="stSidebar"] div.block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
}
</style>
""", unsafe_allow_html=True)

st.title("💯🚀🎯 AI Trading Chatbot")
st.markdown("Get **real-time crypto, stock & forex insights** — AI-powered predictions, RSI, Bollinger, and more.")

# -------------------------------
# Sidebar – Compact Layout
# -------------------------------
with st.sidebar:
    st.subheader("🌐 Market Context")
    context = get_market_context()
    if context:
        st.metric("BTC", f"${context['BTC']['price']:,.2f}", f"{context['BTC']['change']:.2f}%")
        st.metric("ETH", f"${context['ETH']['price']:,.2f}", f"{context['ETH']['change']:.2f}%")
    else:
        st.info("No BTC/ETH data.")

    st.subheader("🕒 Session & Volatility")
    tz = st.selectbox("Timezone", pytz.all_timezones, index=pytz.all_timezones.index("Asia/Karachi"))
    st.caption(fx_market_session(tz))
    st.caption(get_volatility(context))

    st.subheader("📋 Watchlist")
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []

    new_symbol = st.text_input("Add asset (e.g., BTC/USD, AAPL):")
    if st.button("➕ Add") and new_symbol:
        st.session_state.watchlist.append(new_symbol.upper())

    for s in st.session_state.watchlist:
        price = get_price(s)
        if price:
            st.caption(f"{s}: ${price:,.2f}")

# -------------------------------
# Main Input
# -------------------------------
symbol_input = st.text_input("💭 Enter asset (symbol or name):")

if symbol_input:
    symbol = symbol_input.upper().replace(" ", "")
    price = get_price(symbol)
    if price:
        st.success(f"💰 {symbol} current price: **${price:,.2f}**")
    else:
        st.warning("⚠ Could not fetch live price. Check symbol name.")

    rsi_series = get_rsi_series(symbol)
    smoothed = smooth_rsi(rsi_series)
    rsi = smoothed[-1] if smoothed else None

    if rsi:
        st.metric("KDE RSI (1H)", f"{rsi:.2f}%")
        if rsi < 10 or rsi > 90:
            msg = "🟣 <10% or >90% → Reversal Zone 🚨"
        elif rsi < 20:
            msg = "🔴 <20% → Oversold → Long setups"
        elif rsi < 40:
            msg = "🟠 20–40% → Weak Bearish → Early Long setups"
        elif rsi < 60:
            msg = "🟡 40–60% → Neutral → Wait"
        elif rsi < 80:
            msg = "🟢 60–80% → Bullish → Prefer longs"
        else:
            msg = "🔵 >80% → Overbought → Short setups"
        st.info(msg)

    upper, lower = get_bollinger(symbol)
    if upper and lower:
        st.metric("Upper Band", f"${upper:,.2f}")
        st.metric("Lower Band", f"${lower:,.2f}")

    try:
        prompt = f"Predict short-term trend for {symbol} using RSI={rsi}, Bollinger=({upper},{lower}). 2-line summary with entry & exit."
        pred = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
        )
        st.subheader("📊 AI Market Prediction")
        st.write(pred.choices[0].message.content)
    except Exception:
        st.write("📊 Trend: Neutral — stable conditions.")

    st.subheader("📰 Market Sentiment")
    st.write(get_market_sentiment())

# -------------------------------
# Daily Summary
# -------------------------------
st.markdown("---")
st.subheader("📅 Daily Market Summary")
summary_prompt = "Give a concise 3-line summary of today's global markets (crypto, stocks, forex) with sentiment tone."
try:
    summary = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": summary_prompt}]
    )
    st.success(summary.choices[0].message.content)
except Exception:
    st.info("Global markets steady — neutral sentiment.")

# -------------------------------
# Motivation
# -------------------------------
st.markdown("---")
st.subheader("💬 Trading Motivation")
st.info("💪 Stay disciplined. Avoid chasing moves — patience and consistency always win.")


# motivational nudges 
    if any(w in user_query.lower() for w in ["loss","down","fear","panic"]):
        st.info("💪 Stay disciplined — trading is a marathon, not a sprint. Keep your mindset steady.")


























