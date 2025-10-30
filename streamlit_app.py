import streamlit as st
import requests
from datetime import datetime, time
from openai import OpenAI

# -------------------------------
# 🔑 API KEYS
# -------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
TWELVEDATA_API_KEY = st.secrets["TWELVEDATA_API_KEY"]

# -------------------------------
# 📈 PRICE FUNCTION
# -------------------------------
def get_price(symbol):
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol.upper()}&apikey={TWELVEDATA_API_KEY}"
        r = requests.get(url).json()
        if "price" in r:
            return float(r["price"])
    except Exception as e:
        st.error(f"Error fetching {symbol}: {e}")
    return None

# -------------------------------
# 🌐 MARKET CONTEXT (COINGECKO)
# -------------------------------
def get_market_context():
    try:
        data = requests.get("https://api.coingecko.com/api/v3/global").json()["data"]
        btc_d = round(data["market_cap_percentage"]["btc"], 2)
        total_cap = round(data["total_market_cap"]["usd"] / 1e9, 2)
        return btc_d, total_cap
    except:
        return None, None

# -------------------------------
# 📊 RSI, BOLLINGER, SUPERTREND
# -------------------------------
def get_rsi(symbol):
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        d = requests.get(url).json()
        if "values" in d:
            return float(d["values"][0]["rsi"])
    except:
        return None
    return None

def get_bollinger(symbol):
    try:
        url = f"https://api.twelvedata.com/bbands?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        d = requests.get(url).json()
        if "values" in d:
            v = d["values"][0]
            return float(v["upper_band"]), float(v["lower_band"])
    except:
        return None, None
    return None, None

def get_supertrend(symbol):
    try:
        url = f"https://api.twelvedata.com/supertrend?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        d = requests.get(url).json()
        if "values" in d:
            v = d["values"][0]
            return float(v["supertrend"])
    except:
        return None
    return None

# -------------------------------
# 🕐 FX MARKET SESSION (PKT)
# -------------------------------
def get_fx_session():
    now = datetime.now().time()

    def between(t1, t2):
        return t1 <= now <= t2

    if between(time(5, 0), time(14, 0)):
        return "🇯🇵 Asian Session (5:00 AM – 2:00 PM)", "Medium", "Tokyo & Hong Kong volatility"
    elif between(time(12, 0), time(20, 0)):
        return "🇪🇺 European Session (12:00 PM – 8:00 PM)", "High", "London Open hours"
    elif between(time(17, 0), time(1, 0)):
        return "🇺🇸 US Session (5:00 PM – 1:00 AM Next Day)", "High", "Wall Street active period"
    else:
        return "🌙 Low Volatility – Off Hours", "Low", "Session overlap ended"

# -------------------------------
# 🧠 KDE RSI INTERPRETATION
# -------------------------------
def interpret_rsi(rsi):
    if rsi is None:
        return "No RSI data available."
    if rsi < 10 or rsi > 90:
        return "🟣 <10% or >90% → Reversal Danger Zones 🚨 Very High Reversal Probability"
    elif rsi < 20:
        return "🔴 RSI <20% → Extreme Oversold 📈 High chance of Bullish Reversal → Look for long trades."
    elif rsi < 40:
        return "🟠 RSI 20–40% → Weak Bearish 📊 Possible Bullish Trend Starting → Early long setups."
    elif rsi < 60:
        return "🟡 RSI 40–60% → Neutral Zone 🔁 Trend continuation or consolidation."
    elif rsi < 80:
        return "🟢 RSI 60–80% → Strong Bullish ⚠ Trend likely continuing → Prefer longs but watch exhaustion."
    else:
        return "🔵 RSI >80% → Extreme Overbought 📉 High chance of Bearish Reversal → Look for shorts."

# -------------------------------
# 📰 SENTIMENT + MOTIVATION
# -------------------------------
def get_news_sentiment():
    try:
        data = requests.get("https://cryptopanic.com/api/v1/posts/?auth_token=demo&kind=news").json()
        headlines = " ".join([p["title"] for p in data["results"][:5]])
        prompt = f"Summarize the crypto market sentiment (bullish/bearish/neutral) from these headlines:\n{headlines}"
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except:
        return "Could not fetch sentiment."

# -------------------------------
# 💬 STREAMLIT UI
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot MVP", page_icon="💬", layout="centered")
st.title("💯🚀🎯 AI Trading Chatbot MVP")
st.markdown("Ask about any **crypto**, **stock**, or **forex** pair to get live data and AI insights.")

user_input = st.text_input("💭 Enter symbol or question:")

# -------------------------------
# 🌐 SIDEBAR: MARKET CONTEXT
# -------------------------------
with st.sidebar:
    st.subheader("🌐 Market Context")
    btc_d, mcap = get_market_context()
    if btc_d and mcap:
        st.metric("BTC Dominance", f"{btc_d}%")
        st.metric("Total Market Cap", f"${mcap} B")
    else:
        st.info("Unable to load market data.")

    session, volatility, note = get_fx_session()
    st.markdown(f"**🕐 FX Session:** {session}")
    st.caption(f"Volatility: {volatility} — {note}")

# -------------------------------
# 🧩 MAIN CHAT LOGIC
# -------------------------------
if user_input:
    st.markdown("---")
    words = user_input.upper().replace(",", " ").split()
    prices_found = False

    for w in words:
        price = get_price(w)
        if price:
            st.success(f"💰 **{w}** = ${price}")
            prices_found = True

            # RSI, Bollinger, Supertrend
            rsi = get_rsi(w)
            upper, lower = get_bollinger(w)
            supertrend = get_supertrend(w)

            if rsi:
                st.metric("RSI (1H)", f"{rsi:.2f}")
                st.write(interpret_rsi(rsi))
            if upper and lower:
                st.info(f"📊 **Bollinger Bands:** Upper = {upper:.2f}, Lower = {lower:.2f}")
            if supertrend:
                st.info(f"📈 **Supertrend (1H):** {supertrend:.2f}")

            if btc_d and mcap:
                prompt = (
                    f"Analyze {w} with RSI={rsi}, Bollinger=({upper},{lower}), "
                    f"Supertrend={supertrend}, BTC Dominance={btc_d}%, Market Cap=${mcap} B. "
                    "Predict trend direction (bullish/bearish/neutral) and give 2-line entry/exit suggestion."
                )
                pred = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                st.markdown("### 📊 AI Market Prediction:")
                st.write(pred.choices[0].message.content)

    if not prices_found:
        with st.spinner("Analyzing market context..."):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an AI trading assistant providing cross-market insights."},
                    {"role": "user", "content": user_input}
                ]
            )
        st.markdown("### 🤖 AI Insight:")
        st.write(resp.choices[0].message.content)

    # Sentiment + Motivation
    st.markdown("---")
    st.markdown("### 📰 Market Sentiment:")
    st.write(get_news_sentiment())

    if any(x in user_input.lower() for x in ["loss", "down", "bad", "fear"]):
        st.info("💪 Stay calm and disciplined — consistency beats emotion in trading.")





