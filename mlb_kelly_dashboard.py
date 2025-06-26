import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm

st.set_page_config(page_title="MLB Kelly Betting Dashboard", layout="wide")
st.title("⚾ MLB Betting Dashboard with Kelly Criterion")

# --- Simulated input data (replace with live data fetch) ---
data = {
    "home": ["Dodgers", "Dodgers", "Blue Jays", "Blue Jays", "Mariners"],
    "away": ["Rockies", "Rockies", "Guardians", "Guardians", "Twins"],
    "bet_type": ["Moneyline", "Run Line", "Moneyline", "Over", "Moneyline"],
    "line": [None, -1.5, None, 7.5, None],
    "odds": [-276, -110, -102, -115, -120],
    "model_prob": [0.78, 0.62, 0.55, 0.63, 0.59]
}
df = pd.DataFrame(data)

# --- Functions ---
def implied_prob(odds):
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def kelly_criterion(prob, odds, bankroll):
    decimal_odds = (odds / 100) + 1 if odds > 0 else (100 / abs(odds)) + 1
    b = decimal_odds - 1
    q = 1 - prob
    f = (prob * b - q) / b
    return max(0, f) * bankroll

# --- Calculate EV and Kelly stake ---
df["implied_prob"] = df["odds"].apply(implied_prob)
df["expected_value"] = df["model_prob"] - df["implied_prob"]
df["ev_flag"] = df["expected_value"] > 0.05
df["recommendation"] = np.where(df["ev_flag"], "✅ Bet", "🚫 No Bet")

# --- User input for bankroll ---
bankroll = st.sidebar.number_input("Enter Your Bankroll ($)", value=10000)
df["kelly_stake"] = df.apply(
    lambda row: kelly_criterion(row["model_prob"], row["odds"], bankroll),
    axis=1
)

# --- Display ---
st.subheader("📊 Best MLB Bets Today with Kelly Sizing")
st.dataframe(df[[
    "home", "away", "bet_type", "line", "odds", 
    "model_prob", "implied_prob", "expected_value", 
    "recommendation", "kelly_stake"
]].style.format({
    "model_prob": "{:.1%}",
    "implied_prob": "{:.1%}",
    "expected_value": "{:.1%}",
    "kelly_stake": "${:,.2f}"
}).applymap(lambda v: 'background-color: #d4edda' if v == "✅ Bet" else '', subset=["recommendation"]))