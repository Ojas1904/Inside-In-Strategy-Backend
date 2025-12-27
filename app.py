from flask import Flask, render_template, request, jsonify
from datetime import datetime, date
import json
import os

from scanner import run_scan

from dotenv import load_dotenv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# ===================== PATH CONFIG ===================== #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# ===================== APP ===================== #

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates")
)

# ===================== LOAD NSE HOLIDAYS ===================== #

HOLIDAYS_PATH = os.path.join(BASE_DIR, "holidays.json")

with open(HOLIDAYS_PATH, "r") as f:
    NSE_HOLIDAYS = set(json.load(f))

# ===================== CONSTANTS ===================== #

MIN_DATE = date(2020, 1, 1)
TODAY = date.today()

# ===================== HELPERS ===================== #

def is_weekend(trade_date):
    return trade_date.weekday() >= 5

def is_holiday(trade_date):
    return trade_date.strftime("%Y-%m-%d") in NSE_HOLIDAYS

# ===================== ROUTES ===================== #

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/scan", methods=["POST"])
def scan():
    date_str = request.json.get("date")

    if not date_str:
        return jsonify({
            "status": "invalid_date",
            "logs": ["❌ No date received from frontend."]
        })

    trade_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    if trade_date < MIN_DATE or trade_date > TODAY:
        return jsonify({
            "status": "invalid_date",
            "logs": [
                f"❌ Invalid date selected: {trade_date}",
                "📅 Please select a date between 2020 and today."
            ]
        })

    if is_weekend(trade_date):
        day_name = "Saturday" if trade_date.weekday() == 5 else "Sunday"
        return jsonify({
            "status": "closed",
            "reason": day_name,
            "logs": [
                f"📅 {trade_date} is a {day_name}.",
                "🏦 Indian stock markets are closed."
            ]
        })

    if is_holiday(trade_date):
        return jsonify({
            "status": "closed",
            "reason": "Holiday",
            "logs": [
                f"🏦 {trade_date} is an NSE trading holiday.",
                "📉 No market data available."
            ]
        })

    result = run_scan(date_str)

    if not result or not result.get("logs"):
        return jsonify({
            "status": "no_data",
            "logs": [
                "⚠️ No data was fetched.",
                "This may be due to an unexpected market closure or API issue."
            ]
        })

    return jsonify({
        "status": "ok",
        **result
    })

# ===================== ENTRY ===================== #

if __name__ == "__main__":
    app.run(debug=True)
