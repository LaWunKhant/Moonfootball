import plotly.express as px
import streamlit as st
import pandas as pd
import os

# 🚀 Setup
st.set_page_config(page_title="Match Stats Dashboard", layout="wide")

# 🔽 Dropdown to select team and season
data_dir = "data"
teams = ["Arsenal", "Chelsea"]
seasons = ["2024"]

team = st.sidebar.selectbox("Select team", teams)
season = st.sidebar.selectbox("Select season", seasons)

# 📂 Construct file path
filename = f"{team.lower()}_matches_{season}.csv"
filepath = os.path.join(data_dir, filename)

# 🧾 Load data
try:
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
except FileNotFoundError:
    st.error(f"No data found for {team} in {season}")
    st.stop()

# 🧮 Compute stats
total_matches = len(df)
wins = (df["result"] == "w").sum()
draws = (df["result"] == "d").sum()
losses = (df["result"] == "l").sum()
total_goals = df["goals_for"].sum()
total_xg = df["xG_for"].sum()

# 🖼️ Title & Summary
st.title(f"{team} Match Dashboard ({season})")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Matches", total_matches)
col2.metric("Wins", wins)
col3.metric("Draws", draws)
col4.metric("Losses", losses)

st.markdown(f"**Total Goals:** {total_goals} | **Total xG:** {total_xg:.1f}")

# 📈 Line Chart: xG vs Goals
st.subheader("📊 xG vs Goals Over Time")
st.line_chart(df.set_index("date")[["xG_for", "goals_for"]])

st.subheader("🟢 Win / ⚪ Draw / 🔴 Loss Breakdown")

outcome_counts = df["result"].value_counts()
st.plotly_chart(px.pie(
    names=outcome_counts.index,
    values=outcome_counts.values,
    title="Result Breakdown"
))

csv = df.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download CSV", csv, f"{team.lower()}_{season}.csv", "text/csv")

# 📋 Table preview
st.subheader("📄 Match Data")
st.dataframe(df)