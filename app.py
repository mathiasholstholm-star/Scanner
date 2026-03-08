import streamlit as st
import pandas as pd
import requests

# --- 1. SETUP & MODAL STYLING ---
st.set_page_config(layout="wide", page_title="QUANT-X PRO TERMINAL")
FMP_API_KEY = st.secrets["FMP_API_KEY"]

# Eksplosive nøgleord
BULL_KEYWORDS = ["FDA", "APPROVAL", "AI", "DRONE", "DEFENSE", "PENTAGON", "CONTRACT", "SQUEEZE", "LITHIUM"]

# --- 2. DATA FUNKTIONER ---

def get_all_stock_data(symbol):
    """Henter alt: Float, Short, DTC og Nyheder"""
    try:
        # Float & Short Data
        f_url = f"https://financialmodelingprep.com/api/v4/shares_float?symbol={symbol}&apikey={FMP_API_KEY}"
        s_url = f"https://financialmodelingprep.com/api/v4/short-interest?symbol={symbol}&apikey={FMP_API_KEY}"
        
        fl_shares = requests.get(f_url).json()
        sh_data = requests.get(s_url).json()
        
        # Nyheder
        n_url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={symbol}&limit=1&apikey={FMP_API_KEY}"
        news = requests.get(n_url).json()
        
        float_val = round(fl_shares[0]['floatShares'] / 1e6, 2) if fl_shares else 0.0
        si_pct = round(sh_data[0]['shortInterestRatio'], 2) if sh_data else 0.0
        dtc = round(sh_data[0]['daysToCover'], 2) if sh_data else 0.0
        headline = news[0]['title'] if news else "Ingen friske nyheder"
        
        return float_val, si_pct, dtc, headline
    except: return 0.0, 0.0, 0.0, "Data fejl"

# --- 3. CORE SCANNER ---

@st.cache_data(ttl=300)
def run_scanner():
    # Filtre: Pris < 30, Vol > 500k, Mkt Cap < 760M
    url = f"https://financialmodelingprep.com/api/v3/stock_screener?priceLowerThan=30&marketCapLowerThan=760000000&volumeMoreThan=500000&isEtf=false&isActivelyTrading=true&limit=30&apikey={FMP_API_KEY}"
    stocks = requests.get(url).json()
    return stocks

# --- 4. TERMINAL INTERFACE ---
st.title("🚀 QUANT-X PRO TERMINAL")

stocks = run_scanner()

if stocks:
    # Vi bygger oversigten række for række for at muliggøre pop-ups
    for s in stocks:
        symbol = s['symbol']
        
        # Hurtige beregninger for oversigten
        hist_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={FMP_API_KEY}"
        h = requests.get(hist_url).json()
        
        if 'historical' in h:
            df = pd.DataFrame(h['historical']).head(21)
            rvol = round(df.iloc[0]['volume'] / df.iloc[1:21]['volume'].mean(), 2)
            
            # Lav en pæn række med kolonner
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 3, 1])
            
            with col1:
                st.write(f"**{symbol}**")
            with col2:
                st.write(f"RVOL: {rvol}")
            with col3:
                st.write(f"Pris: ${s['price']}")
            with col4:
                # Nyheds-indikator (Avis-ikon)
                st.write("🗞️ Nyhed klar" if rvol > 1.5 else "⚪ Ingen støj")
            with col5:
                # POP-UP KNAP
                if st.button("Se Data", key=symbol):
                    # Alt data hentes kun når man trykker på knappen (sparer API-kald)
                    fl, si, dtc, news = get_all_stock_data(symbol)
                    
                    st.info(f"### 📊 Detaljer for {symbol}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Free Float", f"{fl}M")
                    c2.metric("Short Interest", f"{si}%")
                    c3.metric("Days to Cover", dtc)
                    
                    st.warning(f"**Seneste Overskrift:**\n{news}")
                    st.write("---")

else:
    st.error("Ingen aktier fundet.")
    
