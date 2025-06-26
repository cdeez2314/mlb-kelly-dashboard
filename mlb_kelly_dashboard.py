import streamlit as st
import pandas as pd
import numpy as np
import requests

# Set page configuration
st.set_page_config(page_title="MLB Kelly Betting Dashboard", layout="wide")
st.title("🏁 MLB Betting Dashboard with Kelly Criterion (ESPN Odds)")

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

# --- Fetch Odds Data from ESPN ---
def fetch_espn_odds():
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        games = []
        for event in data.get("events", []):
            competition = event.get("competitions", [{}])[0]
            teams = competition.get("competitors", [])
            odds = competition.get("odds", [{}])[0]
            home = next((t["team"]["displayName"] for t in teams if t["homeAway"] == "home"), "")
            away = next((t["team"]["displayName"] for t in teams if t["homeAway"] == "away"), "")
            games.append({
                "team": home,
                "opponent": away,
                "moneyline": None,
                "spread": None,
                "total": None,
                "details": odds.get("details", "N/A"),
                "provider": odds.get("provider", {}).get("name", "N/A")
            })
        return pd.DataFrame(games)
    except Exception as e:
        st.error(f"Error fetching ESPN odds: {e}")
        return pd.DataFrame()

# --- Simulated Model Probabilities ---
def simulate_model_probs(df):
    np.random.seed(0)
    df["model_prob"] = np.random.uniform(0.6, 0.8, len(df))
    df["implied_prob"] = 0.5  # Placeholder (since we don't have odds values)
    df["expected_value"] = df["model_prob"] - df["implied_prob"]
    df["kelly_fraction"] = df.apply(lambda x: kelly_criterion(x["model_prob"], 100), axis=1)  # Assume +100 odds
    df["kelly_stake"] = (df["kelly_fraction"] * bankroll).round(2)
    df["confidence_level"] = pd.cut(df["expected_value"], bins=[0, 0.05, 0.10, 1], labels=["Low", "Medium", "High"])
    return df

# --- Run Dashboard ---
df = fetch_espn_odds()
if df.empty:
    st.stop()

df = simulate_model_probs(df)
df = df[df["expected_value"] >= min_ev]

def make_recommendation(row):
    return f"BET: {row['team']} to win vs. {row['opponent']} (${row['kelly_stake']})"

df["recommendation"] = df.apply(make_recommendation, axis=1)

# --- Display ---
final_cols = [
    "recommendation", "team", "opponent", "details", "provider", "kelly_stake", "confidence_level"
]

st.subheader("Top Kelly Bets (ESPN Odds)")
st.dataframe(df[final_cols].sort_values("expected_value", ascending=False), use_container_width=True)
