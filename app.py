import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- KONFIGURATION ---
st.set_page_config(page_title="Quant-X Master Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X MASTER TERMINAL</h1>", unsafe_allow_html=True)

# ⚠️ INDSÆT DIN API NØGLE HER ⚠️
API_KEY = "DIN_FMP_API_KEY_HER" 

def is_regular_market_hours():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    if now_est.weekday() >= 5: return False
    return now_est.replace(hour=9, minute=30) <= now_est <= now_est.replace(hour=16, minute=0)

def get_daily_vwap(ticker):
    url = f"https://financialmodelingprep.com/api/v3/historical-chart/1min/{ticker}?apikey={API_KEY}"
    try:
        resp = requests.get(url)
        data = resp.json()
        if not data or not isinstance(data, list): return None
        today_str = data[0]['date'][:10]
        current_day = [c for c in data if c['date'].startswith(today_str)]
        if not current_day: return None
        total_vol = sum(c['volume'] for c in current_day)
        total_pv = sum(((c['high'] + c['low'] + c['close']) / 3) * c['volume'] for c in current_day)
        return total_pv / total_vol if total_vol > 0 else None
    except: return None

@st.cache_data(ttl=10)
def fetch_terminal_data
