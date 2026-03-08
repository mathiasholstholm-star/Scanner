import streamlit as st
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# --- 1. CONFIG & AUTO-REFRESH (30 SEK) ---
st.set_page_config(layout="wide", page_title="QUANT-X ULTIMATE TERMINAL", page_icon="🚀")
st_autorefresh(interval=30000, key="terminal_heartbeat")

FMP_API_KEY = st.secrets["FMP_API_KEY"]
BULL_KEYWORDS = ["FDA", "APPROVAL", "PHASE", "AI", "DRONE", "DEFENSE", "PENTAGON", "CONTRACT", "SQUEEZE", "WARRANT"]

# --- 2. NOTIFIKATIONS ENGINE (Browser Level) ---
def send_chrome_alert(symbol, score, reason):
    js = f"""
    <script>
    if (Notification.permission === "granted") {{
        new Notification("🚀 QUANT-X: {symbol}", {{ 
            body: "SCORE: {score}% | {reason}", 
            icon: "https://cdn-icons-png.flaticon.com/512/2522/2522648.png" 
        }});
    }}
    </script>
    """
    components.html(js, height=0)

# --- 3. DATA & RISIKO LOGIK ---
def get_advanced_metrics(symbol):
    """Henter Float, Short Interest, DTC og SEC filings (Offering Risk)"""
    try:
        # Float & Short Data
        f_url = f"https://financialmodelingprep.com/api/v4/shares_float?symbol={symbol}&apikey={FMP_API_KEY}"
        s_url = f"https://financialmodelingprep.com/api/v4/short-interest?symbol={symbol}&apikey={FMP_API_KEY}"
        sec_url = f"https://financialmodelingprep.com/api/v3/sec_filings/{symbol}?limit=5&apikey={FMP_API_KEY}"
        
        fl_res = requests.get(f_url).json()
        sh_res = requests.get(s_url).json()
        sec_res = requests.get(sec_url).json()
        
        fl = round(fl_res[0]['floatShares'] / 1e6, 2) if fl_res else 0.0
        si = round(sh_res[0]['shortInterestRatio'], 2) if sh_res else 0.0
        dtc = round(sh_res[0]['daysToCover'], 2) if sh_res else 0.0
        
        # Offering/Warrant Check
        risk = "✅ LAV"
        risk_penalty = 0
        if sec_res:
            for f in sec_res:
                if any(k in f['type'] for k in ["S-3", "424B", "F-3"]):
                    risk = "🚨 OFFERING/WARRANT"
                    risk_penalty = -30
                    break
        
        return fl, si, dtc, risk, risk_penalty
    except: return 0.0, 0.0, 0.0, "N/A", 0

# --- 4. CORE SCANNER ENGINE ---
@st.cache_data(ttl=25)
def run_master_scanner():
    # Filtre: Pris < 30, Cap < 760M, Vol > 500k
    url = f"https://financialmodelingprep.com/api/v3/stock_screener?priceLowerThan=30&marketCapLowerThan=760000000&volumeMoreThan=500000&isEtf=false&isActivelyTrading=true&limit=50&apikey={FMP_API_KEY}"
    try:
        stocks = requests.get(url).json()
        final_list = []
        
        for s in stocks:
            symbol = s['symbol']
            # RVOL Beregning (Fredag vs 20 dages snit)
            h_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={FMP_API_KEY}"
            h = requests.get(h_url).json()
            
            if 'historical' in h:
                df = pd.DataFrame(h['historical']).head(21)
                avg_vol = df.iloc[1:21]['volume'].mean()
                rvol = round(s['volume'] / avg_vol, 2)
                vwap = (df.iloc[0]['high'] + df.iloc[0]['low'] + df.iloc[0]['close']) / 3
                
                # Hent Avancerede tal
                fl, si, dtc, risk_label, penalty = get_advanced_metrics(symbol)
                
                # --- SCORE LOGIK ---
                score = 45 + penalty
                if rvol >= 5.0: score += 20
                if fl < 10.0: score += 15
                if si > 15.0: score += 10
                if s['price'] > vwap: score += 10
                
                if rvol >= 1.2 and fl <= 30.0: # Kun Low Float Momentum
                    final_list.append({
                        "SCORE": min(max(score, 0), 100),
                        "SYMBOL": symbol,
                        "DTC": dtc,
                        "RVOL": rvol,
                        "FLOAT (M)": fl,
                        "SHORT %": f"{si}%",
                        "RISIKO": risk_label,
                        "PRIS": f"${round(s['price'], 3)}",
                        "VWAP": "✅" if s['price'] > vwap else "❌"
                    })
        return sorted(final_list, key=lambda x: x['SCORE'], reverse=True)
    except: return []

# --- 5. UI & LIVE MONITOR ---
st.title("🚀 QUANT-X ULTIMATE TERMINAL")
st.markdown(f"**Live Scanning:** Aktiv | **Opdatering:** Hvert 30. sek. | **Tid:** {pd.Timestamp.now().strftime('%H:%M:%S')}")

if st.button("🔔 Aktiver Chrome Alerts"):
    components.html("<script>Notification.requestPermission();</script>", height=0)

data = run_master_scanner()

if data:
    df = pd.DataFrame(data)
    
    # Notifikations-tjek (Hvis topscorer er ny og over 80)
    top = df.iloc[0]
    if top['SCORE'] >= 80:
        send_chrome_alert(top['SYMBOL'], top['SCORE'], f"RVOL: {top['RVOL']}x | DTC: {top['DTC']}")

    # Visuel Tabel
    st.dataframe(df.style.apply(lambda x: ['background-color: #1e4620' if float(str(v).replace('%','')) > 80 else '' for v in x], axis=1), use_container_width=True)
    
    # Pop-up Detaljer (Expander)
    with st.expander("🔍 Hurtigt kig på top-kandidat"):
        st.write(f"### {top['SYMBOL']} Detaljer")
        c1, c2, c3 = st.columns(3)
        c1.metric("Short Squeeze Potentiale", f"DTC: {top['DTC']}")
        c2.metric("Float Eksplosivitet", f"{top['FLOAT (M)']}M")
        c3.metric("Udvandings Risiko", top['RISIKO'])
else:
    st.info("Scanner markedet... Vent på næste 30-sekunders interval.")

st.divider()
st.caption("Quant-X Terminal v3.0 - Built for Low Float Breakouts")
