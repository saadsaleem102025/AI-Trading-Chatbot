import requests
import yfinance as yf
import toml

# --- Load Finnhub API key silently ---
try:
    secrets = toml.load("secrets.toml")
    FINNHUB_API_KEY = secrets.get("finnhub", {}).get("api_key", "")
except Exception:
    FINNHUB_API_KEY = ""


# --- Crypto prices: Binance → CoinGecko ---
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
        pass  # Try fallback silently

    # CoinGecko fallback (works for any coin)
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


# --- Stock prices: Yahoo → Finnhub ---
def get_stock_price(symbol="AAPL"):
    symbol = symbol.upper().strip()

    # Block crypto entered under stock mode
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
        pass  # Silent fallback

    # Finnhub fallback
    try:
        if not FINNHUB_API_KEY:
            raise ValueError("No Finnhub key")

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
