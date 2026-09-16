# Implementation Decisions

This document explains the main implementation decisions made for my Data Engineering solution for the LPDG Innovation Hub Selection Challenge 2026.

## 1. Focus Area

I selected **Data Engineering** as my focus area.

The implementation focuses on building a reproducible data pipeline for the provided gateway telemetry and related operational data.

The main work covers:

- Data loading
- Data cleaning
- Data quality checks
- Feature engineering
- Gateway-level aggregation
- Weekly anomaly scoring
- Prediction generation
- Validation and testing

I did not build a new machine learning model because the challenge provides a working baseline and states that a new model is not required for the Data Engineering track.

## 2. Data Loading

Data loading is separated into `src/data_loader.py`.

The loader handles the different input sources used by the pipeline:

- Gateway master data
- Meter read data
- Field visit data
- Engineer review data
- Monthly telemetry Parquet files

Telemetry is stored in monthly partitions and loaded and combined when required by the pipeline.

Keeping the loading logic separate makes the processing stages easier to maintain.

## 3. Data Cleaning

Data cleaning is implemented in `src/clean_data.py`.

The cleaning stage prepares the input data before feature engineering and scoring.

Cleaned files are generated locally under `data/cleaned/`.

The challenge data itself is not included in this repository.

## 4. Data Quality

Data quality checks are implemented in `src/data_quality.py`.

The checks are used to identify issues in the processed data before it is used by later pipeline stages.

This keeps data validation separate from the feature engineering and scoring logic.

## 5. Feature Engineering

Gateway-level features are created in `src/feature_engineering.py`.

The telemetry data is aggregated to the gateway level so that the scoring process can work with meaningful gateway-level measurements.

The generated features include measures related to:

- Reboots
- Disconnections
- Offline duration
- Average offline duration
- Maximum offline duration
- Reboot duration

## 6. Weekly Scoring

The weekly scoring logic is implemented in `src/scoring.py`.

The scoring process uses a historical baseline and a recent observation period to identify abnormal gateway behaviour.

The implementation uses:

- 28-day historical baseline
- Previous 7 days as the recent period
- 3-sigma anomaly threshold
- Offline duration
- Disconnection count
- Reboot count

Gateways are ranked based on the number of anomalous observations detected during the recent period.

The top 15 gateways are retained for each scoring week.

## 7. Prediction Output

The scoring process generates `predictions.csv`.

The validated output contains:

- 8 scoring weeks
- 15 ranked gateways per week
- 120 total rows

The columns are:

- `week_start`
- `rank`
- `gateway_id`
- `score`
- `reason`

The prediction file was checked using the provided validation script.

## 8. Pipeline Organization

The main pipeline is implemented in `src/pipeline.py`.

The processing stages are executed in sequence:

1. Data cleaning
2. Feature engineering
3. Target creation
4. Feature analysis
5. Weekly scoring

Keeping these stages separate makes the individual parts easier to inspect and modify.

## 9. Validation and Testing

The provided validation script was used to check the final prediction output.

The project test suite was also used during development.

The final prediction file passed validation:

```text
predictions.csv: OK
15 ranked gateways for each of 8 weeks
2026-02-02 to 2026-03-23