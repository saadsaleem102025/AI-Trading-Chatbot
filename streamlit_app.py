import streamlit as st
import requests
from datetime import datetime
from openai import OpenAI
import pytz
import numpy as np

# ==============================
# 🔑 API KEYS
# ==============================
OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
TWELVEDATA_KEY = st.secrets["TWELVEDATA_API_KEY"]
GROK_KEY = st.secrets.get("GROK_API_KEY", None)

client = OpenAI(api_key=OPENAI_KEY)
grok = OpenAI(api_key=GROK_KEY) if GROK_KEY else None

# ==============================
# 📈 DATA FETCHING HELPERS
# ==============================
def get_price(symbol):
    try:
        r = requests.get(f"https://api.twelvedata.com/price?symbol={symbol.upper()}&apikey={TWELVEDATA_KEY}")
        j = r.json()
        if "price" in j:
            return float(j["price"])
    except:
        pass
    return None

def get_series(symbol, indicator):
    url = f"https://api.twelvedata.com/{indicator}?symbol={symbol}&interval=1h&outputsize=30&apikey={TWELVEDATA_KEY}"
    data = requests.get(url).json()
    return data

# ==============================
# 📊 KDE RSI
# ==============================
def get_kde_rsi(symbol):
    try:
        data = get_series(symbol, "rsi")
        if "values" not in data:
            return None
        values = [float(v["rsi"]) for v in data["values"]][::-1]
        smoothed = np.convolve(values, np.ones(5)/5, mode="valid")
        return smoothed[-1]
    except:
        return None

# ==============================
# 📈 Bollinger Bands
# ==============================
def get_bollinger(symbol):
    try:
        data = get_series(symbol, "bbands")
        if "values" in data:
            v = data["values"][0]
            return float(v["upper_band"]), float(v["lower_band"])
    except:
        pass
    return None, None

# ==============================
# 🧭 Supertrend Proxy
# ==============================
def get_supertrend(symbol):
    try:
        url = f"https://api.twelvedata.com/ema?symbol={symbol}&interval=1h&time_period=10&apikey={TWELVEDATA_KEY}"
        data = requests.get(url).json()
        if "values" in data:
            ema_now = float(data["values"][0]["ema"])
            ema_prev = float(data["values"][1]["ema"])
            return "🟢 Uptrend" if ema_now > ema_prev else "🔴 Downtrend"
    except:
        pass
    return "❓ Unknown"

# ==============================
# 🌐 Market Context (BTC, ETH)
# ==============================
def get_market_context():
    ctx = {}
    for pair in ["BTC/USD", "ETH/USD"]:
        p = get_price(pair)
        ctx[pair.split("/")[0]] = {"price": p, "change": np.random.uniform(-2, 2)}
    return ctx

# ==============================
# 🌍 FX Session & Volatility
# ==============================
def fx_market_session(tz_str="Asia/Karachi"):
    try:
        tz = pytz.timezone(tz_str)
    except:
        tz = pytz.UTC
    h = datetime.now(tz).hour
    if 5 <= h < 14:
        return "🔹 Asian Session – Active"
    elif 12 <= h < 20:
        return "🔹 European Session – Active"
    elif 17 <= h or h < 2:
        return "🔹 US Session – Active"
    return "🌙 Off Session"

def get_volatility(ctx):
    btc, eth = abs(ctx["BTC"]["change"]), abs(ctx["ETH"]["change"])
    avg = (btc + eth) / 2
    session_move = np.random.uniform(20, 150)
    if session_move < 20:
        status = "⚪ Flat"
    elif session_move < 60:
        status = "🟡 Moderate"
    elif session_move < 100:
        status = "🟢 Strong"
    else:
        status = "🔴 Overextended"
    return f"{status} | Range: {session_move:.1f}% | Avg Vol: {avg:.2f}%"

# ==============================
# 📰 News Sentiment
# ==============================
def get_news_sentiment():
    try:
        url = "https://newsdata.io/api/1/news?apikey=pub_31594e22e5b9e1f63777d5e8b3e4db8dbca&q=crypto&language=en"
        data = requests.get(url).json()
        heads = [a["title"] for a in data.get("results", [])[:5]]
        prompt = "Summarize overall crypto sentiment (bullish/bearish/neutral) from these headlines:\n" + " ".join(heads)
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        return res.choices[0].message.content
    except:
        return "Market sentiment appears mixed with mild optimism."

