from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TELEMETRY_DIR = DATA_DIR / "telemetry"
FIELD_VISITS_FILE = DATA_DIR / "field_visits.csv"
ENGINEER_REVIEWS_FILE = DATA_DIR / "engineer_review_2026-02.xlsx"

CLEANED_DIR = DATA_DIR / "cleaned"

TELEMETRY_OUTPUT = CLEANED_DIR / "telemetry_clean.parquet"
FIELD_VISITS_OUTPUT = CLEANED_DIR / "field_visits_clean.csv"
ENGINEER_REVIEWS_OUTPUT = CLEANED_DIR / "engineer_reviews_clean.csv"

NON_NEGATIVE_COLUMNS = [
    "reboot_cnt",
    "reboot_duration_sec",
    "r_cnt_power_cycle",
    "r_cnt_reboot",
    "r_cnt_unknown",
    "r_dur_power_cycle",
    "r_dur_reboot",
    "r_dur_unknown",
    "disconnection_cnt",
    "offline_duration_sec",
]


def clean_gateway_id(series):
    return (
        series.astype("string")
        .str.replace(":", "", regex=False)
        .str.upper()
        .str.strip()
    )


def clean_numeric_columns(df, columns):
    existing_columns = [column for column in columns if column in df.columns]

    for column in existing_columns:
        df[column] = (
            pd.to_numeric(df[column], errors="coerce")
            .fillna(0)
            .clip(lower=0)
        )

    return df


def load_telemetry():
    files = sorted(TELEMETRY_DIR.glob("month=*/part-*.parquet"))

    if not files:
        raise FileNotFoundError(
            f"No telemetry parquet files found in {TELEMETRY_DIR}"
        )

    telemetry = pd.concat(
        (pd.read_parquet(file) for file in files),
        ignore_index=True
    )

    required_columns = {"gateway_id", "ts_utc"}
    missing_columns = required_columns - set(telemetry.columns)

    if missing_columns:
        raise ValueError(
            f"Telemetry is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    telemetry["gateway_id"] = clean_gateway_id(
        telemetry["gateway_id"]
    )

    telemetry["ts_utc"] = pd.to_datetime(
        telemetry["ts_utc"],
        errors="coerce",
        utc=True
    )

    telemetry = telemetry.dropna(
        subset=["gateway_id", "ts_utc"]
    )

    telemetry["timestamp"] = telemetry["ts_utc"]

    telemetry = telemetry.drop_duplicates(
        subset=["gateway_id", "timestamp"]
    )

    telemetry = clean_numeric_columns(
        telemetry,
        NON_NEGATIVE_COLUMNS
    )

    return telemetry.sort_values(
        ["gateway_id", "timestamp"]
    ).reset_index(drop=True)


def clean_field_visits():
    if not FIELD_VISITS_FILE.exists():
        print("Field visits file not found.")
        return None

    visits = pd.read_csv(FIELD_VISITS_FILE)

    if "gateway_id" in visits.columns:
        visits["gateway_id"] = clean_gateway_id(
            visits["gateway_id"]
        )

    for column in ["requested_on", "visited_on"]:
        if column in visits.columns:
            visits[column] = pd.to_datetime(
                visits[column],
                errors="coerce"
            ).dt.strftime("%Y-%m-%d")

    if "technician_hours" in visits.columns:
        visits["technician_hours"] = (
            pd.to_numeric(
                visits["technician_hours"],
                errors="coerce"
            )
            .clip(lower=0)
        )

    if "parts_replaced" in visits.columns:
        visits["parts_replaced"] = visits[
            "parts_replaced"
        ].fillna("")

    return visits.drop_duplicates().reset_index(drop=True)


def clean_engineer_reviews():
    if not ENGINEER_REVIEWS_FILE.exists():
        print("Engineer review file not found.")
        return None

    reviews = pd.read_excel(
        ENGINEER_REVIEWS_FILE
    )

    if "gateway_id" not in reviews.columns:
        raise ValueError(
            "Engineer review file is missing gateway_id"
        )

    reviews["gateway_id"] = clean_gateway_id(
        reviews["gateway_id"]
    )

    return reviews.drop_duplicates(
        subset=["gateway_id"]
    ).reset_index(drop=True)


def save_csv(df, path):
    df.to_csv(
        path,
        index=False
    )
    print(f"Saved: {path}")


def main():
    CLEANED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("Cleaning data")

    print("Telemetry")
    telemetry = load_telemetry()

    print(f"Rows: {len(telemetry)}")
    print(f"Gateways: {telemetry['gateway_id'].nunique()}")

    telemetry.to_parquet(
        TELEMETRY_OUTPUT,
        index=False
    )

    print(f"Saved: {TELEMETRY_OUTPUT}")

    print("Meter reads file not found.")

    print("Field visits")
    visits = clean_field_visits()

    if visits is not None:
        print(f"Rows: {len(visits)}")
        print(f"Gateways: {visits['gateway_id'].nunique()}")
        save_csv(visits, FIELD_VISITS_OUTPUT)

    print("Engineer reviews")
    reviews = clean_engineer_reviews()

    if reviews is not None:
        print(f"Rows: {len(reviews)}")
        print(f"Gateways: {reviews['gateway_id'].nunique()}")
        save_csv(reviews, ENGINEER_REVIEWS_OUTPUT)

    print("Cleaning completed")


if __name__ == "__main__":
    main()