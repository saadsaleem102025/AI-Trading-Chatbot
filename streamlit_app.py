import streamlit as st
import requests
from openai import OpenAI
import datetime

# -------------------------------
# 🔑 API Keys
# -------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
TWELVEDATA_API_KEY = st.secrets["TWELVEDATA_API_KEY"]

# -------------------------------
# 📈 Function to get real-time price
# -------------------------------
def get_price(symbol):
    """Fetch real-time price for crypto, stock, or forex symbol using Twelve Data API"""
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol.upper()}&apikey={TWELVEDATA_API_KEY}"
        response = requests.get(url)
        data = response.json()
        if "price" in data:
            return float(data["price"])
    except Exception as e:
        st.error(f"Error fetching price for {symbol}: {e}")
    return None


# -------------------------------
# 🌐 Market Context Panel
# -------------------------------
def get_market_context():
    """Fetch global crypto market context from CoinGecko"""
    url = "https://api.coingecko.com/api/v3/global"
    try:
        data = requests.get(url).json()['data']
        btc_dominance = round(data['market_cap_percentage']['btc'], 2)
        total_market_cap = round(data['total_market_cap']['usd'] / 1e9, 2)
        return btc_dominance, total_market_cap
    except:
        return None, None


# -------------------------------
# 📊 RSI Indicator (KDE RSI Rules)
# -------------------------------
def get_rsi(symbol):
    """Fetch RSI (Relative Strength Index) from Twelve Data"""
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if 'values' in data:
            return float(data['values'][0]['rsi'])
    except:
        return None
    return None


def interpret_rsi(rsi):
    """Interpret RSI based on KDE RSI rules"""
    if rsi is None:
        return "RSI unavailable"
    if rsi < 10 or rsi > 90:
        return "🟣 Reversal Danger Zone – Very High Reversal Probability"
    elif rsi < 20:
        return "🔴 Extreme Oversold – Possible Bullish Reversal"
    elif 20 <= rsi < 40:
        return "🟠 Weak Bearish – Momentum shifting upward"
    elif 40 <= rsi < 60:
        return "🟡 Neutral Zone – Consolidation or continuation likely"
    elif 60 <= rsi < 80:
        return "🟢 Strong Bullish – Trend continuation likely"
    elif rsi >= 80:
        return "🔵 Extreme Overbought – Bearish reversal risk"
    return "Neutral"


# -------------------------------
# 📉 Bollinger Bands & Supertrend
# -------------------------------
def get_bollinger(symbol):
    """Fetch Bollinger Bands data from Twelve Data"""
    try:
        url = f"https://api.twelvedata.com/bbands?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if 'values' in data:
            latest = data['values'][0]
            return float(latest['upper_band']), float(latest['lower_band'])
    except:
        return None, None
    return None, None


def get_supertrend(symbol):
    """Fetch Supertrend from Twelve Data"""
    try:
        url = f"https://api.twelvedata.com/supertrend?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if 'values' in data:
            latest = data['values'][0]
            return float(latest['supertrend'])
    except:
        return None
    return None


# -------------------------------
# 🕒 FX Market Session Logic
# -------------------------------
def fx_market_session():
    """Determine current FX session based on Pakistan time (PKT)"""
    now = datetime.datetime.now().time()
    sessions = {
        "Asian": (datetime.time(5, 0), datetime.time(14, 0)),
        "European": (datetime.time(12, 0), datetime.time(20, 0)),
        "US": (datetime.time(17, 0), datetime.time(1, 0)),
    }
    for name, (start, end) in sessions.items():
        if start <= now <= end or (end < start and (now >= start or now <= end)):
            return name
    return "Off-hours"


# -------------------------------
# 💬 Streamlit UI
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot MVP", page_icon="💬", layout="centered")
st.title("💯🚀🎯 AI Trading Chatbot MVP")
st.markdown("Ask about any **crypto**, **stock**, or **forex** pair to get live data and AI insights.")

# Sidebar: Market Context
with st.sidebar:
    st.subheader("🌐 Market Context")
    btc_d, mcap = get_market_context()
    if btc_d and mcap:
        st.metric("BTC Dominance", f"{btc_d}%")
        st.metric("Total Market Cap", f"${mcap}B")
    else:
        st.info("Unable to load market context right now.")

    st.subheader("🕒 FX Market Session")
    st.write(f"**Current Session:** {fx_market_session()}")


# -------------------------------
# 🧠 Chat Logic
# -------------------------------
user_input = st.text_input("💭 Type a crypto, forex, or stock symbol or question:")

if user_input:
    st.markdown("---")

    # Detect and show price
    words = user_input.upper().replace(",", " ").split()
    prices_found = False
    for w in words:
        price = get_price(w)
        if price:
            st.success(f"💰 **{w}** current price: **${price}**")
            prices_found = True

            # Indicators
            rsi = get_rsi(w)
            bb_upper, bb_lower = get_bollinger(w)
            supertrend = get_supertrend(w)

            if rsi:
                st.metric(f"RSI (1H) for {w}", f"{rsi:.2f}")
                st.caption(interpret_rsi(rsi))

            if bb_upper and bb_lower:
                st.write(f"📊 **Bollinger Bands** → Upper: ${bb_upper:.2f}, Lower: ${bb_lower:.2f}")

            if supertrend:
                st.write(f"📈 **Supertrend Level:** ${supertrend:.2f}")

    # -------------------------------
    # 🤖 AI Insight Logic
    # -------------------------------
    if prices_found:
        prediction_prompt = f"""
Analyze {user_input}.
Include RSI, Bollinger Bands, and Supertrend interpretations.
Provide a short, actionable forecast with entry/exit suggestions.
Also mention BTC Dominance ({btc_d}%) and Market Cap (${mcap}B) impact.
"""
        with st.spinner("Generating AI analysis..."):
            prediction = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional market analyst."},
                    {"role": "user", "content": prediction_prompt},
                ],
            )
        st.markdown("### 🤖 AI Market Prediction:")
        st.write(prediction.choices[0].message.content)

    else:
        # 🧠 Smart fallback when no price found
        with st.spinner("Analyzing market context..."):
            smart_prompt = f"""
You are a professional trading analyst.
The user asked: "{user_input}"

1. Identify what instrument (stock, crypto, forex) this refers to.
2. Use known current market trends to infer direction (bullish, bearish, neutral).
3. Include short-term technical bias (support/resistance, momentum).
4. Provide a 2-line trade idea (entry/exit, risk tip).
5. End with a one-line sentiment summary.
"""
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert financial AI providing concise trade forecasts."},
                    {"role": "user", "content":







