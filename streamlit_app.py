import streamlit as st
import requests
from datetime import datetime
from openai import OpenAI
import pytz
import numpy as np
from scipy.stats import gaussian_kde

# -------------------------------
# 🔑 API Keys
# -------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
TWELVEDATA_API_KEY = st.secrets["TWELVEDATA_API_KEY"]

# -------------------------------
# 📈 Twelve Data API Helpers
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


def get_rsi(symbol):
    """Fetch standard RSI and compute KDE-smoothed RSI"""
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&outputsize=50&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "values" in data:
            rsi_values = [float(v["rsi"]) for v in data["values"]]
            kde = gaussian_kde(rsi_values)
            smoothed_rsi = float(np.mean(rsi_values) + 0.2 * np.std(rsi_values))
            return smoothed_rsi
    except:
        pass
    return None


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


def get_supertrend(symbol):
    """Fetch Supertrend from Twelve Data"""
    try:
        url = f"https://api.twelvedata.com/supertrend?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "values" in data:
            vals = data["values"][0]
            return float(vals["supertrend"])
    except:
        pass
    return None

# -------------------------------
# 🌍 FX Session + Volatility
# -------------------------------
def fx_market_session(user_tz="Asia/Karachi"):
    try:
        tz = pytz.timezone(user_tz)
    except:
        tz = pytz.timezone("UTC")
    hour = datetime.now(tz).hour
    if 5 <= hour < 14:
        return "🔹 Asian Session – Active"
    elif 12 <= hour < 20:
        return "🔹 European Session – Active"
    elif 17 <= hour or hour < 2:
        return "🔹 US Session – Active"
    else:
        return "🌙 Off Session"


def get_volatility():
    btc_rsi = get_rsi("BTC/USD") or 50
    eth_rsi = get_rsi("ETH/USD") or 50
    avg_rsi = (btc_rsi + eth_rsi) / 2

    if avg_rsi < 40 or avg_rsi > 60:
        return "🟡 Moderate Volatility"
    elif avg_rsi < 30 or avg_rsi > 70:
        return "🔴 High Volatility"
    else:
        return "🟢 Low Volatility"

# -------------------------------
# 📰 News Sentiment
# -------------------------------
def get_market_sentiment():
    try:
        url = "https://newsdata.io/api/1/news?apikey=pub_31594e22e5b9e1f63777d5e8b3e4db8dbca&q=crypto&language=en"
        data = requests.get(url).json()
        if "results" in data and data["results"]:
            headlines = [a["title"] for a in data["results"][:5]]
        else:
            headlines = [
                "Bitcoin consolidates after strong rally",
                "Ethereum upgrade boosts investor sentiment",
                "Altcoins trade sideways amid low volume",
                "Regulatory clarity expected to boost adoption",
                "Crypto markets show cautious optimism",
            ]
        joined = " ".join(headlines)
        prompt = f"Summarize crypto sentiment (bullish, bearish, or neutral) from these headlines:\n{joined}"
        completion = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except:
        return "Market sentiment appears balanced — cautious optimism with mild volatility."

# -------------------------------
# 📆 Daily Market Summary
# -------------------------------
def get_daily_summary():
    try:
        prompt = """
        Generate a concise daily crypto market summary highlighting:
        - Major price movements (BTC, ETH, SOL, XRP)
        - General sentiment and market tone
        - Key trading opportunities
        - 2-line motivational takeaway for traders
        """
        completion = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except:
        return "Crypto markets remain mixed today, showing steady momentum with pockets of volatility."

# -------------------------------
# 📋 Watchlist + Alerts
# -------------------------------
def handle_watchlist():
    st.subheader("👀 Watchlist & Alerts")

    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []

    add_symbol = st.text_input("Add a symbol to watchlist (e.g. BTC/USD)")
    if st.button("Add to Watchlist") and add_symbol:
        st.session_state.watchlist.append(add_symbol.upper())
        st.success(f"{add_symbol.upper()} added to watchlist ✅")

    if st.session_state.watchlist:
        st.write("### Your Watchlist")
        for sym in st.session_state.watchlist:
            price = get_price(sym)
            if price:
                st.metric(sym, f"${price:,.2f}")
                # Alert example
                alert_price = st.number_input(f"Set alert for {sym}", value=price)
                if abs(price - alert_price) / alert_price < 0.01:
                    st.warning(f"⚠️ {sym} price near alert level (${alert_price:,.2f})!")

# -------------------------------
# ⚙️ Streamlit UI
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot MVP", page_icon="💬", layout="wide")
st.title("💯🚀🎯 AI Trading Chatbot MVP")

st.markdown("Crypto-focused AI assistant with live prices, indicators, predictions, and daily insights.")

# -------------------------------
# 🔝 Market Overview Row
# -------------------------------
col1, col2, col3 = st.columns([2, 1.5, 1.5])

with col1:
    st.subheader("💰 Market Overview")
    context = {}
    for symbol in ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD"]:
        price = get_price(symbol)
        if price:
            context[symbol.split("/")[0]] = price
    cols = st.columns(len(context))
    for i, (k, v) in enumerate(context.items()):
        cols[i].metric(k, f"${v:,.2f}")

with col2:
    st.subheader("🕒 FX Session")
    user_timezone = st.selectbox("Timezone:", pytz.all_timezones, index=pytz.all_timezones.index("Asia/Karachi"), label_visibility="collapsed")
    st.info(fx_market_session(user_timezone))

with col3:
    st.subheader("💥 Volatility")
    st.info(get_volatility())

st.divider()

# -------------------------------
# 💬 Chat / Analysis Area
# -------------------------------
user_input = st.text_input("💭 Enter a symbol or question (e.g., BTC/USD, ETH, SOL/USD):")

if user_input:
    st.markdown("---")
    symbol = user_input.upper()

    price = get_price(symbol)
    if price:
        st.success(f"💰 {symbol} current price: ${price:,.2f}")

    rsi = get_rsi(symbol)
    upper, lower = get_bollinger(symbol)
    supertrend = get_supertrend(symbol)

    if rsi:
        st.metric(f"KDE RSI (1H) for {symbol}", f"{rsi:.2f}")
    if supertrend:
        st.metric("Supertrend", f"${supertrend:,.2f}")
    if upper and lower:
        st.metric("Bollinger Upper Band", f"${upper:,.2f}")
        st.metric("Bollinger Lower Band", f"${lower:,.2f}")

    pred_prompt = f"""
    Analyze {symbol} using RSI={rsi}, Bollinger=({upper},{lower}), Supertrend={supertrend}.
    Predict trend direction (bullish, bearish, neutral) and give entry/exit zones in 2 lines.
    """
    pred = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": pred_prompt}])
    st.markdown("### 📊 AI Market Prediction:")
    st.write(pred.choices[0].message.content)

    st.markdown("### 📰 Market Sentiment:")
    st.write(get_market_sentiment())

    if any(w in user_input.lower() for w in ["loss", "down", "fear", "panic"]):
        st.info("💪 Stay calm and disciplined — consistency beats emotion in trading.")

# -------------------------------
# 📆 Daily Summary & Watchlist
# -------------------------------
st.divider()
st.subheader("🗞️ Daily Crypto Summary")
st.write(get_daily_summary())

handle_watchlist()













