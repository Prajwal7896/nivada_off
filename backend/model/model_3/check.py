import pandas as pd

# Load dataset
df = pd.read_csv("updated_complaints.csv")

print(df["category"].value_counts())