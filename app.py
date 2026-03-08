import streamlit as st
import pandas as pd
import requests
import time
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Squeeze Scanner", page_icon="🔥", layout="centered")

# Auto-refresh hvert 30. sekund
st_autorefresh(interval=30 * 1000, key="datarefresh")

st.title("🔥 Short Squeeze Radar")
st.caption(f"Scanner efter RVOL > 5x og +15% stigning | Opdateret kl. {time.strftime('%H:%M:%S')}")

API_KEY = "DKC7vblNaiBbTzht7ASgqgnmlvzl5ym"

def fetch_squeeze_data():
    # 1. Hent potentielle runners via screener
    url = (f"https://financialmodelingprep.com/api/v3/stock-screener?"
           f"marketCapLowerThan=760000000&priceMoreThan=0.5&"
           f"isEtf=false&exchange=NYSE,NASDAQ,AMEX&apikey={API_KEY}")
    
    try:
        r = requests.get(url)
        df = pd.DataFrame(r.json())
        if df.empty: return pd.DataFrame()

        # Filtrer først på prisstigning for at spare kræfter
        df = df[df['changesPercentage'] >= 15]
        
        final_list = []
        for _, row in df.iterrows():
            symbol = row['symbol']
            
            # 2. Hent Short Interest og gennemsnitsvolumen (RVOL)
            # Vi bruger quote-endpunktet for at få præcis gennemsnitsvolumen
            q_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={API_KEY}"
            v_data = requests.get(q_url).json()[0]
            
            avg_vol = v_data.get('avgVolume', 1)
            current_vol = v_data.get('volume', 0)
            rvol = current_vol / avg_vol if avg_vol > 0 else 0
            
            # 3. Hent Short Float data
            s_url = f"https://financialmodelingprep.com/api/v4/short-interest?symbol={symbol}&apikey={API_KEY}"
            s_data = requests.get(s_url).json()
            
            short_float = s_data[0].get('shortFloat', 0) if s_data else 0
            days_to_cover = s_data[0].get('daysToCover', 0) if s_data else 0
            
            # FILTER: RVOL skal være over 5
            if rvol >= 5:
                final_list.append({
                    'Symbol': symbol,
                    'Pris': row['price'],
                    'Stigning %': row['changesPercentage'],
                    'RVOL': round(rvol, 2),
                    'Short Float %': round(short_float, 2),
                    'Days to Cover': round(days_to_cover, 2),
                    'Volumen': current_vol
                })
        
        return pd.DataFrame(final_list)
    except:
        return pd.DataFrame()

results = fetch_squeeze_data()

if not results.empty:
    st.success(f"Fundet {len(results)} potentielle Squeezes!")
    for _, row in results.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.subheader(row['Symbol'])
                st.write(f"Pris: ${row['Pris']}")
            with col2:
                st.write(f"**Stigning:** {row['Stigning %']:.1f}%")
                st.write(f"**RVOL:** {row['RVOL']}x")
            with col3:
                st.write(f"**Short:** {row['Short Float %']}%")
                st.write(f"**DTC:** {row['Days to Cover']}")
            
            # Visuel indikator for ekstremt squeeze potentiale
            if row['Short Float %'] > 20:
                st.warning("⚠️ EKSTREMT HØJ SHORT FLOAT")
                
            st.markdown(f"[Nyheder](https://www.google.com/search?q={row['Symbol']}+stock+news&tbm=nws)")
            st.divider()
else:
    st.info("Søger... Ingen aktier med RVOL > 5 og +15% stigning lige nu.")
    
