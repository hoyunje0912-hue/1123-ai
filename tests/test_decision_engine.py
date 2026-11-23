import unittest
from dataclasses import replace
from pathlib import Path

from decision_engine import ACTIVITIES, PREFERENCES, Weather, evaluate
from outfit_assets import ACCESSORIES, OUTFITS


PROJECT = Path(__file__).resolve().parents[1]
MILD = Weather(
    temperature=24, apparent_temperature=24, humidity=67, wind_speed=6,
    weather_code=1, temperature_max=27, temperature_min=22,
    rain_probability=10, uv_max=2, current_time="2026-11-23T09:15", date="2026-11-23",
)


class DecisionTests(unittest.TestCase):
    def test_four_outfit_levels_and_local_paths(self):
        cases = (
            (MILD, "mild", 93),
            (replace(MILD, apparent_temperature=31), "hot", None),
            (replace(MILD, apparent_temperature=20), "layered", None),
            (replace(MILD, apparent_temperature=15), "cold", None),
        )
        for weather, outfit, score in cases:
            with self.subTest(outfit=outfit):
                result = evaluate(weather, "walking", "normal")
                self.assertEqual(result.outfit, OUTFITS[outfit])
                self.assertTrue((PROJECT / "static" / result.outfit.path).is_file())
                if score is not None:
                    self.assertEqual(result.score, score)

    def test_personal_preferences_cross_outfit_thresholds(self):
        almost_hot = replace(MILD, apparent_temperature=27)
        self.assertEqual(evaluate(almost_hot, "outdoor", "normal").outfit, OUTFITS["mild"])
        self.assertEqual(evaluate(almost_hot, "outdoor", "hot").adjusted_temperature, 29)
        self.assertEqual(evaluate(almost_hot, "outdoor", "hot").outfit, OUTFITS["hot"])

        borderline = replace(MILD, apparent_temperature=18)
        self.assertEqual(evaluate(borderline, "walking", "cold").adjusted_temperature, 16)
        self.assertEqual(evaluate(borderline, "walking", "cold").outfit, OUTFITS["cold"])

    def test_rain_and_wind_affect_scooter_score_and_gear(self):
        rainy = replace(MILD, weather_code=63, rain_probability=90, wind_speed=22)
        scooter = evaluate(rainy, "scooter", "normal")
        walking = evaluate(rainy, "walking", "normal")
        self.assertLess(scooter.score, walking.score)
        self.assertIn(ACCESSORIES["raincoat"], scooter.accessories)
        self.assertIn(ACCESSORIES["umbrella"], walking.accessories)

        gusty = evaluate(replace(rainy, wind_speed=35), "walking", "normal")
        self.assertIn("撐傘容易開花", gusty.wind_tip)
        self.assertIn(ACCESSORIES["windbreaker"], gusty.accessories)
        self.assertIn(ACCESSORIES["raincoat"], gusty.accessories)
        self.assertNotIn(ACCESSORIES["umbrella"], gusty.accessories)

    def test_current_rain_does_not_require_high_daily_probability(self):
        rainy = replace(MILD, weather_code=80, rain_probability=20)
        self.assertIn(ACCESSORIES["raincoat"], evaluate(rainy, "scooter", "normal").accessories)

    def test_spread_and_uv_boundaries(self):
        result = evaluate(replace(MILD, temperature_max=29, uv_max=3), "outdoor", "normal")
        self.assertEqual(result.spread, 7)
        self.assertEqual(result.outfit, OUTFITS["layered"])
        self.assertIn("洋蔥式", result.layer_tip)
        self.assertIn(ACCESSORIES["jacket"], result.accessories)
        self.assertIn(ACCESSORIES["sun"], result.accessories)

    def test_extremes_and_accessory_paths_for_all_choices(self):
        extreme = replace(
            MILD, apparent_temperature=44, wind_speed=64,
            weather_code=95, rain_probability=100, uv_max=12,
        )
        for activity in ACTIVITIES:
            for preference in PREFERENCES:
                with self.subTest(activity=activity, preference=preference):
                    result = evaluate(extreme, activity, preference)
                    self.assertEqual(result.score, 0)
                    self.assertEqual(result.level_style, "red")
                    self.assertIn(len(result.accessories), (2, 3))
                    self.assertEqual(len(set(result.accessories)), len(result.accessories))
                    for item in result.accessories:
                        self.assertTrue((PROJECT / "static" / item.path).is_file())


if __name__ == "__main__":
    unittest.main()
