# Implementation Decisions

This document records the main decisions I made while building my Data Engineering solution for the LPDG Innovation Hub Selection Challenge 2026.

## Focus Area

I selected **Data Engineering** for Part 2.

I selected this area because my work is mainly focused on the data pipeline: loading the different data sources, cleaning the data, checking data quality, creating gateway-level features, and producing the final weekly gateway ranking.

I did not build a new machine learning model because the challenge provides a working baseline and states that a new model is not required for the Data Engineering track.

## Decision 1 — Keep the data loading separate

I kept the data loading logic in `src/data_loader.py` instead of putting file loading code inside every processing script.

The alternative was to load the files directly inside each processing step.

I chose the separate loader because the project uses several input sources, including gateway master data, meter data, field visits, engineer reviews, and monthly telemetry files. Keeping this logic in one place makes the pipeline easier to maintain.

## Decision 2 — Keep the processing as separate stages

I divided the processing into separate scripts for cleaning, feature engineering, target creation, feature analysis, and scoring.

The alternative was to put the complete workflow into one large Python script.

I chose separate stages because each step has a different purpose and can be checked or modified independently.

The main scripts are:

- `clean_data.py`
- `feature_engineering.py`
- `create_target.py`
- `analyze_features.py`
- `scoring.py`

## Decision 3 — Aggregate telemetry at gateway level

I used gateway-level aggregation for the features used by the scoring process.

The alternative was to work directly with individual telemetry observations when producing the final ranking.

I chose gateway-level features because the final output is a ranking of gateways. This also makes the scoring process easier to interpret.

The features include measurements related to reboots, disconnections, offline duration, average offline duration, maximum offline duration, and reboot duration.

## Decision 4 — Use a historical 3-sigma baseline

For weekly scoring, I used a 28-day historical baseline and the previous 7 days as the recent period.

The anomaly threshold is based on 3 standard deviations from the historical behaviour.

The alternative was to use a fixed threshold for every gateway.

I chose the historical baseline because gateways can have different normal behaviour. Comparing recent behaviour with the gateway's own historical behaviour provides a more consistent basis for identifying unusual observations.

The scoring uses:

- `offline_duration_sec`
- `disconnection_cnt`
- `reboot_cnt`

## Decision 5 — Keep one pipeline entry point

I created `src/pipeline.py` to run the main processing stages in sequence.

The alternative was to run each Python script manually from the terminal.

I chose a single pipeline entry point so that the main processing workflow can be reproduced with one command.

The pipeline runs:

1. Data cleaning
2. Feature engineering
3. Target creation
4. Feature analysis
5. Weekly scoring

## Final Output

The final output is `predictions.csv`.

It contains:

- 8 scoring weeks
- 15 ranked gateways for each week
- 120 total rows

The output columns are:

- `week_start`
- `rank`
- `gateway_id`
- `score`
- `reason`

The final file was checked using the provided validation script.

Validation result:

```text
predictions.csv: OK
15 ranked gateways for each of 8 weeks
2026-02-02 to 2026-03-23