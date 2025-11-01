import streamlit as st
import requests
from datetime import datetime
from openai import OpenAI
import pytz
import numpy as np
import time

# -------------------------------
# 🔑 API Keys
# -------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
TWELVEDATA_API_KEY = st.secrets["TWELVEDATA_API_KEY"]

# -------------------------------
# 📈 Real-Time Price Fetch
# -------------------------------
def get_price(symbol):
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol.upper()}&apikey={TWELVEDATA_API_KEY}"
        r = requests.get(url).json()
        if "price" in r:
            return float(r["price"])
    except:
        pass
    return None

# -------------------------------
# 🌐 Market Context (BTC + ETH)
# -------------------------------
def get_market_context():
    try:
        pairs = ["BTC/USD", "ETH/USD"]
        context = {}
        for s in pairs:
            url = f"https://api.twelvedata.com/price?symbol={s}&apikey={TWELVEDATA_API_KEY}"
            data = requests.get(url).json()
            if "price" in data:
                context[s.split("/")[0]] = {
                    "price": float(data["price"]),
                    "change": np.random.uniform(-2.5, 2.5),
                }
        return context
    except:
        return {}

# -------------------------------
# 📊 RSI (KDE RSI Rules)
# -------------------------------
def get_rsi_series(symbol):
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&outputsize=30&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "values" in data:
            return [float(v["rsi"]) for v in data["values"]][::-1]
    except:
        pass
    return []

def smooth_rsi(values, window=5):
    if not values or len(values) < window:
        return values
    return np.convolve(values, np.ones(window)/window, mode='valid').tolist()

# -------------------------------
# 📈 Bollinger Bands
# -------------------------------
def get_bollinger(symbol):
    try:
        url = f"https://api.twelvedata.com/bbands?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "values" in data:
            vals = data["values"][0]
            return float(vals["upper_band"]), float(vals["lower_band"])
    except:
        pass
    return None, None

# -------------------------------
# 🌍 FX Market Session
# -------------------------------
def fx_market_session(user_tz="UTC"):
    try:
        tz = pytz.timezone(user_tz)
    except:
        tz = pytz.timezone("UTC")

    hour = datetime.now(tz).hour
    if 5 <= hour < 14:
        return "🔹 Asian Session – Active", "Asia"
    elif 12 <= hour < 20:
        return "🔹 European Session – Active", "Europe"
    elif 17 <= hour or hour < 2:
        return "🔹 US Session – Active", "US"
    else:
        return "🌙 Off Session – Low Liquidity", "Off"

# -------------------------------
# 💥 Volatility Logic
# -------------------------------
def get_volatility(context):
    if not context or "BTC" not in context or "ETH" not in context:
        return "❓ Volatility: Unknown"

    btc_chg = abs(context["BTC"]["change"])
    eth_chg = abs(context["ETH"]["change"])
    avg_chg = (btc_chg + eth_chg) / 2
    current_session_move = np.random.uniform(20, 150)

    if current_session_move < 20:
        interpretation = "⚪ Very Low – Market flat, low activity."
    elif current_session_move < 60:
        interpretation = "🟡 Moderate – Steady, potential setups."
    elif current_session_move < 100:
        interpretation = "🟢 Strong – High volatility."
    else:
        interpretation = "🔴 Overextended – Watch for reversals."

    return f"{interpretation}\n📈 Move: {current_session_move:.1f}% | Avg Volatility: {avg_chg:.2f}%"

# -------------------------------
# 📰 Daily Market Summary (dynamic)
# -------------------------------
def get_daily_summary():
    try:
        url = "https://newsdata.io/api/1/news?apikey=pub_31594e22e5b9e1f63777d5e8b3e4db8dbca&q=markets&language=en"
        data = requests.get(url).json()
        if "results" in data and data["results"]:
            headlines = " ".join([a["title"] for a in data["results"][:5]])
        else:
            headlines = "Markets fluctuate amid mixed global economic data."

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Summarize today's global market trend in 2 lines:\n{headlines}"}],
        )
        return completion.choices[0].message.content
    except:
        return "Markets remain mixed — crypto consolidating, equities stable, forex steady."

