import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# Set page config
st.set_page_config(page_title="MLB Kelly Betting Dashboard", layout="wide")
st.title("🏁 MLB Betting Dashboard with Kelly Criterion")

# User input
bankroll = st.number_input("Enter your bankroll ($)", min_value=100, value=1000)
min_ev = st.slider("Minimum expected value (edge)", min_value=0.00, max_value=0.20, step=0.01, value=0.01)

# Kelly calculations
def implied_prob(odds):
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def kelly_criterion(prob, odds):
    decimal_odds = (odds / 100 + 1) if odds > 0 else (100 / abs(odds)) + 1
    b = decimal_odds - 1
    q = 1 - prob
    f = (prob * b - q) / b
    return max(f, 0)

# Weather
WEATHER_API_KEY = "6BDG77H87GAYL2KNGYFMFNRCP"

def fetch_weather(city, date):
    base_url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
    url = f"{base_url}{city}/{date}?unitGroup=us&key={WEATHER_API_KEY}&include=days"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        day = data["days"][0]
        return {"temp": day.get("temp"), "wind": day.get("windspeed"), "precip": day.get("precip")}
    except:
        return {"temp": None, "wind": None, "precip": None}

# Odds data
def fetch_odds_data():
    api_key = "8a9905b9beedb8254ebc41aa5e600d7a"
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso"
    }
    res = requests.get(url, params=params)
    if res.status_code != 200:
        st.error(f"Odds fetch error: {res.status_code} - {res.text}")
        return pd.DataFrame()

    rows = []
    for game in res.json():
        home = game["home_team"]
        away = [t for t in game["teams"] if t != home][0]
        date_str = game["commence_time"].split("T")[0]
        weather = fetch_weather(home, date_str)

        row = {
            "team": home,
            "opponent": away,
            "moneyline": None,
            "spread": None,
            "total": None,
            **weather
        }

        for book in game.get("bookmakers", []):
            for market in book.get("markets", []):
                for outcome in market.get("outcomes", []):
                    if outcome.get("name") != home:
                        continue
                    if market["key"] == "h2h":
                        row["moneyline"] = outcome.get("price")
                    elif market["key"] == "spreads":
                        row["spread"] = outcome.get("point")
                    elif market["key"] == "totals":
                        row["total"] = outcome.get("point")

        rows.append(row)

    return pd.DataFrame(rows)

# Simulated model
def simulate_model(df):
    np.random.seed(0)
    df["model_prob"] = np.random.uniform(0.6, 0.8, len(df))
    df["implied_prob"] = df["moneyline"].apply(lambda x: implied_prob(x) if pd.notnull(x) else None)
    df["expected_value"] = df["model_prob"] - df["implied_prob"]
    df["kelly_fraction"] = df.apply(lambda x: kelly_criterion(x["model_prob"], x["moneyline"]) if pd.notnull(x["moneyline"]) else 0, axis=1)
    df["kelly_stake"] = (df["kelly_fraction"] * bankroll).round(2)
    df["confidence_level"] = pd.cut(df["expected_value"], [0, 0.05, 0.10, 1], labels=["Low", "Medium", "High"])
    return df

# Fetch + filter
df = fetch_odds_data()
if df.empty:
    st.stop()

df = simulate_model(df)
df = df[df["expected_value"] >= min_ev]

# Recommendation column
df["recommendation"] = df.apply(lambda row: f"BET: {row['team']} to win vs. {row['opponent']} (${row['kelly_stake']})", axis=1)

# Final columns
final_cols = ["recommendation", "team", "opponent", "moneyline", "spread", "total", "confidence_level"]

st.subheader("Top Kelly Bets")
st.dataframe(df[final_cols].sort_values("expected_value", ascending=False), use_container_width=True)
