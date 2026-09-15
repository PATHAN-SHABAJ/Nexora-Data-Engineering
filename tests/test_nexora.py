from pathlib import Path
import unittest

import pandas as pd


# Project paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CLEANED_DIR = DATA_DIR / "cleaned"

FEATURES_FILE = ROOT_DIR / "features.csv"
TRAINING_FILE = ROOT_DIR / "training_data.csv"
PREDICTIONS_FILE = ROOT_DIR / "predictions.csv"
RANKING_FILE = ROOT_DIR / "gateway_ranking.csv"

TELEMETRY_FILE = CLEANED_DIR / "telemetry_clean.parquet"
FIELD_VISITS_FILE = CLEANED_DIR / "field_visits_clean.csv"
REVIEWS_FILE = CLEANED_DIR / "engineer_reviews_clean.csv"


class TestNexoraPipeline(unittest.TestCase):
    """Validate the main outputs of the Nexora data pipeline."""

    def test_required_output_files_exist(self):
        """All expected pipeline output files should exist."""
        required_files = [
            FEATURES_FILE,
            TRAINING_FILE,
            PREDICTIONS_FILE,
            RANKING_FILE,
            TELEMETRY_FILE,
            FIELD_VISITS_FILE,
            REVIEWS_FILE,
        ]

        for file_path in required_files:
            with self.subTest(file=file_path.name):
                self.assertTrue(
                    file_path.exists(),
                    f"Missing file: {file_path}",
                )

    def test_cleaned_telemetry(self):
        """Check cleaned telemetry structure and data quality."""
        telemetry = pd.read_parquet(TELEMETRY_FILE)

        required_columns = [
            "gateway_id",
            "ts_utc",
            "reboot_cnt",
            "disconnection_cnt",
            "offline_duration_sec",
        ]

        for column in required_columns:
            self.assertIn(column, telemetry.columns)

        self.assertGreater(len(telemetry), 0)

        self.assertEqual(
            telemetry["gateway_id"].isna().sum(),
            0,
        )

        self.assertEqual(
            telemetry["ts_utc"].isna().sum(),
            0,
        )

        self.assertGreater(
            telemetry["gateway_id"].nunique(),
            0,
        )

        non_negative_columns = [
            "reboot_cnt",
            "disconnection_cnt",
            "offline_duration_sec",
        ]

        for column in non_negative_columns:
            with self.subTest(column=column):
                self.assertGreaterEqual(
                    telemetry[column].min(),
                    0,
                )

        duplicate_count = telemetry.duplicated(
            subset=["gateway_id", "ts_utc"],
        ).sum()

        self.assertEqual(
            duplicate_count,
            0,
            f"Duplicate gateway/timestamp records: {duplicate_count}",
        )

    def test_field_visits(self):
        """Check cleaned field visit data."""
        visits = pd.read_csv(FIELD_VISITS_FILE)

        required_columns = [
            "visit_id",
            "gateway_id",
            "requested_on",
            "visited_on",
            "technician_hours",
        ]

        for column in required_columns:
            self.assertIn(column, visits.columns)

        self.assertGreater(len(visits), 0)

        self.assertEqual(
            visits["visit_id"].duplicated().sum(),
            0,
        )

        self.assertGreater(
            visits["gateway_id"].nunique(),
            0,
        )

        self.assertGreaterEqual(
            visits["technician_hours"].min(),
            0,
        )

        requested_dates = pd.to_datetime(
            visits["requested_on"],
            errors="coerce",
        )

        visited_dates = pd.to_datetime(
            visits["visited_on"],
            errors="coerce",
        )

        self.assertEqual(
            requested_dates.isna().sum(),
            0,
        )

        self.assertEqual(
            visited_dates.isna().sum(),
            0,
        )

        self.assertTrue(
            (visited_dates >= requested_dates).all(),
        )

    def test_engineer_reviews(self):
        """Check cleaned engineer review data."""
        reviews = pd.read_csv(REVIEWS_FILE)

        self.assertGreater(len(reviews), 0)
        self.assertIn("gateway_id", reviews.columns)

        gateway_ids = reviews["gateway_id"].astype(str)

        self.assertTrue(
            gateway_ids.str.len().eq(12).all(),
        )

    def test_features(self):
        """Check feature engineering output."""
        features = pd.read_csv(FEATURES_FILE)

        required_columns = [
            "gateway_id",
            "total_reboots",
            "total_disconnections",
            "total_offline_seconds",
            "avg_offline_seconds",
            "max_offline_seconds",
            "total_reboot_duration",
            "avg_reboot_duration",
        ]

        for column in required_columns:
            self.assertIn(column, features.columns)

        self.assertGreater(len(features), 0)

        self.assertEqual(
            features["gateway_id"].duplicated().sum(),
            0,
        )

        numeric_columns = [
            "total_reboots",
            "total_disconnections",
            "total_offline_seconds",
            "avg_offline_seconds",
            "max_offline_seconds",
            "total_reboot_duration",
            "avg_reboot_duration",
        ]

        for column in numeric_columns:
            with self.subTest(column=column):
                self.assertTrue(
                    pd.api.types.is_numeric_dtype(
                        features[column]
                    )
                )

                self.assertTrue(
                    features[column].notna().all()
                )

                self.assertGreaterEqual(
                    features[column].min(),
                    0,
                )

    def test_training_data(self):
        """Check training data and binary target values."""
        training = pd.read_csv(TRAINING_FILE)

        self.assertGreater(len(training), 0)
        self.assertIn("target", training.columns)

        self.assertEqual(
            training["target"].isna().sum(),
            0,
        )

        self.assertTrue(
            set(training["target"].unique()).issubset({0, 1})
        )

        self.assertEqual(
            set(training["target"].unique()),
            {0, 1},
        )

    def test_prediction_format(self):
        """Check prediction output structure."""
        predictions = pd.read_csv(PREDICTIONS_FILE)

        required_columns = [
            "week_start",
            "rank",
            "gateway_id",
            "score",
            "reason",
        ]

        for column in required_columns:
            self.assertIn(column, predictions.columns)

        self.assertEqual(len(predictions), 120)
        self.assertEqual(predictions["week_start"].nunique(), 8)

        weekly_counts = predictions.groupby("week_start").size()

        self.assertTrue(
            (weekly_counts == 15).all()
        )

        self.assertTrue(
            predictions["rank"].between(1, 15).all()
        )

        self.assertTrue(
            pd.api.types.is_numeric_dtype(
                predictions["score"]
            )
        )

        self.assertTrue(
            predictions["gateway_id"].notna().all()
        )

        self.assertTrue(
            predictions["reason"].notna().all()
        )

    def test_prediction_ranks(self):
        """Every scoring week must contain ranks 1 through 15."""
        predictions = pd.read_csv(PREDICTIONS_FILE)

        expected_ranks = list(range(1, 16))

        for week, weekly_data in predictions.groupby("week_start"):
            with self.subTest(week=week):
                actual_ranks = sorted(
                    weekly_data["rank"].tolist()
                )

                self.assertEqual(
                    actual_ranks,
                    expected_ranks,
                    f"Invalid ranks for {week}",
                )

    def test_ranking_file(self):
        """Check gateway ranking output."""
        ranking = pd.read_csv(RANKING_FILE)

        self.assertGreater(len(ranking), 0)
        self.assertIn("gateway_id", ranking.columns)

        if "rank" in ranking.columns:
            self.assertTrue(
                pd.api.types.is_numeric_dtype(
                    ranking["rank"]
                )
            )

        if "score" in ranking.columns:
            self.assertTrue(
                pd.api.types.is_numeric_dtype(
                    ranking["score"]
                )
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)