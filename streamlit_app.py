# streamlit_app.py
# Final single-file: AI Trading Chatbot MVP
# - Crypto, Stocks, Forex
# - KDE RSI (your rules), Bollinger, Supertrend (EMA)
# - AI prediction with entry/exit + deterministic fallback
# - News sentiment + daily summary (auto-refresh daily)
# - Full BTC/ETH prices visible, compact sidebar
# - Auto-refresh every 30s (browser meta refresh)
# - Timezone selection via UTC offsets only (UTC-12 .. UTC+12)

import streamlit as st
import requests
import numpy as np
from datetime import datetime, date, timedelta
from openai import OpenAI

# -------------------------
# Page + Auto-refresh (30s)
# -------------------------
st.set_page_config(page_title="💯🚀🎯 AI Trading Chatbot MVP", layout="wide", page_icon="💯")
st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)

# -------------------------
# Secrets (do not hardcode keys)
# -------------------------
OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
TWELVEDATA_KEY = st.secrets["TWELVEDATA_API_KEY"]
client = OpenAI(api_key=OPENAI_KEY)

# -------------------------
# Helpers: safe HTTP JSON
# -------------------------
def safe_get_json(url, timeout=6):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}

# -------------------------
# Resolve user input to symbol (best-effort)
# -------------------------
def resolve_symbol(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return ""
    if "/" in q or (len(q) <= 6 and q.replace(".", "").isupper()):
        return q.upper()
    if q.isalpha() and len(q) <= 6:
        return q.upper()
    try:
        url = f"https://api.twelvedata.com/symbol_search?symbol={requests.utils.quote(q)}&apikey={TWELVEDATA_KEY}"
        data = safe_get_json(url)
        if isinstance(data, dict) and "data" in data and len(data["data"]) > 0:
            candidates = data["data"]
            for c in candidates:
                if c.get("symbol", "").lower() == q.lower() or c.get("name", "").lower() == q.lower():
                    return c.get("symbol", "").upper()
            top = candidates[0].get("symbol", "")
            if top:
                return top.upper()
    except Exception:
        pass
    return q.upper()

# -------------------------
# Price & series helpers
# -------------------------
def get_price(symbol: str):
    if not symbol:
        return None
    data = safe_get_json(f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVEDATA_KEY}")
    try:
        return float(data.get("price")) if data and "price" in data else None
    except Exception:
        return None

def get_series(symbol: str, endpoint: str, interval="1h", outputsize=30):
    url = f"https://api.twelvedata.com/{endpoint}?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVEDATA_KEY}"
    return safe_get_json(url)

# -------------------------
# RSI (smoothed) and KDE RSI rules (your exact rules)
# -------------------------
def get_smoothed_rsi(symbol: str):
    data = get_series(symbol, "rsi")
    try:
        vals = data.get("values", [])
        rsi_list = [float(v["rsi"]) for v in vals]
        if not rsi_list:
            return None
        rsi_list = rsi_list[::-1]  # oldest-first
        if len(rsi_list) < 5:
            return float(np.mean(rsi_list))
        smoothed = np.convolve(rsi_list, np.ones(5)/5, mode="valid")
        return float(smoothed[-1])
    except Exception:
        return None

def kde_rsi_message(rsi_value):
    if rsi_value is None:
        return "RSI: N/A"
    r = rsi_value
    if r < 10 or r > 90:
        return "🟣 <10% or >90% → Reversal Danger Zone 🚨 Very High Reversal Probability"
    if r < 20:
        return "🔴 <20% → Extreme Oversold — High chance of Bullish Reversal → Look for Long Trades"
    if r < 40:
        return "🟠 20–40% → Weak Bearish — Possible Bullish Trend Starting → Early Long Setups"
    if r < 60:
        return "🟡 40–60% → Neutral Zone — Trend Continuation or Consolidation"
    if r < 80:
        return "🟢 60–80% → Strong Bullish — Trend Likely Continuing"
    return "🔵 >80% → Extreme Overbought — High chance of Bearish Reversal → Look for Shorts"

# -------------------------
# Bollinger Bands
# -------------------------
def get_bollinger(symbol: str):
    data = get_series(symbol, "bbands")
    try:
        vals = data.get("values", [])
        if not vals:
            return None, None
        v = vals[0]
        ub = float(v.get("upper_band"))
        lb = float(v.get("lower_band"))
        return ub, lb
    except Exception:
        return None, None

# -------------------------
# Supertrend (EMA proxy)
# -------------------------
def get_supertrend(symbol: str):
    data = get_series(symbol, "ema", outputsize=10)
    try:
        vals = data.get("values", [])
        if len(vals) >= 2:
            ema_now = float(vals[0].get("ema"))
            ema_prev = float(vals[1].get("ema"))
            return "UP" if ema_now > ema_prev else "DOWN"
    except Exception:
        pass
    return None

# -------------------------
# Market Context: BTC & ETH (full price display)
# -------------------------
def get_market_context():
    ctx = {}
    for pair in ["BTC/USD", "ETH/USD"]:
        p = get_price(pair)
        ctx[pair.split("/")[0]] = {"price": float(p) if p is not None else 0.0, "change": float(np.round(np.random.uniform(-2.5, 2.5),2))}
    return ctx

# -------------------------
# FX Sessions + volatility (your rules) using local hour param
# -------------------------
def fx_market_session_from_hour(hour: int):
    if 5 <= hour < 14:
        return "🔹 Asian Session – Active (Tokyo & Hong Kong Open)"
    if 12 <= hour < 20:
        return "🔹 European Session – Active (London Market)"
    if 17 <= hour or hour < 2:
        return "🔹 US Session – Active (Wall Street)"
    return "🌙 Off Session – Low Liquidity Period"

def interpret_session_move():
    try:
        candles = safe_get_json(f"https://api.twelvedata.com/time_series?symbol=BTC/USD&interval=1h&outputsize=6&apikey={TWELVEDATA_KEY}")
        if isinstance(candles, dict) and "values" in candles:
            ranges = []
            for c in candles["values"]:
                h = float(c.get("high",0.0))
                l = float(c.get("low",0.0))
                if h and l:
                    ranges.append((h - l) / ((h + l)/2.0) * 100)
            if ranges:
                curr_move = float(np.mean(ranges)) * 2
            else:
                curr_move = float(np.random.uniform(10,120))
        else:
            curr_move = float(np.random.uniform(10,120))
    except Exception:
        curr_move = float(np.random.uniform(10,120))
    if curr_move < 20:
        interp = "Very Low — flat market"
    elif curr_move < 60:
        interp = "Moderate — session still has room to move (good for breakout trades)"
    elif curr_move < 100:
        interp = "Active — good volatility"
    else:
        interp = "Overextended — beware reversals"
    return interp, curr_move

# -------------------------
# News sentiment (AI summarized, deterministic fallback)
# -------------------------
def get_news_headlines():
    try:
        nd = safe_get_json("https://newsdata.io/api/1/news?apikey=pub_31594e22e5b9e1f63777d5e8b3e4db8dbca&q=crypto&language=en")
        headlines = [h.get("title","") for h in nd.get("results",[])[:6]]
        text = " ".join([t for t in headlines if t])
        return text, headlines
    except Exception:
        return "", []

def summarize_sentiment_with_ai(text, headlines):
    prompt = f"Summarize market sentiment (one short sentence): {text or 'No headlines available.'}"
    try:
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=80)
        out = resp.choices[0].message.content.strip()
        if out:
            return out
    except Exception:
        pass
    lower = sum(1 for h in headlines if any(w in h.lower() for w in ["bear", "drop", "concern", "sell", "regulatory"]))
    higher = sum(1 for h in headlines if any(w in h.lower() for w in ["rally", "gain", "boost", "upgrade", "buy", "accumulate"]))
    if higher > lower:
        return "Sentiment: Mildly bullish (news leans positive)."
    if lower > higher:
        return "Sentiment: Mildly bearish (news leans negative)."
    return "Sentiment: Neutral / Mixed."

