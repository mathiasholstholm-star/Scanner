import streamlit as st
import pandas as pd
import requests
import time
from streamlit_autorefresh import st_autorefresh

# Mobil-optimeret layout
st.set_page_config(page_title="Squeeze Super-App", page_icon="⚡", layout="centered")

# Auto-refresh hvert 30. sekund
st_autorefresh(interval=30 * 1000, key="datarefresh")

# Skjul Streamlit standard menu for "App-følelse"
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div.block-container {padding-top: 2rem;}
    </style>
    """
st.markdown(hide_style, unsafe_allow_html=True)

st.title("⚡ Squeeze Terminal")
st.caption(f"Status: Live • {time.strftime('%H:%M:%S')}")

API_KEY = "DKC7vblNaiBbTzht7ASgqgnmlvzl5ym"

def get_data():
    url = (f"https://financialmodelingprep.com/api/v3/stock-screener?"
           f"marketCapLowerThan=760000000&priceMoreThan=0.5&"
           f"isEtf=false&exchange=NYSE,NASDAQ,AMEX&apikey={API_KEY}")
    try:
        r = requests.get(url).json()
        df = pd.DataFrame(r)
        if df.empty: return []
        
        # Filter: Kun dem med fart på (+15%)
        df = df[df['changesPercentage'] >= 15]
        
        results = []
        for _, row in df.head(10).iterrows(): # Max 10 for hastighed
            sym = row['symbol']
            
            # Hent Quote (RVOL)
            q = requests.get(f"https://financialmodelingprep.com/api/v3/quote/{sym}?apikey={API_KEY}").json()[0]
            avg_v = q.get('avgVolume', 1)
            curr_v = q.get('volume', 0)
            rvol = curr_v / avg_v if avg_v > 0 else 0
            
            # Filter: Kun høj volumen (RVOL > 5)
            if rvol < 5: continue
            
            # Hent Short Data
            s = requests.get(f"https://financialmodelingprep.com/api/v4/short-interest?symbol={sym}&apikey={API_KEY}").json()
            sf = s[0].get('shortFloat', 0) if s else 0
            dtc = s[0].get('daysToCover', 0) if s else 0
            
            # Simpel AI Sentiment Logik (Kombinerer stigning og RVOL)
            sentiment = "🟢 POSITIV" if rvol > 10 and row['changesPercentage'] > 20 else "🟡 NEUTRAL"
            
            results.append({
                "sym": sym, "price": row['price'], "chg": row['changesPercentage'],
                "rvol": round(rvol, 1), "sf": round(sf, 1), "dtc": round(dtc, 1),
                "sent": sentiment
            })
        return results
    except: return []

data = get_data()

if data:
    for stock in data:
        # Kompakt overskrift til mobil
        with st.expander(f"{stock['sym']} | ${stock['price']} | +{stock['chg']:.1f}%", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.metric("RVOL (Tryk)", f"{stock['rvol']}x")
                st.write(f"**Short Float:** {stock['sf']}%")
            with c2:
                st.write(f"**Sentiment:** {stock['sent']}")
                st.write(f"**Days to Cover:** {stock['dtc']}")
            
            st.markdown(f"[🔍 Hurtig Analyse](https://www.google.com/search?q={stock['sym']}+stock+short+squeeze)")
            if stock['sf'] > 20:
                st.error("🔥 HIGH SQUEEZE POTENTIAL")
else:
    st.info("Scanner markedet for 5x volumen og +15% stigning...")