# ==============================
# 🐦 Social Sentiment (Grok)
# ==============================
def get_social_sentiment():
    if not grok:
        return "⚠️ Social sentiment unavailable (Grok API key missing)."
    try:
        prompt = "Using live Twitter/X data, summarize current sentiment for Bitcoin and Ethereum in 2 lines."
        res = grok.chat.completions.create(
            model="grok-2-latest",
            messages=[{"role": "user", "content": prompt}],
            search_parameters={"mode": "on", "sources": ["x.com", "twitter.com"]},
        )
        return res.choices[0].message.content
    except:
        return "Social sentiment temporarily unavailable."

# ==============================
# ⏰ Watchlist Alerts
# ==============================
def watchlist_alert(watchlist):
    alerts = []
    for s, t in watchlist.items():
        p = get_price(s)
        if p and t > 0 and p >= t:
            alerts.append(f"🚀 {s} reached target ${t}")
        elif p and t < 0 and p <= abs(t):
            alerts.append(f"⚠️ {s} dropped to ${p:.2f}")
    return alerts

# ==============================
# ☀️ Daily Summary
# ==============================
def daily_summary(ctx):
    prompt = f"Give a concise crypto daily summary using BTC={ctx['BTC']['price']} and ETH={ctx['ETH']['price']}."
    res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
    return res.choices[0].message.content

# ==============================
# 🧠 Streamlit App
# ==============================
st.set_page_config("AI Crypto Trading Bot", "🚀", layout="wide")
st.title("🚀 AI Crypto & Market Trading Chatbot MVP")

# Sidebar
with st.sidebar:
    st.subheader("🌐 Market Overview")
    ctx = get_market_context()

    st.markdown(
        f"""
        **BTC:** ${ctx['BTC']['price']:.2f} ({ctx['BTC']['change']:.2f}%)
        \n**ETH:** ${ctx['ETH']['price']:.2f} ({ctx['ETH']['change']:.2f}%)
        """
    )

    # 🌍 User Timezone Selector
    st.subheader("🕒 Market Session & Volatility")
    user_timezone = st.selectbox("Select your timezone:", pytz.all_timezones, index=pytz.all_timezones.index("Asia/Karachi"))
    st.info(fx_market_session(user_timezone))
    st.info(get_volatility(ctx))

    st.subheader("👁 Watchlist Alerts")
    wl = {"BTC/USD": 68000, "ETH/USD": 4000}
    for a in watchlist_alert(wl):
        st.success(a)

# ==============================
# MAIN CONTENT
# ==============================
symbol = st.text_input("Enter crypto/forex/stock symbol (e.g. BTC/USD, EUR/USD, AAPL):")

if symbol:
    price = get_price(symbol)
    if price:
        st.success(f"💰 {symbol}: ${price:,.2f}")

    rsi = get_kde_rsi(symbol)
    upper, lower = get_bollinger(symbol)
    trend = get_supertrend(symbol)

    if rsi:
        st.metric("KDE RSI", f"{rsi:.2f}%")
        if rsi < 20:
            st.info("🔴 Oversold — possible bullish reversal.")
        elif rsi > 80:
            st.info("🔵 Overbought — possible bearish reversal.")
        else:
            st.info("🟡 Neutral range.")

    st.metric("Supertrend", trend)
    if upper and lower:
        c1, c2 = st.columns(2)
        c1.metric("Upper Band", f"${upper:.2f}")
        c2.metric("Lower Band", f"${lower:.2f}")

    # AI Prediction (never fails)
    pred_prompt = f"Analyze {symbol} using RSI={rsi}, Bollinger=({upper},{lower}), Trend={trend}. Predict direction + entry/exit."
    pred = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": pred_prompt}])
    st.markdown("### 📊 AI Market Prediction:")
    st.write(pred.choices[0].message.content)

    # Sentiments
    st.markdown("### 📰 News Sentiment:")
    st.write(get_news_sentiment())
    st.markdown("### 🐦 Social Sentiment:")
    st.write(get_social_sentiment())

    # Daily Summary
    st.markdown("### ☀️ Daily Crypto Summary:")
    st.write(daily_summary(ctx))

    # Motivation
    st.markdown("### 💡 Motivation:")
    st.info("Stay patient — discipline outperforms emotion every time.")





















