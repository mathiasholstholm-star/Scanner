# --- NYE FUNKTIONER TIL RISIKO-ANALYSE ---

def check_dilution_risk(symbol):
    """Scanner fundamentale tal og SEC-filer for offering-risiko"""
    try:
        # 1. Tjek kontantbeholdning (Balance Sheet)
        url_bs = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{symbol}?limit=1&apikey={FMP_API_KEY}"
        bs = requests.get(url_bs).json()
        
        # 2. Tjek seneste SEC Filings for Warrants/S-3
        url_sec = f"https://financialmodelingprep.com/api/v3/sec_filings/{symbol}?limit=5&apikey={FMP_API_KEY}"
        sec = requests.get(url_sec).json()
        
        risk_msg = "✅ LAV"
        risk_score = 0
        
        if bs:
            cash = bs[0].get('cashAndCashEquivalents', 0)
            debt = bs[0].get('totalDebt', 0)
            # Hvis gæld er 3x større end kontanter = Høj risiko
            if debt > (cash * 3): 
                risk_msg = "⚠️ HØJ (Cash Low)"
                risk_score -= 20

        if sec:
            for filing in sec:
                if any(k in filing['type'] for k in ["S-3", "424B", "F-3"]):
                    risk_msg = "🚨 OFFERING RISK (SEC)"
                    risk_score -= 30
                    break
                    
        return risk_msg, risk_score
    except: return "N/A", 0

# --- INTEGRATION I DIN LISTE ---
# (I din loop for hver aktie tilføjer vi nu dette:)

risk_label, risk_penalty = check_dilution_risk(symbol)
total_score += risk_penalty # Trækker point fra hvis de mangler penge

# NY KOLONNE I TABELLEN:
# "RISIKO": risk_label
