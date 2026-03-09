import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Quant-X Master Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X MASTER TERMINAL</h1>", unsafe_allow_html=True)

# ⚠️ INDSÆT DIN API NØGLE HER ⚠️
API_KEY = "DIN_FMP_API_KEY_HER"

def get_live_metrics(ticker):
    """Henter realtidsdata og float i ét workflow per ticker"""
    try:
        # 1. Hent pris og gain (Quote endpoint er mest stabilt på Free Tier)
        q_url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={API_KEY}"
        q_res = requests.get(q_url).json()
        if not q_res or not isinstance(q_res, list): return None
        q = q_res[0]
        
        # 2. Hent Float (Key Metrics)
        f_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?limit=1&apikey={API_KEY}"
        f_res = requests.get(f_url).json()
        f_shares = f_res[0].get('floatShares', 0) if f_res and isinstance(f_res, list) else 0
        
        # 3. Hent VWAP (Historical 1-min)
        v_url = f"https://financialmodelingprep.com/api/v3/historical-chart/1min/{ticker}?apikey={API_KEY}"
        v_res = requests.get(v_url).json()
        vwap_status = "N/A"
        if v_res and isinstance(v_res, list):
            day_data = v_res[:30] # Tjek de sidste 30 minutter
            v = sum(c['volume'] for c in day_data)
            pv = sum(((c['high'] + c['low'] + c['close']) / 3) * c['volume'] for c in day_data)
            vwap_val = pv / v if v > 0 else 0
            vwap_status = "🟢 OVER" if q.get('price', 0) >= vwap_val else "🔴 UNDER"

        return {
            'TICKER': ticker,
            'PRICE': q.get('price', 0),
            'GAIN %': q.get('changesPercentage', 0),
            'VOLUME': q.get('volume', 0),
            'FLOAT': f_shares,
            'VWAP': vwap_status
        }
    except:
        return None

@st.cache_data(ttl=5)
def run_scanner(manual_list):
    # Core overvågning (AZI er førsteprioritet)
    core_tickers = ["AZI", "NINE", "GME", "KOSS"]
    for t in manual_list:
        if t and t.upper() not in core_tickers:
            core_tickers.append(t.upper())
            
    valid_stocks = []
    for ticker in core_tickers:
        data = get_live_metrics(ticker)
        if data:
            # DINE FILTRE: Pris < 30 og Gain > 15%
            if data['PRICE'] <= 30 and data['GAIN %'] >= 15.0:
                
                # --- RISK SCORE MOTOR ---
                score = 65
                if 0 < data['FLOAT'] < 15000000: score += 15 # Low Float bonus
                if data['GAIN %'] > 40: score += 10
                if data['VWAP'] == "🟢 OVER": score += 5
                
                valid_stocks.append({
                    'TICKER': data['TICKER'],
                    'PRICE': f"${data['PRICE']:.2f}",
                    'GAIN %': f"+{data['GAIN %']:.2f}%",
                    'VWAP': data['VWAP'],
                    'FLOAT': f"{int(data['FLOAT']/1000000)}M" if data['FLOAT'] > 0 else "N/A",
                    'VOLUME': f"{int(data['VOLUME']):,}",
                    'SCORE': min(99, score)
                })
    return pd.DataFrame(valid_stocks)

# --- BRUGERFLADE ---
st.subheader("Live Momentum Terminal (AZI & Gappers)")

# Input felt til at tvinge nye tickers ind
user_input = st.text_input("Tving scanner til specifikke tickers (separeret med komma):", "AZI")
manual_list = [x.strip() for x in user_input.split(",") if x.strip()]

if st.button("🔄 FORCE REFRESH"):
    run_scanner.clear()
    st.rerun()

with st.spinner("Henter live markedsdata..."):
    df = run_scanner(manual_list)

if not df.empty:
    # Viser tabellen sorteret efter SCORE
    st.dataframe(df.sort_values('SCORE', ascending=False), use_container_width=True, hide_index=True)
else:
    st.warning("Scanner... Hvis AZI ikke er her, tjek om den er over 15% gain på din telefon.")

st.markdown("---")
st.caption(f"Status: Live | Engine: Standard Requests | Tid: {datetime.now().strftime('%H:%M:%S')}")
                 
