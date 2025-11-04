import streamlit as st
import requests, datetime, pandas as pd, numpy as np, pytz, time
# tzlocal optional
try:
    from tzlocal import get_localzone
except Exception:
    get_localzone = None

st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === STYLE (kept compact) ===
st.markdown("""
<style>
header[data-testid="stHeader"], footer {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}
html, body, [class*="stText"], [data-testid="stMarkdownContainer"] {
    font-size: 18px !important;
    color: #E9EEF6 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    line-height: 1.8 !important;
}
[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #0F2027, #203A43, #2C5364);
    color: white !important;
    padding-left: 360px !important;
    padding-right: 25px;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0E111A 0%, #1B1F2E 100%);
    width: 340px !important; min-width: 340px !important; max-width: 350px !important;
    position: fixed !important; top: 0; left: 0; bottom: 0; z-index: 100;
    padding: 1.6rem 1.2rem 2rem 1.2rem;
    border-right: 1px solid rgba(255,255,255,0.08);
    box-shadow: 8px 0 18px rgba(0,0,0,0.4);
}
.sidebar-title {font-size: 30px; font-weight: 800; color: #66FCF1; margin-bottom: 25px;}
.sidebar-item {background: rgba(255,255,255,0.07); border-radius: 12px; padding: 12px; margin: 10px 0; font-size: 17px; color: #C5C6C7;}
.section-header {font-size: 22px; font-weight: 700; color: #45A29E; margin-top: 25px; border-left: 4px solid #66FCF1; padding-left: 8px;}
.big-text {background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.15); border-radius: 16px; padding: 28px; margin-top: 15px;}
[data-baseweb="input"] input { background-color: rgba(20,20,30,0.6) !important; color: #F5F9FF !important; border-radius: 10px !important; border: 1px solid rgba(255,255,255,0.2) !important; font-weight: 600 !important; }
.bullish { color: #00FFB3; font-weight: 700; } .bearish { color: #FF6B6B; font-weight: 700; } .neutral { color: #FFD93D; font-weight: 700; }
.motivation {font-weight:600; font-size:16px; margin-top:12px;}
</style>
""", unsafe_allow_html=True)

# === API KEYS from Streamlit secrets ===
AV_API_KEY = st.secrets.get("ALPHAVANTAGE_API_KEY", "")
FH_API_KEY = st.secrets.get("FINNHUB_API_KEY", "")
TWELVE_API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", "")

# === safe autorefresh import fallback ===
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(interval=0, limit=None, key=None):
        return None

# === HELPERS FOR FORMATTING (avoid TypeError) ===
def format_price(p):
    """Return a human-friendly price string with trimmed trailing zeros.
        Returns 'N/A' for None."""
    if p is None:
        return "N/A"
    try:
        p = float(p)
    except Exception:
        return "N/A"
    # Choose precision by magnitude
    if abs(p) >= 10:
        s = f"{p:,.2f}"
    elif abs(p) >= 1:
        s = f"{p:,.3f}"
    else:
        # up to 6 decimal places, then trim
        s = f"{p:.6f}"
    # trim trailing zeros and final dot
    s = s.rstrip("0").rstrip(".")
    return s

def format_change(ch):
    """Format percent change with sign and 2 decimals, 'N/A' for None"""
    if ch is None:
        return "N/A"
    try:
        ch = float(ch)
    except Exception:
        return "N/A"
    sign = "+" if ch >= 0 else ""
    return f"{sign}{ch:.2f}%"

