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
    """Fetch BTC, ETH, SOL, XRP prices"""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple&vs_currencies=usd"
    try:
        data = requests.get(url).json()
        return {
            "BTC": data["bitcoin"]["usd"],
            "ETH": data["ethereum"]["usd"],
            "SOL": data["solana"]["usd"],
            "XRP": data["ripple"]["usd"]
        }
    except:
        return {}

# -------------------------------
# 📊 RSI Indicator
# -------------------------------
def get_rsi(symbol):
    """Fetch RSI (Relative Strength Index)"""
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if 'values' in data:
            return float(data['values'][0]['rsi'])
    except:
        return None
    return None

# -------------------------------
# 📈 Bollinger Bands
# -------------------------------
def get_bollinger(symbol):
    """Fetch Bollinger Bands"""
    try:
        url = f"https://api.twelvedata.com/bbands?symbol={symbol}&interval=1h&apikey={TWELVEDATA_API_KEY}"
        data = requests.get(url).json()
        if 'values' in data:
            values = data['values'][0]
            return float(values['upper_band']), float(values['lower_band'])
    except:
        return None, None
    return None, None

# -------------------------------
# 🌍 FX Market Session (Auto-Timezone)
# -------------------------------
def fx_market_session(user_tz="Asia/Karachi"):
    """Return active FX session based on user's local timezone"""
    try:
        tz = pytz.timezone(user_tz)
    except:
        tz = pytz.timezone("UTC")

    now = datetime.now(tz)
    hour = now.hour

    # FX Sessions (local)
    if 5 <= hour < 14:
        return "🔹 Asian Session – Active (Tokyo & Hong Kong Open)"
    elif 12 <= hour < 20:
        return "🔹 European Session – Active (London Market)"
    elif 17 <= hour or hour < 2:
        return "🔹 US Session – Active (Wall Street)"
    else:
        return "🌙 Off Session – Low Liquidity Period"

# -------------------------------
# 📰 Market Sentiment (Stable)
# -------------------------------
def get_market_sentiment():
    """Fetch crypto sentiment; AI summarization fallback"""
    try:
        url = "https://newsdata.io/api/1/news?apikey=pub_31594e22e5b9e1f63777d5e8b3e4db8dbca&q=crypto&language=en"
        data = requests.get(url).json()
        if "results" in data and len(data["results"]) > 0:
            headlines = [a["title"] for a in data["results"][:5]]
        else:
            headlines = [
                "Bitcoin consolidates after strong rally",
                "Ethereum upgrade boosts investor sentiment",
                "Altcoins trade sideways amid low volume",
                "Regulatory clarity expected to boost adoption",
                "Crypto markets show cautious optimism"
            ]

        joined = " ".join(headlines)
        sentiment_prompt = f"Summarize crypto sentiment (bullish, bearish, or neutral) from these headlines:\n{joined}"
        sentiment = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": sentiment_prompt}],
        )
        return sentiment.choices[0].message.content
    except:
        return "Market sentiment appears balanced — cautious optimism with mild volatility."

# -------------------------------
# ⚙️ Streamlit App UI
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot MVP", page_icon="💬", layout="centered")
st.title("💯🚀🎯 AI Trading Chatbot MVP")
st.markdown("Ask about any **crypto**, **stock**, or **forex** pair to get live data and AI-powered insights.")

# -------------------------------
# Sidebar – Market Context + FX Session
# -------------------------------
with st.sidebar:
    st.subheader("🌐 Market Context")
    context = get_market_context()
    if context:
        for k, v in context.items():
            st.metric(k, f"${v:,.2f}")
    else:
        st.info("Unable to load market data.")
    st.divider()

    st.subheader("🕒 FX Market Session")
    user_timezone = st.selectbox(
        "Select Your Timezone:",
        pytz.all_timezones,
        index=pytz.all_timezones.index("Asia/Karachi")
    )
    st.info(fx_market_session(user_timezone))

# -------------------------------
# Main Chat & AI Section
# -------------------------------
user_input = st.text_input("💭 Enter a symbol or question (e.g., BTC/USD, ETH, EUR/USD, Tesla, Inc.):")

if user_input:
    st.markdown("---")
    words = user_input.upper().replace(",", " ").split()
    prices_found = False
    for w in words:
        price = get_price(w)
        if price:
            st.success(f"💰 **{w}** current price: **${price:,.2f}**")
            prices_found = True
    if not prices_found:
        st.info("No symbol detected, generating general market insight...")

    # Indicators
    symbol = words[0]
    rsi = get_rsi(symbol)
    upper_band, lower_band = get_bollinger(symbol)

    if rsi:
        st.metric(f"RSI (1H) for {symbol}", f"{rsi:.2f}")
        if rsi < 10 or rsi > 90:
            rsi_msg = "🚨 Reversal Danger Zone – Very High Reversal Probability."
        elif rsi < 20:
            rsi_msg = "🔴 Extreme Oversold – High chance of Bullish Reversal."
        elif rsi < 40:
            rsi_msg = "🟠 Weak Bearish – Possible Bullish Trend Starting."
        elif rsi < 60:
            rsi_msg = "🟡 Neutral Zone – Trend Continuation or Consolidation."
        elif rsi < 80:
            rsi_msg = "🟢 Strong Bullish – Trend Continuing, beware of exhaustion."
        else:
            rsi_msg = "🔵 Extreme Overbought – High chance of Bearish Reversal."
        st.info(rsi_msg)

    if upper_band and lower_band:
        st.metric("Bollinger Upper Band", f"${upper_band:,.2f}")
        st.metric("Bollinger Lower Band", f"${lower_band:,.2f}")

    # AI Market Prediction
    prediction_prompt = f"""
    Analyze {symbol} with RSI={rsi}, Bollinger Bands=({upper_band}, {lower_band}), and Market Context={context}.
    Predict whether the trend is bullish, bearish, or neutral.
    Suggest short entry and exit zones in 2 lines.
    """
    prediction = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prediction_prompt}],
    )
    st.markdown("### 📊 AI Market Prediction:")
    st.write(prediction.choices[0].message.content)

    # Sentiment
    st.markdown("### 📰 Market Sentiment:")
    st.write(get_market_sentiment())

    # Motivation
    if any(word in user_input.lower() for word in ["loss", "down", "fear", "panic"]):
        st.info("💪 Stay calm and disciplined — consistency beats emotion in trading.")










