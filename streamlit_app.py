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
# 💬 Streamlit UI
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot MVP", page_icon="💯🚀🎯", layout="centered")
st.title("💬 AI Trading Chatbot MVP")
st.markdown("Ask about any **crypto**, **stock**, or **forex** pair to get live data and AI insights.")

# -------------------------------
# 🧠 Chat Logic
# -------------------------------
user_input = st.text_input("💭 Type your question or trading pair:")

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



