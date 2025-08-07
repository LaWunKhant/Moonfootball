import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV
df = pd.read_csv("data/arsenal_matches.csv")

# Convert date column to datetime
df["date"] = pd.to_datetime(df["date"])

# Plot xG vs Goals
plt.figure(figsize=(12, 6))
plt.plot(df["date"], df["xG"], label="xG", marker="o")
plt.plot(df["date"], df["goals"], label="Goals", marker="x")
plt.title("Arsenal: xG vs Goals (2023 Season)")
plt.xlabel("Match Date")
plt.ylabel("Value")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.grid()
plt.show()
