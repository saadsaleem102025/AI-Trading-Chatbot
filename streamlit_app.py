```python
BULLISH PRESSURE: Capitalize on the upward force. **Successful trading is 80% preparation, 20% execution.**"
        ],
        "Strong Bearish": [
            "DOWNTREND CONFIRMED: Respect stops and look for short opportunities near resistance. **Keep risk management paramount.**",
            "STRONG SELL SIGNAL: Sentiment has turned decisively. **Manage the downside, and the upside will take care of itself.**",
            "BEARISH PRESSURE: Do not hold against a strong downtrend. **The goal is not to trade often, but to trade well.**"
        ],
        "Neutral (Consolidation/Wait for Entry Trigger)": [
            "MARKET RESTING: Patience now builds precision later. Preserve capital. **Successful trading is 80% waiting.**",
            "CONSOLIDATION ZONE: Wait for the price to show its hand. **No position is a position.**",
            "IDLE CAPITAL: Do not enter a trade without a clear edge. **The best opportunities are often the ones you wait for.**"
        ],
        "Neutral (Conflicting Signals/Extreme Condition)": [
            "CONFLICTING SIGNALS: Wait for clear confirmation from trend or momentum. **Avoid emotional trading; trade only what you see.**",
            "HIGH UNCERTAINTY: Indicators are mixed or at extremes. **Protect your capital; avoid the urge to guess.**",
            "AVOID THE CHOP: This is a market for scalpers or observers. **Focus on the next clear setup, not this messy one.**"
        ]
    }
    
    default_motivation = "MAINTAIN EMOTIONAL DISTANCE: Trade the strategy, not the emotion."
    motivation = random.choice(motivation_options.get(bias, [default_motivation]))
    
    current_price_line = f"Current Price : <span class='asset-price-value'>{price_display} {vs_currency.upper()}</span>{change_display}"
    trade_parameters = get_trade_recommendation(bias, current_price, atr_val)
    analysis_summary_html = get_natural_language_summary(symbol, bias, trade_parameters)
    
    # --- FINAL OUTPUT STRUCTURE (Unchanged) ---
    full_output = f"""
<div class='big-text'>
<div class='analysis-item'>{current_price_line}</div>

<div class='section-header'>📊 Detailed Indicator Analysis</div>

<div class='analysis-item'>KDE RSI Status: <b>{kde_rsi_output}</b></div>
<div class='indicator-explanation'>{get_kde_rsi_explanation()}</div>

<div class='analysis-item'><b>{supertrend_output}</b> ({st_status_1h.split(' - ')[1]})</div>
<div class='indicator-explanation'>{get_supertrend_explanation(st_status_1h)}</div>

<div class='analysis-item'>Bollinger Bands: <b>{bb_status}</b></div>
<div class='indicator-explanation'>{get_bollinger_explanation(bb_status)}</div>

<div class='analysis-item'>EMA Crossover (5/20): <b>{ema_status}</b></div>
<div class='indicator-explanation'>{get_ema_explanation(ema_status)}</div>

<div class='analysis-item'>Parabolic SAR: <b>{psar_status}</b></div>
<div class='indicator-explanation'>{get_psar_explanation(psar_status)}</div>

<div class='analysis-bias'>Overall Market Bias: <span class='{bias.split(" ")[0].lower()}'>{bias}</span></div>

<div class='section-header'>⭐ AI Trading Recommendation Summary</div>
{analysis_summary_html}

<div class='analysis-motto-prominent'>{motivation}</div>

<div class='risk-warning'>
⚠️ <b>Risk Disclaimer:</b> The ChatBot uses Risk-Reward Ratio as 1:2. This is not financial advice. All trading involves risk. Past performance doesn't guarantee future results. Only trade with money you can afford to lose. Always use stop losses .
</div>
</div>
"""
    return full_output

# === Session Logic (Unchanged) ---
utc_now = datetime.datetime.now(timezone.utc)
utc_hour = utc_now.hour

SESSION_TOKYO = (dt_time(0, 0), dt_time(9, 0))
SESSION_LONDON = (dt_time(8, 0), dt_time(17, 0))
SESSION_NY = (dt_time(13, 0), dt_time(22, 0)) 
OVERLAP_START_UTC = dt_time(13, 0)
OVERLAP_END_UTC = dt_time(17, 0) 

def get_session_info(utc_now):
    current_time_utc = utc_now.time()
    utc_hour = utc_now.hour  # <-- add this line
    session_name = "Quiet/Sydney Session"
    current_range_pct = 0.02
    
    if OVERLAP_START_UTC <= current_time_utc < OVERLAP_END_UTC:
        session_name = "Overlap: London / New York"
        current_range_pct = 0.30 
    elif dt_time(8, 0) <= current_time_utc < dt_time(9, 0):
        session_name = "Overlap: Tokyo / London"
        current_range_pct = 0.18
    elif SESSION_NY[0] <= current_time_utc < SESSION_NY[1]:
        session_name = "US Session (New York)"
        current_range_pct = 0.15
    elif SESSION_LONDON[0] <= current_time_utc < SESSION_LONDON[1]:
        session_name = "European Session (London)"
        current_range_pct = 0.15
    elif SESSION_TOKYO[0] <= current_time_utc < SESSION_TOKYO[1]:
        session_name = "Asian Session (Tokyo)"
        current_range_pct = 0.08 if utc_hour < 3 else 0.05
    
    avg_range_pct = 0.1
    ratio = (current_range_pct / avg_range_pct) * 100
    if ratio < 20:
        status = "Flat / Very Low Volatility"
    elif 20 <= ratio < 60:
        status = "Low Volatility / Room to Move"
    elif 60 <= ratio < 100:
        status = "Moderate Volatility / Near Average"
    else:
        status = "High Volatility / Possible Exhaustion"
    
    volatility_html = f"<span class='status-volatility-info'><b>Status:</b> {status} ({ratio:.0f}% of Avg)</span>"
    return session_name, volatility_html

session_name, volatility_html = get_session_info(utc_now)


session_name, volatility_html = get_session_info(utc_now)

# --- SIDEBAR DISPLAY ---
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context</p>", unsafe_allow_html=True)

# 💡 CHANGE: Removed the BTC and SPY price fetching and display block
# This makes the app load instantly.

tz_options = [f"UTC{h:+03d}:{m:02d}" for h in range(-12, 15) for m in (0, 30) if not (h == 14 and m == 30) or (h == 13 and m==30) or (h == -12 and m == 30) or (h==-11 and m==30)]
tz_options.extend(["UTC+05:45", "UTC+08:45", "UTC+12:45"])
tz_options = sorted(list(set(tz_options))) 
try: default_ix = tz_options.index("UTC+05:00") 
except ValueError: default_ix = tz_options.index("UTC+00:00") 

selected_tz_str = st.sidebar.selectbox("Select Your Timezone", tz_options, index=default_ix)

offset_str = selected_tz_str.replace("UTC", "")
hours, minutes = map(int, offset_str.split(':'))
total_minutes = (abs(hours) * 60 + minutes) * (-1 if hours < 0 or offset_str.startswith('-') else 1)
user_tz = timezone(timedelta(minutes=total_minutes))
user_local_time = datetime.datetime.now(user_tz)

st.sidebar.markdown(f"<div class='sidebar-item'><b>Your Local Time:</b> <span class='local-time-info'>{user_local_time.strftime('%H:%M')}</span></div>", unsafe_allow_html=True)

# 💡 CHANGE 2: Fixed the typo (class='sidebar-item') to correctly wrap the Session Info in a box
st.sidebar.markdown(f"<div class='sidebar-item'><b>Active Session:</b> <span class='active-session-info'>{session_name}</span><br>{volatility_html}</div>", unsafe_allow_html=True)

today_overlap_start_utc = datetime.datetime.combine(utc_now.date(), OVERLAP_START_UTC, tzinfo=timezone.utc)
today_overlap_end_utc = datetime.datetime.combine(utc_now.date(), OVERLAP_END_UTC, tzinfo=timezone.utc)

overlap_start_local = today_overlap_start_utc.astimezone(user_tz)
overlap_end_local = today_overlap_end_utc.astimezone(user_tz)

st.sidebar.markdown(f"""
<div class='sidebar-item sidebar-overlap-time'>
<b>London/NY Overlap Times (Peak Liquidity)</b><br>
<span style='font-size: 20px; color: #22D3EE; font-weight: 700;'>
{overlap_start_local.strftime('%H:%M')} - {overlap_end_local.strftime('%H:%M')}
</span>
<br>({selected_tz_str})
</div>
""", unsafe_allow_html=True)

# --- MAIN EXECUTION ---
st.title("AI Trading Chatbot")

col1, col2 = st.columns([1.5, 2.5])

with col1:
    asset_type = st.selectbox(
        "Select Asset Type",
        ("Stock/Index", "Crypto"),
        index=0,
        help="Select 'Stock/Index' for stocks/indices. Select 'Crypto' for cryptocurrencies."
    )

with col2:
    user_input = st.text_input(
        "Enter Official Ticker Symbol",
        placeholder="e.g., TSLA, HOOD, BTC, HYPE",
        help="Please enter the official ticker symbol (e.g., AAPL, BTC, NDX)."
    )

vs_currency = "usd"
if user_input:
    # 1. Resolve to the base symbol (input is now assumed to be the ticker)
    base_symbol, resolved_symbol = resolve_asset_symbol(user_input, asset_type, vs_currency)
    
    # 2. PERFORM SIMPLIFIED ASSET TYPE VALIDATION
    validation_error = None
    
    is_common_crypto = base_symbol in KNOWN_CRYPTO_SYMBOLS
    is_common_stock = base_symbol in KNOWN_STOCK_SYMBOLS

    if asset_type == "Crypto" and is_common_stock:
        validation_error = f"You selected <strong>Crypto</strong> but entered a known stock/index symbol (<strong>{base_symbol}</strong>). Please select 'Stock/Index' from the dropdown to proceed."
    elif asset_type == "Stock/Index" and is_common_crypto:
        validation_error = f"You selected <strong>Stock/Index</strong> but entered a known crypto symbol (<strong>{base_symbol}</strong>). Please select 'Crypto' from the dropdown to proceed."

    # 3. Handle Validation Error or Proceed to Fetch/Analyze
    if validation_error:
        st.markdown(generate_error_message(
            title="⚠️ Asset Type Mismatch ⚠️",
            message="Please ensure the selected **Asset Type** matches the **Ticker Symbol** you entered.",
            details=validation_error
        ), unsafe_allow_html=True)
    else:
        # 💡 CHANGE 2: Use a custom spinner to provide feedback during network latency
        with st.spinner(f"Fetching live data and generating analysis for {resolved_symbol}...") :
            price, price_change_24h = get_asset_price(resolved_symbol, vs_currency, asset_type)
            st.markdown(analyze(resolved_symbol, price, price_change_24h, vs_currency, asset_type), unsafe_allow_html=True)
```
