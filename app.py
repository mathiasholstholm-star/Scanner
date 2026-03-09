import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- TERMINAL SETUP ---
st.set_page_config(page_title="Quant-X Master Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X MASTER TERMINAL</h1>", unsafe_allow_html=True)

# ⚠️ INDSÆT DIN API NØGLE HER ⚠️
API_KEY = "DIN_FMP_API_KEY_HER" 

def get_vwap(ticker):
    """Beregner live VWAP via 1-minuts historik"""
    url = f"https://financialmodelingprep.com/api/v3/historical-chart/1min/{ticker}?apikey={API_KEY}"
    try:
        resp = requests.get(url).json()
        if not resp or not isinstance(resp, list): return None
        today = resp[0]['date'][:10]
        d = [c for c in resp if c['date'].startswith(today)]
        if not d: return None
        v = sum(c['volume'] for c in d)
        pv = sum(((c['high']+c['low']+c['close'])/3) * c['volume'] for c in d)
        return pv / v if v > 0 else None
    except: return None

def get_metrics(ticker):
    """Henter Float og Real-time prisdata direkte"""
    try:
        # Quote for pris og gain
        q_url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={API_KEY}"
        q_res = requests.get(q_url).json()
        if not q_res: return None
        q = q_res[0]

        # Metrics for Float
        m_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?limit=1&apikey={API_KEY}"
        m_res = requests.get(m_url).json()
        f_shares = m_res[0].get('floatShares', 0) if isinstance(m_res, list) and len(m_res) > 0 else 0
        
        return {
            'TICKER': ticker,
            'PRICE': q.get('price', 0),
            'GAIN %': q.get('changesPercentage', 0),
            'VOLUME': q.get('volume', 0),
            'FLOAT': f_shares
        }
    except: return None

@st.cache_data(ttl=5)
def fetch_terminal_data(manual_tickers):
    # Vi kombinerer dine manuelle tickers med de mest aktive (hvis API'et tillader det)
    base_list = ["AZI", "NINE", "GME", "KOSS"] # Dine primære targets
    for t in manual_tickers:
        if t and t not in base_list:
            base_list.append(t.upper())

    valid_stocks = []
    for ticker in base_list:
        data = get_metrics(ticker)
        if not data: continue
        
        # DINE FILTRE: Gain > 15% og Pris < $30
        if data['GAIN %'] >= 15.0 and data['PRICE'] <= 30.0:
            vwap_val = get_vwap(ticker)
            vwap_status = "🟢 OVER" if vwap_val and data['PRICE'] >= vwap_val else "🔴 UNDER"
            
            # RISK SCORE LOGIK (Din motor)
            score = 65
            if 0 < data['FLOAT'] < 15000000: score += 15 # Low float bonus
            if data['GAIN %'] > 40: score += 10
            if vwap_status == "🟢 OVER": score += 5
            
            final_score = min(99, score)
            
            if final_score >= 70: # Sænket en smule så vi er sikre på at se data
                valid_stocks.append({
                    'TICKER': data['TICKER'],
                    'PRICE': f"${data['PRICE']:.2f}",
                    'GAIN %': f"+{data['GAIN %']:.2f}%",
                    'VWAP': vwap_status,
                    'FLOAT': f"{int(data['FLOAT']/1000000)}M" if data['FLOAT'] > 0 else "N/A",
                    'VOLUME': f"{int(data['VOLUME']):,}",
                    'SCORE': final_score
                })
    return pd.DataFrame(valid_stocks)

# --- UI ---
st.subheader("Live Real-Time Monitor")

# Manuelt input så du kan tvinge AZI eller andre tickers ind
user_input = st.text_input("Tilføj tickers manuelt (adskilt af komma):", "AZI")
manual_list = [x.strip() for x in user_input.split(",")]

if st.button("🔄 TVING OPDATERING"):
    fetch_terminal_data.clear()
    st.rerun()

with st.spinner("Henter live data for overvågede aktier..."):
    df = fetch_terminal_data(manual_list)

if not df.empty:
    st.dataframe(df.sort_values('SCORE', ascending=False), use_container_width=True, hide_index=True)
else:
    st.info("Ingen aktier matcher kriterierne lige nu. Tjek om AZI er over 15% gain.")

st.markdown("---")
st.caption(f"Scanner Status: Aktiv | Tid: {datetime.now().strftime('%H:%M:%S')}")
