import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- KONFIGURATION ---
st.set_page_config(page_title="Quant-X Master Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X MASTER TERMINAL</h1>", unsafe_allow_html=True)

# INDSÆT DIN NØGLE HER
API_KEY = "DIN_FMP_API_KEY_HER" 

def is_regular_market_hours():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    if now_est.weekday() >= 5: return False
    return now_est.replace(hour=9, minute=30) <= now_est <= now_est.replace(hour=16, minute=0)

def get_daily_vwap(ticker):
    """Beregner VWAP ud fra dagens 1-minuts data"""
    url = f"https://financialmodelingprep.com/api/v3/historical-chart/1min/{ticker}?apikey={API_KEY}"
    try:
        data = requests.get(url).json()
        if not data: return None
        today_str = data[0]['date'][:10]
        # Beregn kun for i dag
        current_day_data = [c for c in data if c['date'].startswith(today_str)]
        total_vol = sum(c['volume'] for c in current_day_data)
        total_pv = sum(((c['high'] + c['low'] + c['close']) / 3) * c['volume'] for c in current_day_data)
        return total_pv / total_vol if total_vol > 0 else None
    except: return None

@st.cache_data(ttl=10)
def fetch_terminal_data():
    # Vi bruger 'quote' endpointet for at få AZI og alle andre uden Market Cap begrænsning
    # Vi henter top gainers listen først for at finde kandidaterne
    url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        if not data: return pd.DataFrame()

        regular_hours = is_regular_market_hours()
        # Pre-market volumen = 50.000, Normal marked = 500.000
        min_vol = 500000 if regular_hours else 50000
        valid_stocks = []

        for stock in data:
            ticker = stock.get('symbol')
            price = stock.get('price', 0)
            change_pct = stock.get('changesPercentage', 0)
            vol = stock.get('volume', 0)

            # --- DINE PARAMETRE (PUNKT FOR PUNKT) ---
            # 1. Gain >= 15%
            # 2. Pris <= $30
            # 3. Volumen tjek (Pre-market tilpasset)
            if change_pct >= 15.0 and price <= 30.0 and
            
