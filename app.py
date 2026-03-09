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
    
    # Er det weekend? (Lørdag=5, Søndag=6)
    if now_est.weekday() >= 5:
        return False
        
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now_est <= market_close

@st.cache_data(ttl=15) # Forhindrer at appen spammer API'et. Opdaterer hver 15. sekund.
def fetch_terminal_data():
    regular_hours = is_regular_market_hours()
    
    # 1. DYNAMISK VOLUMEN FILTER
    # 50.000 i Pre/After-market. 500.000 i normal åbningstid.
    min_volume = 500000 if regular_hours else 50000
    
    # 2. Hent bruttoliste via screener (Filtrerer på pris og volumen)
    screener_url = f"https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=1000000&volumeMoreThan={min_volume}&priceMoreThan=0.5&priceLowerThan=30&isEtf=false&isFund=false&isActivelyTrading=true&apikey={API_KEY}"
    
    try:
        screen_resp = requests.get(screener_url)
        if screen_resp.status_code != 200:
            return pd.DataFrame()
            
        screener_data = screen_resp.json()
        if not screener_data:
            return pd.DataFrame()
            
        # Træk tickers ud for at få real-time quotes (Max 100 ad gangen for hurtighed)
        tickers = [item['symbol'] for item in screener_data[:100]] 
        if not tickers:
            return pd.DataFrame()
            
        tickers_str = ",".join(tickers)
        
        # 3. HENT REAL-TIME QUOTES FOR AT FANGE PRE-MARKET GAINS
        # Screeneren halter i pre-market, 'quote' endpointet er live.
        quote_url = f"https://financialmodelingprep.com/api/v3/quote/{tickers_str}?apikey={API_KEY}"
        quote_resp = requests.get(quote_url)
        
        if quote_resp.status_code != 200:
            return pd.DataFrame()
            
        quotes = quote_resp.json()
        valid_stocks = []
        
        for q in quotes:
            price = q.get('price', 0)
            changes_pct = q.get('changesPercentage', 0)
            vol = q.get('volume', 0)
            
            # Anvend dit 15% gain filter på de live pre-market tal
            if changes_pct >= 15.0 and vol >= min_volume and 0.5 <= price <= 30:
                
                # --- DIN RISK SCORE LOGIK ---
                # Her integrerer du dine specifikke FMP kald for Warrants, Float osv.
                # Lige nu har jeg indsat en dummy-beregning, du skal erstatte med din egen funktion
                risk_score = min(99, int(50 + changes_pct + (vol / 100000))) 
                
                if risk_score >= 75:
                    valid_stocks.append({
                        'TICKER': q.get('symbol'),
                        'PRICE': f"${price:.2f}",
                        'GAIN %': f"+{changes_pct:.2f}%",
                        'VOLUME': f"{int(vol):,}",
                        'SCORE': risk_score,
                        'SESSION': "REGULAR" if regular_hours else "EXTENDED"
                    })
                    
        return pd.DataFrame(valid_stocks)
        
    except Exception as e:
        st.error(f"Netværksfejl eller API-fejl: {e}")
        return pd.DataFrame()

# --- HOVEDPROGRAM (STREAMLIT VISNING) ---
st.subheader("Live Momentum Scanner (Score > 75 | Gain > 15%)")

# Refresh knap i højre side
col1, col2 = st.columns([8, 1])
with col2:
    if st.button("🔄 Refresh Data"):
        fetch_terminal_data.clear() # Rydder cachen ved manuelt klik
        st.rerun()

# Hent og vis data
with st.spinner("Søger efter tickers med >15% gain og høj score..."):
    df = fetch_terminal_data()

if not df.empty:
    # Sortér listen så den med højest gain ligger øverst
    df['sort_gain'] = df['GAIN %'].str.replace('+', '').str.replace('%', '').astype(float)
    df = df.sort_values(by='sort_gain', ascending=False).drop(columns=['sort_gain'])
    
    # Vis den lækre, rene tabel i terminalen
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Scanneren kører, men ingen aktier opfylder kravene lige nu (Gain > 15%, Score > 75, Min. Volumen).")

st.markdown("---")
st.caption(f"Status: Venter på næste opdatering. Volumen filter er pt. sat til: **{'500.000' if is_regular_market_hours() else '50.000'}**.")
