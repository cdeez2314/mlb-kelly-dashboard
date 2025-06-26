import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

st.set_page_config(page_title="MLB Betting Dashboard with Kelly Criterion", layout="wide")
st.title("⚾ MLB Betting Dashboard with Kelly Criterion")

# --- User Inputs ---
bankroll = st.number_input("Enter your bankroll ($)", min_value=100, step=50, value=1000)
min_edge = st.slider("Minimum expected value (edge)", 0.0, 0.20, 0.01, step=0.01)

# --- Helper Functions ---
def implied_prob(odds):
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def kelly_criterion(prob, odds, bankroll):
    decimal_odds = (odds / 100) + 1 if odds > 0 else (100 / abs(odds)) + 1
    b = decimal_odds - 1
    q = 1 - prob
    f = (prob * b - q) / b
    return max(f, 0) * bankroll

# --- Fetch Odds Data from Odds API ---
def fetch_odds_data():
    api_key = "8a9905b9beedb8254ebc41aa5e600d7a"
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "apiKey": api_key
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        st.error(f"Failed to fetch odds: {response.status_code} - {response.text}")
        return pd.DataFrame()

    games = response.json()
    rows = []
    for game in games:
        home = game['home_team']
        commence_time = datetime.strptime(game['commence_time'], "%Y-%m-%dT%H:%M:%SZ")

        for bookmaker in game.get("bookmakers", []):
            lines = {market['key']: market for market in bookmaker.get('markets', [])}
            if 'h2h' in lines:
                for outcome in lines['h2h']['outcomes']:
                    rows.append({
                        "type": "Moneyline",
                        "team": outcome['name'],
                        "opponent": home if outcome['name'] != home else game['away_team'],
                        "odds": outcome['price'],
                        "commence_time": commence_time,
                    })
            if 'spreads' in lines:
                for outcome in lines['spreads']['outcomes']:
                    rows.append({
                        "type": "Run Line",
                        "team": outcome['name'],
                        "opponent": home if outcome['name'] != home else game['away_team'],
                        "odds": outcome['price'],
                        "point": outcome['point'],
                        "commence_time": commence_time,
                    })
            if 'totals' in lines:
                for outcome in lines['totals']['outcomes']:
                    rows.append({
                        "type": "Total Runs",
                        "team": outcome['name'],
                        "opponent": home if outcome['name'] != home else game['away_team'],
                        "odds": outcome['price'],
                        "point": outcome['point'],
                        "commence_time": commence_time,
                    })

    return pd.DataFrame(rows)

# --- Main Logic ---
df = fetch_odds_data()
if df.empty:
    st.stop()

df['implied_prob'] = df['odds'].apply(implied_prob)
df['model_prob'] = df['implied_prob'] * np.random.uniform(1.15, 1.25, len(df))  # mock model probability
df['expected_value'] = df['model_prob'] - df['implied_prob']
df['kelly_fraction'] = df.apply(lambda x: max((x['model_prob'] * ((x['odds']/100)+1 if x['odds'] > 0 else (100/abs(x['odds'])) + 1) - (1 - x['model_prob'])) / (((x['odds']/100)+1 if x['odds'] > 0 else (100/abs(x['odds'])) + 1) - 1), 0), axis=1)
df['kelly_stake'] = df['kelly_fraction'] * bankroll
df['confidence'] = pd.cut(df['expected_value'], bins=[0, 0.1, 0.2, 1], labels=["Low", "Medium", "High"])
df['recommendation'] = df.apply(lambda x: f"✅ BET: {x['team']} to win vs. {x['opponent']} (${x['kelly_stake']:.2f})", axis=1)

# Filter
filtered_df = df[df['expected_value'] >= min_edge]
filtered_df = filtered_df.sort_values(by='kelly_stake', ascending=False)

# Display
st.subheader("Top Kelly Bets")
st.dataframe(
    filtered_df[["recommendation", "type", "team", "opponent", "odds", "implied_prob", "model_prob", "expected_value", "kelly_fraction", "kelly_stake", "confidence"]]
    .rename(columns={
        "type": "Market",
        "implied_prob": "Implied %",
        "model_prob": "Model %",
        "expected_value": "EV",
        "kelly_fraction": "Kelly %",
        "kelly_stake": "Stake $"
    })
    .style.format({
        "Implied %": "{:.2%}",
        "Model %": "{:.2%}",
        "EV": "{:.2%}",
        "Kelly %": "{:.2%}",
        "Stake $": "$ {:.2f}"
    }), use_container_width=True
)
