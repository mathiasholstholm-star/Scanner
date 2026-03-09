import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- TERMINAL SETUP ---
st.set_page_config(page_title="Quant-X Master Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X MASTER TERMINAL</h1>", unsafe_allow_html=True)

# ⚠️ DIN API NØGLE ⚠️
API_KEY = "DIN_FMP_API_KEY_HER" 

def get_daily_vwap(ticker):
    """Beregner intraday VWAP - Afgørende for din Risk Score"""
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

def get_float_data(ticker):
    """Henter Float shares (Vigtigt for din momentum-strategi)"""
    url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?limit=1&apikey={API_KEY}"
    try:
        data = requests.get(url).json()
        if isinstance(data, list) and len(data) > 0:
            return data[0].get('floatShares', 0)
        return 0
    except: return 0

@st.cache_data(ttl=10)
def fetch_terminal_data():
    # DIN INSTRUKS: Vi henter ALLE aktive aktier under $30. 
    # Vi fjerner ALLE andre filtre i URL'en for at sikre at AZI kommer med.
    url = f"https://financialmodelingprep.com/api/v3/stock-screener?priceLowerThan=30&isActivelyTrading=true&limit=1000&apikey={API_KEY}"
    
    try:
        response = requests.get(url).json()
        if not response or not isinstance(response, list):
            return pd.DataFrame()

        # Tjekker om vi er i pre-market for volumen-grænsen
        est = pytz.timezone('US/Eastern')
        now_est = datetime.now(est)
        is_reg = now_est.weekday() < 5 and now_est.replace(hour=9, minute=30) <= now_est <= now_est.replace(hour=16, minute=0)
        min_vol = 500000 if is_reg else 50000

        valid_stocks = []

        # Vi kører igennem de 1000 aktier og finder dine gappers manuelt
        for stock in response:
            ticker = stock.get('symbol')
            price = stock.get('price', 0)
            vol = stock.get('volume', 0)
            
            # Vi bruger quote for at få REAL-TIME gain, da screeneren er forsinket
            # Dette er tricket der henter AZI frem nu!
            if vol >= min_vol and price <= 30:
                q_url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={API_KEY}"
                q_data = requests.get(q_url).json()
                if not q_data: continue
                
                change_pct = q_data[0].get('changesPercentage', 0)
                
                # DIN GRÆNSE: Gain > 15%
                if change_pct >= 15.0:
                    vwap_val = get_daily_vwap(ticker)
                    vwap_status = "🟢 OVER" if vwap_val and price >= vwap_val else "🔴 UNDER"
                    float_shares = get_float_data(ticker)
                    
                    # DIN RISK SCORE LOGIK (Følg dine instrukser)
                    score = 65
                    if 0 < float_shares < 15000000: score += 15 # Low float bonus
                    if change_pct > 30: score += 10
                    if vwap_status == "🟢 OVER": score += 5
                    
                    final_score = min(99, score)

                    if final_score >= 75:
                        valid_stocks.append({
                            'TICKER': ticker,
                            'PRICE': f"${price:.2f}",
                            'GAIN %': f"+{change_pct:.2f}%",
                            'VWAP': vwap_status,
                            'FLOAT': f"{int(float_shares/1000000)}M" if float_shares > 0 else "N/A",
                            'VOLUME': f"{int(vol):,}",
                            'SCORE': final_score
                        })
        
        return pd.DataFrame(valid_stocks)
    except Exception as e:
        st.error(f"Fejl: {e}")
        return pd.DataFrame()

# --- UI ---
st.subheader("Live Momentum Scanner (Realtid Check)")

if st.button("🔄 FORCE REFRESH"):
    fetch_terminal_data.clear()
    st.rerun()

with st.spinner("Scanner 1.000+ aktier for dine parametre..."):
    df = fetch_terminal_data()

if not df.empty:
    # Sorter efter højeste gain
    df['n_gain'] = df['GAIN %'].str.replace('+', '').str.replace('%', '').astype(float)
    st.dataframe(df.sort_values('n_gain', ascending=False).drop(columns=['n_gain']), use_container_width=True, hide_index=True)
else:
    st.info("Ingen aktier fundet over 15% gain med din volumen-grænse. Prøv 'Force Refresh'.")

st.markdown("---")
st.caption(f"Status: Aktiv | Filter: {'>50k' if datetime.now().hour < 15 else '>500k'} vol")
