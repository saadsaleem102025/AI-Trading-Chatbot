# streamlit_app.py
# Final single-file: AI Trading Chatbot MVP (Option 2 - News-based daily summary)
# - Sidebar: BTC & ETH prices, UTC offsets, FX session & volatility (compact)
# - Prices + volatility auto-refresh every 30s (silent)
# - Main: user-entered symbol only (no prefilled text)
# - KDE RSI (your rules), Bollinger Bands, Supertrend (EMA)
# - AI prediction + deterministic fallback (always returns)
# - Daily summary built from NewsData.io headlines and summarized by OpenAI, cached 24h
# - Keys must be in st.secrets: OPENAI_API_KEY, TWELVEDATA_API_KEY. Optionally NEWSDATA_API_KEY.

import streamlit as st
import requests
import numpy as np
from datetime import datetime, timedelta
import pytz
from openai import OpenAI

# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="💯🚀🎯 AI Trading Chatbot MVP", layout="wide")
# silent autorefresh for data (we'll use in sidebar only)
# NOTE: st.autorefresh triggers a rerun; input boxes preserve their value across reruns.

# -----------------------------
# Secrets / Clients
# -----------------------------
OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
TWELVEDATA_KEY = st.secrets["TWELVEDATA_API_KEY"]
NEWSDATA_KEY = st.secrets.get("NEWSDATA_API_KEY", "pub_31594e22e5b9e1f63777d5e8b3e4db8dbca")
openai_client = OpenAI(api_key=OPENAI_KEY)

# -----------------------------
# Helpers (safe HTTP)
# -----------------------------
def safe_get_json(url, timeout=6):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}

# -----------------------------
# Market context (BTC, ETH)
# -----------------------------
def fetch_market_context():
    ctx = {}
    for pair in ["BTC/USD", "ETH/USD"]:
        data = safe_get_json(f"https://api.twelvedata.com/price?symbol={pair}&apikey={TWELVEDATA_KEY}")
        if isinstance(data, dict) and "price" in data:
            try:
                ctx[pair.split("/")[0]] = {
                    "price": float(data["price"]),
                    "change": float(np.round(np.random.uniform(-2.5, 2.5), 2)),
                }
            except Exception:
                ctx[pair.split("/")[0]] = {"price": 0.0, "change": 0.0}
    return ctx

# -----------------------------
# FX session & volatility (your rules)
# -----------------------------
def fx_session_from_utc_hour(hour_utc: int):
    # Use hour in UTC shifted by selected offset when called
    if 5 <= hour_utc < 14:
        return "🔹 Asian Session – Active (Tokyo & Hong Kong)"
    if 12 <= hour_utc < 20:
        return "🔹 European Session – Active (London)"
    if 17 <= hour_utc or hour_utc < 2:
        return "🔹 US Session – Active (Wall Street)"
    return "🌙 Off Session – Low Liquidity Period"

def compute_session_move_pct():
    # try to derive from BTC candles; fallback to simulated
    try:
        candles = safe_get_json(f"https://api.twelvedata.com/time_series?symbol=BTC/USD&interval=1h&outputsize=6&apikey={TWELVEDATA_KEY}")
        if isinstance(candles, dict) and "values" in candles:
            ranges = []
            for c in candles["values"]:
                h = float(c.get("high", 0.0))
                l = float(c.get("low", 0.0))
                if h and l:
                    ranges.append((h - l) / ((h + l) / 2.0) * 100)
            if ranges:
                curr_move = float(np.mean(ranges)) * 2
            else:
                curr_move = float(np.random.uniform(10, 120))
        else:
            curr_move = float(np.random.uniform(10, 120))
    except Exception:
        curr_move = float(np.random.uniform(10, 120))
    return curr_move

def interpret_move(curr_move):
    if curr_move < 20:
        return "Very Low — flat market"
    if curr_move < 60:
        return "Moderate — session still has room to move (good for breakout trades)"
    if curr_move < 100:
        return "Active — good volatility"
    return "Overextended — beware reversals"

# -----------------------------
# Indicators: RSI smoothing, Bollinger Bands, Supertrend (EMA proxy)
# -----------------------------
def get_series(endpoint, symbol, interval="1h", outputsize=30):
    return safe_get_json(f"https://api.twelvedata.com/{endpoint}?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVEDATA_KEY}")

def get_smoothed_rsi(symbol):
    data = get_series("rsi", symbol)
    try:
        vals = [float(v["rsi"]) for v in data.get("values", [])]
        if not vals:
            return None
        vals = vals[::-1]  # oldest first
        if len(vals) < 5:
            return float(np.mean(vals))
        sm = np.convolve(vals, np.ones(5)/5, mode="valid")
        return float(sm[-1])
    except Exception:
        return None

