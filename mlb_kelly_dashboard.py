from fetch_odds_data import fetch_odds_data
import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm

# Streamlit page setup
st.set_page_config(page_title="MLB Kelly Betting Dashboard", layout="wide")
st.title("⚾ MLB Betting Dashboard with Kelly Criterion")

# Fetch the odds data
df = fetch_odds_data()

# --- Functions ---

def kelly_criterion(prob, odds, bankroll):
    if odds < 0:
        decimal_odds = (100 / abs(odds)) + 1
    else:
        decimal_odds = (odds / 100) + 1
    b = decimal_odds - 1
    q = 1 - prob
    f = (prob * b - q) / b
    stake = max(0, f * bankroll)
    return round(stake, 2), round(f, 4)

# --- Run Calculation and Display ---

if not df.empty:
    bankroll = st.number_input("Enter your bankroll ($)", min_value=0, value=1000, step=100)

    # Calculate Kelly stakes and expected value
    df["expected_value"] = df["model_prob"] - df["implied_prob"]
    df["kelly_stake"], df["kelly_fraction"] = zip(*df.apply(
        lambda row: kelly_criterion(row["model_prob"], row["odds"], bankroll), axis=1
    ))

    # Filter based on edge threshold
    threshold = st.slider("Minimum expected value (edge)", 0.0, 0.2, 0.05, 0.01)
    filtered_df = df[df["expected_value"] > threshold].sort_values(by="expected_value", ascending=False)

    st.subheader("Top Kelly Bets")
    st.dataframe(filtered_df[[
        "team", "opponent", "odds", "implied_prob", "model_prob", "expected_value", "kelly_fraction", "kelly_stake"
    ]].style.format({
        "implied_prob": "{:.2%}",
        "model_prob": "{:.2%}",
        "expected_value": "{:.2%}",
        "kelly_fraction": "{:.2%}",
        "kelly_stake": "${:,.2f}"
    }))
else:
    st.warning("No data available. Please check your API key or data source.")
