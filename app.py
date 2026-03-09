import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- KONFIGURATION AF TERMINAL ---
st.set_page_config(page_title="Quant-X Master Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00; margin-bottom: 0;'>QUANT-X MASTER TERMINAL</h1>", unsafe_allow_html=True)

# ⚠️ INDSÆT DIN API NØGLE HER ⚠️
API_KEY = "DIN_FMP_API_KEY_HER" 

def is_regular_market_hours():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    if now_est.weekday() >= 5: return False
    return now_est.replace(hour=9, minute=30, second=0) <= now_est <= now_est.replace(hour=16, minute=0, second=0)

def get_detailed_metrics(ticker):
    """Henter Float og Institutionelle data med fejlsikring"""
    try:
        m_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?limit=1&apikey={API_KEY}"
        m_data = requests.get(m_url).json()
        f_val = m_data[0].get('floatShares', 0) if isinstance(m_data, list) and len(m_data) > 0 else 0
        
        i_url = f"https://financialmodelingprep.com/api/v3/institutional-ownership/symbol-ownership-percent/{ticker}?apikey={API_KEY}"
        i_data = requests.get(i_url).json()
        i_val = i_data[0].get('totalWeight', 0) if isinstance(i_data, list) and len(i_data) > 0 else 0
        return f_val, i_val
    except:
        return 0, 0

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
    except:
        return None

@st.cache_data(ttl=10)
def fetch_terminal_data():
    # NY STRATEGI: Vi henter alle aktive symboler og finder dem med høj volumen manuelt
    # Dette omgår fejlen 'slice(None, 150, None)'
    try:
        # Vi bruger quote-tradeable endpointet som er mere stabilt
        url = f"https://financialmodelingprep.com/api/v3/stock_market/actives?apikey={API_KEY}"
        resp = requests.get(url).json()
        
        if not isinstance(resp, list):
            # Fallback til top-gainers hvis actives fejler
            url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"
            resp = requests.get(url).json()

        if not resp or not isinstance(resp, list):
            return pd.DataFrame()
            
        reg_h = is_regular_market_hours()
        m_vol = 500000 if reg_h else 50000
        valid = []

        for q in resp:
            t = q.get('symbol')
            p = q.get('price', 0)
            ch = q.get('changesPercentage', 0)
            v = q.get('volume', 0)

            # DINE FILTRE: Gain > 15%, Pris < 30, Volumen tjek
            if ch >= 15.0 and p <= 30.0 and v >= m_vol:
                f_v, i_v = get_detailed_metrics(t)
                vw_v = get_daily_vwap(t)
                vw_s = "🟢 OVER" if vw_v and p >= vw_v else "🔴 UNDER"
                
                # DIN SCORE LOGIK
                sc = 65
                if 0 < f_v < 15000000: sc += 15 
                if ch > 30: sc += 10
                if vw_s == "🟢 OVER": sc += 5
                
                final_score = min(99, sc)

                if final_score >= 75:
                    valid.append({
                        'TICKER': t,
                        'PRICE': f"${p:.2f}",
                        'GAIN %': f"+{ch:.2f}%",
                        'VWAP': vw_s,
                        'FLOAT': f"{int(f_v/1000000)}M" if f_v > 0 else "N/A",
                        'INST %': f"{i_v:.1f}%",
                        'VOLUME': f"{int(v):,}",
                        'SCORE': final_score
                    })
        return pd.DataFrame(valid)
    except Exception as e:
        st.error(f"Fejl i datahentning: {e}")
        return pd.DataFrame()

# --- UI VISNING ---
st.subheader("Live Momentum Terminal")

if st.button("🔄 Manuel Opdatering"):
    fetch_terminal_data.clear()
    st.rerun()

with st.spinner("Tjekker markedet for gappers..."):
    df = fetch_terminal_data()

if not df.empty:
    df['n'] = df['GAIN %'].str.replace('+', '').str.replace('%', '').astype(float)
    st.dataframe(df.sort_values('n', ascending=False).drop(columns=['n']), use_container_width=True, hide_index=True)
else:
    st.info("Ingen aktier fundet i øjeblikket med dine kriterier (15% Gain / 50k Vol).")

st.markdown("---")
st.caption(f"Scanner Status: OK | Sidste tjek: {datetime.now().strftime('%H:%M:%S')}")
