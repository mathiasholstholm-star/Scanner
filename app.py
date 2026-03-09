import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

# --- KONFIGURATION AF TERMINAL ---
st.set_page_config(page_title="Quant-X Master Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X MASTER TERMINAL</h1>", unsafe_allow_html=True)

# ⚠️ DIN API NØGLE ⚠️
API_KEY = "DIN_FMP_API_KEY_HER" 

def is_regular_market_hours():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    if now_est.weekday() >= 5: return False
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now_est <= market_close

def get_detailed_metrics(ticker):
    """Henter Float og Institutionelle data"""
    try:
        m_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?limit=1&apikey={API_KEY}"
        m_resp = requests.get(m_url).json()
        float_val = m_resp[0].get('floatShares', 0) if isinstance(m_resp, list) and len(m_resp) > 0 else 0
        
        i_url = f"https://financialmodelingprep.com/api/v3/institutional-ownership/symbol-ownership-percent/{ticker}?apikey={API_KEY}"
        i_resp = requests.get(i_url).json()
        inst_own = i_resp[0].get('totalWeight', 0) if isinstance(i_resp, list) and len(i_resp) > 0 else 0
        
        return float_val, inst_own
    except:
        return 0, 0

def get_daily_vwap(ticker):
    """Beregner intraday VWAP"""
    url = f"https://financialmodelingprep.com/api/v3/historical-chart/1min/{ticker}?apikey={API_KEY}"
    try:
        resp = requests.get(url).json()
        if not resp or not isinstance(resp, list): return None
        today_str = resp[0]['date'][:10]
        day_data = [c for c in resp if c['date'].startswith(today_str)]
        if not day_data: return None
        total_vol = sum(c['volume'] for c in day_data)
        total_pv = sum(((c['high'] + c['low'] + c['close']) / 3) * c['volume'] for c in day_data)
        return total_pv / total_vol if total_vol > 0 else None
    except: return None

@st.cache_data(ttl=10)
def fetch_terminal_data():
    # NY STRATEGI: Vi bruger 'stock_market/gainers' - det er det hurtigste live-feed i pre-market
    # Dette endpoint ignorerer alle filtre og viser bare dem, der stiger MEST lige nu.
    url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"
    
    try:
        response = requests.get(url).json()
        if not response or not isinstance(response, list): 
            return pd.DataFrame()

        regular_hours = is_regular_market_hours()
        min_vol = 500000 if regular_hours else 50000
        valid_stocks = []

        for q in response:
            ticker = q.get('symbol')
            price = q.get('price', 0)
            change_pct = q.get('changesPercentage', 0)
            vol = q.get('volume', 0)

            # --- DINE STRIKTE FILTRE (AZI ER $0.59 OG >100% GAIN, SÅ DEN SKAL MED HER) ---
            if change_pct >= 15.0 and price <= 30.0 and vol >= min_vol:
                
                # Hent de tunge data kun for kandidaterne
                float_val, inst_val = get_detailed_metrics(ticker)
                vwap_val = get_daily_vwap(ticker)
                vwap_status = "🟢 OVER" if vwap_val and price >= vwap_val else "🔴 UNDER"
                
                # Score-logik
                score = 65
                if 0 < float_val < 20000000: score += 15
                if change_pct > 40: score += 10
                if vwap_status == "🟢 OVER": score += 5
                
                final_score = min(99, score)

                if final_score >= 75:
                    valid_stocks.append({
                        'TICKER': ticker,
                        'PRICE': f"${price:.2f}",
                        'GAIN %': f"+{change_pct:.2f}%",
                        'VWAP': vwap_status,
                        'FLOAT': f"{int(float_val/1000000)}M" if float_val > 0 else "N/A",
                        'INST %': f"{inst_val:.1f}%",
                        'VOLUME': f"{int(vol):,}",
                        'SCORE': final_score
                    })
        
        return pd.DataFrame(valid_stocks)
    except Exception as e:
        st.error(f"Fejl: {e}")
        return pd.DataFrame()

# --- UI VISNING ---
st.subheader("Quant-X Live Momentum (AZI & Gappers)")

if st.button("🔄 Force Refresh"):
    fetch_terminal_data.clear()
    st.rerun()

with st.spinner("Tvinger live-data frem..."):
    df = fetch_terminal_data()

if not df.empty:
    df['n_gain'] = df['GAIN %'].str.replace('+', '').str.replace('%', '').astype(float)
    final_df = df.sort_values('n_gain', ascending=False).drop(columns=['n_gain'])
    st.dataframe(final_df, use_container_width=True, hide_index=True)
else:
    st.warning("Venter på at FMP opdaterer Gainers-listen. AZI burde dukke op hvert øjeblik.")

st.markdown("---")
st.caption(f"Pre-market Mode: AKTIV | Min Vol: 50k")