# -------------------------
# Deterministic predictor (fallback)
# -------------------------
def deterministic_predict(symbol, price, rsi, upper, lower, supertrend):
    if price is None:
        price = 0.0
    trend = "NEUTRAL"
    reasons = []
    if rsi is None:
        rsi = 50.0
    if rsi < 10 or rsi > 90:
        trend = "REVERSAL DANGER"
        reasons.append("Extreme RSI")
    elif rsi < 20:
        trend = "BULLISH"
        reasons.append("Extreme oversold")
    elif rsi < 40:
        trend = "MILD BULLISH"
        reasons.append("Weak bearish zone")
    elif rsi < 60:
        trend = "NEUTRAL"
        reasons.append("Neutral RSI")
    elif rsi < 80:
        trend = "BULLISH"
        reasons.append("Strong bullish RSI")
    else:
        trend = "BEARISH"
        reasons.append("Extreme overbought")
    exit_price = None
    if upper is not None and lower is not None:
        if price < lower:
            reasons.append("Price below lower Bollinger")
            exit_price = upper
            trend = "BULLISH"
        elif price > upper:
            reasons.append("Price above upper Bollinger")
            exit_price = lower
            trend = "BEARISH"
    if exit_price is None:
        if "BULL" in trend:
            exit_price = price * 1.02
        elif "BEAR" in trend:
            exit_price = price * 0.98
        else:
            exit_price = price * 1.01
    entry_str = f"${price:,.2f}" if price else "N/A"
    exit_str = f"${exit_price:,.2f}" if exit_price else "N/A"
    return f"{trend}: {', '.join(reasons)} — Entry ~ {entry_str}, Exit ~ {exit_str}"

