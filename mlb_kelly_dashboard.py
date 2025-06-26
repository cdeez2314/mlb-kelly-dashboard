import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# Set page configuration
st.set_page_config(page_title="MLB Kelly Betting Dashboard", layout="wide")
st.title("🏁 MLB Betting Dashboard with Kelly Criterion")

# --- User Inputs ---
bankroll = st.number_input("Enter your bankroll ($)", min_value=100, value=1000)
min_ev = st.slider("Minimum expected value (edge)", min_value=0.00, max_value=0.20, step=0.01, value=0.01)

# --- Kelly Criterion ---
def implied_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def kelly_criterion(prob, odds):
    decimal_odds = (odds / 100 + 1) if odds > 0 else (100 / abs(odds)) + 1
    b = decimal_odds - 1
    q = 1 - prob
    f = (prob * b - q) / b
    return max(f, 0)

# --- Weather API ---
WEATHER_API_KEY = "6BDG77H87GAYL2KNGYFMFNRCP"

def fetch_weather(city, date):
    base_url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
    url = f"{base_url}{city}/{date}?unitGroup=us&key={WEATHER_API_KEY}&include=days"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        weather = data["days"][0]
        return {
            "temp": weather.get("temp"),
            "wind": weather.get("windspeed"),
            "precip": weather.get("precip")
        }
    except:
        return {"temp": None, "wind": None, "precip": None}

# --- Fetch Odds Data ---
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
    response = requests.get(url, params=params)
    if response.status_code != 200:
        st.error(f"Error fetching odds: {response.status_code} - {response.text}")
        return pd.DataFrame()

    rows = []
    for game in response.json():
        home = game.get("home_team")
        away = [t for t in game.get("teams") if t != home][0]
        date_str = game.get("commence_time", "").split("T")[0]
        weather = fetch_weather(home, date_str)

        row = {
            "team": home,
            "opponent": away,
            "moneyline": None,
            "spread": None,
            "total": None,
            **weather,
        }

        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
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

# --- Simulated Model Probabilities ---
def simulate_model_probs(df):
    np.random.seed(0)
    df["model_prob"] = np.random.uniform(0.6, 0.8, len(df))
    df["implied_prob"] = df["moneyline"].apply(lambda x: implied_prob(x) if pd.notnull(x) else None)
    df["expected_value"] = df["model_prob"] - df["implied_prob"]
    df["kelly_fraction"] = df.apply(lambda x: kelly_criterion(x["model_prob"], x["moneyline"]) if pd.notnull(x["moneyline"]) else 0, axis=1)
    df["kelly_stake"] = (df["kelly_fraction"] * bankroll).round(2)
    df["confidence_level"] = pd.cut(df["expected_value"], bins=[0, 0.05, 0.10, 1], labels=["Low", "Medium", "High"])
    return df

# --- Run Dashboard ---
df = fetch_odds_data()
if df.empty:
    st.stop()

df = simulate_model_probs(df)
df = df[df["expected_value"] >= min_ev]

def make_recommendation(row):
    return f"BET: {row['team']} to win vs. {row['opponent']} (${row['kelly_stake']})"

df["recommendation"] = df.apply(make_recommendation, axis=1)

# --- Display ---
final_cols = [
    "recommendation", "team", "opponent", "moneyline", "spread", "total", "confidence_level"
]

st.subheader("Top Kelly Bets")
st.dataframe(df[final_cols].sort_values("expected_value", ascending=False), use_container_width=True)
