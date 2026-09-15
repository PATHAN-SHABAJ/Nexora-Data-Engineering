from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


METRICS = [
    "offline_duration_sec",
    "disconnection_cnt",
    "reboot_cnt",
]

SCORED_WEEKS = [
    date(2026, 2, 2),
    date(2026, 2, 9),
    date(2026, 2, 16),
    date(2026, 2, 23),
    date(2026, 3, 2),
    date(2026, 3, 9),
    date(2026, 3, 16),
    date(2026, 3, 23),
]

BASELINE_DAYS = 28
RECENT_DAYS = 7
SIGMA = 3.0
TOP_N = 15

OUTPUT_COLUMNS = [
    "week_start",
    "rank",
    "gateway_id",
    "score",
    "reason",
]


def load_telemetry(data_dir):
    telemetry_path = data_dir / "cleaned" / "telemetry_clean.parquet"

    if not telemetry_path.exists():
        raise FileNotFoundError(
            f"Cleaned telemetry file not found: {telemetry_path}"
        )

    columns = ["gateway_id", "ts_utc", *METRICS]

    telemetry = pd.read_parquet(
        telemetry_path,
        columns=columns,
    )

    telemetry["ts"] = pd.to_datetime(
        telemetry["ts_utc"],
        utc=True,
        errors="coerce",
    )

    telemetry = telemetry.drop(columns="ts_utc")
    telemetry = telemetry.dropna(subset=["gateway_id", "ts"])

    telemetry = telemetry.drop_duplicates(
        subset=["gateway_id", "ts"]
    )

    telemetry = telemetry.sort_values(
        ["gateway_id", "ts"],
        kind="stable",
    ).reset_index(drop=True)

    return telemetry


def calculate_week_score(telemetry, week_start):
    week_end = pd.Timestamp(week_start, tz="UTC")
    baseline_start = week_end - timedelta(days=BASELINE_DAYS)
    recent_start = week_end - timedelta(days=RECENT_DAYS)

    baseline_mask = (
        (telemetry["ts"] >= baseline_start)
        & (telemetry["ts"] < week_end)
    )

    baseline = telemetry.loc[baseline_mask]

    if baseline.empty:
        return pd.DataFrame(
            columns=["gateway_id", "score", "worst_metric"]
        )

    recent = baseline.loc[
        baseline["ts"] >= recent_start
    ].copy()

    if recent.empty:
        return pd.DataFrame(
            columns=["gateway_id", "score", "worst_metric"]
        )

    statistics = (
        baseline.groupby("gateway_id", sort=False)[METRICS]
        .agg(["mean", "std"])
    )

    scores = pd.DataFrame(
        index=recent.index,
        columns=METRICS,
        dtype=bool,
    )

    for metric in METRICS:
        means = recent["gateway_id"].map(
            statistics[(metric, "mean")]
        )

        stds = recent["gateway_id"].map(
            statistics[(metric, "std")]
        )

        threshold = means + SIGMA * stds.replace(0, np.nan)

        scores[metric] = (
            recent[metric] > threshold
        ).fillna(False)

    recent["score"] = scores.sum(axis=1)

    hit_values = scores.to_numpy()

    first_hit = np.argmax(hit_values, axis=1)

    has_hit = scores.any(axis=1).to_numpy()

    worst_metrics = np.where(
        has_hit,
        np.asarray(METRICS, dtype=object)[first_hit],
        "",
    )

    recent["worst_metric"] = worst_metrics

    ranking = (
        recent.groupby("gateway_id", sort=False)
        .agg(
            score=("score", "sum"),
            worst_metric=("worst_metric", "first"),
        )
        .reset_index()
    )

    return ranking.sort_values(
        ["score", "gateway_id"],
        ascending=[False, True],
        kind="stable",
    )


def build_reason(score, metric):
    if metric:
        return (
            f"{score} anomalous hour(s) detected in the previous 7 days "
            f"based on {metric} exceeding the gateway's 28-day baseline."
        )

    return "Gateway ranked using recent telemetry anomaly score."


def build_predictions(telemetry):
    results = []

    for week_start in SCORED_WEEKS:
        ranking = calculate_week_score(
            telemetry,
            week_start,
        ).head(TOP_N)

        for rank, row in enumerate(
            ranking.itertuples(index=False),
            start=1,
        ):
            score = int(row.score)

            results.append(
                {
                    "week_start": week_start.isoformat(),
                    "rank": rank,
                    "gateway_id": row.gateway_id,
                    "score": float(score),
                    "reason": build_reason(
                        score,
                        row.worst_metric,
                    )[:300],
                }
            )

    return pd.DataFrame(
        results,
        columns=OUTPUT_COLUMNS,
    )


def main():
    project_dir = Path(__file__).resolve().parent.parent
    data_dir = project_dir / "data"

    print("Loading telemetry...")

    telemetry = load_telemetry(data_dir)

    print(f"Telemetry rows: {len(telemetry)}")
    print(f"Unique gateways: {telemetry['gateway_id'].nunique()}")

    predictions = build_predictions(telemetry)

    predictions.to_csv(
        project_dir / "predictions.csv",
        index=False,
    )

    predictions.to_csv(
        project_dir / "gateway_ranking.csv",
        index=False,
    )

    print(f"Prediction rows: {len(predictions)}")
    print(f"Weeks scored: {predictions['week_start'].nunique()}")

    print(
        predictions.head(TOP_N).to_string(index=False)
    )

    print("Saved: predictions.csv")
    print("Saved: gateway_ranking.csv")


if __name__ == "__main__":
    main()