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
    """Henter Float og Institutionelle data med fejlsikring"""
    try:
        # 1. Float data
        m_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?limit=1&apikey={API_KEY}"
        m_resp = requests.get(m_url).json()
        # Tjekker om m_resp er en liste og har indhold (fikser din 'string indices' fejl)
        float_val = m_resp[0].get('floatShares', 0) if isinstance(m_resp, list) and len(m_resp) > 0 else 0
        
        # 2. Institutional Ownership
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
    # 1. Hent rådata (Fjernet Market Cap filter for at få AZI med)
    url = f"https://financialmodelingprep.com/api/v3/stock-screener?priceLowerThan=30&isActivelyTrading=true&limit=150&apikey={API_KEY}"
    
    try:
        response = requests.get(url).json()
        if not response or not isinstance(response, list): return pd.DataFrame()

        regular_hours = is_regular_market_hours()
        # Dine volumenkrav: 50k pre / 500k regular
        min_vol = 500000 if
        
