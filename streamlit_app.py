import yfinance as yf
import requests
import toml

# --- Load Finnhub API key ---
try:
    secrets = toml.load("secrets.toml")
    FINNHUB_API_KEY = secrets.get("finnhub", {}).get("api_key", "")
except Exception as e:
    print("Error loading secrets.toml:", e)
    FINNHUB_API_KEY = ""

# --- Crypto (Binance → CoinGecko) ---
def get_crypto_price(symbol="BTC"):
    try:
        # Auto-append USDT if not included
        if "USDT" not in symbol.upper():
            symbol = symbol.upper() + "USDT"

        res = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", timeout=5)
        res.raise_for_status()
        data = res.json()
        price = float(data["lastPrice"])
        change = float(data["priceChangePercent"])
        return round(price, 2), round(change, 2)
    except Exception as e:
        print(f"Binance failed for {symbol}: {e}")

    # --- Fallback: CoinGecko ---
    try:
        # convert to lowercase and map symbol to known CoinGecko IDs if needed
        coin_id = symbol.replace("USDT", "").lower()
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=5
        )
        res.raise_for_status()
        data = res.json()
        if coin_id not in data:
            return "Invalid crypto symbol — please enter a valid one like BTC or ETH.", ""
        price = float(data[coin_id]["usd"])
        change = float(data[coin_id]["usd_24h_change"])
        return round(price, 2), round(change, 2)
    except Exception as e2:
        print(f"CoinGecko also failed: {e2}")
        return "API failed — try again later", ""

# --- Stocks (Yahoo → Finnhub) ---
def get_index_price(symbol="AAPL"):
    try:
        # Reject crypto symbols in stock mode
        if any(x in symbol.upper() for x in ["USDT", "BTC", "ETH", "SOL", "BNB"]):
            return "Invalid stock symbol — please enter a valid ticker like AAPL or ^IXIC.", ""
        data = yf.Ticker(symbol).history(period="2d")
        if len(data) >= 2:
            last_price = data["Close"].iloc[-1]
            prev_price = data["Close"].iloc[-2]
            change = ((last_price - prev_price) / prev_price) * 100
            return round(last_price, 2), round(change, 2)
        else:
            raise ValueError("Insufficient Yahoo data")
    except Exception as e:
        print(f"Yahoo Finance failed for {symbol}: {e}")

    # --- Fallback: Finnhub ---
    try:
        res = requests.get(
            f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}",
            timeout=5
        )
        res.raise_for_status()
        data = res.json()
        price = float(data.get("c", 0))
        prev_close = float(data.get("pc", 0))
        if price > 0 and prev_close > 0:
            change = ((price - prev_close) / prev_close) * 100
            return round(price, 2), round(change, 2)
        else:
            raise ValueError("Incomplete Finnhub data")
    except Exception as e2:
        print(f"Finnhub also failed: {e2}")
        return "API failed — try again later", ""

# --- Unified wrapper ---
def get_asset_price(user_input, asset_type="auto"):
    symbol = user_input.strip().upper()

    # Auto-detect if crypto or stock
    if asset_type == "crypto" or any(x in symbol for x in ["USDT", "BTC", "ETH", "SOL", "BNB"]):
        price, change = get_crypto_price(symbol)
        currency = "USDT"
    elif asset_type == "stock" or symbol.isalpha() or symbol.startswith("^"):
        price, change = get_index_price(symbol)
        currency = "USD"
    else:
        return "❌ Please enter a valid stock ticker (e.g. AAPL) or crypto symbol (e.g. BTC or BTCUSDT)."

    # Handle friendly outputs
    if isinstance(price, str) and "Invalid" in price:
        return f"⚠️ {price}"
    elif isinstance(price, str) and "API failed" in price:
        return f"⚠️ {price}"
    else:
        return f"{symbol}: {price} {currency} ({change}%)"

# --- Example usage ---
print(get_asset_price("BTC", "crypto"))    # BTC auto → BTCUSDT
print(get_asset_price("AAPL", "stock"))    # USD
print(get_asset_price("BTC", "stock"))     # Error message
print(get_asset_price("AAPL", "crypto"))   # Error message
