import streamlit as st
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# --- 1. CONFIG & AUTO-REFRESH (30 SEK) ---
st.set_page_config(layout="wide", page_title="QUANT-X ULTIMATE")
st_autorefresh(interval=30000, key="datarefresh")

FMP_API_KEY = st.secrets["FMP_API_KEY"]
BULL_KEYWORDS = ["FDA", "APPROVAL", "AI", "DRONE", "DEFENSE", "PENTAGON", "CONTRACT", "SQUEEZE"]

# --- 2. JAVASCRIPT TIL NOTIFIKATIONER ---
def trigger_browser_notification(symbol, score):
    js = f"""
    <script>
    if (Notification.permission === "granted") {{
        new Notification("🚀 NY RAKET FUNDET", {{ body: "{symbol} har en score på {score}%", icon: "https://cdn-icons-png.flaticon.com/512/2522/2522648.png" }});
    }}
    </script>
    """
    components.html(js, height=0)

# --- 3. DATA FUNKTIONER (FIXET NAMEERROR) ---

def check_dilution_risk(symbol):
    """Scanner for warrants og offering risiko"""
    try:
        url_sec = f"https://financialmodelingprep.com/api/v3/sec_filings/{symbol}?limit=5&apikey={FMP_API_KEY}"
        sec = requests.get(url_sec).json()
        if sec:
            for filing in sec:
                if any(k in filing['type'] for k in ["S-3", "424B", "F-3"]):
                    return "🚨 HØJ (SEC)", -30
        return "✅ LAV", 0
    except: return "N/A", 0

def get_detailed_data(symbol):
    """Henter Float, Short Interest og DTC"""
    try:
        f_url = f"https://financialmodelingprep.com/api/v4/shares_float?symbol={symbol}&apikey={FMP_API_KEY}"
        s_url = f"https://financialmodelingprep.com/api/v4/short-interest?symbol={symbol}&apikey={FMP_API_KEY}"
        fl = requests.get(f_url).json()
        sh = requests.get(s_url).json()
        
        float_val = round(fl[0]['floatShares'] / 1e6, 2) if fl else 0.0
        si_pct = round(sh[0]['shortInterestRatio'], 2) if sh else 0.0
        dtc = round(sh[0]['daysToCover'], 2) if sh else 0.0
        return float_val, si_pct, dtc
    except: return 0.0, 0.0, 0.0

# --- 4. CORE SCANNER ---

@st.cache_data(ttl=25)
def run_ultimate_scanner():
    # Filtre fra dine screenshots: Pris < 30, Cap < 760M, Vol > 500k
    url = f"https://financialmodelingprep.com/api/v3/stock_screener?priceLowerThan=30&marketCapLowerThan=760000000&volumeMoreThan=500000&isEtf=false&isActivelyTrading=true&limit=40&apikey={FMP_API_KEY}"
    try:
        stocks = requests.get(url).json()
        results = []
        for s in stocks:
            symbol = s['symbol']
            hist_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={FMP_API_KEY}"
            h = requests.get(hist_url).json()
            
            if 'historical' in h:
                df = pd.DataFrame(h['historical']).head(21)
                rvol = round(s['volume'] / df.iloc[1:21]['volume'].mean(), 2)
                
                # Hent alle parametre
                fl, si, dtc = get_detailed_data(symbol)
                risk_label, risk_penalty = check_dilution_risk(symbol)
                
                # BEREGN SCORE (0-100)
                score = 50 + risk_penalty
                if rvol >= 5.0: score += 20
                if fl < 10.0: score += 15
                if si > 15.0: score += 10
                if dtc > 3.0: score += 5
                
                results.append({
                    "SYMBOL": symbol,
                    "SCORE": min(max(score, 0), 100),
                    "DTC": dtc,
                    "RVOL": rvol,
                    "FLOAT (M)": fl,
                    "SHORT %": f"{si}%",
                    "RISIKO": risk_label,
                    "PRIS": f"${s['price']}",
                    "CHANGE": f"{round(s['beta'], 2)}%" # Proxy for change i screener
                })
        return results
    except: return []

# --- 5. INTERFACE ---
st.title("🚀 QUANT-X TERMINAL")

if st.button("🔔 Aktiver Notifikationer"):
    components.html("<script>Notification.requestPermission();</script>", height=0)

data = run_ultimate_power_scanner() if 'run_ultimate_power_scanner' in locals() else run_ultimate_scanner()

if data:
    df = pd.DataFrame(data).sort_values(by="SCORE", ascending=False)
    
    # Tjek for nye topscorere til notifikation
    top_stock = df.iloc[0]
    if top_stock['SCORE'] >= 80:
        trigger_browser_notification(top_stock['SYMBOL'], top_stock['SCORE'])
    
    # Visuel tabel
    st.table(df)
    
