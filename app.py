import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Micro-Scanner", layout="centered")
st.title("🚀 Live Micro-Scanner")

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

if st.button('KØR SCANNER', use_container_width=True):
    results = fetch_data()
    if not results.empty:
        for _, row in results.iterrows():
            with st.expander(f"🟢 {row['symbol']} (+{row['changesPercentage']:.1f}%)", expanded=True):
                st.write(f"**Pris:** ${row['price']} | **Volumen:** {int(row['volume']):,}")
                st.markdown(f"[Tjek Nyheder](https://www.google.com/search?q={row['symbol']}+stock+news&tbm=nws)")
    else:
        st.info("Ingen aktier matcher kriterierne lige nu.")
      
