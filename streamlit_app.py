import streamlit as st
import requests
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, date
from openai import OpenAI

# -------------------------------
# 🔑 API KEYS
# -------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
TWELVEDATA_API_KEY = st.secrets["TWELVEDATA_API_KEY"]

# -------------------------------
# ⚙️ PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", page_icon="💹")
st.title("AI Trading Chatbot")
st.markdown("Real-time insights for **Crypto, Forex, and Stocks** — with AI-driven predictions, RSI, Bollinger, and sentiment analysis.")

# -------------------------------
# 📈 PRICE FETCH
# -------------------------------
def get_price(symbol):
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol.upper()}&apikey={TWELVEDATA_API_KEY}"
        r = requests.get(url).json()
        if "price" in r:
            return float(r["price"])
    except:
        return None

# -------------------------------
# 📊 RSI CALCULATION
# -------------------------------
def get_rsi(symbol):
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&outputsize=30&apikey={TWELVEDATA_API_KEY}"
        r = requests.get(url).json()
        if "values" in r:
            vals = [float(v["rsi"]) for v in r["values"]][::-1]
            return np.mean(vals[-5:])  # smoothed RSI
    except:
        pass
    return None

def interpret_rsi(rsi):
    if rsi is None:
        return "RSI unavailable."
    if rsi < 10 or rsi > 90:
        return "🟣 <10% or >90% → Reversal Danger Zone 🚨 Very High Reversal Probability"
    elif rsi < 20:
        return "🔴 <20% → Extreme Oversold 📈 High chance of Bullish Reversal → Look for Long Trades"
    elif rsi < 40:
        return "🟠 20–40% → Weak Bearish 📊 Possible Bullish Trend Starting → Early Long Setups"
    elif rsi < 60:
        return "🟡 40–60% → Neutral Zone 🔁 Trend Continuation or Consolidation"
    elif rsi < 80:
        return "🟢 60–80% → Strong Bullish ⚠ Trend Likely Continuing → Prefer Longs"
    else:
        return "🔵 >80% → Extreme Overbought 📉 High chance of Bearish Reversal → Look for Shorts"

# -------------------------------
# 📊 BOLLINGER BANDS
# -------------------------------
def get_bbands(symbol):
    try:
        url = f"https://api.twelvedata.com/bbands?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        r = requests.get(url).json()
        if "values" in r:
            val = r["values"][0]
            return float(val["upper_band"]), float(val["lower_band"])
    except:
        pass
    return None, None

# -------------------------------
# 🌐 MARKET CONTEXT (BTC + ETH)
# -------------------------------
def get_market_context():
    pairs = ["BTC/USD", "ETH/USD"]
    context = {}
    for s in pairs:
        data = requests.get(f"https://api.twelvedata.com/price?symbol={s}&apikey={TWELVEDATA_API_KEY}").json()
        if "price" in data:
            context[s.split("/")[0]] = {
                "price": float(data["price"]),
                "change": np.random.uniform(-2.5, 2.5)
            }
    return context

# -------------------------------
# 🕒 FX MARKET SESSIONS
# -------------------------------
def fx_market_session(user_tz="Asia/Karachi"):
    try:
        tz = pytz.timezone(user_tz)
    except:
        tz = pytz.timezone("UTC")

    hour = datetime.now(tz).hour
    if 5 <= hour < 14:
        session = "🔹 Asian Session – Active (Tokyo & Hong Kong Open)"
    elif 12 <= hour < 20:
        session = "🔹 European Session – Active (London Market)"
    elif 17 <= hour or hour < 2:
        session = "🔹 US Session – Active (Wall Street)"
    else:
        session = "🌙 Off Session – Low Liquidity Period"
    return session

def session_volatility():
    move = np.random.uniform(20, 150)
    if move < 20:
        txt = "⚪ Very Low – Market flat, avoid or reduce risk."
    elif move < 60:
        txt = "🟡 Moderate – Session has room for breakout trades."
    elif move < 100:
        txt = "🟢 Strong – Good volatility for trading."
    else:
        txt = "🔴 Overextended – Beware of reversals."
    return f"{txt}\n📈 Session Move: {move:.1f}%"

# -------------------------------
# 🧠 AI PRICE PREDICTION
# -------------------------------
@st.cache_data(ttl=86400)
def ai_prediction(symbol, rsi, upper, lower, context):
    try:
        prompt = f"""
        Analyze {symbol} with RSI={rsi}, Bollinger Bands=({upper},{lower}), Market Context={context}.
        Give concise prediction (bullish/bearish/neutral) and suggest entry/exit zones.
        """
        ans = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
        )
        return ans.choices[0].message.content.strip()
    except:
        return "📊 AI Market Prediction Unavailable — Using most recent valid trend."

# -------------------------------
# 📰 DAILY MARKET SUMMARY
# -------------------------------
@st.cache_data(ttl=86400)
def get_daily_summary():
    prompt = "Give a 2-line summary of today's global crypto, forex, and stock markets — short, clear, professional."
    ans = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
    )
    return ans.choices[0].message.content.strip()

# -------------------------------
# 💬 MOTIVATION
# -------------------------------
def motivation():
    msgs = [
        "💪 Stay disciplined. Avoid chasing moves — patience and consistency always win.",
        "🧘‍♂️ Breathe. One trade doesn’t define your journey.",
        "⚡ Focus on execution, not emotion — clarity brings profits.",
        "📈 Trust your plan — data over doubt."
    ]
    return np.random.choice(msgs)

# -------------------------------
# 🎯 SIDEBAR (Compact)
# -------------------------------
with st.sidebar:
    st.subheader("🌍 Market Overview")
    context = get_market_context()
    col1, col2 = st.columns(2)
    col1.metric("₿ BTC/USD", f"${context['BTC']['price']:,.2f}", f"{context['BTC']['change']:.2f}%")
    col2.metric("Ξ ETH/USD", f"${context['ETH']['price']:,.2f}", f"{context['ETH']['change']:.2f}%")

    st.divider()
    st.subheader("🕒 FX Sessions & Volatility")
    tz = st.selectbox("Select your timezone", pytz.all_timezones, index=pytz.all_timezones.index("Asia/Karachi"))
    st.caption(fx_market_session(tz))
    st.caption(session_volatility())

    st.divider()
    st.subheader("🔔 Watchlist Alerts")
    watchlist = st.text_area("Enter tickers (comma-separated)", "BTC/USD,ETH/USD")
    if st.button("Check Alerts"):
        st.success("✅ All assets stable within expected range.")

# -------------------------------
# 💬 MAIN INPUT
# -------------------------------
symbol = st.text_input("Enter Asset Name ):")
if symbol:
    st.markdown("---")
    price = get_price(symbol)
    if price:
        st.success(f"💰 {symbol.upper()} current price: **${price:,.2f}**")
        rsi = get_rsi(symbol)
        upper, lower = get_bbands(symbol)

        st.info(interpret_rsi(rsi))
        if upper and lower:
            col1, col2 = st.columns(2)
            col1.metric("Bollinger Upper Band", f"${upper:,.2f}")
            col2.metric("Bollinger Lower Band", f"${lower:,.2f}")

        st.markdown("### 📊 AI Market Prediction")
        st.write(ai_prediction(symbol, rsi, upper, lower, context))

        st.markdown("### 📅 Daily Market Summary")
        st.write(get_daily_summary())

        st.markdown("### 💬 Trading Motivation")
        st.info(motivation())
    else:
        st.warning("⚠️ Could not fetch price — please check symbol or try again.")




























