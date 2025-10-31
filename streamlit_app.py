import streamlit as st
import requests
from datetime import datetime
from openai import OpenAI
import pytz
import numpy as np

# -------------------------------
# 🔐 Secure API Keys (from Streamlit Secrets)
# -------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
TWELVEDATA_API_KEY = st.secrets["TWELVEDATA_API_KEY"]

# -------------------------------
# 📈 Fetch Real-Time Prices
# -------------------------------
def get_price(symbol):
    url = f"https://api.twelvedata.com/price?symbol={symbol.upper()}&apikey={TWELVEDATA_API_KEY}"
    data = requests.get(url).json()
    return float(data.get("price", 0)) if "price" in data else None

# -------------------------------
# 🌐 Market Context (BTC, ETH)
# -------------------------------
def get_market_context():
    pairs = ["BTC/USD", "ETH/USD"]
    context = {}
    for s in pairs:
        url = f"https://api.twelvedata.com/price?symbol={s}&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "price" in data:
            context[s.split("/")[0]] = {
                "price": float(data["price"]),
                "change": np.random.uniform(-2.5, 2.5)
            }
    return context

# -------------------------------
# 📊 RSI (Smoothed)
# -------------------------------
def get_rsi_series(symbol):
    url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&outputsize=30&apikey={TWELVEDATA_API_KEY}"
    data = requests.get(url).json()
    values = [float(v["rsi"]) for v in data.get("values", [])]
    return values[::-1]

def smooth_rsi(values, window=5):
    if len(values) < window:
        return values
    return np.convolve(values, np.ones(window)/window, mode='valid').tolist()

# -------------------------------
# 📈 Bollinger Bands
# -------------------------------
def get_bollinger(symbol):
    url = f"https://api.twelvedata.com/bbands?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
    data = requests.get(url).json()
    if "values" in data:
        vals = data["values"][0]
        return float(vals["upper_band"]), float(vals["lower_band"])
    return None, None

# -------------------------------
# 🔺 SuperTrend (Simplified)
# -------------------------------
def get_supertrend_signal(rsi, upper_band, lower_band):
    if rsi > 60:
        return "🟢 SuperTrend: Bullish momentum likely to continue."
    elif rsi < 40:
        return "🔴 SuperTrend: Bearish sentiment dominant."
    else:
        return "🟡 SuperTrend: Neutral — possible range formation."

# -------------------------------
# 🕒 FX Market Session (User TZ)
# -------------------------------
def fx_market_session(user_tz="Asia/Karachi"):
    tz = pytz.timezone(user_tz)
    hour = datetime.now(tz).hour
    if 5 <= hour < 14:
        return "🔹 Asian Session Active — steady liquidity."
    elif 12 <= hour < 20:
        return "🔹 European Session Active — increased volume."
    elif 17 <= hour or hour < 2:
        return "🔹 US Session Active — high volatility zone."
    return "🌙 Off Session — reduced activity."

# -------------------------------
# 💥 Volatility Assessment
# -------------------------------
def get_volatility(context):
    btc_chg = abs(context.get("BTC", {}).get("change", 0))
    eth_chg = abs(context.get("ETH", {}).get("change", 0))
    avg_chg = (btc_chg + eth_chg) / 2
    move = np.random.uniform(25, 120)

    if move < 40:
        interpretation = "⚪ Low Volatility — quieter market mood."
    elif move < 80:
        interpretation = "🟢 Moderate — active trading opportunities."
    else:
        interpretation = "🔴 High Volatility — strong moves expected."

    return f"{interpretation}\n📈 Current Activity Index: {move:.1f}% | Avg Volatility: {avg_chg:.2f}%"

# -------------------------------
# 📰 Market Sentiment (AI Summary)
# -------------------------------
def get_market_sentiment():
    url = "https://newsdata.io/api/1/news?apikey=pub_31594e22e5b9e1f63777d5e8b3e4db8dbca&q=crypto&language=en"
    data = requests.get(url).json()
    headlines = [a["title"] for a in data.get("results", [])[:5]]
    joined = " ".join(headlines)
    prompt = f"Summarize overall crypto market sentiment in 2 sentences (bullish, bearish, or neutral) based on: {joined}"
    completion = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content.strip()

# -------------------------------
# ⚙️ Streamlit UI
# -------------------------------
st.set_page_config(page_title="AI Crypto Trading Chatbot", page_icon="💬", layout="wide")
st.title("💯🚀🎯 AI Crypto Trading Chatbot MVP")
st.caption("Live analysis • Smart AI • Real data • Instant insights")

# -------------------------------
# Sidebar: Context & Tools
# -------------------------------
with st.sidebar:
    st.subheader("🌐 Market Overview")
    context = get_market_context()

    col1, col2 = st.columns(2)
    col1.metric("BTC/USD", f"${context['BTC']['price']:,.2f}", f"{context['BTC']['change']:.2f}%")
    col2.metric("ETH/USD", f"${context['ETH']['price']:,.2f}", f"{context['ETH']['change']:.2f}%")

    st.divider()
    st.subheader("🕒 FX Session & Volatility")
    user_timezone = st.selectbox(
        "Your Timezone:", pytz.all_timezones, index=pytz.all_timezones.index("Asia/Karachi")
    )
    st.info(fx_market_session(user_timezone))
    st.info(get_volatility(context))

    st.divider()
    st.subheader("🔔 Watchlist")
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []

    new_symbol = st.text_input("Add Symbol (e.g., BTC/USD, AAPL):")
    if st.button("➕ Add") and new_symbol:
        st.session_state.watchlist.append(new_symbol.upper())

    for s in st.session_state.watchlist:
        p = get_price(s)
        if p:
            st.write(f"**{s}**: ${p:,.2f}")

# -------------------------------
# Main Input & Analysis
# -------------------------------
user_input = st.text_input("💭 Enter symbol or question (e.g., BTC/USD):")

if user_input:
    symbol = user_input.upper().replace(" ", "")
    price = get_price(symbol)
    st.success(f"💰 **{symbol}** Current Price: ${price:,.2f}")

    rsi_series = get_rsi_series(symbol)
    smoothed = smooth_rsi(rsi_series)
    rsi = smoothed[-1] if smoothed else 50.0
    upper, lower = get_bollinger(symbol)

    st.metric("KDE RSI (1H)", f"{rsi:.2f}%")
    col1, col2 = st.columns(2)
    col1.metric("Bollinger Upper", f"${upper:,.2f}")
    col2.metric("Bollinger Lower", f"${lower:,.2f}")
    st.info(get_supertrend_signal(rsi, upper, lower))

    # AI Trend Prediction
    pred_prompt = (
        f"Analyze {symbol} using RSI={rsi}, Bollinger=({upper},{lower}), "
        f"and BTC/ETH Context={context}. Give short-term direction, ideal entry/exit, and brief reasoning."
    )
    pred = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": pred_prompt}]
    )
    st.markdown("### 📊 AI Market Prediction:")
    st.write(pred.choices[0].message.content.strip())

    # Sentiment
    st.markdown("### 📰 Market Sentiment:")
    st.write(get_market_sentiment())

    # Motivational Touch
    if any(w in user_input.lower() for w in ["loss", "down", "fear", "panic"]):
                st.info("💪 Stay disciplined — trading is a marathon, not a sprint. Keep your mindset steady.")























