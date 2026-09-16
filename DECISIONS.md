# Implementation Decisions

I selected **Data Engineering** as my focus area for the LPDG Innovation Hub Selection Challenge 2026.

I decided to keep the solution as a small, reproducible pipeline instead of putting all the processing into one script. The main flow is data loading, cleaning, feature engineering, target creation, feature analysis, weekly scoring, and validation.

For data loading, I kept the logic in `src/data_loader.py`. It handles the gateway master data, meter read data, field visit data, engineer review data, and the monthly telemetry Parquet files. The telemetry files are read from the monthly partition structure and combined when needed.

I kept data cleaning separate in `src/clean_data.py`. This makes it easier to prepare the input data before feature engineering and scoring. The cleaned files are generated locally during execution.

I also kept the data quality checks separate in `src/data_quality.py`. The purpose is to check the processed data before it is used by the later stages instead of mixing validation logic into every processing script.

For feature engineering, I used `src/feature_engineering.py` to convert the telemetry information into gateway-level features. The features include reboot-related information, disconnection counts, offline duration, average offline duration, maximum offline duration, and reboot duration. Gateway-level aggregation was used because the final scoring is done at the gateway level.

I kept target creation separate in `src/create_target.py`. The target information is created for the analysis workflow. During development, the generated training data contained 120 records, with 60 records having target `0` and 60 records having target `1`. I did not train a new machine learning model because I selected the Data Engineering track and the challenge provides a working baseline.

For feature analysis, I used `src/analyze_features.py`. This compares numerical features between the available target groups using their mean values, differences, and percentage differences. This helped me inspect the behaviour of the features produced by the pipeline.

For the final scoring, I used `src/scoring.py`. The scoring compares recent gateway behaviour with a historical baseline. I used a 28-day historical period and a previous 7-day period for recent observations, with a 3-sigma threshold. The scoring uses offline duration, disconnection count, and reboot count. Gateways are then ranked based on the number of anomalous observations, with the top 15 gateways retained for each scoring week.

The final output is `predictions.csv`. It contains 8 scoring weeks, 15 ranked gateways per week, and 120 rows in total. The output columns are `week_start`, `rank`, `gateway_id`, `score`, and `reason`. The generated output covers the period from `2026-02-02` to `2026-03-23`.

I used `src/pipeline.py` to keep the main processing stages in one execution flow. It runs data cleaning, feature engineering, target creation, feature analysis, and scoring in sequence.

Before submission, I checked the prediction file using the provided validation script:

```text
python validate_submission.py predictions.csv