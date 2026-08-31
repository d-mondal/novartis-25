import pandas as pd
import numpy as np

# Load existing dataset
df = pd.read_csv("data/CPID_EDC_Metrics_Enriched.xlsx - Sheet1.csv")

# Set seed for reproducibility (optional)
np.random.seed(42)

# Add DQI column with random values (0–100)
df["dqi"] = np.random.randint(0, 101, size=len(df))

# Optional: round / convert to int if needed
df["dqi"] = df["dqi"].astype(int)

# Save updated dataset
df.to_csv("data/master_dataset.csv", index=False)

print("DQI column added successfully.")
print(df[["dqi"]].head())
