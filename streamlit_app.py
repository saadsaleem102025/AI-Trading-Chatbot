import streamlit as st
import pandas as pd
import pandas_ta as ta
import requests
import yfinance as yf
import toml
from datetime import datetime

# ===============================
# Load Finnhub Key Safely
# ===============================
try:
    secrets = toml.load("secrets.toml")
    FINNHUB_API_KEY = secrets.get("finnhub", {}).get("api_key", "")
except Exception:
    FINNHUB_API_KEY = ""

# ===============================
# PRICE FETCHERS (No UI change)
# ===============================
def get_crypto_price(symbol="BTC"):
    symbol = symbol.upper().replace("/", "")
    if not symbol.endswith("USDT"):
        symbol = symbol + "USDT"

    # Binance primary
    try:
        res = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", timeout=5)
        res.raise_for_status()
        data = res.json()
        price = float(data["lastPrice"])
        change = float(data["priceChangePercent"])
        return round(price, 4), round(change, 2), "USDT"
    except Exception:
        pass

    # CoinGecko fallback
    try:
        coin_id = symbol.replace("USDT", "").lower()
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        if coin_id not in data:
            return "⚠️ Invalid crypto symbol — please check and try again.", "", ""
        price = float(data[coin_id]["usd"])
        change = float(data[coin_id].get("usd_24h_change", 0))
        return round(price, 4), round(change, 2), "USDT"
    except Exception:
        return "⚠️ API failed — try again later", "", ""


def get_stock_price(symbol="AAPL"):
    symbol = symbol.upper().strip()

    if any(x in symbol for x in ["BTC", "ETH", "SOL", "BNB", "USDT"]):
        return "⚠️ Invalid stock symbol — please enter a valid ticker like AAPL or ^IXIC.", "", ""

    # Yahoo primary
    try:
        data = yf.Ticker(symbol).history(period="2d")
        if len(data) >= 2:
            last_price = data["Close"].iloc[-1]
            prev_price = data["Close"].iloc[-2]
            change = ((last_price - prev_price) / prev_price) * 100
            return round(last_price, 2), round(change, 2), "USD"
    except Exception:
        pass

    # Finnhub fallback
    try:
        if not FINNHUB_API_KEY:
            raise ValueError("Missing Finnhub key")
        res = requests.get(
            f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}",
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        price = float(data.get("c", 0))
        prev_close = float(data.get("pc", 0))
        if price > 0 and prev_close > 0:
            change = ((price - prev_close) / prev_close) * 100
            return round(price, 2), round(change, 2), "USD"
        else:
            raise ValueError("Invalid Finnhub data")
    except Exception:
        return "⚠️ API failed — try again later", "", ""


def get_asset_price(symbol):
    symbol = symbol.upper().strip()
    crypto_hint = any(c in symbol for c in ["BTC", "ETH", "SOL", "BNB", "USDT", "XRP"])
    if crypto_hint:
        return get_crypto_price(symbol)
    else:
        return get_stock_price(symbol)


# ===============================
# STREAMLIT UI (unchanged)
# ===============================
st.set_page_config(page_title="AI Trading Chatbot MVP", layout="wide")
st.title("💹 AI Trading Chatbot MVP")

st.sidebar.header("Settings")
asset_input = st.sidebar.text_input("Enter asset symbol (e.g. BTC, AAPL, ^IXIC)", value="BTC")
fetch_btn = st.sidebar.button("Fetch Price")

if fetch_btn:
    with st.spinner("Fetching latest data..."):
        price, change, currency = get_asset_price(asset_input)

    st.subheader(f"Results for {asset_input}")
    if isinstance(price, str) and "⚠️" in price:
        st.warning(price)
    else:
        st.metric(label=f"{asset_input} Price", value=f"{price} {currency}", delta=f"{change}%")

