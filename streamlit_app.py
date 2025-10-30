import streamlit as st
import requests
from datetime import datetime
from openai import OpenAI
import pytz

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
# 🌐 Market Context Panel
# -------------------------------
def get_market_context():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple&vs_currencies=usd&include_24hr_change=true"
        data = requests.get(url).json()
        return {
            "BTC": {"price": data["bitcoin"]["usd"], "change": data["bitcoin"]["usd_24h_change"]},
            "ETH": {"price": data["ethereum"]["usd"], "change": data["ethereum"]["usd_24h_change"]},
            "SOL": {"price": data["solana"]["usd"], "change": data["solana"]["usd_24h_change"]},
            "XRP": {"price": data["ripple"]["usd"], "change": data["ripple"]["usd_24h_change"]},
        }
    except:
        return {}

# -------------------------------
# 📊 RSI
# -------------------------------
def get_rsi(symbol):
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if "values" in data:
            return float(data["values"][0]["rsi"])
    except:
        pass
    return None

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
# 🌍 FX Session by Timezone
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
# ⚙️ Streamlit App
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot MVP", page_icon="💬", layout="centered")
st.title("💯🚀🎯 AI Trading Chatbot MVP")
st.markdown("Ask about any **crypto**, **stock**, or **forex** pair to get live data and AI-powered insights.")

# -------------------------------
# Sidebar – Context, Session & Volatility
# -------------------------------
with st.sidebar:
    st.subheader("🌐 Market Context")
    context = get_market_context()
    if context:
        for k, v in context.items():
            st.metric(k, f"${v['price']:,.2f}", f"{v['change']:.2f}%")
    else:
        st.info("Unable to load market data.")
    st.divider()

    st.subheader("🕒 FX Market Session & Volatility")
    user_timezone = st.selectbox(
        "Select Your Timezone:", pytz.all_timezones, index=pytz.all_timezones.index("Asia/Karachi")
    )
    st.info(fx_market_session(user_timezone))
    st.info(get_volatility(context))

# -------------------------------
# Main Chat
# -------------------------------
user_input = st.text_input("💭 Enter a symbol or question (e.g., BTC/USD, ETH, EUR/USD):")

if user_input:
    st.markdown("---")
    tokens = user_input.upper().replace(",", " ").split()
    found = False
    for t in tokens:
        price = get_price(t)
        if price:
            st.success(f"💰 **{t}** current price: **${price:,.2f}**")
            found = True
    if not found:
        st.info("No symbol detected, generating general market insight...")

    symbol = tokens[0]
    rsi = get_rsi(symbol)
    upper, lower = get_bollinger(symbol)

    if rsi:
        st.metric(f"RSI (1H) for {symbol}", f"{rsi:.2f}")
        if rsi < 10 or rsi > 90:
            msg = "🚨 Reversal Danger Zone – Very High Reversal Probability."
        elif rsi < 20:
            msg = "🔴 Extreme Oversold – High chance of Bullish Reversal."
        elif rsi < 40:
            msg = "🟠 Weak Bearish – Possible Bullish Trend Starting."
        elif rsi < 60:
            msg = "🟡 Neutral Zone – Trend Continuation or Consolidation."
        elif rsi < 80:
            msg = "🟢 Strong Bullish – Trend Continuing, beware of exhaustion."
        else:
            msg = "🔵 Extreme Overbought – High chance of Bearish Reversal."
        st.info(msg)

    if upper and lower:
        st.metric("Bollinger Upper Band", f"${upper:,.2f}")
        st.metric("Bollinger Lower Band", f"${lower:,.2f}")

    pred_prompt = f"""
    Analyze {symbol} using RSI={rsi}, Bollinger=({upper},{lower}), and Market Context={context}.
    Predict trend direction (bullish, bearish, neutral) and give entry/exit zones in 2 lines.
    """
    pred = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": pred_prompt}]
    )
    st.markdown("### 📊 AI Market Prediction:")
    st.write(pred.choices[0].message.content)

    st.markdown("### 📰 Market Sentiment:")
    st.write(get_market_sentiment())

    if any(w in user_input.lower() for w in ["loss", "down", "fear", "panic"]):
        st.info("💪 Stay calm and disciplined — consistency beats emotion in trading.")










