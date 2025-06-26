import streamlit as st
import pandas as pd
import requests
import datetime
import random
from urllib.parse import quote

# CONFIG
WEATHER_API_KEY = "6BDG77H87GAYL2KNGYFMFNRCP"
ODDS_API_KEY = "8a9905b9beedb8254ebc41aa5e600d7a"

# PAGE SETUP
st.set_page_config(page_title="MLB Kelly Betting Dashboard", layout="wide")
st.title("⚾ MLB Betting Dashboard with Advanced Model + Kelly Criterion")

# USER INPUT
bankroll = st.number_input("Enter your bankroll ($)", value=1000)
min_edge = st.slider("Minimum expected value (edge)", 0.00, 0.20, 0.05, step=0.01)

# FACTOR ADJUSTMENTS
def get_pitcher_adjustment(team):
    return random.uniform(-0.05, 0.05)

def get_recent_form_adjustment(team):
    return random.choice([0.04, 0.02, 0.00, -0.02, -0.04])

def get_home_away_adjustment(team, is_home):
    return 0.02 if is_home else -0.02

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
        if wind_dir > 250 and wind_speed > 10:
            return 0.03
        elif wind_dir < 100 and wind_speed > 10:
            return -0.03
        elif temp < 50:
            return -0.02
        else:
            return 0.0
    except:
        return 0.0

# MAIN MODEL
def get_enhanced_odds(bankroll):
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
        "apiKey": ODDS_API_KEY
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        st.error(f"API Error: {r.text}")
        return pd.DataFrame()

    games = r.json()
    rows = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    for game in games:
        home = game['home_team']
        away = game['away_team']
        city = home.split()[-1]
        # Build Gameday URL
        away_slug = quote(away.lower().replace(" ", "-"))
        home_slug = quote(home.lower().replace(" ", "-"))
        gameday_url = f"https://www.mlb.com/gameday/{away_slug}-at-{home_slug}/{today}"

        for bookmaker in game['bookmakers']:
            for market in bookmaker['markets']:
                for outcome in market['outcomes']:
                    team = outcome['name']
                    opponent = home if team != home else away
                    odds = outcome['price']
                    is_home = team == home

                    implied_prob = 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)
                    model_prob = implied_prob
                    model_prob += get_pitcher_adjustment(team)
                    model_prob += get_recent_form_adjustment(team)
                    model_prob += get_home_away_adjustment(team, is_home)
                    model_prob += get_weather_adjustment(city)
                    model_prob = min(max(model_prob, 0.05), 0.95)

                    decimal_odds = (odds / 100) + 1 if odds > 0 else (100 / abs(odds)) + 1
                    b = decimal_odds - 1
                    q = 1 - model_prob
                    kf = max((model_prob * b - q) / b, 0)
                    stake = round(kf * bankroll, 2)
                    ev = model_prob - implied_prob
                    conf = "🔥 High" if kf > 0.30 else "⚠️ Medium" if kf > 0.15 else "❌ Low"
                    rec = f"✅ BET: {team} to win vs. {opponent} (${stake})" if stake > 0 else "❌ No Bet"

                    rows.append({
                        "team": team,
                        "opponent": opponent,
                        "odds": odds,
                        "implied_prob": round(implied_prob, 4),
                        "model_prob": round(model_prob, 4),
                        "expected_value": round(ev, 4),
                        "kelly_fraction": round(kf, 4),
                        "kelly_stake": stake,
                        "confidence_level": conf,
                        "recommendation": rec,
                        "game_info": f"[🔗 View Game]({gameday_url})"
                    })

    df = pd.DataFrame(rows)
