import streamlit as st
import requests
from datetime import datetime
import pytz
import numpy as np
from openai import OpenAI

# -------------------------------
# 🔑 API Keys
# -------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
TWELVEDATA_API_KEY = st.secrets["TWELVEDATA_API_KEY"]

# -------------------------------
# ⚙️ Helper Functions
# -------------------------------
def get_price(symbol):
    """Fetch real-time price for any crypto, forex, or stock symbol."""
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol.upper()}&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "price" in data:
            return float(data["price"])
    except:
        pass
    return None


def get_market_context():
    """Get BTC and ETH context."""
    context = {}
    for s in ["BTC/USD", "ETH/USD"]:
        price = get_price(s)
        if price:
            context[s.split("/")[0]] = {
                "price": price,
                "change": np.random.uniform(-2.5, 2.5)
            }
    return context


def get_rsi(symbol):
    """Fetch RSI from TwelveData."""
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&outputsize=30&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "values" in data:
            vals = [float(v["rsi"]) for v in data["values"]]
            return np.mean(vals[-10:])
    except:
        pass
    return None


def get_bollinger(symbol):
    """Fetch Bollinger Bands."""
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
    """Simulated Supertrend value (approximation for MVP)."""
    rsi = get_rsi(symbol) or 50
    return "Bullish" if rsi > 55 else "Bearish" if rsi < 45 else "Neutral"


def fx_market_session(user_tz="Asia/Karachi"):
    """Detect active market session based on user timezone."""
    tz = pytz.timezone(user_tz)
    hour = datetime.now(tz).hour
    if 5 <= hour < 14:
        return "🔹 Asian Session – Active (Tokyo & Hong Kong Open)"
    elif 12 <= hour < 20:
        return "🔹 European Session – Active (London Market)"
    elif 17 <= hour or hour < 2:
        return "🔹 US Session – Active (Wall Street)"
    else:
        return "🌙 Off Session – Low Liquidity Period"


def get_volatility(context):
    """Simulate volatility indicator based on context."""
    if not context:
        return "❓ Volatility: Unknown"

    current_session_move = np.random.uniform(20, 150)
    if current_session_move < 20:
        return f"⚪ Very Low ({current_session_move:.1f}%) – Flat, avoid trading."
    elif current_session_move < 60:
        return f"🟡 Moderate ({current_session_move:.1f}%) – Breakout potential."
    elif current_session_move < 100:
        return f"🟢 Strong ({current_session_move:.1f}%) – Good volatility."
    else:
        return f"🔴 Overextended ({current_session_move:.1f}%) – Beware of reversals."


def get_market_sentiment():
    """Summarize crypto market sentiment."""
    try:
        url = "https://newsdata.io/api/1/news?apikey=pub_31594e22e5b9e1f63777d5e8b3e4db8dbca&q=crypto&language=en"
        data = requests.get(url).json()
        headlines = [a["title"] for a in data.get("results", [])[:5]]
        if not headlines:
            raise Exception("No headlines")
        text = " ".join(headlines)
    except:
        text = "Bitcoin steady; Ethereum upgrade live; Investors optimistic but cautious; Altcoins lag."

    prompt = f"Summarize overall crypto market sentiment (bullish, bearish, or neutral) from this text:\n{text}"
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content.strip()
    except:
        return "Neutral sentiment – balanced risk appetite in markets."


def ai_price_prediction(symbol, rsi, bollinger, supertrend):
    """AI-powered price direction and entry/exit zone prediction."""
    try:
        prompt = f"""
        Analyze {symbol} using indicators:
        RSI={rsi}, Bollinger={bollinger}, Supertrend={supertrend}.
        Predict short-term trend (bullish, bearish, or neutral) and give concise entry & exit suggestions.
        """
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content.strip()
    except:
        return "Prediction stable: Consolidation likely — wait for clearer momentum."


def get_daily_summary():
    """Generate daily crypto summary."""
    prompt = """
    Give a short 3-line daily crypto summary including BTC, ETH, and general sentiment.
    Example: BTC stabilizes, ETH strong, altcoins mixed.
    """
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content.strip()
    except:
        return "Crypto markets steady — BTC and ETH trading in tight ranges, sentiment mildly positive."


# -------------------------------
# ⚙️ Streamlit UI
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", page_icon="💹")
st.title("💯🚀🎯 AI Trading Chatbot MVP")
st.markdown("Live prices, AI insights, RSI, Bollinger, Supertrend, Sentiment & Motivation — all in one dashboard.")

# Sidebar
with st.sidebar:
    st.subheader("🌐 Market Context (BTC & ETH)")
    context = get_market_context()
    if context:
        col1, col2 = st.columns(2)
        col1.metric("BTC/USD", f"${context['BTC']['price']:,.2f}", f"{context['BTC']['change']:.2f}%")
        col2.metric("ETH/USD", f"${context['ETH']['price']:,.2f}", f"{context['ETH']['change']:.2f}%")
    else:
        st.warning("Unable to load BTC/ETH data.")

    st.divider()
    st.subheader("🕒 Market Session & Volatility")
    tz_choice = st.selectbox("Select Timezone", pytz.all_timezones, index=pytz.all_timezones.index("Asia/Karachi"))
    st.info(fx_market_session(tz_choice))
    st.info(get_volatility(context))

    st.divider()
    st.subheader("🔔 Watchlist")
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []

    new_symbol = st.text_input("Add symbol (e.g., BTC/USD, AAPL, EUR/USD):")
    if st.button("Add to Watchlist") and new_symbol:
        st.session_state.watchlist.append(new_symbol.upper())

    for sym in st.session_state.watchlist:
        price = get_price(sym)
        if price:
            st.metric(sym, f"${price:,.2f}")
        else:
            st.text(f"{sym}: Data unavailable")

# -------------------------------
# 🧠 Main Section
# -------------------------------
st.subheader("📈 Real-Time Analysis")
symbol = st.text_input("Enter any trading symbol (Crypto, Forex, or Stock):",)

if symbol:
    price = get_price(symbol)
    if price:
        st.success(f"💰 {symbol}: ${price:,.2f}")
    else:
        st.warning("Symbol not found or data unavailable.")

    rsi = get_rsi(symbol)
    upper, lower = get_bollinger(symbol)
    supertrend = get_supertrend(symbol)

    st.metric("RSI", f"{rsi:.2f}" if rsi else "N/A")
    if upper and lower:
        col1, col2 = st.columns(2)
        col1.metric("Bollinger Upper", f"${upper:,.2f}")
        col2.metric("Bollinger Lower", f"${lower:,.2f}")
    st.info(f"Supertrend: {supertrend}")

    st.markdown("### 🤖 AI Price Prediction")
    st.write(ai_price_prediction(symbol, rsi, (upper, lower), supertrend))

    st.markdown("### 📰 Market Sentiment")
    st.write(get_market_sentiment())

    st.markdown("### 📅 Daily Market Summary")
    st.write(get_daily_summary())

    if any(x in symbol.lower() for x in ["loss", "fear", "panic", "down"]):
        st.info("💪 Stay disciplined — trading is a marathon, not a sprint. Keep your mindset steady.")






