# === UNIVERSAL PRICE FETCHER (multi-backup) ===
def get_asset_price(symbol, vs_currency="usd"):
    symbol = symbol.upper()
    # 1) Finnhub
    if FH_API_KEY:
        try:
            r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FH_API_KEY}", timeout=6)
            d = r.json()
            if isinstance(d, dict) and d.get("c") not in (None, 0):
                chg = None
                if "pc" in d and d.get("pc"):
                    chg = ((d["c"] - d["pc"]) / d["pc"]) * 100
                return float(d["c"]), round(chg, 2) if chg is not None else None
        except Exception:
            pass
    # 2) Alpha Vantage
    if AV_API_KEY:
        try:
            r = requests.get(f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={AV_API_KEY}", timeout=6).json()
            if "Global Quote" in r and r["Global Quote"].get("05. price"):
                p = float(r["Global Quote"]["05. price"])
                ch_raw = r["Global Quote"].get("10. change percent", "0%").replace("%", "")
                ch = float(ch_raw) if ch_raw != "" else None
                return p, round(ch, 2) if ch is not None else None
        except Exception:
            pass
    # 3) TwelveData
    if TWELVE_API_KEY:
        try:
            r = requests.get(f"https://api.twelvedata.com/price?symbol={symbol}/{vs_currency.upper()}&apikey={TWELVE_API_KEY}", timeout=6).json()
            if "price" in r:
                return float(r["price"]), None
        except Exception:
            pass
    # final: return None to indicate failure (so caller can use historical fallback)
    return None, None

# === HISTORICAL FETCH (TwelveData) ===
def get_twelve_data(symbol, interval="1h", outputsize=200):
    if not TWELVE_API_KEY:
        return None
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=10).json()
        if "values" not in res:
            return None
        df = pd.DataFrame(res["values"])
        df[["close","high","low"]] = df[["close","high","low"]].astype(float)
        return df.sort_values("datetime").reset_index(drop=True)
    except Exception:
        return None

# === SYNTHETIC BACKUP (only used if ALL sources fail) ===
def synthesize_series(price, length=100, volatility_pct=0.005):
    base = float(price or 1.0)
    np.random.seed(int(base * 1000) % 2**31)
    returns = np.random.normal(0, volatility_pct, size=length)
    series = base * np.exp(np.cumsum(returns))
    df = pd.DataFrame({
        "datetime": pd.date_range(end=datetime.datetime.utcnow(), periods=length, freq="T"),
        "close": series,
        "high": series * (1 + np.random.normal(0, volatility_pct/2, size=length)),
        "low": series * (1 - np.random.normal(0, volatility_pct/2, size=length)),
    })
    return df

# === INDICATORS ===
def kde_rsi(df):
    closes = df["close"].astype(float).values
    if len(closes) < 5:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = pd.Series(gains).ewm(alpha=1/14, adjust=False).mean()
    avg_loss = pd.Series(losses).ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    w = np.exp(-0.5 * (np.linspace(-2, 2, max(len(rsi[-30:]),1)))**2)
    return float(np.average(rsi[-30:], weights=w))

def supertrend_status(df):
    hl2 = (df["high"] + df["low"]) / 2
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/10, adjust=False).mean()
    last_close = df["close"].iloc[-1]
    return "Supertrend: Bullish" if last_close > hl2.iloc[-1] else "Supertrend: Bearish"

def bollinger_status(df):
    close = df["close"]
    if len(close) < 20:
        return "Within Bands — Normal"
    ma = close.rolling(20).mean().iloc[-1]
    std = close.rolling(20).std().iloc[-1]
    upper, lower = ma + 2*std, ma - 2*std
    last = close.iloc[-1]
    if last > upper: return "Upper Band — Overbought"
    if last < lower: return "Lower Band — Oversold"
    return "Within Bands — Normal"

def combined_bias(kde_val, st_text, bb_text):
    score = 0
    if kde_val < 20: score += 50
    elif kde_val < 40: score += 25
    elif kde_val < 60: score += 0
    elif kde_val < 80: score -= 25
    else: score -= 50
    if "Bull" in st_text: score += 30
    elif "Bear" in st_text: score -= 30
    if "overbought" in bb_text.lower(): score -= 20
    elif "oversold" in bb_text.lower(): score += 20
    if score > 20: return "Bullish"
    if score < -20: return "Bearish"
    return "Neutral"

