import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

# --- OPSÆTNING AF TERMINAL UI ---
st.set_page_config(page_title="Quant-X Master Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X MASTER TERMINAL</h1>", unsafe_allow_html=True)

# ⚠️ HUSK AT INDSÆTTE DIN RIGTIGE FMP API NØGLE HER ⚠️
API_KEY = "DIN_FMP_API_KEY_HER" 

def is_regular_market_hours():
    """Tjekker om det er normale åbningstider i USA (09:30 - 16:00 EST)"""
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    
    if now_est.weekday() >= 5:
        return False
        
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now_est <= market_close

def get_daily_vwap(ticker):
    """Beregner præcis intraday VWAP ud fra dagens 1-minuts candles"""
    url = f"https://financialmodelingprep.com/api/v3/historical-chart/1min/{ticker}?apikey={API_KEY}"
    try:
        resp = requests.get(url)
        if resp.status_code != 200: return None
        data = resp.json()
        if not data: return None
        
        # Tag datoen for det nyeste candle (i dag)
        today_str = data[0]['date'][:10]
        
        total_vol = 0
        total_pv = 0
        
        for candle in data:
            if candle['date'].startswith(today_str):
                # Typisk pris = (High + Low + Close) / 3
                typ_price = (candle['high'] + candle['low'] + candle['close']) / 3.0
                total_vol += candle['volume']
                total_pv += typ_price * candle['volume']
                
        if total_vol == 0: return None
        return total_pv / total_vol
    except:
        return None

@st.cache_data(ttl=15)
def fetch_terminal_data():
    regular_hours = is_regular_market_hours()
    min_volume = 500000 if regular_hours else 50000
    
    # 1. Hent bruttoliste via screener
    screener_url = f"https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=1000000&volumeMoreThan={min_volume}&priceMoreThan=0.5&priceLowerThan=30&isEtf=false&isFund=false&isActivelyTrading=true&apikey={API_KEY}"
    
    try:
        screen_resp = requests.get(screener_url)
        if screen_resp.status_code != 200: return pd.DataFrame()
            
        screener_data = screen_resp.json()
        if not screener_data: return pd.DataFrame()
            
        tickers = [item['symbol'] for item in screener_data[:100]] 
        if not tickers: return pd.DataFrame()
            
        tickers_str = ",".join(tickers)
        
        # 2. HENT REAL-TIME QUOTES
        quote_url = f"https://financialmodelingprep.com/api/v3/quote/{tickers_str}?apikey={API_KEY}"
        quote_resp = requests.get(quote_url)
        
        if quote_resp.status_code != 200: return pd.DataFrame()
            
        quotes = quote_resp.json()
        valid_stocks = []
        
        for q in quotes:
            price = q.get('price', 0)
            changes_pct = q.get('changesPercentage', 0)
            vol = q.get('volume', 0)
            ticker_sym = q.get('symbol')
            
            # 3. Filtrer for 15% gain og dynamisk volumen
            if changes_pct >= 15.0 and vol >= min_volume and 0.5 <= price <= 30:
                
                # BEREGN VWAP (Kun for aktier der slipper igennem filtret!)
                vwap_val = get_daily_vwap(ticker_sym)
                vwap_status = "Ukendt"
                
                if vwap_val is not None:
                    if price >= vwap_val:
                        vwap_status = "🟢 OVER"
                    else:
                        vwap_status = "🔴 UNDER"
                
                # --- DIN RISK SCORE LOGIK ---
                risk_score = min(99, int(50 + changes_pct + (vol / 100000))) 
                
                if risk_score >= 75:
                    valid_stocks.append({
                        'TICKER': ticker_sym,
                        'PRICE': f"${price:.2f}",
                        'GAIN %': f"+{changes_pct:.2f}%",
                        'VWAP': vwap_status,
                        'VOLUME': f"{int(vol):,}",
                        'SCORE': risk_score,
                        'SESSION': "REGULAR" if regular_hours else "EXTENDED"
                    })
                    
        return pd.DataFrame(valid_stocks)
        
    except Exception as e:
        st.error(f"Netværksfejl eller API-fejl: {e}")
        return pd.DataFrame()

# --- HOVEDPROGRAM ---
st.subheader("Live Momentum Scanner (Score > 75 | Gain > 15%)")

col1, col2 = st.columns([8, 1])
with col2:
    if st.button("🔄 Refresh Data"):
        fetch_terminal_data.clear()
        st.rerun()

with st.spinner("Søger efter tickers med >15% gain og høj score..."):
    df = fetch_terminal_data()

if not df.empty:
    df['sort_gain'] = df['GAIN %'].str.replace('+', '').str.replace('%', '').astype(float)
    df = df.sort_values(by='sort_gain', ascending=False).drop(columns=['sort_gain'])
    
    # Vis datatabel (Streamlit fanger automatisk din nye VWAP kolonne)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Scanneren kører, men ingen aktier opfylder kravene lige nu (Gain > 15%, Score > 75, Min. Volumen).")

st.markdown("---")
st.caption(f"Status: Venter på næste opdatering. Volumen filter er pt. sat til: **{'500.000' if is_regular_market_hours() else '50.000'}**.")
            