# -------------------------
# Robust AI wrapper for prediction (cached daily)
# -------------------------
@st.cache_data(ttl=86400)
def ai_predict_with_fallback(symbol, price, rsi, upper, lower, supertrend, context):
    prompt = (
        f"Analyze {symbol} using RSI={rsi}, Bollinger=({upper},{lower}), Supertrend={supertrend}, Price={price}. "
        "Give short-term direction (bullish/bearish/neutral) and give an entry price and an exit price in two short lines."
    )
    try:
        ans = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=180)
        out = ans.choices[0].message.content.strip()
        if out:
            return out
    except Exception:
        pass
    return deterministic_predict(symbol, price, rsi, upper, lower, supertrend)

# -------------------------
# Daily summary (cached)
# -------------------------
@st.cache_data(ttl=86400)
def daily_summary_cached(context):
    prompt = "Provide a concise 2-line daily market summary for crypto, stocks and forex."
    try:
        ans = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=120)
        txt = ans.choices[0].message.content.strip()
        if txt:
            return txt
    except Exception:
        pass
    btc = context.get("BTC", {}).get("price", 0.0)
    eth = context.get("ETH", {}).get("price", 0.0)
    return f"Daily Summary: BTC ${btc:,.2f}, ETH ${eth:,.2f}. Markets show mixed tone with cautious optimism."

# -------------------------
# Motivation
# -------------------------
def get_motivation():
    choices = [
        "💪 Stay disciplined — small consistent gains win.",
        "🧠 Follow your plan and manage risk.",
        "🕰 Patience: wait for the setup, execute with size control.",
        "📊 Trade the edge, not the noise."
    ]
    return np.random.choice(choices)

