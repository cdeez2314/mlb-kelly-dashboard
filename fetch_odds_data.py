import requests
import pandas as pd
import streamlit as st
import os

def fetch_odds_data():
    api_key = st.secrets["ODDS_API_KEY"]["ODDS_API_KEY"]
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
        home_team = game["home_team"]
        away_team = game["away_team"]
        commence_time = game["commence_time"]
        for bookmaker in game["bookmakers"]:
            for market in bookmaker["markets"]:
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        rows.append({
                            "bet_type": "Moneyline",
                            "team": outcome["name"],
                            "odds": outcome["price"],
                            "home": home_team,
                            "away": away_team,
                            "market": market["key"],
                            "bookmaker": bookmaker["title"],
                            "commence_time": commence_time
                        })
                elif market["key"] == "spreads":
                    for outcome in market["outcomes"]:
                        rows.append({
                            "bet_type": "Run Line",
                            "team": outcome["name"],
                            "odds": outcome["price"],
                            "line": outcome["point"],
                            "home": home_team,
                            "away": away_team,
                            "market": market["key"],
                            "bookmaker": bookmaker["title"],
                            "commence_time": commence_time
                        })
                elif market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        rows.append({
                            "bet_type": "Total",
                            "team": outcome["name"],
                            "odds": outcome["price"],
                            "line": outcome["point"],
                            "home": home_team,
                            "away": away_team,
                            "market": market["key"],
                            "bookmaker": bookmaker["title"],
                            "commence_time": commence_time
                        })
    return pd.DataFrame(rows)