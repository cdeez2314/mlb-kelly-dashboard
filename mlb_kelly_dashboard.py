import streamlit as st
import pandas as pd
import requests
import datetime
import random
from urllib.parse import quote

# CONFIG
WEATHER_API_KEY = "6BDG77H87GAYL2KNGYFMFNRCP"
ODDS_API_KEY = "8a9905b9beedb8254ebc41aa5e600d7a"

st.set_page_config(page_title="MLB Betting Dashboard", layout="wide")
st.title("⚾ MLB Betting Dashboard – Moneyline, Run Line, Totals")

# USER SETTINGS
bankroll = st.number_input("Enter your bankroll ($)", value=1000)
min_edge = st.slider("Minimum expected value (edge)", 0.00, 0.20, 0.05, step=0.01)

# Adjustment Functions
def get_pitcher_adjustment(team): return random.uniform(-0.05, 0.05)
def get_recent_form_adjustment(team): return random.choice([0.04, 0.02, 0.00, -0.02, -0.04])
def get_home_away_adjustment(team, is_home): return 0.02 if is_home else -0.02
def get_weather_adjustment(city):
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}/{today}?unitGroup=us&key={WEATHER_API_KEY}&include=days"
    try:
        response = requests.get(url)
        data = response.json()
        day = data['days'][0]
        temp = day.get("temp", 70)
        wind_speed = day.get("windspeed", 5)
        wind_dir = day.get("winddir", 0)
        if wind_dir > 250 and wind_speed > 10: return 0.03
        elif wind_dir < 100 and wind_speed > 10: return -0.03
        elif temp < 50: return -0.02
        else: return 0.0
    except: return 0.0

# Main Data Fetch
def fetch_all_markets(bankroll):
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "apiKey": ODDS_API_KEY
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        st.error(f"API Error: {r.text}")
        return pd.DataFrame()

    games = r.json()
    bets = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    for game in games:
        home = game['home_team']
        away = game['away_team']
        city = home.split()[-1]
        url_slug = f"https://www.mlb.com/gameday/{quote(away.lower().replace(' ', '-'))}-at-{quote(home.lower().replace(' ', '-'))}/{today}"

        for book in game['bookmakers']:
            for market in book['markets']:
                mkt_type = market['key']  # h2h, spreads, totals
                for out in market['outcomes']:
                    team = out['name']
                    odds = out['price']
                    is_home = team == home

                    if mkt_type == "h2h":
                        label = f"{team} ML"
                        model_prob = 0.50 + get_pitcher_adjustment(team) + get_recent_form_adjustment(team) + get_home_away_adjustment(team, is_home) + get_weather_adjustment(city)
                    elif mkt_type == "spreads":
                        line = out['point']
                        label = f"{team} {line:+.1f}"
                        model_prob = 0.50 + get_recent_form_adjustment(team) + get_home_away_adjustment(team, is_home)
                    elif mkt_type == "totals":
                        line = out['point']
                        label = f"{team} {line}"
                        model_prob = 0.50 + get_weather_adjustment(city)
                    else:
                        continue

                    implied_prob = 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)
                    model_prob = min(max(model_prob, 0.05), 0.95)
                    decimal_odds = (odds / 100) + 1 if odds > 0 else (100 / abs(odds)) + 1
                    b = decimal_odds - 1
                    q = 1 - model_prob
                    kf = max((model_prob * b - q) / b, 0)
                    stake = round(kf * bankroll, 2)
                    ev = model_prob - implied_prob
                    conf = "🔥 High" if kf > 0.30 else "⚠️ Medium" if kf > 0.15 else "❌ Low"
                    rec = f"✅ BET: {label} (${stake})" if stake > 0 else "❌ No Bet"

                    bets.append({
                        "market": mkt_type,
                        "matchup": f"{away} @ {home}",
                        "bet": label,
                        "odds": odds,
                        "model_prob": round(model_prob, 4),
                        "implied_prob": round(implied_prob, 4),
                        "expected_value": round(ev, 4),
                        "kelly_fraction": round(kf, 4),
                        "kelly_stake": stake,
                        "confidence_level": conf,
                        "recommendation": rec,
                        "game_link": f"[🔗 View]({url_slug})"
                    })

    return pd.DataFrame(bets)

# Load Bets
df = fetch_all_markets(bankroll)

if not df.empty:
    df = df[df["expected_value"] >= min_edge]
    df = df.sort_values(by=["kelly_stake"], ascending=False).reset_index(drop=True)

    # Format for display
    df["implied_prob"] = (df["implied_prob"] * 100).round(2).astype(str) + "%"
    df["model_prob"] = (df["model_prob"] * 100).round(2).astype(str) + "%"
    df["expected_value"] = (df["expected_value"] * 100).round(2).astype(str) + "%"
    df["kelly_fraction"] = (df["kelly_fraction"] * 100).round(2).astype(str) + "%"
    df["kelly_stake"] = df["kelly_stake"].apply(lambda x: f"${x:.2f}")

    # Separate views by market
    for market_type, label in [("h2h", "💵 Moneyline Bets"), ("spreads", "📉 Run Line Bets"), ("totals", "🔢 Totals (O/U) Bets")]:
        section = df[df["market"] == market_type]
        if not section.empty:
            st.subheader(label)
            st.dataframe(section[[
                "recommendation", "matchup", "bet", "odds",
                "implied_prob", "model_prob", "expected_value",
                "kelly_fraction", "kelly_stake", "confidence_level", "game_link"
            ]], use_container_width=True)
else:
    st.warning("No games available or API limit reached.")
