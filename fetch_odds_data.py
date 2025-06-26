import requests
import pandas as pd
import streamlit as st
import random

def implied_prob(odds):
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def fetch_odds_data():
    api_key = st.secrets["ODDS_API_KEY"]
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/"
    params = {
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
        "apiKey": api_key
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        st.error(f"Failed to fetch odds: {response.status_code} - {response.text}")
        return pd.DataFrame()

    games = response.json()
    rows = []

    for game in games:
        bookmakers = game.get("bookmakers", [])
        if not bookmakers:
            continue

        markets = bookmakers[0].get("markets", [])
        if not markets or "outcomes" not in markets[0]:
            continue

        outcomes = markets[0]["outcomes"]
        if len(outcomes) < 2:
            continue

        team1 = outcomes[0]
        team2 = outcomes[1]

        for team, opponent in [(team1, team2), (team2, team1)]:
            odds = team.get("price")
            if odds is None:
                continue

            row = {
                "team": team["name"],
                "opponent": opponent["name"],
                "odds": odds,
                "implied_prob": implied_prob(odds),
                "model_prob": round(random.uniform(0.4, 0.6), 3)  # mock value
            }
            rows.append(row)

    return pd.DataFrame(rows)