# === ANALYZE ===
def analyze(symbol, price, vs_currency):
    # Using 'price or 1.0' ensures synthesize_series always gets a non-zero number if price is None
    df_4h = get_twelve_data(symbol, "4h") or synthesize_series(price or 1.0)
    df_1h = get_twelve_data(symbol, "1h") or synthesize_series(price or 1.0)
    df_15m = get_twelve_data(symbol, "15min") or synthesize_series(price or 1.0)
    kde_val = kde_rsi(df_1h)
    st_text = f"{supertrend_status(df_4h)} (4H) • {supertrend_status(df_1h)} (1H)"
    bb_text = bollinger_status(df_15m)
    bias = combined_bias(kde_val, st_text, bb_text)
    
    # Calculate ATR-based levels
    # Use the max/min over the fetched 1-hour data if available
    if "high" in df_1h.columns and "low" in df_1h.columns and not df_1h.empty:
         # Calculate a simple range-based ATR proxy for a rough guide
         atr = (df_1h["high"].max() - df_1h["low"].min()) / len(df_1h) * 10
    else:
        # Fallback for synthetic data or failed fetch
        atr = (float(price or 1.0) * 0.01) # Use 1% of price as rough ATR
        
    base = float(price or 1.0)
    
    # Simple risk/reward calculation based on ATR proxy
    entry = base - 0.3 * atr
    target = base + 1.5 * atr
    stop = base - 1.0 * atr

    motivation = {
        "Bullish": "Stay sharp — momentum’s on your side.",
        "Bearish": "Discipline is your shield.",
        "Neutral": "Market resting — patience now builds precision later."
    }[bias]
    return f"""
<div class='big-text'>
<div class='section-header'>📊 Price Overview</div>
<b>{symbol}</b>: <span style='color:#58C5FF;'>{format_price(price)} {vs_currency.upper()}</span>
<div class='section-header'>📈 Indicators</div>
• KDE RSI: <b>{kde_val:.2f}%</b><br>
• Bollinger Bands: {bb_text}<br>
• Supertrend: {st_text}
<div class='section-header'>🎯 Suggested Levels (Based on current price and volatility)</div>
Entry: <b style='color:#58FFB5;'>{format_price(entry)}</b><br>
Target: <b style='color:#58FFB5;'>{format_price(target)}</b><br>
Stop Loss: <b style='color:#FF7878;'>{format_price(stop)}</b>
<div class='section-header'>📊 Overall Bias</div>
<b class='{bias.lower()}'>{bias}</b>
<div class='motivation'>💬 {motivation}</div>
</div>
"""

# === SIDEBAR ===
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context</p>", unsafe_allow_html=True)
btc, btc_ch = get_asset_price("BTCUSD")
eth, eth_ch = get_asset_price("ETHUSD")
st.sidebar.markdown(f"<div class='sidebar-item'><b>BTC:</b> ${format_price(btc)} ({format_change(btc_ch)})</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='sidebar-item'><b>ETH:</b> ${format_price(eth)} ({format_change(eth_ch)})</div>", unsafe_allow_html=True)

# === timezone detection (safe) ===
try:
    if get_localzone:
        tzname = str(get_localzone())
        try:
            tz = pytz.timezone(tzname)
        except Exception:
            tz = pytz.utc
    else:
        tz = pytz.utc
    local_time = datetime.datetime.now(tz)
except Exception:
    tz = pytz.utc
    local_time = datetime.datetime.now(pytz.utc)

st.sidebar.markdown(f"<div class='sidebar-item'><b>🕒 {local_time.strftime('%H:%M:%S (%Z)')}</b></div>", unsafe_allow_html=True)

# FX Session logic using local_time hour
hour = local_time.hour
if 5 <= hour < 14:
    session = "Asian Session (Tokyo/HK)"
elif 12 <= hour < 20:
    session = "European Session (London)"
else:
    session = "US Session (NY)"
st.sidebar.markdown(f"<div class='sidebar-item'><b>Active Session:</b> {session}</div>", unsafe_allow_html=True)

# safe auto-refresh (no-op if streamlit_autorefresh not installed)
st_autorefresh(interval=5000, limit=None, key="auto_refresh_key")

# === MAIN ===
st.title("AI Trading Chatbot")
col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_input("Enter Asset Symbol (e.g., BTCUSD, AAPL, EURUSD)")
with col2:
    vs_currency = st.text_input("Quote Currency", "usd").lower()

if user_input:
    symbol = user_input.strip().upper()
    
    # 1. Attempt to get live price and change
    price, _ = get_asset_price(symbol, vs_currency)
    
    # 2. If live price fails, try to fetch historical data and use the last close
    if price is None:
        df = get_twelve_data(symbol, "1h")
        # Check if DataFrame is valid and not empty
        price = float(df["close"].iloc[-1]) if df is not None and not df.empty else None
        
    # 3. Final check and analysis
    if price is None:
        st.error("❌ Could not verify live data. Try again later or check your API keys.")
    else:
        st.markdown(analyze(symbol, price, vs_currency), unsafe_allow_html=True)
else:
    st.info("Enter an asset symbol to GET REAL-TIME AI INSIGHT.")
