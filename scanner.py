#This is the main backend file where all the checking of candles and all is done


import requests
import pandas as pd
from datetime import datetime, time

# ===================== CONFIG ===================== #

def log(msg, logs):
    print(msg)          # still prints to terminal
    logs.append(msg)    # also stores for frontend


import os

API_KEY = os.getenv("API_KEY")
ACCESS_TOKEN = os.getenv("BASE_URL")

if not API_KEY:
    raise ValueError("API_KEY not found in environment variables")


BASE_URL = "https://api.kite.trade/instruments/historical"
HEADERS = {
    "X-Kite-Version": "3",
    "Authorization": f"token {API_KEY}:{ACCESS_TOKEN}"
}

NIFTY50 = {
    "ADANIENT": 6401,
    "ADANIPORTS": 3861249,
    "APOLLOHOSP": 40193,
    "ASIANPAINT": 60417,
    "AXISBANK": 1510401,
    "BAJAJ-AUTO": 4267265,
    "BAJFINANCE": 81153,
    "BAJAJFINSV": 4268801,
    "BHARTIARTL": 2714625,
    "BPCL": 134657,
    "BRITANNIA": 140033,
    "CIPLA": 177665,
    "COALINDIA": 5215745,
    "DIVISLAB": 2800641,
    "DRREDDY": 225537,
    "EICHERMOT": 232961,
    "GRASIM": 315393,
    "HCLTECH": 1850625,
    "HDFCBANK": 341249,
    "HDFCLIFE": 119553,
    "HEROMOTOCO": 345089,
    "HINDALCO": 348929,
    "HINDUNILVR": 356865,
    "ICICIBANK": 1270529,
    "INDUSINDBK": 1346049,
    "INFY": 408065,
    "ITC": 424961,
    "JSWSTEEL": 3001089,
    "KOTAKBANK": 492033,
    "LT": 2939649,
    "M&M": 519937,
    "MARUTI": 2815745,
    "NESTLEIND": 4598529,
    "NTPC": 2977281,
    "ONGC": 633601,
    "POWERGRID": 3834113,
    "RELIANCE": 738561,
    "SBILIFE": 5582849,
    "SBIN": 779521,
    "SUNPHARMA": 857857,
    "TATACONSUM": 878593,
    "TATAMOTORS": 884737,
    "TATASTEEL": 895745,
    "TCS": 2953217,
    "TECHM": 3465729,
    "TITAN": 897537,
    "ULTRACEMCO": 2952193,
    "UPL": 2889473,
    "WIPRO": 969473
}

CHECK_TIMES = ["09:30", "09:45", "10:00"]

# ===================== DATA FETCH ===================== #

def fetch_1min_data(token, trade_date):
    from_dt = datetime.combine(trade_date, time(9, 15))
    to_dt   = datetime.combine(trade_date, time(10, 0))

    url = f"{BASE_URL}/{token}/minute"
    params = {
        "from": from_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "to": to_dt.strftime("%Y-%m-%d %H:%M:%S")
    }

    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()

    candles = r.json()["data"]["candles"]

    df = pd.DataFrame(
        candles,
        columns=["datetime", "open", "high", "low", "close", "volume"]
    )
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)

    return df

# ===================== STRATEGY LOGIC ===================== #

def passes_condition(df, check_time):
    target = df[df.index.strftime("%H:%M") == check_time]
    if target.empty:
        return False

    curr_time = target.index[0]
    prev1 = curr_time - pd.Timedelta(minutes=1)
    prev2 = curr_time - pd.Timedelta(minutes=2)

    if prev1 not in df.index or prev2 not in df.index:
        return False

    curr = df.loc[curr_time]
    p1   = df.loc[prev1]
    p2   = df.loc[prev2]

    return (
        curr.high >= p1.high and curr.high >= p2.high and
        curr.low  <= p1.low  and curr.low  <= p2.low
    )

# ===================== SANITY CHECK ===================== #

def sanity_check(stock, df):
    if df is None or df.empty:
        print(f"❌ {stock}: NO DATA FETCHED")
        return False

    print(f"🧪 {stock}: {len(df)} candles fetched")

    required_times = ["09:28", "09:29", "09:30", "09:44", "09:45", "09:59", "10:00"]
    available = set(df.index.strftime("%H:%M"))

    missing = [t for t in required_times if t not in available]
    if missing:
        print(f"⚠️ {stock}: Missing candles {missing}")
        return False

    print(f"✅ {stock}: All critical candles present")
    return True

# ===================== MAIN SCAN FUNCTION ===================== #

def run_scan(trade_date_str):
    logs = []

    trade_date = datetime.strptime(trade_date_str, "%Y-%m-%d").date()
    log(f"📅 Running scan for {trade_date}", logs)

    survivors = list(NIFTY50.keys())
    data_cache = {}

    log("🔍 Fetching data & sanity checking...\n", logs)

    for stock, token in NIFTY50.items():
        try:
            df = fetch_1min_data(token, trade_date)
            data_cache[stock] = df

            if df is None or df.empty:
                log(f"❌ {stock}: NO DATA FETCHED", logs)
            else:
                log(f"🧪 {stock}: {len(df)} candles fetched", logs)

        except Exception as e:
            log(f"❌ {stock}: API ERROR {e}", logs)
            data_cache[stock] = None

    stage_results = {}

    for ct in CHECK_TIMES:
        log(f"\n⏱ Checking {ct}", logs)
        next_round = []

        for stock in survivors:
            df = data_cache.get(stock)
            if df is None:
                continue

            if passes_condition(df, ct):
                next_round.append(stock)

        survivors = next_round
        stage_results[ct] = survivors.copy()

        if survivors:
            log(f"✅ Forwarded after {ct}: {survivors}", logs)
        else:
            log("❌ No stocks passed at this stage", logs)
            break

    log("\n🎯 FINAL FILTERED STOCKS:", logs)
    log(str(survivors if survivors else "None"), logs)

    return {
        "final": survivors,
        "stagewise": stage_results,
        "logs": logs
    }
