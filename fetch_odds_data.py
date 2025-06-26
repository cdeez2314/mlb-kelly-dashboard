import requests
import streamlit as st

def fetch_odds_data(api_key: str):
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "apiKey": api_key
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        st.error(f"Odds fetch error: {resp.status_code} - {resp.text}")
        return []
    return resp.json()
