from pathlib import Path
import re
import unicodedata

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

TELEMETRY_DIR = DATA_DIR / "cleaned"
RAW_TELEMETRY_DIR = DATA_DIR / "telemetry"
FIELD_VISITS_PATH = DATA_DIR / "cleaned" / "field_visits_clean.csv"
GATEWAY_MASTER_PATH = DATA_DIR / "gateway_master.csv"
OUTPUT_PATH = BASE_DIR / "features.csv"

METER_READS_PATHS = [
    DATA_DIR / "meter_reads.csv",
    DATA_DIR / "meter_reads.parquet",
    DATA_DIR / "cleaned" / "meter_reads_clean.csv",
    DATA_DIR / "cleaned" / "meter_reads_clean.parquet",
]

TELEMETRY_NUMERIC_COLUMNS = [
    "reboot_cnt",
    "disconnection_cnt",
    "offline_duration_sec",
    "reboot_duration_sec",
]

FEATURE_NUMERIC_COLUMNS = [
    "total_reboots",
    "total_disconnections",
    "total_offline_seconds",
    "avg_offline_seconds",
    "max_offline_seconds",
    "total_reboot_duration",
    "avg_reboot_duration",
    "total_meters_expected",
    "total_meters_read",
    "avg_read_rate",
    "min_read_rate",
    "total_visits",
    "problems_fixed",
    "no_problem_found",
    "total_technician_hours",
    "avg_technician_hours",
    "parts_replaced_count",
]


def clean_gateway_id(series):
    return (
        series.astype(str)
        .str.replace(":", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.upper()
        .str.strip()
    )


def normalize_text(series):
    series = series.fillna("").astype(str).str.strip().str.lower()

    series = series.map(
        lambda value: unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )

    return series.str.replace(r"\s+", " ", regex=True)


def read_data(path):
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)

    return pd.read_csv(path, encoding="utf-8-sig")


def load_telemetry():
    cleaned_path = TELEMETRY_DIR / "telemetry_clean.parquet"

    if cleaned_path.exists():
        print("Loading cleaned telemetry...")
        telemetry = pd.read_parquet(cleaned_path)
    else:
        print("Loading telemetry partitions...")

        files = sorted(
            RAW_TELEMETRY_DIR.glob("month=*/part-*.parquet")
        )

        if not files:
            raise FileNotFoundError(
                f"No telemetry parquet files found in {RAW_TELEMETRY_DIR}"
            )

        telemetry = pd.concat(
            (pd.read_parquet(file) for file in files),
            ignore_index=True,
        )

    required_columns = {"gateway_id"}

    missing_columns = required_columns - set(telemetry.columns)

    if missing_columns:
        raise ValueError(
            f"Telemetry is missing columns: {sorted(missing_columns)}"
        )

    telemetry["gateway_id"] = clean_gateway_id(
        telemetry["gateway_id"]
    )

    print(f"Telemetry rows: {len(telemetry)}")
    print(
        f"Telemetry gateways: "
        f"{telemetry['gateway_id'].nunique()}"
    )

    return telemetry


def build_telemetry_features(telemetry):
    for column in TELEMETRY_NUMERIC_COLUMNS:
        if column not in telemetry.columns:
            telemetry[column] = 0

        telemetry[column] = (
            pd.to_numeric(
                telemetry[column],
                errors="coerce",
            )
            .fillna(0)
        )

    features = (
        telemetry.groupby("gateway_id")
        .agg(
            total_reboots=("reboot_cnt", "sum"),
            total_disconnections=("disconnection_cnt", "sum"),
            total_offline_seconds=("offline_duration_sec", "sum"),
            avg_offline_seconds=("offline_duration_sec", "mean"),
            max_offline_seconds=("offline_duration_sec", "max"),
            total_reboot_duration=("reboot_duration_sec", "sum"),
            avg_reboot_duration=("reboot_duration_sec", "mean"),
        )
        .reset_index()
    )

    print("Telemetry features:")
    print(features.head())
    print(f"Shape: {features.shape}")

    return features


def find_meter_reads():
    return next(
        (path for path in METER_READS_PATHS if path.exists()),
        None,
    )


