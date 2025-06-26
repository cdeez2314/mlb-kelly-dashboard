import streamlit as st
import pandas as pd
import numpy as np
from fetch_odds_data import fetch_odds_data
from scipy.stats import norm

# Configure
st.set_page_config(page_title="MLB Kelly Bets", layout="wide")
st.title("⚾️ MLB Betting Dashboard - Moneyline, Run Line, Totals")

# User Inputs
bankroll = st.number_input("Enter your bankroll ($)", min_value=1.0, value=1000.0, step=1.0)
min_edge = st.slider("Minimum expected value (edge)", 0.0, 0.2, 0.05, 0.01)

# Fetch and transform
api_key = st.secrets["ODDS_API_KEY"]
data = fetch_odds_data(api_key)

rows = []
for game in data:
    home = game["home_team"]
    away = game["away_team"]
    for book in game["bookmakers"]:
        for m in book["markets"]:
            if m["key"] == "h2h":
                for o in m["outcomes"]:
                    team, odds = o["name"], o["price"]
                    rows.append({"team": team, "opponent": away if team==home else home, 
                                 "market":"Moneyline", "odds": odds})
            if m["key"] == "spreads":
                for o in m["outcomes"]:
                    rows.append({"team": o["name"], "opponent": away if o["name"]==home else home, 
                                 "market":"Run Line", "odds": o["price"], "line": o["point"]})
            if m["key"] == "totals":
                for o in m["outcomes"]:
                    rows.append({"team":"Total", "opponent": "", 
                                 "market": f"Totals ({o['point']})", "odds": o["price"], "side":o["name"]})

df = pd.DataFrame(rows)
df.drop_duplicates(inplace=True)

# Model: simulate model_prob using implied + margin
df["implied_prob"] = df["odds"].apply(lambda x: 100/(x+100) if x>0 else abs(x)/(abs(x)+100))
df["model_prob"] = df["implied_prob"] + 0.05  # example model edge
df["edge"] = df["model_prob"] - df["implied_prob"]
df = df[df["edge"] >= min_edge]

def calc_kelly(p, odds):
    b = (odds/100 if odds>0 else 100/abs(odds)) 
    q = 1-p
    return (p*(b+1)-1)/b if p*(b+1)>1 else 0

df["kelly_fraction"] = df.apply(lambda r: calc_kelly(r["model_prob"], r["odds"]), axis=1)
df["kelly_stake"] = (df["kelly_fraction"] * bankroll).round(2)

# Confidence
df["confidence_level"] = pd.cut(df["edge"], bins=[0,0.08,0.15,1], labels=["Low","Medium","High"])

df["recommendation"] = df.apply(
    lambda r: f"✅ BET: {r['team']} {r['market']} vs {r['opponent']} (${r['kelly_stake']:.2f})", axis=1
)

cols = ["recommendation","team","opponent","market","odds","kelly_stake","confidence_level"]
st.table(df[cols].sort_values("kelly_stake", ascending=False))
