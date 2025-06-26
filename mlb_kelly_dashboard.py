import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# Set up page
st.set_page_config(page_title="MLB Kelly Betting Dashboard", layout="wide")
st.title("\ud83c\udfc1 MLB Betting Dashboard with Kelly Criterion")

# --- User Inputs ---
bankroll = st.number_input("Enter your bankroll ($)", min_value=100, value=1000)
min_ev = st.slider("Minimum expected value (edge)", min_value=0.00, max_value=0.20, step=0.01, value=0.01)

# --- Kelly Criterion ---
def implied_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def kelly_criterion(prob, odds, bankroll):
    decimal_odds = (odds / 100 + 1) if odds > 0 else (100 / abs(odds)) + 1
    b = decimal_odds - 1
    q = 1 - prob
    f = (prob * b - q) / b
    return max(f, 0)

# --- Weather API ---
WEATHER_API_KEY = "6BDG77H87GAYL2KNGYFMFNRCP"

# --- Fetch Weather ---
def fetch_weather(city, date):
    base_url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
    url = f"{base_url}{city}/{date}?unitGroup=us&key={WEATHER_API_KEY}&include=days"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        weather = data["days"][0]
        return {
            "temp": weather["temp"],
            "windSpeed": weather["windspeed"],
            "precip": weather["precip"]
        }
    except:
        return {"temp": None, "windSpeed": None, "precip": None}

# --- Fetch Starting Pitchers ---
def fetch_pitchers_for_game(game_date):
    try:
        url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={game_date}"
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()

        pitcher_map = {}
        for date in data.get("dates", []):
            for game in date.get("games", []):
                teams = game.get("teams", {})
                home = teams.get("home", {}).get("team", {}).get("name", "")
                away = teams.get("away", {}).get("team", {}).get("name", "")

                home_pitcher = teams.get("home", {}).get("probablePitcher", {}).get("fullName", "")
                away_pitcher = teams.get("away", {}).get("probablePitcher", {}).get("fullName", "")

                pitcher_map[home] = home_pitcher
                pitcher_map[away] = away_pitcher

        return pitcher_map
    except:
        return {}

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

    games = response.json()
    rows = []
    if not games:
        return pd.DataFrame()

    sample_date = games[0].get("commence_time", "").split("T")[0]
    pitcher_lookup = fetch_pitchers_for_game(sample_date)

    for game in games:
        teams = game["teams"]
        home_team = game.get("home_team", "")
        opponent = [t for t in teams if t != home_team][0]
        commence_time = game["commence_time"]
        date_str = commence_time.split("T")[0]
        weather = fetch_weather(home_team, date_str)

        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    team_name = outcome["name"]
                    row = {
                        "commence_time": commence_time,
                        "market": market["key"],
                        "team": team_name,
                        "opponent": [t for t in teams if t != team_name][0],
                        "odds": outcome["price"],
                        "temp": weather["temp"],
                        "wind": weather["windSpeed"],
                        "precip": weather["precip"],
                        "pitcher": pitcher_lookup.get(team_name, "Unknown")
                    }
                    if market["key"] == "spreads":
                        row["spread"] = outcome.get("point")
                    elif market["key"] == "totals":
                        row["total"] = outcome.get("point")
                    rows.append(row)
    return pd.DataFrame(rows)

# --- Simulated Model Probabilities ---
def simulate_model_probs(df):
    np.random.seed(42)
    model_probs = []
    for _ in range(len(df)):
        model_probs.append(np.random.uniform(0.5, 0.8))
    df["model_prob"] = model_probs
    return df

# --- Run Dashboard Logic ---
df = fetch_odds_data()
if df.empty:
    st.stop()

df = df.dropna(subset=["odds"])
df = simulate_model_probs(df)

# Calculations
df["implied_prob"] = df["odds"].apply(implied_prob)
df["expected_value"] = df["model_prob"] - df["implied_prob"]
df["kelly_fraction"] = df.apply(lambda x: kelly_criterion(x["model_prob"], x["odds"], bankroll), axis=1)
df["kelly_stake"] = (df["kelly_fraction"] * bankroll).round(2)
df["confidence_level"] = pd.cut(df["expected_value"], bins=[0, 0.05, 0.10, 1], labels=["Low", "Medium", "High"])

# Filter
df = df[df["expected_value"] >= min_ev]

# Recommendations
recommendations = []
for i, row in df.iterrows():
    bet_type = row["market"]
    if bet_type == "h2h":
        rec = f"BET: {row['team']} to win vs. {row['opponent']}"
    elif bet_type == "spreads":
        rec = f"BET: {row['team']} {row['spread']} vs. {row['opponent']}"
    elif bet_type == "totals":
        rec = f"BET: {row['team']} {row['total']} vs. {row['opponent']}"
    else:
        rec = "BET: Unknown"
    recommendations.append(rec)
df["recommendation"] = recommendations

# Display
cols = ["recommendation", "team", "opponent", "odds", "market", "confidence_level", "pitcher", "temp", "wind", "precip"]
df = df.sort_values("expected_value", ascending=False)

st.subheader("Top Kelly Bets")
st.dataframe(df[cols], use_container_width=True)
