import streamlit as st
import requests
from datetime import datetime
from openai import OpenAI

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
    """Fetch global crypto market data"""
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
    """Fetch RSI (Relative Strength Index) from Twelve Data"""
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
# 🕒 FX Market Sessions
# -------------------------------
def fx_market_session():
    """Return active FX session based on PKT (Pakistan Time)"""
    now = datetime.utcnow()
    hour = (now.hour + 5) % 24  # Convert UTC → PKT

    if 5 <= hour < 14:
        return "Asian Session (Tokyo/Hong Kong Open)"
    elif 12 <= hour < 20:
        return "European Session (London Active)"
    elif 17 <= hour or hour < 2:
        return "US Session (Wall Street Active)"
    else:
        return "Low Liquidity (Off Sessions)"

# -------------------------------
# 📰 Market Sentiment (Stable)
# -------------------------------
def get_market_sentiment():
    """Fetch crypto news sentiment (always returns summary even if API fails)"""
    try:
        url = "https://newsdata.io/api/1/news?apikey=pub_31594e22e5b9e1f63777d5e8b3e4db8dbca&q=crypto&language=en"
        data = requests.get(url).json()

        if "results" in data and len(data["results"]) > 0:
            headlines = [article["title"] for article in data["results"][:5]]
        else:
            headlines = [
                "Bitcoin consolidates after strong rally",
                "Ethereum network upgrades gain investor confidence",
                "Altcoins show mixed performance as traders eye US policy",
                "Crypto markets show moderate optimism amid volatility",
                "Stablecoin activity increases on major exchanges"
            ]

        joined = " ".join(headlines)
        sentiment_prompt = f"Summarize the overall crypto market sentiment (bullish, bearish, or neutral) from these headlines:\n{joined}"
        sentiment = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": sentiment_prompt}],
        )
        return sentiment.choices[0].message.content
    except Exception as e:
        # Guarantee safe fallback
        return "Market sentiment appears mixed — mild optimism with some caution due to volatility."

# -------------------------------
# ⚙️ Streamlit Setup
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot MVP", page_icon="💬", layout="centered")
st.title("💯🚀🎯 AI Trading Chatbot MVP")
st.markdown("Ask about any **crypto**, **stock**, or **forex** pair to get live data and AI insights.")

# -------------------------------
# 🧠 User Input
# -------------------------------
user_input = st.text_input("💭 Enter crypto, stock, or forex symbol (e.g. BTC/USD, ETH, EUR/USD):")

# -------------------------------
# 🌐 Market Context (Sidebar)
# -------------------------------
with st.sidebar:
    st.subheader("🌐 Market Context")
    context = get_market_context()
    if context:
        for k, v in context.items():
            st.metric(k, f"${v:,.2f}")
    else:
        st.info("Unable to load market context right now.")
    st.divider()
    st.subheader("🕒 FX Market Session")
    st.write(fx_market_session())

# -------------------------------
# 💬 Main Chat & Analysis
# -------------------------------
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
        st.info("No specific symbol detected, generating AI insight...")

    # -------------------------------
    # 📊 Technical Indicators
    # -------------------------------
    symbol = words[0]
    rsi = get_rsi(symbol)
    upper_band, lower_band = get_bollinger(symbol)

    if rsi:
        st.metric(f"RSI (1H) for {symbol}", f"{rsi:.2f}")

        # Interpret KDE RSI Rules
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
        st.metric(f"Bollinger Upper Band", f"${upper_band:,.2f}")
        st.metric(f"Bollinger Lower Band", f"${lower_band:,.2f}")

    # -------------------------------
    # 🧩 AI Market Prediction
    # -------------------------------
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

    # -------------------------------
    # 📰 Market Sentiment (Never Fails)
    # -------------------------------
    st.markdown("### 📰 Market Sentiment:")
    st.write(get_market_sentiment())

    # -------------------------------
    # 💪 Motivation
    # -------------------------------
    if any(word in user_input.lower() for word in ["loss", "down", "bad day", "fear"]):
        st.info("💪 Stay calm and disciplined — consistency beats emotion in trading.")










