import pandas as pd

# Load dataset
df = pd.read_csv("prof.csv")

print(df["category"].value_counts())