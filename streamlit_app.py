# --- NEW API HELPERS ---
def fetch_stock_price_alphavantage(ticker):
    """Fetches real-time price and change from AlphaVantage."""
    if not AV_API_KEY:
        return None, None
        
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={AV_API_KEY}"
    try:
        r = requests.get(url, timeout=5).json()
        quote = r.get("Global Quote", {})
        
        if quote and quote.get("05. price") and quote.get("10. change percent"):
            price = float(quote["05. price"])
            change_percent = float(quote["10. change percent"].replace('%', ''))
            
            if price > 0:
                time.sleep(1)
                return price, change_percent
    except Exception:
        pass
    return None, None

def fetch_stock_price_yahoo(ticker):
    """Fetches real-time price from Yahoo Finance (no API key needed)."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
    try:
        r = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'}).json()
        
        if 'chart' in r and 'result' in r['chart'] and r['chart']['result']:
            result = r['chart']['result'][0]
            meta = result.get('meta', {})
            
            current_price = meta.get('regularMarketPrice')
            prev_close = meta.get('previousClose')
            
            if current_price and prev_close and prev_close > 0:
                change_percent = ((current_price - prev_close) / prev_close) * 100
                return float(current_price), float(change_percent)
    except Exception as e:
        pass
    return None, None

def fetch_crypto_price_binance(symbol):
    """Fetches real-time price from Binance Public API."""
    binance_symbol = symbol.replace("USD", "USDT")
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
    
    try:
        r = requests.get(url, timeout=5).json()
        
        if 'lastPrice' in r and 'priceChangePercent' in r:
            price = float(r['lastPrice'])
            change_percent = float(r['priceChangePercent'])
            
            if price > 0:
                time.sleep(0.5)
                return price, change_percent
    except Exception:
        pass
    return None, None

def fetch_crypto_price_coingecko(symbol):
    """Fetches crypto price from CoinGecko (no API key needed)."""
    base_symbol = symbol.replace("USD", "").replace("USDT", "").lower()
    
    # CoinGecko uses full coin names, map common symbols
    coingecko_ids = {
        'btc': 'bitcoin', 'eth': 'ethereum', 'ada': 'cardano', 
        'xrp': 'ripple', 'xlm': 'stellar', 'doge': 'dogecoin',
        'sol': 'solana', 'trx': 'tron', 'cvx': 'convex-finance',
        'cfx': 'conflux-token', 'pi': 'pi-network-defi'
    }
    
    coin_id = coingecko_ids.get(base_symbol, base_symbol)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
    
    try:
        r = requests.get(url, timeout=5).json()
        
        if coin_id in r and 'usd' in r[coin_id]:
            price = float(r[coin_id]['usd'])
            change_percent = float(r[coin_id].get('usd_24h_change', 0))
            
            if price > 0:
                time.sleep(0.5)
                return price, change_percent
    except Exception:
        pass
    return None, None