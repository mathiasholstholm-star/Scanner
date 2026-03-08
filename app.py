import streamlit as st
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# --- 1. CONFIG & REFRESH ---
st.set_page_config(layout="wide", page_title="QUANT-X MOMENTUM", page_icon="📈")
st_autorefresh(interval=30000, key="live_refresh")

FMP_API_KEY = st.secrets["FMP_API_KEY"]

# --- 2. NOTIFIKATIONER ---
def send_alert(symbol, score, change):
    js = f"""<script>if (Notification.permission === "granted") 
    {{ new Notification("🚀 {symbol} EKSPLODERER", {{ body: "Score: {score}% | Stigning: {change}", icon: "" }}); }}</script>"""
    components.html(js, height=0)

# --- 3. DATA FUNKTIONER ---
def get_stock_details(symbol):
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
        
        risk = "✅ LAV"
        risk_penalty = 0
        if sec_res:
            for f in sec_res:
                if any(k in f['type'] for k in ["S-3", "424B", "F-3"]):
                    risk = "🚨 OFFERING/WARRANT"
                    risk_penalty = -35 # Hård straf for udvanding
                    break
        return fl, si, dtc, risk, risk_penalty
    except: return 0.0, 0.0, 0.0, "N/A", 0

# --- 4. SCANNER (FILTER > 15%) ---
@st.cache_data(ttl=20)
def run_ultimate_scanner():
    url = f"https://financialmodelingprep.com/api/v3/stock_screener?priceLowerThan=30&marketCapLowerThan=760000000&volumeMoreThan=500000&isEtf=false&isActivelyTrading=true&limit=50&apikey={FMP_API_KEY}"
    try:
        stocks = requests.get(url).json()
        results = []
        for s in stocks:
            change_pct = round(s.get('changesPercentage', 0), 2)
            
            # KUN BREAKOUTS OVER 15%
            if change_pct >= 15.0:
                symbol = s['symbol']
                fl, si, dtc, risk_label, penalty = get_stock_details(symbol)
                
                # SCORE LOGIK (0-100)
                score = 40 + penalty
                if change_pct > 30: score += 20
                if fl < 10.0: score += 25  # Stor vægt på Low Float
                if dtc > 2.0: score += 10
                if s.get('volume', 0) > 1500000: score += 5
                
                results.append({
                    "SCORE": min(max(score, 0), 100),
                    "SYMBOL": symbol,
                    "STIGNING": f"{change_pct}%",
                    "DTC": dtc,
                    "FLOAT (M)": fl,
                    "RISIKO": risk_label,
                    "PRIS": f"${round(s['price'], 3)}",
                    "VOLUMEN": f"{round(s['volume']/1e6, 2)}M"
                })
        return sorted(results, key=lambda x: x['SCORE'], reverse=True)
    except: return []

# --- 5. UI ---
st.title("🚀 QUANT-X BREAKOUT MONITOR")
st.write(f"Søger i NYSE, NASDAQ & AMEX | Sidst opdateret: {pd.Timestamp.now().strftime('%H:%M:%S')}")

if st.button("🔔 Tillad Notifikationer"):
    components.html("<script>Notification.requestPermission();</script>", height=0)

data = run_ultimate_scanner()

if data:
    df = pd.DataFrame(data)
    # Send notifikation for den øverste aktie hvis den er ny
    top = df.iloc[0]
    if top['SCORE'] > 75:
        send_alert(top['SYMBOL'], top['SCORE'], top['STIGNING'])
    
    st.table(df)
else:
    st.info("Ingen aktier over 15% stigning lige nu. Venter på næste raket...")
    
