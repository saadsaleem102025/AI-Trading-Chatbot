import streamlit as st
import requests
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
    """Fetch global crypto market context from CoinGecko"""
    url = "https://api.coingecko.com/api/v3/global"
    try:
        data = requests.get(url).json()['data']
        btc_dominance = round(data['market_cap_percentage']['btc'], 2)
        total_market_cap = round(data['total_market_cap']['usd'] / 1e9, 2)
        return btc_dominance, total_market_cap
    except:
        return None, None

with st.sidebar:
    st.subheader("🌐 Market Context")
    btc_d, mcap = get_market_context()
    if btc_d and mcap:
        st.metric("BTC Dominance", f"{btc_d}%")
        st.metric("Total Market Cap", f"${mcap}B")
    else:
        st.info("Unable to load market context right now.")
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
st.markdown("###  AI Response:")
st.write(ai_message)

# -------------------------------
# 📈 AI-Powered Price Prediction
# -------------------------------
symbol = words[0]
rsi = get_rsi(symbol)
if rsi:
    st.metric(f"RSI (1H) for {symbol}", f"{rsi:.2f}")

if btc_d and mcap:
    prediction_prompt = f"""
    Analyze {symbol} with RSI={rsi}, BTC Dominance={btc_d}%, Market Cap=${mcap}B.
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
# 💬 Streamlit UI
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot MVP", page_icon="💬", layout="centered")
st.title("💯🚀🎯 AI Trading Chatbot MVP")
st.markdown("Ask about any **crypto**, **stock**, or **forex** pair to get live data and AI insights.")

# -------------------------------
# 🧠 Chat Logic
# -------------------------------
user_input = st.text_input("💭 Type crypto,forex,crypto trading pair:")

if user_input:
    st.markdown("---")
    
    # Try detecting and showing price for symbols mentioned
    words = user_input.upper().replace(",", " ").split()
    prices_found = False
    for w in words:
        price = get_price(w)
        if price:
            st.success(f"💰 **{w}** current price: **${price}**")
            prices_found = True

    if not prices_found:
        st.info("No specific symbol detected, generating AI insight...")

    # -------------------------------
    # 🧩 AI Response
    # -------------------------------
    with st.spinner("Analyzing market and generating response..."):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are an AI trading assistant. Provide crypto, stock, and forex insights "
                    "based on user queries. If market data is shown, build your answer around it."
                )},
                {"role": "user", "content": user_input},
            ],
        )
    
    ai_message = response.choices[0].message.content
    st.markdown("###  AI Response:")
    st.write(ai_message)
    # -------------------------------
# 📰 Sentiment + Motivation
# -------------------------------
def get_news_sentiment():
    """Fetch crypto news and summarize sentiment"""
    url = "https://cryptopanic.com/api/v1/posts/?auth_token=demo&kind=news"
    try:
        data = requests.get(url).json()
        headlines = [post['title'] for post in data['results'][:5]]
        joined = " ".join(headlines)
        sentiment_prompt = f"Summarize crypto sentiment (bullish/bearish/neutral) from these headlines:\n{joined}"
        sentiment = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": sentiment_prompt}],
        )
        return sentiment.choices[0].message.content
    except:
        return "Could not fetch sentiment right now."

st.markdown("---")
st.markdown("### 📰 Market Sentiment:")
st.write(get_news_sentiment())

if any(word in user_input.lower() for word in ["loss", "down", "bad day", "fear"]):
    st.info("💪 Stay calm and disciplined — consistency beats emotion in trading.")




