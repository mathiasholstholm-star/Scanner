import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- KONFIGURATION ---
st.set_page_config(page_title="Quant-X Master Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X MASTER TERMINAL</h1>", unsafe_allow_html=True)

# ⚠️ HUSK DIN API NØGLE ⚠️
API_KEY = "DIN_FMP_API_KEY_HER" 

def is_regular_market_hours():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    if now_est.weekday() >= 5: return False
    return now_est.replace(hour=9, minute=30) <= now_est <= now_est.replace(hour=16, minute=0)

def get_detailed_metrics(ticker):
    """Henter Float og Institutionelle data"""
    try:
        m_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?limit=1&apikey={API_KEY}"
        m_data = requests.get(m_url).json()
        f_val = m_data[0].get('floatShares', 0) if isinstance(m_data, list) and len(m_data) > 0 else 0
        
        i_url = f"https://financialmodelingprep.com/api/v3/institutional-ownership/symbol-ownership-percent/{ticker}?apikey={API_KEY}"
        i_data = requests.get(i_url).json()
        i_val = i_data[0].get('totalWeight', 0) if isinstance(i_data, list) and len(i_data) > 0 else 0
        return f_val, i_val
    except: return 0, 0

def get_daily_vwap(ticker):
    """Beregner intraday VWAP fra 1-min data"""
    url = f"https://financialmodelingprep.com/api/v3/historical-chart/1min/{ticker}?apikey={API_KEY}"
    try:
        data = requests.get(url).json()
        if not data or not isinstance(data, list): return None
        t_str = data[0]['date'][:10]
        day_c = [c for c in data if c['date'].startswith(t_str)]
        if not day_c: return None
        v = sum(c['volume'] for c in day_c)
        pv = sum(((c['high']+c['low']+c['close'])/3) * c['volume'] for c in day_c)
        return pv / v if v > 0 else None
    except: return None

@st.cache_data(ttl=5)
def fetch_terminal_data():
    # METODE: Vi henter samtlige NASDAQ symboler og tjekker dem én efter én
    # Dette er den ENESTE måde at sikre at AZI ikke bliver overset af et langsomt filter
    try:
        # Vi henter de mest aktive NASDAQ aktier
        url = f"https://financialmodelingprep.com/api/v3/symbol/NASDAQ?apikey={API_KEY}"
        resp = requests.get(url).json()
        if not resp: return pd.DataFrame()
        
        # Vi tager de 150 mest aktive og henter deres LIVE quotes
        syms = [s['symbol'] for s in resp[:150]]
        q_url = f"https://financialmodelingprep.com/api/v3/quote/{','.join(syms)}?apikey={API_KEY}"
        quotes = requests.get(q_url).json()
        
        reg_h = is_regular_market_hours()
        m_vol = 500000 if reg_h else 50000
        valid = []

        for q in quotes:
            t = q.get('symbol')
            p = q.get('price', 0)
            ch = q.get('changesPercentage', 0)
            v = q.get('volume', 0)

            # DINE STRIKTE KRITERIER (AZI ER $0.59 OG >100% GAIN)
            if ch >= 15.0 and p <= 30.0 and v >= m_vol:
                f_v, i_v = get_detailed_metrics(t)
                vw_v = get_daily_vwap(t)
                vw_s = "🟢 OVER" if vw_v and p >= vw_v else "🔴 UNDER"
                
                # DIN SCORE LOGIK (Float + Momentum + VWAP)
                sc = 65
                if 0 < f_v < 15000000: sc += 15 # Bonus for low float
                if ch > 30: sc += 10
                if vw_s == "🟢 OVER": sc += 5
                
                if sc >= 75:
                    valid.append({
                        'TICKER': t,
                        'PRICE': f"${p:.2f}",
                        'GAIN %': f"+{ch:.2f}%",
                        'VWAP': vw_s,
                        'FLOAT': f"{int(f_v/1000000)}M" if f_v > 0 else "N/A",
                        'INST %': f"{i_v:.1f}%",
                        'VOLUME': f"{int(v):,}",
                        'SCORE': sc
                    })
        return pd.DataFrame(valid)
    except Exception as e:
        st.error(f"Fejl: {e}")
        return pd.DataFrame()

# --- UI ---
st.subheader("Quant-X Master Momentum Scanner")

if st.button("🔄 FORCE REFRESH"):
    fetch_terminal_data.clear()
    st.rerun()

with st.spinner("Tvinger live-data frem fra NASDAQ..."):
    df = fetch_terminal_data()

if not df.empty:
    df['n'] = df['GAIN %'].str.replace('+', '').str.replace('%', '').astype(float)
    st.dataframe(df.sort_values('n', ascending=False).drop(columns=['n']), use_container_width=True, hide_index=True)
else:
    st.info("Scanner... Hvis AZI ikke er her nu, så tjek din API-nøgle for 'Starter' adgang.")

st.markdown("---")
st.caption(f"Status: Aktiv | Tid: {datetime.now().strftime('%H:%M:%S')} | Pre-market Filter: 50k")
        
