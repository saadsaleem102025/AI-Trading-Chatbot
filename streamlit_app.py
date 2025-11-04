# === SIDEBAR ===
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context</p>", unsafe_allow_html=True)

btc, btc_ch = get_asset_price("BTCUSD")
eth, eth_ch = get_asset_price("ETHUSD")

# Safe number formatting (avoid TypeError when None)
def fmt_price(val):
    if val is None:
        return "N/A"
    try:
        return f"{float(val):,.2f}"
    except Exception:
        return "N/A"

def fmt_change(ch):
    if ch is None:
        return "N/A"
    try:
        return f"{float(ch):+.2f}%"
    except Exception:
        return "N/A"

st.sidebar.markdown(
    f"<div class='sidebar-item'><b>BTC:</b> ${fmt_price(btc)} ({fmt_change(btc_ch)})</div>",
    unsafe_allow_html=True
)
st.sidebar.markdown(
    f"<div class='sidebar-item'><b>ETH:</b> ${fmt_price(eth)} ({fmt_change(eth_ch)})</div>",
    unsafe_allow_html=True
)
