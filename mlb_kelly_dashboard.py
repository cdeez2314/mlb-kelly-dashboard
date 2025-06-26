import streamlit as st
import pandas as pd
import numpy as np
import requests

def implied_prob(odds):
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def kelly_criterion(prob, odds, bankroll):
    decimal_odds = (odds / 100) + 1 if odds > 0 else (100 / abs(odds)) + 1
    b = decimal_odds - 1
    q = 1 - prob
    f = (prob * b - q) / b
    return max(f, 0)

def expected_value(model_prob, implied):
    return model_prob - implied

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
        for market in game.get("bookmakers", []):
            for outcome in market.get("markets", []):
                for bet in outcome.get("outcomes", []):
                    rows.append({
                        "game": game["id"],
                        "team": bet.get("name"),
                        "opponent": [t for t in game["teams"] if t != bet.get("name")][0],
                        "commence_time": game.get("commence_time"),
                        "market": outcome.get("key"),
                        "odds": bet.get("price"),
                    })

    return pd.DataFrame(rows)

def process_bets(df, bankroll, edge_threshold):
    df["implied_prob"] = df["odds"].apply(implied_prob)
    df["model_prob"] = df["implied_prob"] * 1.2  # Assume model has a 20% edge on average
    df["expected_value"] = df.apply(lambda row: expected_value(row["model_prob"], row["implied_prob"]), axis=1)
    df = df[df["expected_value"] >= edge_threshold]
    df["kelly_fraction"] = df.apply(lambda row: kelly_criterion(row["model_prob"], row["odds"], bankroll), axis=1)
    df["kelly_stake"] = (df["kelly_fraction"] * bankroll).round(2)
    df["confidence"] = pd.cut(df["kelly_fraction"], bins=[0, 0.1, 0.2, 1.0], labels=["Low", "Medium", "High"])
    df["recommendation"] = df.apply(
        lambda row: f"BET: {row['team']} to win vs. {row['opponent']} (${row['kelly_stake']})",
        axis=1
    )
    return df.sort_values(by="kelly_fraction", ascending=False)

def show_section(title, df):
    if not df.empty:
        st.subheader(title)
        st.dataframe(df[["recommendation", "team", "opponent", "odds", "implied_prob", "model_prob", "expected_value", "kelly_fraction", "kelly_stake", "confidence"]])

st.set_page_config(page_title="MLB Kelly Betting Dashboard", layout="wide")
st.title("🎾 MLB Betting Dashboard with Kelly Criterion")

bankroll = st.number_input("Enter your bankroll ($)", min_value=10, value=1000, step=10)
edge_threshold = st.slider("Minimum expected value (edge)", 0.00, 0.20, 0.01, step=0.01)

raw_data = fetch_odds_data()

moneyline_df = process_bets(raw_data[raw_data["market"] == "h2h"].copy(), bankroll, edge_threshold)
spread_df = process_bets(raw_data[raw_data["market"] == "spreads"].copy(), bankroll, edge_threshold)
totals_df = process_bets(raw_data[raw_data["market"] == "totals"].copy(), bankroll, edge_threshold)

show_section("💰 Top Moneyline Bets", moneyline_df)
show_section("📊 Top Run Line Bets", spread_df)
show_section("🔥 Top Totals (Over/Under) Bets", totals_df)
