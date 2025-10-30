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
    except:
        pass
    return None

# -------------------------------
# 🌐 MARKET CONTEXT
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
# 📊 INDICATORS
# -------------------------------
def get_rsi(symbol):
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        d = requests.get(url).json()
        if "values" in d:
            return float(d["values"][0]["rsi"])
    except:
        pass
    return None

def get_bollinger(symbol):
    try:
        url = f"https://api.twelvedata.com/bbands?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        d = requests.get(url).json()
        if "values" in d:
            v = d["values"][0]
            return float(v["upper_band"]), float(v["lower_band"])
    except:
        pass
    return None, None

def get_supertrend(symbol):
    try:
        url = f"https://api.twelvedata.com/supertrend?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        d = requests.get(url).json()
        if "values" in d:
            return float(d["values"][0]["supertrend"])
    except:
        pass
    return None

# -------------------------------
# 🕐 FX SESSION (PKT)
# -------------------------------
def get_fx_session():
    now = datetime.now().time()
    def between(t1, t2): return t1 <= now <= t2

    if between(time(5, 0), time(14, 0)):
        return "🇯🇵 Asian (5 AM–2 PM)", "Medium"
    elif between(time(12, 0), time(20, 0)):
        return "🇪🇺 European (12 PM–8 PM)", "High"
    elif between(time(17, 0), time(23, 59)) or between(time(0, 0), time(1, 0)):
        return "🇺🇸 US (5 PM–1 AM)", "High"
    else:
        return "🌙 Off-Hours", "Low"

# -------------------------------
# 🧠 KDE RSI INTERPRETATION
# -------------------------------
def interpret_rsi(rsi):
    if rsi is None: return "No RSI data available."
    if rsi < 10 or rsi > 90:
        return "🟣 <10% or >90% → Reversal Danger Zone 🚨"
    elif rsi < 20:
        return "🔴 <20% → Extreme Oversold 📈 Possible Bullish Reversal."
    elif rsi < 40:
        return "🟠 20–40% → Weak Bearish 📊 Early Bullish Setup."
    elif rsi < 60:
        return "🟡 40–60% → Neutral 🔁 Consolidation or Continuation."
    elif rsi < 80:
        return "🟢 60–80% → Strong Bullish ⚠ Possible Exhaustion."
    else:
        return "🔵 >80% → Overbought 📉 Reversal Risk."

# -------------------------------
# 📰 SENTIMENT (no external API fail)
# -------------------------------
def get_news_sentiment():
    try:
        # Try CryptoPanic
        data = requests.get("https://cryptopanic.com/api/v1/posts/?auth_token=demo&kind=news", timeout=5).json()
        headlines = " ".join([p["title"] for p in data.get("results", [])[:5]])
        if headlines:
            prompt = f"Summarize crypto sentiment (bullish/bearish/neutral) from these headlines:\n{headlines}"
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content
    except:
        pass

    # fallback AI-only sentiment
    fallback_prompt = "Give a short 2-line summary of overall crypto market mood today (bullish/bearish/neutral)."
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": fallback_prompt}]
    )
    return resp.choices[0].message.content

# -------------------------------
# 💬 UI
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot MVP", page_icon="💬", layout="centered")
st.title("💯🚀🎯 AI Trading Chatbot MVP")
st.markdown("Ask about any **crypto**, **stock**, or **forex** pair to get live data and AI insights.")

user_input = st.text_input("💭 Enter symbol or question:")

# -------------------------------
# 🌐 SIDEBAR CONTEXT
# -------------------------------
with st.sidebar:
    st.subheader("🌐 Market Context")
    btc_d, mcap = get_market_context()
    if btc_d and mcap:
        st.metric("BTC Dominance", f"{btc_d}%")
        st.metric("Total Market Cap", f"${mcap} B")
    else:
        st.info("Context unavailable.")
    session, vol = get_fx_session()
    st.caption(f"🕐 {session} | Volatility: {vol}")

# -------------------------------
# ⚙ MAIN LOGIC
# -------------------------------
if user_input:
    st.markdown("---")
    stop_words = {"FOR", "OF", "THE", "PRICE", "SHOW", "WHAT", "IS", "TO"}
    words = [w for w in user_input.upper().replace(",", " ").split() if w not in stop_words]
    prices_found = False

    for w in words:
        price = get_price(w)
        if price:
            st.success(f"💰 **{w}** = ${price}")
            prices_found = True

            rsi = get_rsi(w)
            upper, lower = get_bollinger(w)
            supertrend = get_supertrend(w)

            if rsi: st.metric("RSI (1H)", f"{rsi:.2f}")
            st.write(interpret_rsi(rsi))
            if upper and lower:
                st.info(f"📊 Bollinger: Upper={upper:.2f}, Lower={lower:.2f}")
            if supertrend:
                st.info(f"📈 Supertrend: {supertrend:.2f}")

            if btc_d and mcap:
                prompt = (
                    f"Analyze {w} using RSI={rsi}, Bollinger=({upper},{lower}), "
                    f"Supertrend={supertrend}, BTC Dominance={btc_d}%, Market Cap=${mcap} B. "
                    "Predict trend (bullish/bearish/neutral) and give 2-line entry/exit zones."
                )
                pred = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                st.markdown("### 📊 AI Market Prediction:")
                st.write(pred.choices[0].message.content)

    if not prices_found:
        with st.spinner("Analyzing..."):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an AI trading assistant."},
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






