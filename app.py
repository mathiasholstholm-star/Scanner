import streamlit as st
import pandas as pd
import requests
import time
import base64
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Squeeze Terminal Pro", page_icon="⚡", layout="centered")

# Auto-refresh hvert 30. sekund
st_autorefresh(interval=30 * 1000, key="datarefresh")

# Funktion til at afspille lyd
def play_sound():
    sound_url = "https://www.soundjay.com/buttons/sounds/button-3.mp3"
    sound_html = f"""
        <audio autoplay>
            <source src="{sound_url}" type="audio/mp3">
        </audio>
    """
    st.markdown(sound_html, unsafe_allow_html=True)

# Skjul Streamlit menu
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)

st.title("⚡ Squeeze Terminal Pro")
st.caption(f"Filter: RVOL > 5x, +15% & Over VWAP | Kl. {time.strftime('%H:%M:%S')}")

API_KEY = "DKC7vblNaiBbTzht7ASgqgnmlvzl5ym"

def get_data():
    url = (f"https://financialmodelingprep.com/api/v3/stock-screener?"
           f"marketCapLowerThan=760000000&priceMoreThan=0.5&"
           f"isEtf=false&exchange=NYSE,NASDAQ,AMEX&apikey={API_KEY}")
    try:
        r = requests.get(url).json()
        df = pd.DataFrame(r)
        if df.empty: return []
        
        df = df[df['changesPercentage'] >= 15]
        results = []
        
        for _, row in df.head(10).iterrows():
            sym = row['symbol']
            
            # Hent Quote & VWAP
            q_url = f"https://financialmodelingprep.com/api/v3/quote/{sym}?apikey={API_KEY}"
            q = requests.get(q_url).json()[0]
            
            price = q.get('price', 0)
            vwap = q.get('vwap', 0)
            avg_v = q.get('avgVolume', 1)
            curr_v = q.get('volume', 0)
            rvol = curr_v / avg_v if avg_v > 0 else 0
            
            # FILTRE: RVOL > 5 OG Pris skal være OVER VWAP
            if rvol >= 5 and price > vwap:
                # Hent Short Data
                s_url = f"https://financialmodelingprep.com/api/v4/short-interest?symbol={sym}&apikey={API_KEY}"
                s = requests.get(s_url).json()
                sf = s[0].get('shortFloat', 0) if s else 0
                dtc = s[0].get('daysToCover', 0) if s else 0
                
                results.append({
                    "sym": sym, "price": price, "vwap": round(vwap, 2),
                    "chg": row['changesPercentage'], "rvol": round(rvol, 1),
                    "sf": round(sf, 1), "dtc": round(dtc, 1)
                })
        return results
    except: return []

data = get_data()

if data:
    play_sound() # Afspiller lyd når der er fundet aktier
    st.success(f"ALERT: {len(data)} aktier over VWAP med høj volumen!")
    for stock in data:
        with st.expander(f"🟢 {stock['sym']} | ${stock['price']} (+{stock['chg']:.1f}%)", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**VWAP:** ${stock['vwap']}")
                st.write(f"**RVOL:** {stock['rvol']}x")
            with c2:
                st.write(f"**Short Float:** {stock['sf']}%")
                st.write(f"**DTC:** {stock['dtc']}")
            st.markdown(f"[Nyheder](https://www.google.com/search?q={stock['sym']}+stock+news)")
else:
    st.info("Scanner... Venter på aktier over VWAP med RVOL > 5.")
    
