import unittest

import numpy as np
import pandas as pd

from src.lifecycle_classifier import classify_lifecycle
from src.lifecycle_curve_models import classify_product_curve_from_series
from src.trend_analytics import _align_forecast_with_lifecycle

YEAR_POINTS = 269


def classify(values: np.ndarray | list[float]):
    return classify_lifecycle(pd.DataFrame({"total": values}))


def fad_curve() -> np.ndarray:
    """Spike that peaked three days ago and already collapsed (screenshot case)."""
    return np.r_[np.zeros(YEAR_POINTS - 7), [0.0, 13.0, 78.0, 100.0, 32.0, 13.0, 8.0]]


class LifecycleClassifierTests(unittest.TestCase):
    def test_low_absolute_signal_is_nascent(self):
        values = np.r_[np.zeros(YEAR_POINTS - 3), [1.0, 3.0, 6.0]]
        self.assertEqual(classify(values).stage, "Naciente")

    def test_recent_acceleration_is_emerging(self):
        values = np.r_[np.zeros(YEAR_POINTS - 20), np.linspace(0.0, 35.0, 20)]
        self.assertEqual(classify(values).stage, "Emergente")

    def test_sustained_broad_rise_is_growth(self):
        self.assertEqual(classify(np.linspace(5.0, 90.0, YEAR_POINTS)).stage, "Crecimiento")

    def test_recent_high_plateau_is_massive(self):
        values = np.r_[np.linspace(2.0, 95.0, YEAR_POINTS - 20), np.full(20, 95.0)]
        self.assertEqual(classify(values).stage, "Masiva")

    def test_long_high_plateau_is_saturated(self):
        values = np.r_[np.linspace(5.0, 80.0, 100), np.full(YEAR_POINTS - 100, 78.0)]
        self.assertEqual(classify(values).stage, "Saturada")

    def test_drop_from_100_to_9_is_declining(self):
        values = np.r_[
            np.full(120, 5.0),
            np.linspace(5.0, 100.0, 40),
            np.linspace(100.0, 9.0, YEAR_POINTS - 160),
        ]
        result = classify(values)
        self.assertEqual(result.stage, "En declive")
        self.assertLess(result.metrics["current_to_peak"], 0.35)

    def test_past_spike_cannot_return_to_nascent(self):
        values = np.r_[np.zeros(130), [100.0], np.zeros(YEAR_POINTS - 131)]
        self.assertEqual(classify(values).stage, "En declive")

    def test_collapsed_fad_is_declining_despite_positive_30d_slope(self):
        result = classify(fad_curve())
        self.assertEqual(result.stage, "En declive")
        # The 30-day slope is still positive because the spike sits inside it,
        # so the decision must come from the short-horizon signals.
        self.assertGreater(result.metrics["momentum_30"], 0)
        self.assertLess(result.metrics["acceleration_now"], 0)

    def test_two_day_old_peak_is_not_smeared_into_the_now_window(self):
        """Centered smoothing used to leak the peak into "now" and read as rising."""
        values = np.r_[np.zeros(YEAR_POINTS - 7), [1.0, 1.0, 1.0, 6.0, 100.0, 25.0, 2.0]]
        result = classify(values)
        self.assertEqual(result.stage, "En declive")
        # Today is 2/100 of the peak; the level must reflect that, not ~0.64.
        self.assertLess(result.metrics["current_to_peak"], 0.2)
        self.assertGreater(result.metrics["peak_drawdown"], 0.7)

    def test_rising_branch_is_gated_by_drawdown(self):
        """A collapsed spike keeps a positive 30d slope but must not read as rising."""
        result = classify(np.r_[np.zeros(YEAR_POINTS - 7), [1.0, 1.0, 1.0, 6.0, 100.0, 25.0, 2.0]])
        self.assertGreater(result.metrics["momentum_30"], 0)
        self.assertNotIn(result.stage, {"Emergente", "Crecimiento"})

    def test_direction_never_contradicts_the_stage(self):
        """Exhaustive guard: "En declive · Alcista" must be unrepresentable."""
        rng = np.random.default_rng(20260921)
        curves: list[np.ndarray] = [
            # Collapsed spikes that rebound off a near-zero base: the case where
            # relative acceleration explodes (+800%) at 7% of the peak.
            np.r_[np.zeros(250), [5, 40, 100, 60, 20, 6, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 6, 9]],
            np.r_[np.zeros(255), [10, 60, 100, 40, 10, 3, 1, 1, 1, 1, 2, 8, 20, 18]],
            np.r_[np.zeros(YEAR_POINTS - 7), [1.0, 1.0, 1.0, 6.0, 100.0, 25.0, 2.0]],
            np.linspace(5.0, 90.0, YEAR_POINTS),
            np.r_[np.linspace(20.0, 100.0, 180), np.linspace(100.0, 9.0, YEAR_POINTS - 180)],
            np.r_[np.linspace(2.0, 95.0, YEAR_POINTS - 20), np.full(20, 95.0)],
        ]
        for _ in range(200):
            base = rng.uniform(0, 8, YEAR_POINTS)
            peak_at = int(rng.integers(20, YEAR_POINTS - 2))
            base[peak_at] = 100.0
            width = int(rng.integers(1, 12))
            for offset in range(1, width):
                if peak_at + offset < YEAR_POINTS:
                    base[peak_at + offset] = 100.0 / (offset + 1)
            curves.append(base)

        for values in curves:
            result = classify(values)
            direction = result.metrics["momentum_direction"]
            self.assertIn(direction, {"bullish", "bearish", "flat"})
            if direction == "bullish":
                self.assertIn(
                    result.stage,
                    {"Emergente", "Crecimiento"},
                    f"{result.stage} no puede mostrarse como Alcista",
                )
            if result.stage in {"Emergente", "Crecimiento"}:
                self.assertEqual(direction, "bullish")

    def test_stage_and_product_curve_type_stay_coherent(self):
        values = fad_curve()
        result = classify(values)
        curve = classify_product_curve_from_series(
            pd.Series(values),
            stage=result.stage,
            metrics=result.metrics,
        )
        self.assertEqual(curve["curveType"], "fad")
        self.assertEqual(result.stage, "En declive")

    def test_declining_curve_does_not_project_a_rebound(self):
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
                "metrics": {
                    "current_to_peak": 0.09,
                    "momentum_7": -0.8,
                    "acceleration_now": -0.6,
                },
            },
        )
        self.assertEqual(
            [point["forecast"] for point in adjusted["timeline"]],
            [9.0, 9.0],
        )

    def test_recency_weighting_favours_the_short_horizon(self):
        """A year of high interest that just collapsed must read as declining."""
        values = np.r_[np.full(YEAR_POINTS - 5, 90.0), [60.0, 35.0, 15.0, 8.0, 5.0]]
        result = classify(values)
        self.assertEqual(result.stage, "En declive")
        self.assertLess(result.metrics["acceleration_now"], 0)


if __name__ == "__main__":
    unittest.main()