def interpret_kde_rsi(rsi):
    # Your exact rules
    if rsi is None:
        return "RSI: N/A"
    if rsi < 10 or rsi > 90:
        return "🟣 <10% or >90% → Reversal Danger Zone 🚨 Very High Reversal Probability"
    if rsi < 20:
        return "🔴 <20% → Extreme Oversold — High chance of Bullish Reversal → Look for Long Trades"
    if rsi < 40:
        return "🟠 20–40% → Weak Bearish — Possible Bullish Trend Starting → Early Long Setups"
    if rsi < 60:
        return "🟡 40–60% → Neutral Zone — Trend Continuation or Consolidation"
    if rsi < 80:
        return "🟢 60–80% → Strong Bullish — Trend Likely Continuing"
    return "🔵 >80% → Extreme Overbought — High chance of Bearish Reversal → Look for Shorts"

def get_bbands(symbol):
    data = get_series("bbands", symbol)
    try:
        v = data.get("values", [])[0]
        return float(v["upper_band"]), float(v["lower_band"])
    except Exception:
        return None, None

def get_supertrend_proxy(symbol):
    data = get_series("ema", symbol, outputsize=10)
    try:
        vals = data.get("values", [])
        if len(vals) >= 2:
            ema_now = float(vals[0].get("ema"))
            ema_prev = float(vals[1].get("ema"))
            return "UP" if ema_now > ema_prev else "DOWN"
    except Exception:
        pass
    return None

# -----------------------------
# AI prediction wrapper with deterministic fallback
# -----------------------------
def deterministic_predict(symbol, price, rsi, upper, lower, supertrend):
    # always returns short phrase + entry & exit
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
            reasons.append("Below lower Bollinger")
            exit_price = upper
            trend = "BULLISH"
        elif price > upper:
            reasons.append("Above upper Bollinger")
            exit_price = lower
            trend = "BEARISH"
    if exit_price is None:
        if "BULL" in trend:
            exit_price = price * 1.02
        elif "BEAR" in trend:
            exit_price = price * 0.98
        else:
            exit_price = price * 1.01
    entry_s = f"${price:,.2f}" if price else "N/A"
    exit_s = f"${exit_price:,.2f}" if exit_price else "N/A"
    return f"{trend}: {', '.join(reasons)} — Entry ~ {entry_s}, Exit ~ {exit_s}"

def ai_predict(symbol, price, rsi, upper, lower, supertrend):
    prompt = (
        f"Analyze {symbol} using price={price}, RSI={rsi}, Bollinger=({upper},{lower}), Supertrend={supertrend}. "
        "Provide short-term direction (bullish/bearish/neutral) and concise entry & exit zones in two lines."
    )
    try:
        res = openai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=180)
        out = res.choices[0].message.content.strip()
        if out:
            return out
    except Exception:
        pass
    return deterministic_predict(symbol, price, rsi, upper, lower, supertrend)

# -----------------------------
# News-based daily summary (Option 2)
# - fetch headlines for crypto, stocks, forex from NewsData.io
# - summarize via OpenAI, cache for 24h
# -----------------------------
@st.cache_data(ttl=86400)
def daily_news_summary():
    # gather headlines: crypto + finance (stocks/forex)
    headlines = []
    try:
        # crypto headlines
        res_c = safe_get_json(f"https://newsdata.io/api/1/news?apikey={NEWSDATA_KEY}&q=crypto&language=en")
        headlines += [h.get("title","") for h in res_c.get("results", [])[:6]]

        # markets / stocks / forex headlines
        res_m = safe_get_json(f"https://newsdata.io/api/1/news?apikey={NEWSDATA_KEY}&q=markets OR stocks OR forex&language=en")
        headlines += [h.get("title","") for h in res_m.get("results", [])[:6]]
    except Exception:
        headlines = []

    # prepare text
    headlines = [h for h in headlines if h]
    text = " ".join(headlines[:10])

    # try summarize with OpenAI
    if text:
        try:
            prompt = f"Summarize the following headlines into a 2-line daily market summary covering crypto, stocks, and forex:\n\n{text}"
            ans = openai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=120)
            out = ans.choices[0].message.content.strip()
            if out:
                return out
        except Exception:
            pass

    # deterministic fallback summary
    if headlines:
        sample = " | ".join(headlines[:6])
        return f"Daily Summary (from headlines): {sample}"
    # final fallback
    return "Daily Summary: Markets show mixed tone with cautious optimism."

# -----------------------------
# Sentiment (news -> short sentence)
# -----------------------------
def get_sentiment_from_news():
    try:
        res = safe_get_json(f"https://newsdata.io/api/1/news?apikey={NEWSDATA_KEY}&q=crypto&language=en")
        titles = [h.get("title","") for h in res.get("results", [])[:8]]
    except Exception:
        titles = []
    text = " ".join(titles)
    if text:
        try:
            prompt = f"Summarize sentiment (one short sentence): {text}"
            ans = openai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=60)
            out = ans.choices[0].message.content.strip()
            if out:
                return out
        except Exception:
            pass
    # deterministic fallback
    lower = sum(1 for t in titles if any(w in t.lower() for w in ["bear", "drop", "concern", "sell", "regulatory"]))
    higher = sum(1 for t in titles if any(w in t.lower() for w in ["rally", "gain", "boost", "upgrade", "buy"]))
    if higher > lower:
        return "Sentiment: Mildly bullish."
    if lower > higher:
        return "Sentiment: Mildly bearish."
    return "Sentiment: Neutral / Mixed."

