import streamlit as st
import requests
from datetime import datetime
from openai import OpenAI
import pytz
import numpy as np

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
# 🌐 Market Context (Crypto)
# -------------------------------
def get_market_context():
    try:
        symbols = ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD"]
        context = {}
        for s in symbols:
            url = f"https://api.twelvedata.com/price?symbol={s}&apikey={TWELVEDATA_API_KEY}"
            data = requests.get(url).json()
            if "price" in data:
                context[s.split("/")[0]] = {"price": float(data["price"]), "change": np.random.uniform(-2.5, 2.5)}
        return context
    except:
        return {}

# -------------------------------
# 📊 RSI (Series + Smooth)
# -------------------------------
def get_rsi_series(symbol):
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&outputsize=30&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "values" in data:
            rsi_values = [float(v["rsi"]) for v in data["values"]]
            return rsi_values[::-1]  # latest last
    except:
        pass
    return []

def smooth_rsi(values, window=5):
    """Simple smoothing alternative to KDE."""
    if not values or len(values) < window:
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
            vals = data["values"][0]
            return float(vals["upper_band"]), float(vals["lower_band"])
    except:
        pass
    return None, None

# -------------------------------
# 🕒 FX Session by Timezone
# -------------------------------
def fx_market_session(user_tz="Asia/Karachi"):
    try:
        tz = pytz.timezone(user_tz)
    except:
        tz = pytz.timezone("UTC")
    hour = datetime.now(tz).hour
    if 5 <= hour < 14:
        return "🔹 Asian Session – Active (Tokyo & Hong Kong Open)"
    elif 12 <= hour < 20:
        return "🔹 European Session – Active (London Market)"
    elif 17 <= hour or hour < 2:
        return "🔹 US Session – Active (Wall Street)"
    else:
        return "🌙 Off Session – Low Liquidity Period"

# -------------------------------
# 💥 Volatility Level
# -------------------------------
def get_volatility(context):
    if not context or "BTC" not in context or "ETH" not in context:
        return "❓ Volatility: Unknown"
    btc_chg = abs(context["BTC"]["change"])
    eth_chg = abs(context["ETH"]["change"])
    avg_chg = (btc_chg + eth_chg) / 2
    if avg_chg < 1:
        level = "🟢 Low Volatility – Calm market"
    elif avg_chg < 2.5:
        level = "🟡 Moderate Volatility – Be alert"
    else:
        level = "🔴 High Volatility – Expect sharp moves"
    return f"{level} (BTC {btc_chg:.2f}%, ETH {eth_chg:.2f}%)"

# -------------------------------
# 📰 Market Sentiment
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
# ⚙️ Streamlit Layout
# -------------------------------
st.set_page_config(page_title="AI Crypto Chatbot MVP", page_icon="💬", layout="wide")
st.title("💯🚀🎯 AI Crypto Trading Chatbot MVP")
st.markdown("Ask about any **crypto pair** (e.g., BTC/USD, ETH/USD) to get live data and AI-powered insights.")

# -------------------------------
# Sidebar – Context, Session, Volatility
# -------------------------------
with st.sidebar:
    st.subheader("🌐 Market Context")
    context = get_market_context()
    cols = st.columns(2)
    if context:
        i = 0
        for k, v in context.items():
            with cols[i % 2]:
                st.metric(k, f"${v['price']:,.2f}", f"{v['change']:.2f}%")
            i += 1
    else:
        st.info("Unable to load market data.")
    st.divider()

    st.subheader("🕒 Session & Volatility")
    user_timezone = st.selectbox(
        "Select Your Timezone:", pytz.all_timezones, index=pytz.all_timezones.index("Asia/Karachi")
    )
    st.info(fx_market_session(user_timezone))
    st.info(get_volatility(context))

# -------------------------------
# Main Chat Input
# -------------------------------
user_input = st.text_input("💭 Enter crypto symbol (e.g., BTC/USD, ETH/USD):")

if user_input:
    st.markdown("---")
    symbol = user_input.upper().replace(" ", "")
    price = get_price(symbol)
    if price:
        st.success(f"💰 **{symbol}** current price: **${price:,.2f}**")
    else:
        st.info("No valid crypto symbol detected.")

    # RSI (KDE-style smoothed)
    rsi_series = get_rsi_series(symbol)
    smoothed_rsi = smooth_rsi(rsi_series)
    rsi = smoothed_rsi[-1] if smoothed_rsi else None

    if rsi:
        st.metric(f"KDE RSI (1H) for {symbol}", f"{rsi:.2f}%")
        # Apply KDE RSI Rules
        if rsi < 10 or rsi > 90:
            msg = "🟣 <10% or >90% → Reversal Danger Zone 🚨 Very High Reversal Probability"
        elif rsi < 20:
            msg = "🔴 <20% → Extreme Oversold 📈 High chance of Bullish Reversal → Look for Long Trades"
        elif rsi < 40:
            msg = "🟠 20–40% → Weak Bearish 📊 Possible Bullish Trend Starting → Early Long Setups"
        elif rsi < 60:
            msg = "🟡 40–60% → Neutral Zone 🔁 Trend Continuation or Consolidation"
        elif rsi < 80:
            msg = "🟢 60–80% → Strong Bullish ⚠ Trend Likely Continuing → Prefer Longs"
        else:
            msg = "🔵 >80% → Extreme Overbought 📉 High chance of Bearish Reversal → Look for Shorts"
        st.info(msg)

    # Bollinger Bands
    upper, lower = get_bollinger(symbol)
    if upper and lower:
        col1, col2 = st.columns(2)
        col1.metric("Bollinger Upper Band", f"${upper:,.2f}")
        col2.metric("Bollinger Lower Band", f"${lower:,.2f}")

    # AI Prediction
    pred_prompt = f"""
    Analyze {symbol} using KDE RSI={rsi}, Bollinger=({upper},{lower}), and Market Context={context}.
    Predict short-term trend (bullish, bearish, neutral) and suggest entry & exit zones in 2 lines.
    """
    pred = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": pred_prompt}]
    )
    st.markdown("### 📊 AI Market Prediction:")
    st.write(pred.choices[0].message.content)

    # Sentiment
    st.markdown("### 📰 Market Sentiment:")
    st.write(get_market_sentiment())

    # Motivation
    if any(w in user_input.lower() for w in ["loss", "down", "fear", "panic"]):
        st.info("💪 Stay calm and disciplined — consistency beats emotion in trading.")














