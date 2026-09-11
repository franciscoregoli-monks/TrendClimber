import unittest

import pandas as pd

from src.lifecycle_classifier import classify_lifecycle_windows
from src.trend_analytics import _enforce_stage_consistency


class LifecycleWindowTests(unittest.TestCase):
    def test_each_window_is_classified_from_its_own_curve(self):
        index_year = pd.date_range("2025-12-17", periods=269, freq="D")
        year_values = [0.0] * 269
        year_values[-19] = 100.0

        index_30 = index_year[-30:]
        days30_values = [0.0] * 30
        days30_values[11] = 100.0

        index_7 = index_year[-7:]
        days7_values = [100.0, 30.0, 5.0, 0.0, 0.0, 0.0, 0.0]

        results = classify_lifecycle_windows(
            {
                "year": pd.Series(year_values, index=index_year),
                "days30": pd.Series(days30_values, index=index_30),
                "days7": pd.Series(days7_values, index=index_7),
            }
        )

        self.assertEqual(results["days30"].stage, "En declive")
        self.assertEqual(results["days7"].stage, "En declive")
        self.assertEqual(results["days30"].metrics["days_analyzed"], 30)
        self.assertEqual(results["days7"].metrics["days_analyzed"], 7)
        self.assertNotEqual(
            results["year"].metrics["peak_position"],
            results["days30"].metrics["peak_position"],
        )

    def test_declining_forecast_cannot_rebound_above_last_observation(self):
        series = pd.Series(
            [0.0, 100.0, 25.0, 2.0, 0.0, 0.0, 0.0],
            index=pd.date_range("2026-09-05", periods=7, freq="D"),
        )
        forecast = {
            "label": "Test forecast",
            "timeline": [
                {
                    "date": "2026-09-12",
                    "forecast": 20.0,
                    "lower": 5.0,
                    "upper": 30.0,
                    "isFuture": True,
                },
                {
                    "date": "2026-09-13",
                    "forecast": 40.0,
                    "lower": 10.0,
                    "upper": 50.0,
                    "isFuture": True,
                },
            ],
        }

        adjusted = _enforce_stage_consistency(
            forecast,
            series,
            {"stage": "En declive"},
        )

        self.assertIsNotNone(adjusted)
        self.assertEqual(
            [point["forecast"] for point in adjusted["timeline"]],
            [0.0, 0.0],
        )
        self.assertIn("ajustada al declive observado", adjusted["label"])


if __name__ == "__main__":
    unittest.main()