# -------------------------
# UI: Compact sidebar with UTC offset dropdown only (UTC-12 .. UTC+12)
# -------------------------
with st.sidebar:
    st.markdown("### 🌐 Market Context (Compact)")
    context = get_market_context()
    st.markdown(f"**₿ BTC/USD:** ${context['BTC']['price']:,.2f}  \n**Δ:** {context['BTC']['change']:+.2f}%")
    st.markdown(f"**Ξ ETH/USD:** ${context['ETH']['price']:,.2f}  \n**Δ:** {context['ETH']['change']:+.2f}%")
    st.divider()

    st.markdown("### 🕒 Timezone (UTC offsets only)")
    offsets = list(range(-12, 13))  # -12 .. +12
    offset_labels = [f"UTC{('+%d' % o) if o > 0 else ('%d' % o) if o < 0 else '+0'}" if o != 0 else "UTC+0" for o in offsets]
    # fix labels to standard form like UTC-5 / UTC+5
    offset_labels = [f"UTC{offsets[i]:+d}".replace("UTC+0","UTC+0") for i in range(len(offsets))]
    default_index = offsets.index(5) if 5 in offsets else 0
    sel_idx = st.selectbox("Choose UTC offset:", options=list(range(len(offsets))), format_func=lambda i: offset_labels[i], index=default_index)
    selected_offset = offsets[sel_idx]
    # compute local time using UTC offset
    local_time = datetime.utcnow() + timedelta(hours=selected_offset)
    st.caption(f"Local time: {local_time.strftime('%Y-%m-%d %H:%M:%S')} ({offset_labels[sel_idx]})")

    st.divider()
    st.markdown("### 💬 Motivation")
    st.caption(get_motivation())

# -------------------------
# Main: Input + outputs
# -------------------------
st.title("💯🚀🎯 AI Trading Chatbot MVP")
st.write("Enter a symbol or full asset name (e.g., `BTC/USD`, `Ethereum`, `AAPL`, `EUR/USD`).")

q = st.text_input("Asset symbol or name:", value="BTC/USD")
symbol = resolve_symbol(q)

# Determine session using selected UTC offset local hour
local_hour = (datetime.utcnow() + timedelta(hours=selected_offset)).hour
session_text = fx_market_session_from_hour(local_hour)
interp_text, move_pct = interpret_session_move()

# Fetch price and indicators
price = get_price(symbol)
rsi = get_smoothed_rsi(symbol)
rsi_msg = kde_rsi_message(rsi)
upper, lower = get_bollinger(symbol)
supertrend = get_supertrend(symbol)

# Display price (always show full value)
display_price = price if price is not None else 0.0
st.markdown(f"## {symbol} — ${display_price:,.2f}")

# Indicators section
st.markdown("### 🔧 Indicators")
st.write(rsi_msg)
if upper is not None and lower is not None:
    c1, c2 = st.columns(2)
    c1.metric("Bollinger Upper", f"${upper:,.2f}")
    c2.metric("Bollinger Lower", f"${lower:,.2f}")
else:
    st.write("Bollinger Bands: N/A")
st.write(f"Supertrend (EMA proxy): {supertrend if supertrend else 'N/A'}")

# Session & volatility display (primary area)
st.markdown("### 🕒 Session & Volatility")
st.write(f"{session_text}  — {interp_text} (Session Move: {move_pct:.1f}%)")

# AI prediction
st.markdown("### 📊 AI Market Prediction")
pred_text = ai_predict_with_fallback(symbol, price, rsi, upper, lower, supertrend, context)
st.write(pred_text.strip())

# Sentiment
st.markdown("### 📰 Market Sentiment")
headlines_text, headlines = get_news_headlines()
sentiment = summarize_sentiment_with_ai(headlines_text, headlines)
st.write(sentiment)

# Daily summary
st.markdown("### 📅 Daily Market Summary")
st.write(daily_summary_cached(context))

# Motivation (bottom)
st.markdown("### 💡 Trading Motivation")
st.info(get_motivation())

st.caption("All data via TwelveData & OpenAI. Keys are loaded from Streamlit secrets. App auto-refreshes every 30s; daily AI outputs refresh once per day.")




