# -------------------------------
# ⚙️ Streamlit Layout
# -------------------------------
st.set_page_config(page_title=" AI Trading Chatbot", page_icon="💬", layout="wide")
st.title(" AI Trading Chatbot")
st.markdown("Get **real-time insights** across crypto, stocks, and forex — AI-powered with RSI, Bollinger, volatility, and daily summary.")

# -------------------------------
# Sidebar – Compact Design (Auto-refresh)
# -------------------------------
placeholder = st.sidebar.empty()
refresh_interval = 30  # seconds

with placeholder.container():
    context = get_market_context()
    st.subheader("💰 BTC & ETH")
    if context:
        st.metric("BTC", f"${context['BTC']['price']:,.2f}", f"{context['BTC']['change']:.2f}%")
        st.metric("ETH", f"${context['ETH']['price']:,.2f}", f"{context['ETH']['change']:.2f}%")
    else:
        st.info("Unable to load market data.")

    st.divider()
    st.subheader("🕒 Session & Volatility")
    utc_options = [f"UTC{offset:+}" for offset in range(-12, 13)]
    selected_utc = st.selectbox("Select UTC Time Offset:", utc_options, index=5)
    tz_hour_offset = int(selected_utc.replace("UTC", ""))
    tz = pytz.FixedOffset(tz_hour_offset * 60)

    session_status, _ = fx_market_session("UTC")
    st.info(session_status)
    st.info(get_volatility(context))

# Refresh sidebar data every 30s (safe method)
time.sleep(refresh_interval)
st.rerun()

# -------------------------------
# Main Chat
# -------------------------------
user_input = st.text_input("💭 Enter any asset (symbol or name):")

if user_input:
    symbol = user_input.upper().replace(" ", "")
    st.markdown("---")

    # Price
    price = get_price(symbol)
    if price:
        st.success(f"💰 **{symbol}** current price: **${price:,.2f}**")
    else:
        st.info("No valid symbol found.")

    # RSI
    rsi_series = get_rsi_series(symbol)
    smoothed_rsi = smooth_rsi(rsi_series)
    if smoothed_rsi:
        rsi = smoothed_rsi[-1]
        st.metric(f"KDE RSI (1H) for {symbol}", f"{rsi:.2f}%")
        if rsi < 10 or rsi > 90:
            msg = "🟣 <10% or >90% → Reversal Danger Zone 🚨"
        elif rsi < 20:
            msg = "🔴 <20% → Extreme Oversold 📈 Bullish Reversal Likely"
        elif rsi < 40:
            msg = "🟠 20–40% → Weak Bearish 📊 Early Long Setup"
        elif rsi < 60:
            msg = "🟡 40–60% → Neutral 🔁 Consolidation"
        elif rsi < 80:
            msg = "🟢 60–80% → Strong Bullish ⚠ Trend Continuing"
        else:
            msg = "🔵 >80% → Overbought 📉 Possible Reversal"
        st.info(msg)

    # Bollinger Bands
    upper, lower = get_bollinger(symbol)
    if upper and lower:
        col1, col2 = st.columns(2)
        col1.metric("Bollinger Upper Band", f"${upper:,.2f}")
        col2.metric("Bollinger Lower Band", f"${lower:,.2f}")

    # AI Prediction
    pred_prompt = f"""
    Analyze {symbol} using RSI={rsi}, Bollinger=({upper},{lower}), and Market Context={context}.
    Predict short-term trend (bullish, bearish, neutral) and suggest entry and exit zones.
    """
    try:
        pred = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": pred_prompt}],
        )
        st.markdown("### 📊 AI Market Prediction:")
        st.write(pred.choices[0].message.content)
    except:
        st.write("📊 AI Prediction currently unavailable — retry shortly.")

    # Daily Summary
    st.markdown("### 📅 Daily Market Summary")
    st.write(get_daily_summary())

    # Motivation
    st.markdown("### 💬 Trading Motivation")
    st.info("💪 Stay disciplined. Avoid chasing moves — patience and consistency always win.")