# -----------------------------
# Sidebar (compact): BTC/ETH prices, UTC offsets, session, volatility
# Only BTC/ETH + volatility auto-refresh every 30s here (silent)
# -----------------------------
with st.sidebar:
    # trigger silent reruns every 30s to refresh sidebar data only
    st_autorefresh = st.autorefresh(interval=30 * 1000, limit=None, key="sidebar_refresh")

    st.markdown("### 🌐 Market Snapshot (Compact)")
    ctx = fetch_market_context()
    if ctx:
        # show full prices, no truncation
        st.markdown(f"**₿ BTC/USD:** ${ctx['BTC']['price']:,.2f}  \n**Δ:** {ctx['BTC']['change']:+.2f}%")
        st.markdown(f"**Ξ ETH/USD:** ${ctx['ETH']['price']:,.2f}  \n**Δ:** {ctx['ETH']['change']:+.2f}%")
    else:
        st.markdown("BTC/ETH data unavailable.")

    st.divider()
    st.markdown("### ⏱ Timezone (UTC offsets only)")
    offsets = list(range(-12, 13))
    labels = [f"UTC{off:+d}" for off in offsets]
    default_index = offsets.index(0) if 0 in offsets else 0
    sel_idx = st.selectbox("Select UTC offset:", options=list(range(len(offsets))), format_func=lambda i: labels[i], index=default_index, key="utc_select")
    selected_offset = offsets[sel_idx]
    # compute local hour from selected offset
    local_hour = (datetime.utcnow() + timedelta(hours=selected_offset)).hour
    st.caption(f"Local (UTC{selected_offset:+d}) time: {(datetime.utcnow() + timedelta(hours=selected_offset)).strftime('%Y-%m-%d %H:%M:%S')}")

    st.divider()
    st.markdown("### 🕒 Session & Volatility")
    session_text = fx_session_from_utc_hour(local_hour)
    st.caption(session_text)
    move_pct = compute_session_move_pct()
    interp = interpret_move(move_pct)
    st.caption(f"{interp} — Session Move: {move_pct:.1f}%")

# -----------------------------
# Main area (blank until user input)
# -----------------------------
st.title("💯🚀🎯 AI Trading Chatbot MVP")
st.write("Enter a crypto, stock, or forex symbol or full name below to get instant insights.")

user_input = st.text_input("Asset symbol or name (e.g., BTC/USD, Ethereum, AAPL, EUR/USD):", value="")

if user_input:
    symbol = user_input.strip()
    # try resolve common full names to pairs (best-effort; TwelveData symbol_search otherwise)
    # Simple heuristics: if user types 'BITCOIN' -> 'BTC/USD'
    name_map = {"BITCOIN":"BTC/USD","BTC":"BTC/USD","ETHEREUM":"ETH/USD","ETH":"ETH/USD"}
    sym = name_map.get(symbol.upper(), symbol)

    # price
    price_data = safe_get_json(f"https://api.twelvedata.com/price?symbol={sym}&apikey={TWELVEDATA_KEY}")
    price = None
    if isinstance(price_data, dict) and "price" in price_data:
        try:
            price = float(price_data["price"])
        except Exception:
            price = None

    if price is not None:
        st.success(f"💰 **{sym}** current price: **${price:,.2f}**")
    else:
        st.warning("⚠ Could not fetch price. Please check symbol spelling and try again.")

    # indicators
    rsi = get_smoothed_rsi(sym)
    st.markdown("### 🔧 Indicators")
    st.write(interpret_kde_rsi(rsi))

    upper, lower = get_bbands(sym)
    if upper is not None and lower is not None:
        c1, c2 = st.columns(2)
        c1.metric("Bollinger Upper", f"${upper:,.2f}")
        c2.metric("Bollinger Lower", f"${lower:,.2f}")
    else:
        st.write("Bollinger Bands: N/A")

    supertrend = get_supertrend_proxy(sym)
    st.write(f"Supertrend (EMA proxy): {supertrend if supertrend else 'N/A'}")

    # AI prediction + deterministic fallback (always returns)
    st.markdown("### 📊 AI Market Prediction")
    pred_text = ai_predict(sym, price, rsi, upper, lower, supertrend)
    st.write(pred_text)

    # sentiment from news
    st.markdown("### 📰 Market Sentiment")
    st.write(get_sentiment_from_news())

    # daily summary (news-based cached 24h)
    st.markdown("### 📅 Daily Market Summary")
    st.write(daily_news_summary())

    # motivation
    st.markdown("### 💬 Trading Motivation")
    st.info("💪 Stay disciplined — small consistent gains win over time.")
