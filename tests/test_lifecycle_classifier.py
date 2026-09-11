import unittest

import numpy as np
import pandas as pd

from src.lifecycle_classifier import classify_lifecycle
from src.trend_analytics import _align_forecast_with_lifecycle


def classify(values: np.ndarray | list[float]):
    return classify_lifecycle(pd.DataFrame({"total": values}))


class LifecycleClassifierTests(unittest.TestCase):
    def test_low_new_signal_is_nascent(self):
        values = np.r_[np.zeros(266), [1.0, 3.0, 6.0]]
        result = classify(values)
        self.assertEqual(result.stage, "Naciente")

    def test_recent_acceleration_is_emerging(self):
        values = np.r_[np.zeros(249), np.linspace(0.0, 35.0, 20)]
        result = classify(values)
        self.assertEqual(result.stage, "Emergente")

    def test_sustained_rise_is_growth(self):
        result = classify(np.linspace(5.0, 90.0, 269))
        self.assertEqual(result.stage, "Crecimiento")

    def test_recent_high_plateau_is_massive(self):
        values = np.r_[np.linspace(2.0, 95.0, 249), np.full(20, 95.0)]
        result = classify(values)
        self.assertEqual(result.stage, "Masiva")

    def test_long_high_plateau_is_saturated(self):
        values = np.r_[np.linspace(5.0, 80.0, 100), np.full(169, 78.0)]
        result = classify(values)
        self.assertEqual(result.stage, "Saturada")

    def test_drop_from_100_to_9_is_declining(self):
        values = np.r_[
            np.full(120, 5.0),
            np.linspace(5.0, 100.0, 40),
            np.linspace(100.0, 9.0, 109),
        ]
        result = classify(values)
        self.assertEqual(result.stage, "En declive")
        self.assertLess(result.metrics["current_to_peak"], 0.35)
        self.assertGreater(result.metrics["peak_age_points"], 3)

    def test_past_spike_cannot_return_to_nascent(self):
        values = np.r_[np.zeros(130), [100.0], np.zeros(138)]
        result = classify(values)
        self.assertEqual(result.stage, "En declive")

    def test_declining_curve_does_not_project_an_unsupported_rebound(self):
        series = pd.Series(
            [100.0, 60.0, 25.0, 9.0],
            index=pd.date_range("2026-09-08", periods=4, freq="D"),
        )
        forecast = {
            "label": "Modelo de prueba",
            "hasSeasonality": False,
            "timeline": [
                {"forecast": 20.0, "lower": 8.0, "upper": 30.0},
                {"forecast": 35.0, "lower": 12.0, "upper": 50.0},
            ],
        }
        adjusted = _align_forecast_with_lifecycle(
            forecast,
            series,
            {
                "stage": "En declive",
                "metrics": {"current_to_peak": 0.09, "momentum_30": -0.8},
            },
        )
        self.assertEqual(
            [point["forecast"] for point in adjusted["timeline"]],
            [9.0, 9.0],
        )


if __name__ == "__main__":
    unittest.main()
