import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- ULTRA-LIGHT SETUP ---
st.set_page_config(page_title="Quant-X Emergency Terminal", layout="wide")
st.markdown("<h1 style='color: #00ff00;'>QUANT-X EMERGENCY MONITOR</h1>", unsafe_allow_html=True)

# ⚠️ INDSÆT DIN API NØGLE HER ⚠️
API_KEY = "DIN_FMP_API_KEY_HER"

@st.cache_data(ttl=2)
def get_emergency_data(tickers):
    results = []
    for t in tickers:
        # Vi bruger kun 'quote' - det mest basale kald der findes
        url = f"https://financialmodelingprep.com/api/v3/quote/{t}?apikey={API_KEY}"
        try:
            r = requests.get(url).json()
            if r and isinstance(r, list):
                q = r[0]
                results.append({
                    'TICKER': q.get('symbol'),
                    'PRICE': f"${q.get('price', 0):.2f}",
                    'GAIN %': f"+{q.get('changesPercentage', 0):.2f}%",
                    'VOLUME': f"{int(q.get('volume', 0)):,}",
                    'RAW_GAIN': q.get('changesPercentage', 0)
                })
        except:
            continue
    return pd.DataFrame(results)

# --- UI ---
# Vi tvinger AZI ind her
watchlist = st.text_input("Overvågning (tickers adskilt af komma):", "AZI, NINE, GME")
ticker_list = [x.strip().upper() for x in watchlist.split(",") if x.strip()]

if st.button("🔄 TVING OPDATERING NU"):
    get_emergency_data.clear()
    st.rerun()

df = get_emergency_data(ticker_list)

if not df.empty:
    # Vi viser alt der er over 0% gain bare for at SE at der er liv
    st.table(df) 
else:
    st.error("INGEN DATA MODTAGET. Tjek om din API-KEY er sat rigtigt ind i koden.")

st.caption(f"Sidste tjek: {datetime.now().strftime('%H:%M:%S')} (Direct Quote Mode)")
