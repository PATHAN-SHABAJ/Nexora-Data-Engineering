from pathlib import Path
import pandas as pd


def load_gateway_master(data_dir):
    return pd.read_csv(data_dir / "gateway_master.csv", encoding="latin1")


def load_meter_reads(data_dir):
    return pd.read_csv(data_dir / "meter_read_success.csv")


def load_field_visits(data_dir):
    return pd.read_csv(data_dir / "field_visits.csv")


def load_engineer_reviews(data_dir):
    return pd.read_excel(data_dir / "engineer_review_2026-02.xlsx")


def load_telemetry(data_dir):
    telemetry_path = data_dir / "telemetry"

    files = sorted(telemetry_path.glob("month=*/part-*.parquet"))

    if not files:
        raise FileNotFoundError("No telemetry parquet files found")

    frames = []

    for file in files:
        print(f"Loading: {file}")

        df = pd.read_parquet(file)
        frames.append(df)

    telemetry = pd.concat(frames, ignore_index=True)

    return telemetry


def load_all(data_dir):
    data_dir = Path(data_dir)

    return {
        "gateway_master": load_gateway_master(data_dir),
        "meter_reads": load_meter_reads(data_dir),
        "field_visits": load_field_visits(data_dir),
        "engineer_reviews": load_engineer_reviews(data_dir),
        "telemetry": load_telemetry(data_dir),
    }
    
    
if __name__ == "__main__":
    data = load_all("data")

    for name, df in data.items():
        print(f"{name}: {df.shape}")