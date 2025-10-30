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
    e








