import pandas as pd


data = pd.read_csv("training_data.csv")

numeric_columns = data.select_dtypes(
    include=["int64", "float64"]
).columns.tolist()

numeric_columns.remove("target")

summary = data.groupby("target")[numeric_columns].mean().T

summary.columns = ["Normal", "Schlecht"]

summary["difference"] = (
    summary["Schlecht"] - summary["Normal"]
)

summary["difference_percent"] = (
    summary["difference"]
    / summary["Normal"].replace(0, pd.NA)
) * 100

summary = summary.sort_values(
    "difference_percent",
    ascending=False
)

print("Training data:", data.shape)

print("Target counts:")
print(data["target"].value_counts())

print("Feature comparison:")
print(summary.to_string())

summary.to_csv(
    "feature_comparison.csv"
)

print("Saved: feature_comparison.csv")