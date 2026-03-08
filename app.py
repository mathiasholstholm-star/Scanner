import streamlit as st
import pandas as pd
import requests
import time

# Sætter siden op
st.set_page_config(page_title="Micro-Scanner", layout="centered")

# Automatisk opdatering hver 30. sekund
# Dette genindlæser koden automatisk
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=30 * 1000, key="datarefresh")

st.title("🚀 Live Micro-Scanner")
st.caption("Opdaterer automatisk hver 30. sekund")

API_KEY = "DKC7vblNaiBbTzht7ASgqgnmlvzl5ym"

def fetch_data():
    url = (f"https://financialmodelingprep.com/api/v3/stock-screener?"
           f"marketCapLowerThan=760000000&"
           f"priceMoreThan=0.5&priceLowerThan=30&"
           f"isEtf=false&volumeMoreThan=490000&"
           f"exchange=NYSE,NASDAQ,AMEX&"
           f"apikey={API_KEY}")
    try:
        r = requests.get(url)
        df = pd.DataFrame(r.json())
        if not df.empty:
            df = df[df['changesPercentage'] >= 15]
            return df.sort_values(by='changesPercentage', ascending=False)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# Henter data
results = fetch_data()

if not results.empty:
    st.success(f"Fundet {len(results)} aktier kl. {time.strftime('%H:%M:%S')}")
    for _, row in results.iterrows():
        with st.expander(f"🟢 {row['symbol']} (+{row['changesPercentage']:.1f}%)", expanded=True):
            st.write(f"**Pris:** ${row['price']} | **Volumen:** {int(row['volume']):,}")
            st.markdown(f"[Tjek Nyheder](https://www.google.com/search?q={row['symbol']}+stock+news&tbm=nws)")
else:
    st.info("Søger... Ingen aktier matcher kriterierne lige nu.")
    
