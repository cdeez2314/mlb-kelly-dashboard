import requests
import pandas as pd
import streamlit as st
import random

def implied_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def fetch_odds_data():
    api_key = st.secrets["ODDS_API_KEY"]
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/"
    
    params = {
        "regions": "us",
        "markets": "h2h",
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
        if not game.get("bookmakers"):
            continue

        bookmaker = game["bookmakers"][0]
        if not bookmaker.get("markets"):
            continue

        market = next((m for m in bookmaker["markets"] if m["key"] == "h2h"), None)
        if not market:
            continue

        outcomes = market["outcomes"]
        if len(outcomes) != 2:
            continue

        team1 = outcomes[0]
        team2 = outcomes[1]

        row1 = {
            "team": team1["name"],
            "opponent": team2["name"],
            "odds": team1["price"],
