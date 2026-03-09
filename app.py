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

def get_stock_data(ticker):
    """Henter realtidsdata for en specifik ticker (AZI-sikring)"""
    try:
        # Quote giver os prisen NU (selvom screeneren er forsinket)
        url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={API_KEY}"
        res = requests.get(url).json()
        if not res or not isinstance(res, list): return None
        
        q = res[0]
        # Hent Float for scoren
        f_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?limit=1&apikey={API_KEY}"
        f_res = requests.get(f_url).json()
        float_shares = f_res[0].get('floatShares', 0) if isinstance(f_res, list) and len(f_res) > 0 else 0
        
        return {
            'TICKER': ticker,
            'PRICE': q.get('price', 0),
            'GAIN %': q.get('changesPercentage', 0),
            'VOLUME': q.get('volume', 0),
            'FLOAT': float_shares
        }
    except: return None

@st.cache_data(ttl=5)
def fetch_terminal_data():
    # 1. Start med de tickers vi VED rører på sig (AZI-sikring)
    hot_list = ["AZI", "NINE", "GME", "KOSS"]
    
    # 2. Hent også de generelle gainers som backup
    try:
        url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"
        gainers_res = requests.get(url).json()
        if isinstance(gainers_res, list):
            for g in gainers_res[:10]: # Tag top 10
                if g['symbol'] not in hot_list:
                    hot_list.append(g['symbol'])
    except: pass

    valid_stocks = []
    for ticker in hot_list:
        data = get_stock_data(ticker)
        if not data: continue
        
        # DINE FILTRE: Gain > 15% og Pris < $30
        if data['GAIN %'] >= 15.0 and data['PRICE'] <= 30.0:
            
            # RISK SCORE LOGIK (Din motor)
            score = 70
            if 0 < data['FLOAT'] < 20000000: score += 15 # Low float bonus
            if data['GAIN %'] > 40: score += 10
            
            final_score = min(99, score)
            
            if final_score >= 75:
                valid_stocks.append({
                    'TICKER': data['TICKER'],
                    'PRICE': f"${data['PRICE']:.2f}",
                    'GAIN %': f"+{data['GAIN %']:.2f}%",
                    'FLOAT': f"{int(data['FLOAT']/1000000)}M" if data['FLOAT'] > 0 else "N/A",
                    'VOLUME': f"{int(data['VOLUME']):,}",
                    'SCORE': final_score
                })
    
    return pd.DataFrame(valid_stocks)

# --- UI VISNING ---
st.subheader("Live Momentum Scanner (AZI Force-Mode)")

if st.button("🔄 TVING REFRESH"):
    fetch_terminal_data.clear()
    st.rerun()

with st.spinner("Henter data direkte fra markeds-feedet..."):
    df = fetch_terminal_data()

if not df.empty:
    st.dataframe(df.sort_values('SCORE', ascending=False), use_container_width=True, hide_index=True)
else:
    st.info("Scanner... Hvis AZI ikke er her, så tjek om din API-nøgle er korrekt indsat.")

st.markdown("---")
st.caption(f"Status: Aktiv | Tid: {datetime.now().strftime('%H:%M:%S')} | Kilde: FMP Direct")
