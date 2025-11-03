import streamlit as st
import time, requests, datetime, pandas as pd, numpy as np, pytz
from streamlit_javascript import st_javascript

st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === STYLING ===
st.markdown("""<style>
header[data-testid="stHeader"], footer {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0E111A 0%, #1B1F2E 100%);
    width: 340px !important; min-width: 340px !important;
    border-right: 1px solid rgba(255,255,255,0.08);
    box-shadow: 8px 0 18px rgba(0,0,0,0.4);
}
.sidebar-title {font-size: 30px; font-weight: 800; color: #66FCF1;}
.sidebar-item {
    background: rgba(255,255,255,0.07); border-radius: 12px;
    padding: 10px; margin: 10px 0; color: #C5C6C7;
}
.sidebar-clock {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px; border-radius: 8px;
    color: #D8DEE9; font-size: 15px; font-weight: 600;
    text-shadow: 0 0 6px rgba(102,252,241,0.4);
    box-shadow: inset 0 0 5px rgba(255,255,255,0.05);
}
.fx-session {
    font-size: 14px; padding: 10px; border-radius: 8px;
    margin-top: 8px; font-weight: 600;
}
.fx-high { background: rgba(0,255,0,0.15); color: #00FFB3; }
.fx-med { background: rgba(255,215,0,0.15); color: #FFD93D; }
.fx-low { background: rgba(255,255,255,0.05); color: #BBBBBB; }
</style>""", unsafe_allow_html=True)

# === AUTO-DETECT LOCAL TIMEZONE ===
try:
    tz_name = st_javascript("Intl.DateTimeFormat().resolvedOptions().timeZone")
except Exception:
    tz_name = "Asia/Karachi"  # fallback
user_tz = pytz.timezone(tz_name)
local_time = datetime.datetime.now(user_tz)

# === FX SESSION DETECTOR ===
def get_fx_session(local_time):
    hour = local_time.hour
    dst_active = local_time.astimezone(pytz.timezone("US/Eastern")).dst() != datetime.timedelta(0)
    if 5 <= hour < 12:
        return "🔹 Asian Session", "⚪ Low → Moderate Volatility", "fx-low"
    elif (dst_active and 12 <= hour < 20) or (not dst_active and 13 <= hour < 21):
        return "🔸 European Session", "🟡 Moderate Volatility (London Active)", "fx-med"
    elif (dst_active and 17 <= hour or hour < 1) or (not dst_active and 18 <= hour or hour < 2):
        return "🔴 US Session", "🟢 High Volatility (Wall Street Open)", "fx-high"
    elif 17 <= hour < 21:
        return "🟢 Europe–US Overlap", "🔥 Highest Liquidity & Strongest Moves", "fx-high"
    else:
        return "🌙 Off Hours", "⚪ Flat or Ranging Market", "fx-low"

session_name, volatility, color_class = get_fx_session(local_time)

# === SIDEBAR HEADER ===
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='sidebar-clock'>🕒 {local_time.strftime('%H:%M:%S')} ({tz_name})</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='fx-session {color_class}'>{session_name}<br>{volatility}</div>", unsafe_allow_html=True)

# === MAIN UI ===
st.title("AI Trading Chatbot")

st.info("💬 Enter an asset symbol (e.g. BTC, EURUSD, AAPL) below to get live analysis.")
