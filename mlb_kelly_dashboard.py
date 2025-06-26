from fetch_odds_data import fetch_odds_data
import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm

# Page setup
st.set_page_config(page_title="MLB Kelly Betting Dashboard", layout="wide")
st.title("⚾ MLB Betting Dashboard with Kelly Criterion")

# --- Functions ---

def implied_prob(odds):
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def kelly_criterion(prob, odds, bankroll):
    decimal_odds = (odds / 100) + 1 if odds > 0 else (100 / abs(odds)) + 1
    b = decimal_odds - 1
    q = 1 - prob
    f = (prob * b - q) / b
    return max(f, 0)  # Avoid negative Kelly fractions

def label_confidence(kf):
    if kf > 0.30:
        return "🔥 High"
    elif kf > 0.15:
        return "⚠️ Medium"
    else:
        return "❌ Low"

# --- User Inputs ---
bankroll = st.number_input("Enter your bankroll ($)", value=1000)
min_edge = st.slider("Minimum expected value (edge)", 0.00, 0.20, 0.05, step=0.01)

# --- Data Fetch ---
df = fetch_odds_data()

if df.empty:
    st.warning("No data returned from API.")
else:
    # Add computed columns
    df["implied_prob"] = df["odds"].apply(implied_prob)
    df["model_prob"] = np.random.uniform(df["implied_prob"] + 0.05, 0.80)  # Simulated model
    df["expected_value"] = df["model_prob"] - df["implied_prob"]
    df["kelly_fraction"] = df.apply(lambda row: kelly_criterion(row["model_prob"], row["odds"], bankroll), axis=1)
    df["kelly_stake"] = (df["kelly_fraction"] * bankroll).round(2)

    # Confidence tagging
    df["confidence_level"] = df["kelly_fraction"].apply(label_confidence)

    # Betting recommendation text
    df["recommendation"] = df.apply(
        lambda row: f"✅ BET: {row['team']} to win vs. {row['opponent']} (${row['kelly_stake']})",
        axis=1
    )

    # Filter by edge threshold
    df = df[df["expected_value"] >= min_edge]

    # Sort by Kelly stake
    df = df.sort_values(by="kelly_stake", ascending=False).reset_index(drop=True)

    # Format percentages
    df["implied_prob"] = (df["implied_prob"] * 100).round(2).astype(str) + "%"
    df["model_prob"] = (df["model_prob"] * 100).round(2).astype(str) + "%"
    df["expected_value"] = (df["expected_value"] * 100).round(2).astype(str) + "%"
    df["kelly_fraction"] = (df["kelly_fraction"] * 100).round(2).astype(str) + "%"
    df["kelly_stake"] = df["kelly_stake"].apply(lambda x: f"${x:.2f}")

    # Display final table
    st.subheader("Top Kelly Bets")
    st.dataframe(df[[
        "recommendation", "team", "opponent", "odds", "implied_prob", "model_prob",
        "expected_value", "kelly_fraction", "kelly_stake", "confidence_level"
    ]])
