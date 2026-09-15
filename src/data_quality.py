from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")
TELEMETRY_DIR = DATA_DIR / "telemetry"

TELEMETRY_REQUIRED = [
    "gateway_id",
    "ts_utc",
    "reboot_cnt",
    "disconnection_cnt",
    "offline_duration_sec",
]

METER_REQUIRED = [
    "week_start",
    "gateway_id",
    "meters_expected",
    "meters_read",
]

FIELD_VISIT_REQUIRED = [
    "visit_id",
    "gateway_id",
    "requested_on",
    "visited_on",
    "reason_reported",
    "outcome",
    "technician_hours",
]

REVIEW_REQUIRED = [
    "gateway_id",
    "Kategorie",
    "reviewed_on",
]


def load_file(path):
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".csv":
        return pd.read_csv(path)
    if path.suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def find_file(names):
    for name in names:
        for path in DATA_DIR.rglob(name):
            return path
    return None


def print_basic_stats(df, name):
    print(f"{name}:")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Missing values: {int(df.isna().sum().sum())}")
    print(f"Duplicate rows: {int(df.duplicated().sum())}")


def check_required_columns(df, required):
    missing = [column for column in required if column not in df.columns]

    if missing:
        print(f"Missing required columns: {missing}")
        return False

    print("Required columns: OK")
    return True


def check_telemetry():
    files = sorted(TELEMETRY_DIR.glob("month=*/part-*.parquet"))

    if not files:
        print("No telemetry files found.")
        return

    frames = []

    for path in files:
        df = pd.read_parquet(path)
        frames.append(df)

        print(f"\n{path}")
        print_basic_stats(df, "Telemetry")

        if not check_required_columns(df, TELEMETRY_REQUIRED):
            continue

        numeric_columns = [
            "reboot_cnt",
            "disconnection_cnt",
            "offline_duration_sec",
        ]

        negative_values = {
            column: int(df[column].lt(0).sum())
            for column in numeric_columns
        }

        print(f"Negative values: {negative_values}")

        timestamps = pd.to_datetime(df["ts_utc"], errors="coerce")

        print(f"Invalid timestamps: {int(timestamps.isna().sum())}")

        if timestamps.notna().any():
            print(f"Date range: {timestamps.min()} to {timestamps.max()}")

    telemetry = pd.concat(frames, ignore_index=True)

    print("\nAll telemetry:")
    print(f"Rows: {len(telemetry)}")
    print(f"Unique gateways: {telemetry['gateway_id'].nunique()}")
    print(f"Duplicate rows: {int(telemetry.duplicated().sum())}")

    duplicate_keys = telemetry.duplicated(
        subset=["gateway_id", "ts_utc"]
    ).sum()

    print(f"Duplicate gateway/timestamp records: {int(duplicate_keys)}")


def check_meter_reads():
    path = find_file(
        [
            "meter_reads.parquet",
            "meter_reads.csv",
            "meter_reads.xlsx",
        ]
    )

    if path is None:
        print("\nMeter reads file could not be located.")
        return

    df = load_file(path)

    print(f"\n{path}")
    print_basic_stats(df, "Meter reads")

    if not check_required_columns(df, METER_REQUIRED):
        return

    print(f"Unique gateways: {df['gateway_id'].nunique()}")
    print(f"Expected = 0: {int(df['meters_expected'].eq(0).sum())}")
    print(
        "Read greater than expected: "
        f"{int(df['meters_read'].gt(df['meters_expected']).sum())}"
    )
    print(
        "Negative expected values: "
        f"{int(df['meters_expected'].lt(0).sum())}"
    )
    print(
        "Negative read values: "
        f"{int(df['meters_read'].lt(0).sum())}"
    )


def check_field_visits():
    path = find_file(
        [
            "field_visits.parquet",
            "field_visits.csv",
            "field_visits.xlsx",
        ]
    )

    if path is None:
        print("\nField visits file could not be located.")
        return

    df = load_file(path)

    print(f"\n{path}")
    print_basic_stats(df, "Field visits")

    if not check_required_columns(df, FIELD_VISIT_REQUIRED):
        return

    print(f"Unique gateways: {df['gateway_id'].nunique()}")
    print(f"Unique visits: {df['visit_id'].nunique()}")

    negative_hours = df["technician_hours"].lt(0).sum()
    print(f"Negative technician hours: {int(negative_hours)}")

    requested = pd.to_datetime(df["requested_on"], errors="coerce")
    visited = pd.to_datetime(df["visited_on"], errors="coerce")

    print(f"Invalid requested dates: {int(requested.isna().sum())}")
    print(f"Invalid visited dates: {int(visited.isna().sum())}")

    valid_dates = requested.notna() & visited.notna()

    print(
        "Visited before requested: "
        f"{int((visited[valid_dates] < requested[valid_dates]).sum())}"
    )


def check_engineer_reviews():
    path = find_file(
        [
            "engineer_reviews_2026-02.xlsx",
            "engineer_reviews.xlsx",
            "engineer_reviews.csv",
            "engineer_reviews.parquet",
        ]
    )

    if path is None:
        print("\nEngineer review file could not be located.")
        return

    df = load_file(path)

    print(f"\n{path}")
    print_basic_stats(df, "Engineer reviews")

    if not check_required_columns(df, REVIEW_REQUIRED):
        return

    print(f"Unique gateways: {df['gateway_id'].nunique()}")

    print("Categories:")
    print(df["Kategorie"].value_counts(dropna=False).to_string())

    reviewed = pd.to_datetime(df["reviewed_on"], errors="coerce")

    print(f"Invalid review dates: {int(reviewed.isna().sum())}")


def main():
    print("Data quality check")

    check_telemetry()
    check_meter_reads()
    check_field_visits()
    check_engineer_reviews()

    


if __name__ == "__main__":
    main()