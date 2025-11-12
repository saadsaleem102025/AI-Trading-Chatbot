import streamlit as st
import requests, datetime, pandas as pd, numpy as np, pytz, time, json, random
from datetime import timedelta
import pandas_ta as ta
import yfinance as yf
import openai

# --- CONFIGURATION & CONSTANTS ---
st.set_page_config(page_title="AI Trading Chatbot", layout="wide")

# Private API keys (add in .streamlit/secrets.toml)
openai.api_key = st.secrets["OPENAI_API_KEY"]
FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"]

# --- HELPER FUNCTIONS ---
def get_finnhub_data(symbol, resolution='D', count=100):
    """Fetch stock candles from Finnhub"""
    try:
        url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution={resolution}&count={count}&token={FINNHUB_API_KEY}"
        r = requests.get(url)
        data = r.json()
        if 'c' not in data:
            return None
        df = pd.DataFrame({
            'time': pd.to_datetime(data['t'], unit='s'),
            'open': data['o'],
            'high': data['h'],
            'low': data['l'],
            'close': data['c'],
            'volume': data['v']
        })
        return df
    except Exception as e:
        st.error(f"Finnhub error: {e}")
        return None

def get_yfinance_data(symbol, period="1mo", interval="1d"):
    """Backup stock data from Yahoo Finance"""
    try:
        df = yf.download(symbol, period=period, interval=interval)
        df.reset_index(inplace=True)
        df.rename(columns={'Date': 'time'}, inplace=True)
        return df
    except Exception as e:
        st.error(f"Yahoo Finance error: {e}")
        return None

def get_crypto_data(symbol="BTCUSDT"):
    """Fetch crypto candles from Binance"""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=100"
        r = requests.get(url)
        data = r.json()
        df = pd.DataFrame(data, columns=[
            'time','open','high','low','close','volume',
            'close_time','qav','num_trades','taker_base_vol','taker_quote_vol','ignore'
        ])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].astype(float)
        return df
    except Exception as e:
        st.error(f"Binance data error: {e}")
        return None

def get_coingecko_price(symbol="bitcoin"):
    """Get current price from CoinGecko as fallback"""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
        r = requests.get(url)
        return r.json().get(symbol, {}).get("usd", None)
    except Exception as e:
        st.warning(f"CoinGecko error: {e}")
        return None

def calculate_indicators(df):
    """Calculate basic technical indicators"""
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['EMA_20'] = ta.ema(df['close'], length=20)
    df['EMA_50'] = ta.ema(df['close'], length=50)
    return df

# --- OPENAI SUMMARIZATION FUNCTION ---
def generate_openai_analysis(df, symbol):
    """Generate natural language analysis using OpenAI"""
    try:
        latest = df.iloc[-1]
        prompt = f"""
        You are an expert trading analyst. Analyze the following data for {symbol}:

        RSI: {latest['RSI']:.2f}
        ATR: {latest['ATR']:.2f}
        EMA20: {latest['EMA_20']:.2f}
        EMA50: {latest['EMA_50']:.2f}
        Current Price: {latest['close']:.2f}

        Based on these indicators, give a concise summary with trading insight.
        """

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a trading analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return f"Error generating AI analysis: {e}"

# --- UI SECTION ---
st.sidebar.title("Market Selection")
market_type = st.sidebar.selectbox("Choose Market", ["Stocks", "Crypto"])
symbol = st.sidebar.text_input("Enter Symbol (e.g. AAPL, TSLA, BTCUSDT)", "AAPL")
risk_ratio = st.sidebar.number_input("Risk-Reward Ratio", value=2.0, step=0.5)
trade_style = st.sidebar.radio("Trading Style", ["Scalp", "Swing", "Long-Term"])

st.title("📊 AI Trading Chatbot")
st.write("Get AI-powered market summaries, indicators, and insights.")

# --- DATA FETCHING ---
if market_type == "Stocks":
    df = get_finnhub_data(symbol)
    if df is None or df.empty:
        df = get_yfinance_data(symbol)
    if df is None or df.empty:
        st.error("No data fetched for this stock.")
        st.stop()
elif market_type == "Crypto":
    df = get_crypto_data(symbol)
    if df is None or df.empty:
        st.error("No data fetched for this crypto.")
        st.stop()
else:
    st.error("Unsupported market type.")
    st.stop()

df = calculate_indicators(df)

# --- DISPLAY CHART ---
st.line_chart(df[['close', 'EMA_20', 'EMA_50']].set_index(df['time']))

# --- SHOW SUMMARY ---
ai_summary = generate_openai_analysis(df, symbol)
st.subheader("AI Trading Summary")
st.write(ai_summary)

# --- RISK MANAGEMENT ---
latest = df.iloc[-1]
atr = latest['ATR']
entry = latest['close']
stop_loss = entry - (atr * risk_ratio)
take_profit = entry + (atr * risk_ratio)

st.metric("Entry", f"{entry:.2f}")
st.metric("Stop Loss", f"{stop_loss:.2f}")
st.metric("Take Profit", f"{take_profit:.2f}")