def load_meter_reads():
    path = find_meter_reads()

    if path is None:
        print("Meter reads file not found.")
        return None

    print(f"Loading meter reads: {path}")

    meter = read_data(path)

    meter["gateway_id"] = clean_gateway_id(
        meter["gateway_id"]
    )

    expected_column = next(
        (
            column
            for column in [
                "meters_expected",
                "meter_expected",
                "n_meters_expected",
                "expected",
            ]
            if column in meter.columns
        ),
        None,
    )

    read_column = next(
        (
            column
            for column in [
                "meters_read",
                "meter_read",
                "n_meters_read",
                "read",
            ]
            if column in meter.columns
        ),
        None,
    )

    if expected_column is None or read_column is None:
        print("Meter reads columns not recognized.")
        return None

    meter[expected_column] = (
        pd.to_numeric(
            meter[expected_column],
            errors="coerce",
        )
        .fillna(0)
    )

    meter[read_column] = (
        pd.to_numeric(
            meter[read_column],
            errors="coerce",
        )
        .fillna(0)
    )

    denominator = meter[expected_column].replace(0, pd.NA)

    meter["read_rate"] = (
        meter[read_column]
        .div(denominator)
        .fillna(0)
    )

    return (
        meter.groupby("gateway_id")
        .agg(
            total_meters_expected=(
                expected_column,
                "sum",
            ),
            total_meters_read=(
                read_column,
                "sum",
            ),
            avg_read_rate=(
                "read_rate",
                "mean",
            ),
            min_read_rate=(
                "read_rate",
                "min",
            ),
        )
        .reset_index()
    )


def load_field_visits():
    if not FIELD_VISITS_PATH.exists():
        print("Field visits file not found.")
        return None

    print("Loading field visits...")

    visits = pd.read_csv(
        FIELD_VISITS_PATH,
        encoding="utf-8-sig",
    )

    visits["gateway_id"] = clean_gateway_id(
        visits["gateway_id"]
    )

    visits["outcome_normalized"] = normalize_text(
        visits["outcome"]
    )

    visits["parts_normalized"] = normalize_text(
        visits["parts_replaced"]
    )

    visits["technician_hours"] = (
        pd.to_numeric(
            visits["technician_hours"],
            errors="coerce",
        )
        .fillna(0)
    )

    visits["problems_fixed_flag"] = (
        visits["outcome_normalized"]
        .isin(
            {
                "fehler behoben",
                "problem behoben",
                "problem fixed",
                "fixed",
            }
        )
        .astype(int)
    )

    visits["no_problem_found_flag"] = (
        visits["outcome_normalized"]
        .isin(
            {
                "kein fehler gefunden",
                "kein fehler",
                "no problem found",
                "no fault found",
            }
        )
        .astype(int)
    )

    visits["parts_replaced_flag"] = (
        visits["parts_normalized"].ne("")
        & ~visits["parts_normalized"].isin(
            {
                "nan",
                "none",
                "na",
                "n a",
            }
        )
    ).astype(int)

    features = (
        visits.groupby("gateway_id")
        .agg(
            total_visits=("visit_id", "count"),
            problems_fixed=("problems_fixed_flag", "sum"),
            no_problem_found=("no_problem_found_flag", "sum"),
            total_technician_hours=(
                "technician_hours",
                "sum",
            ),
            avg_technician_hours=(
                "technician_hours",
                "mean",
            ),
            parts_replaced_count=(
                "parts_replaced_flag",
                "sum",
            ),
        )
        .reset_index()
    )

    print("Visit features:")
    print(features.head())
    print(f"Shape: {features.shape}")

    return features


def load_gateway_master():
    if not GATEWAY_MASTER_PATH.exists():
        raise FileNotFoundError(
            f"Gateway master not found: {GATEWAY_MASTER_PATH}"
        )

    print(
        f"Loading gateway master: "
        f"{GATEWAY_MASTER_PATH}"
    )

    for encoding in ["utf-8-sig", "cp1252", "latin1"]:
        try:
            master = pd.read_csv(
                GATEWAY_MASTER_PATH,
                encoding=encoding,
            )
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(
            "Unable to decode gateway_master.csv"
        )

    master["gateway_id"] = clean_gateway_id(
        master["gateway_id"]
    )

    return master


def fill_numeric_features(dataframe):
    columns = [
        column
        for column in FEATURE_NUMERIC_COLUMNS
        if column in dataframe.columns
    ]

    dataframe[columns] = (
        dataframe[columns]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
    )

    return dataframe


def main():
    telemetry = load_telemetry()
    telemetry_features = build_telemetry_features(
        telemetry
    )

    meter_features = load_meter_reads()
    visit_features = load_field_visits()
    gateway_master = load_gateway_master()

    final = gateway_master.copy()

    final["gateway_id"] = clean_gateway_id(
        final["gateway_id"]
    )

    final = final.merge(
        telemetry_features,
        on="gateway_id",
        how="left",
    )

    if meter_features is not None:
        final = final.merge(
            meter_features,
            on="gateway_id",
            how="left",
        )

    if visit_features is not None:
        final = final.merge(
            visit_features,
            on="gateway_id",
            how="left",
        )

    final = fill_numeric_features(final)

    final = (
        final.drop_duplicates(
            subset="gateway_id",
            keep="first",
        )
        .reset_index(drop=True)
    )

    print("Final features:")
    print(final.head())
    print(f"Shape: {final.shape}")

    final.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()