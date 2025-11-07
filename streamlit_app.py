import streamlit as st
import requests
import yfinance as yf
import toml

# ------------------------------
# Load Finnhub API key (optional)
# ------------------------------
try:
    secrets = toml.load("secrets.toml")
    FINNHUB_API_KEY = secrets.get("finnhub", {}).get("api_key", "")
except Exception:
    FINNHUB_API_KEY = ""  # Silent fallback if not found


# ------------------------------
# Crypto Prices (Binance → CoinGecko)
# ------------------------------
def get_crypto_price(symbol="BTC"):
    symbol = symbol.upper().replace("/", "")  # Clean user input
    if not symbol.endswith("USDT"):
        symbol = symbol + "USDT"

    # --- Binance primary ---
    try:
        res = requests.get(
            f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", timeout=5
        )
        res.raise_for_status()
        data = res.json()
        price = float(data["lastPrice"])
        change = float(data["priceChangePercent"])
        return round(price, 4), round(change, 2), "USDT"
    except Exception:
        pass  # Move to fallback silently

    # --- CoinGecko fallback ---
    try:
        coin_id = symbol.replace("USDT", "").lower()
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        if coin_id not in data:
            return "⚠️ Invalid crypto symbol — please enter a valid one like BTC or ETH.", "", ""
        price = float(data[coin_id]["usd"])
        change = float(data[coin_id].get("usd_24h_change", 0))
        return round(price, 4), round(change, 2), "USDT"
    except Exception:
        return "⚠️ API failed — try again later", "", ""


# ------------------------------
# Stock Prices (Yahoo → Finnhub)
# ------------------------------
def get_stock_price(symbol="AAPL"):
    symbol = symbol.upper().strip()

    # Reject crypto-like inputs
    if any(x in symbol for x in ["BTC", "ETH", "SOL", "BNB", "USDT"]):
        return "⚠️ Invalid stock symbol — please enter a valid ticker like AAPL or ^IXIC.", "", ""

    # --- Yahoo Finance primary ---
    try:
        data = yf.Ticker(symbol).history(period="2d")
        if len(data) >= 2:
            last_price = data["Close"].iloc[-1]
            prev_price = data["Close"].iloc[-2]
            change = ((last_price - prev_price) / prev_price) * 100
            return round(last_price, 2), round(change, 2), "USD"
        else:
            raise ValueError("Insufficient data")
    except Exception:
        pass  # Try fallback silently

    # --- Finnhub fallback ---
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


# ------------------------------
# Unified Function
# ------------------------------
def get_asset_price(user_input, asset_type="auto"):
    symbol = user_input.strip().upper()

    # Auto detect crypto vs stock
    if asset_type == "crypto" or any(x in symbol for x in ["BTC", "ETH", "USDT", "BNB", "SOL"]):
        price, change, currency = get_crypto_price(symbol)
    elif asset_type == "stock" or symbol.isalpha() or symbol.startswith("^"):
        price, change, currency = get_stock_price(symbol)
    else:
        return "⚠️ Please enter a valid stock ticker (e.g., AAPL) or crypto symbol (e.g., BTC)."

    # Handle friendly outputs
    if isinstance(price, str):
        return price
    else:
        return f"{symbol}: {price} {currency} ({change}%)"


# ------------------------------
# Streamlit UI
# ------------------------------
st.title("📊 AI Trading Chatbot – Market Data MVP")

user_symbol = st.text_input("Enter stock or crypto symbol:", "AAPL")
asset_choice = st.radio("Select asset type:", ["auto", "stock", "crypto"])

if st.button("Fetch Price"):
    result = get_asset_price(user_symbol, asset_choice)
    st.success(result)
