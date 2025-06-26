import requests
import pandas as pd

def fetch_odds_data():
    api_key = "8a9905b9beedb8254ebc41aa5e600d7a"
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"

    params = {
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
        "apiKey": api_key
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch odds: {response.status_code} - {response.text}")
        return pd.DataFrame()

    games = response.json()
    rows = []

    for game in games:
        home_team = game['home_team']
        for bookmaker in game['bookmakers']:
            for market in bookmaker['markets']:
                for outcome in market['outcomes']:
                    rows.append({
                        "team": outcome['name'],
                        "opponent": home_team if outcome['name'] != home_team else game['away_team'],
                        "odds": outcome['price']
                    })

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["team", "opponent"])
    df["implied_prob"] = 100 / (df["odds"] + 100) if df["odds"].gt(0).all() else df["odds"].abs() / (df["odds"].abs() + 100)
    df["model_prob"] = df["implied_prob"] + 0.15  # simulate model value
    return df
