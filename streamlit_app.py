st.markdown("""
<style>
/* === REMOVE STREAMLIT DEFAULT HEADER + FOOTER === */
header[data-testid="stHeader"], footer {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}

/* === GLOBAL MODERN UI === */
html, body, [class*="stText"], [data-testid="stMarkdownContainer"] {
    font-size: 18px !important;
    color: #E9EEF6 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    line-height: 1.8 !important;
}

/* === MAIN BACKGROUND === */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #0F2027, #203A43, #2C5364);
    color: white !important;
    padding: 25px;
}

/* === SIDEBAR: FLUSH LEFT + ENHANCED VISUAL SEPARATION === */
section[data-testid="stSidebar"] {
    padding-left: 0 !important;
    margin-left: 0 !important;
}
[data-testid="stSidebar"] {
    background: linear-gradient(165deg, #202538, #1C1F2E);
    width: 340px !important;
    min-width: 340px !important;
    max-width: 350px !important;
    padding: 1.6rem 1.2rem 2rem 1.2rem;
    border-right: 1px solid rgba(255,255,255,0.08);
    box-shadow: 6px 0 15px rgba(0,0,0,0.35);
    margin: 0 !important;
}

/* === SIDEBAR ELEMENTS === */
.sidebar-title {
    font-size: 24px;
    font-weight: 800;
    color: #66FCF1;
    margin-bottom: 25px;
}

.sidebar-item {
    background: rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 12px;
    margin: 10px 0;
    font-size: 17px;
    box-shadow: inset 0 0 10px rgba(0,0,0,0.3);
    color: #C5C6C7;
}

/* === SECTION HEADERS === */
.section-header {
    font-size: 22px;
    font-weight: 700;
    color: #45A29E;
    margin-top: 25px;
    border-left: 4px solid #66FCF1;
    padding-left: 8px;
}

/* === ANALYSIS BOX === */
.big-text {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 16px;
    padding: 28px;
    margin-top: 15px;
    box-shadow: 0 0 25px rgba(0,0,0,0.4);
}

/* === TEXT COLORS === */
.bullish { color: #00FFB3; font-weight: 700; }
.bearish { color: #FF6B6B; font-weight: 700; }
.neutral { color: #FFD93D; font-weight: 700; }

/* === MOTIVATIONAL BOX === */
.motivation {
    font-weight: 600;
    font-size: 19px;
    margin-top: 25px;
    color: #FFD700;
    background: rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 14px 16px;
    text-shadow: 0 0 8px rgba(255,215,0,0.5);
    box-shadow: inset 0 0 8px rgba(255,255,255,0.05);
}

/* === INPUT FIELDS === */
[data-baseweb="input"] input {
    background-color: rgba(255,255,255,0.12) !important;
    color: #E9EEF6 !important;
    border-radius: 10px !important;
}

/* === TITLES === */
h1, h2, h3 {
    color: #66FCF1 !important;
    text-shadow: 0 0 10px rgba(102,252,241,0.4);
}
</style>
""", unsafe_allow_html=True)
