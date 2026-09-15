from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
FEATURES_FILE = BASE_DIR / "features.csv"
REVIEWS_FILE = BASE_DIR / "data" / "engineer_review_2026-02.xlsx"
OUTPUT_FILE = BASE_DIR / "training_data.csv"


def clean_gateway_id(series):
    return (
        series.astype("string")
        .str.replace(":", "", regex=False)
        .str.upper()
        .str.strip()
    )


def load_features():
    if not FEATURES_FILE.exists():
        raise FileNotFoundError(f"Features file not found: {FEATURES_FILE}")

    features = pd.read_csv(FEATURES_FILE)

    if "gateway_id" not in features.columns:
        raise ValueError("Features file is missing gateway_id")

    features["gateway_key"] = clean_gateway_id(features["gateway_id"])

    return features


def load_reviews():
    if not REVIEWS_FILE.exists():
        raise FileNotFoundError(f"Engineer review file not found: {REVIEWS_FILE}")

    reviews = pd.read_excel(REVIEWS_FILE)

    required_columns = {"gateway_id", "Kategorie"}

    missing_columns = required_columns - set(reviews.columns)

    if missing_columns:
        raise ValueError(
            f"Engineer review file is missing columns: "
            f"{sorted(missing_columns)}"
        )

    reviews["gateway_key"] = clean_gateway_id(reviews["gateway_id"])

    reviews["Kategorie"] = (
        reviews["Kategorie"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    reviews["target"] = (reviews["Kategorie"] == "schlecht").astype(int)

    return (
        reviews[["gateway_key", "target"]]
        .drop_duplicates(subset="gateway_key", keep="last")
    )


def create_training_data(features, reviews):
    training_data = features.merge(
        reviews,
        on="gateway_key",
        how="inner"
    )

    training_data = (
        training_data
        .drop(columns="gateway_key")
        .dropna(axis=1, how="all")
    )

    if training_data.empty:
        raise ValueError("No matching gateways found between features and reviews")

    if "target" not in training_data.columns:
        raise ValueError("Target column was not created")

    return training_data


def main():
    features = load_features()
    reviews = load_reviews()
    training_data = create_training_data(features, reviews)

    training_data.to_csv(OUTPUT_FILE, index=False)

    print(f"Features: {features.shape}")
    print(f"Engineer reviews: {reviews.shape}")
    print(f"Training data: {training_data.shape}")
    print("Target counts:")
    print(training_data["target"].value_counts().sort_index())
    print("Target distribution:")
    print(training_data["target"].value_counts(normalize=True).sort_index())
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()