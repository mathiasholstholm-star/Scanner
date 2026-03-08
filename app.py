import streamlit as st
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# --- 1. TERMINAL CONFIGURATION ---
st.set_page_config(layout="wide", page_title="QUANT-X SYSTEM", page_icon="📈")
st_autorefresh(interval=30000, key="terminal_refresh")

# Professional UI Styling (CSS)
st.markdown("""
    <style>
    .main { background-color: #0b0e11; }
    .stMetric { 
        background-color: #161b22; 
        border: 1px solid #30363d; 
        padding: 10px; 
        border-radius: 4px; 
    }
    div[data-testid="stTable"] { 
        background-color: #0b0e11; 
        border: 1px solid #30363d; 
    }
    .status-bar {
        font-family: 'Courier New', Courier, monospace;
        color: #848d97;
        font-size: 12px;
        padding-bottom: 20px;
    }
    .header-text {
        color: #f0f6fc;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    </style>
    """, unsafe_allow_html=True)

FMP_API_KEY = st.secrets["FMP_API_KEY"]

# --- 2. BROWSER NOTIFICATIONS ---
def send_alert(symbol, score, change):
    js = f"""<script>if (Notification.permission === "granted") 
    {{ new Notification("QUANT-X ALERT: {symbol}", {{ body: "SCORE: {score}% | GAIN: {change}", icon: "" }}); }}</script>"""
    components.html(js, height=0)

# --- 3. ANALYTICS ENGINE ---
def fetch_asset_metrics(symbol):
    try:
        f_url = f"https://financialmodelingprep.com/api/v4/shares_float?symbol={symbol}&apikey={FMP_API_KEY}"
        s_url = f"https://financialmodelingprep.com/api/v4/short-interest?symbol={symbol}&apikey={FMP_API_KEY}"
        sec_url = f"https://financialmodelingprep.com/api/v3/sec_filings/{symbol}?limit=3&apikey={FMP_API_KEY}"
        
        fl_res = requests.get(f_url).json()
        sh_res = requests.get(s_url).json()
        sec_res = requests.get(sec_url).json()
        
        fl = round(fl_res[0]['floatShares'] / 1e6, 2) if fl_res else 0.0
        si = round(sh_res[0]['shortInterestRatio'], 2) if sh_res else 0.0
        dtc = round(sh_res[0]['daysToCover'], 2) if sh_res else 0.0
        
        risk_status = "STABLE"
        risk_penalty = 0
        if sec_res:
            for f in sec_res:
                if any(k in f['type'] for k in ["S-3", "424B", "F-3"]):
                    risk_status = "DILUTION RISK"
                    risk_penalty = -35
                    break
        return fl, si, dtc, risk_status, risk_penalty
    except: return 0.0, 0.0, 0.0, "N/A", 0

@st.cache_data(ttl=20)
def execute_market_scan():
    url = f"https://financialmodelingprep.com/api/v3/stock_screener?priceLowerThan=30&marketCapLowerThan=760000000&volumeMoreThan=500000&isEtf=false&isActivelyTrading=true&limit=50&apikey={FMP_API_KEY}"
    try:
        stocks = requests.get(url).json()
        dataset = []
        for s in stocks:
            change_pct = round(s.get('changesPercentage', 0), 2)
            if change_pct >= 15.0:
                symbol = s['symbol']
                fl, si, dtc, risk_msg, penalty = fetch_asset_metrics(symbol)
                
                # Quantitative Scoring Model
                score = 40 + penalty
                if change_pct > 30: score += 20
                if fl < 10.0: score += 25
                if dtc > 2.0: score += 10
                if s.get('volume', 0) > 1500000: score += 5
                
                dataset.append({
                    "SCORE": min(max(score, 0), 100),
                    "TICKER": symbol,
                    "GAIN %": change_pct,
                    "DTC": dtc,
                    "FLOAT (M)": fl,
                    "RISK ASSESSMENT": risk_msg,
                    "LAST PRICE": s['price'],
                    "VOLUME (M)": round(s['volume']/1e6, 2)
                })
        return sorted(dataset, key=lambda x: x['SCORE'], reverse=True)
    except: return []

# --- 4. TERMINAL INTERFACE ---
st.markdown("<h1 class='header-text'>QUANT-X INTELLIGENCE TERMINAL</h1>", unsafe_allow_html=True)
st.markdown("<div class='status-bar'>SYSTEM: OPERATIONAL | FEED: REAL-TIME | EXCHANGE: NYSE/NASDAQ/AMEX</div>", unsafe_allow_html=True)

col_actions = st.columns([1, 4])
with col_actions[0]:
    if st.button("ENABLE NOTIFICATIONS", use_container_width=True):
        components.html("<script>Notification.requestPermission();</script>", height=0)

st.divider()

data = execute_market_scan()

if data:
    # Top Momentum Summary
    top_asset = data[0]
    st.markdown("### PRIMARY SIGNAL")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("ASSET", top_asset['TICKER'])
    m2.metric("CONFIDENCE", f"{top_asset['SCORE']}%")
    m3.metric("PERFORMANCE", f"+{top_asset['GAIN %']}%")
    m4.metric("DTC", top_asset['DTC'])
    m5.metric("RISK", top_asset['RISK ASSESSMENT'])
    
    if top_asset['SCORE'] > 75:
        send_alert(top_asset['TICKER'], top_asset['SCORE'], f"{top_asset['GAIN %']}%")

    st.divider()

    # Data Grid
    df = pd.DataFrame(data)
    
    # Professional Styling of Dataframe
    def style_risk(val):
        color = '#f85149' if val == "DILUTION RISK" else '#238636'
        return f'color: {color}; font-weight: bold;'

    styled_df = df.style.applymap(style_risk, subset=['RISK ASSESSMENT'])\
                        .background_gradient(cmap='Greys', subset=['SCORE'])\
                        .format({"LAST PRICE": "${:.2f}", "GAIN %": "{:.1f}%", "FLOAT (M)": "{:.1f}"})

    st.dataframe(styled_df, use_container_width=True, height=500, hide_index=True)

else:
    st.info("Scanning infrastructure for high-velocity assets (>15% gain). No current matches.")

st.divider()
st.caption("QUANT-X SYSTEM | DATA REFRESH 30S | NO INVESTMENT ADVICE")
    