# ===============================
# Indicator + Summary Section
# ===============================
symbol = asset_input
if not isinstance(price, str):
    try:
        if any(x in symbol for x in ["BTC", "ETH", "SOL", "BNB", "USDT"]):
            df_1h = pd.DataFrame(requests.get(
                f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1h&limit=500"
            ).json(), columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'a', 'b', 'c', 'd', 'e', 'f'])
            df_1h["Close"] = df_1h["Close"].astype(float)
        else:
            df_1h = yf.download(symbol, period="1mo", interval="1h")
    except Exception:
        df_1h = pd.DataFrame()

    if not df_1h.empty:
        df_1h.ta.rsi(length=14, append=True)
        kde_rsi_output = round(df_1h["RSI_14"].iloc[-1], 2) if "RSI_14" in df_1h.columns else "N/A"

        df_1h.ta.supertrend(length=10, multiplier=3, append=True)
        supertrend_output = df_1h["SUPERT_10_3.0"].iloc[-1] if "SUPERT_10_3.0" in df_1h.columns else "N/A"

        df_1h.ta.bbands(length=20, append=True)
        if "BBL_20_2.0" in df_1h.columns:
            last_close = df_1h["Close"].iloc[-1]
            lower = df_1h["BBL_20_2.0"].iloc[-1]
            upper = df_1h["BBU_20_2.0"].iloc[-1]
            if last_close > upper:
                bb_status = "Overbought"
            elif last_close < lower:
                bb_status = "Oversold"
            else:
                bb_status = "Neutral"
        else:
            bb_status = "N/A"

        ema_status = "Bullish" if df_1h.ta.ema(50).iloc[-1] > df_1h.ta.ema(200).iloc[-1] else "Bearish"
        psar_status = "Bullish" if df_1h.ta.psar().iloc[-1] else "Bearish"
        bias = "Bullish" if supertrend_output == "up" or ema_status == "Bullish" else "Bearish"

        current_price = df_1h["Close"].iloc[-1]
        if all(col in df_1h.columns for col in ['High', 'Low', 'Close']):
            df_1h.ta.atr(append=True, length=14)
            atr_synth_val = df_1h['ATR_14'].iloc[-1] if 'ATR_14' in df_1h.columns else current_price * 0.01
        else:
            atr_synth_val = current_price * 0.01

        trade_params = {"Entry": round(current_price, 2),
                        "Target": round(current_price * (1.02 if bias == "Bullish" else 0.98), 2),
                        "Stop": round(current_price * (0.98 if bias == "Bullish" else 1.02), 2)}
        summary = f"**Bias:** {bias} | Entry: {trade_params['Entry']} | Target: {trade_params['Target']} | Stop: {trade_params['Stop']}"

        st.markdown(f"""
        <div class='big-text'>
            <div class='section-header'>💹 Asset Overview</div>
            <div style='font-size: 22px;'>
                <b>{symbol}</b> — <span class='asset-price-value'>{price} {currency}</span>
                ({change}%)
            </div>
        </div>

        <div class='big-text'>
            <div class='section-header'>📊 Indicator Insights</div>
            <div class='analysis-item'><b>KDE RSI:</b> {kde_rsi_output}</div>
            <div class='analysis-item'><b>SuperTrend:</b> {supertrend_output}</div>
            <div class='analysis-item'><b>Bollinger Bands:</b> {bb_status}</div>
            <div class='analysis-item'><b>EMA Crossover:</b> {ema_status}</div>
            <div class='analysis-item'><b>Parabolic SAR:</b> {psar_status}</div>
            <div class='analysis-bias'><b>Overall Bias:</b> {bias}</div>
        </div>

        <div class='big-text'>
            <div class='section-header'>🎯 Trade Recommendation</div>
            {summary}
        </div>

        <div class='risk-warning'>
        ⚠️ <b>Risk Disclaimer:</b> This AI model provides technical analysis insights for educational purposes only. 
        Always do your own research before making any investment decisions.
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
