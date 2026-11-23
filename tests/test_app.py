import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from xml.etree import ElementTree

import requests

from app import CURRENT_FIELDS, DAILY_FIELDS, FORECAST_URL, app
from cities import CITIES
from outfit_assets import ACCESSORIES, OUTFITS


PROJECT = Path(__file__).resolve().parents[1]
FORM = {"city": "高雄市", "activity": "scooter", "preference": "hot"}


def forecast():
    return {
        "current": {
            "time": "2026-11-23T14:15",
            "temperature_2m": 29.5,
            "apparent_temperature": 29.1,
            "relative_humidity_2m": 78,
            "wind_speed_10m": 23.7,
            "weather_code": 61,
        },
        "daily": {
            "time": ["2026-11-23"],
            "temperature_2m_max": [30.2],
            "temperature_2m_min": [21.7],
            "precipitation_probability_max": [90],
            "uv_index_max": [5.0],
        },
    }


class FlaskTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch("app.requests.get")
    def test_homepage_shows_input_and_preview_without_calling_api(self, upstream):
        result = self.client.get("/")
        html = result.get_data(as_text=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn('action="/weather"', html)
        self.assertIn("台北市", html)
        self.assertIn("/static/images/outfits/mild.svg", html)
        self.assertNotIn("<progress", html)
        upstream.assert_not_called()

    @patch("app.requests.get")
    def test_weather_page_renders_result_and_passes_taiwan_parameters(self, upstream):
        upstream.return_value = Mock(status_code=200, **{"json.return_value": forecast()})
        result = self.client.post("/weather", data=FORM)
        html = result.get_data(as_text=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn("高雄市的出門建議", html)
        self.assertIn("<progress", html)
        self.assertIn("兩件式雨衣", html)
        self.assertIn("/static/images/outfits/hot.svg", html)
        self.assertIn('value="hot" selected', html)
        upstream.assert_called_once_with(
            FORECAST_URL,
            params={
                "latitude": CITIES["高雄市"][0],
                "longitude": CITIES["高雄市"][1],
                "current": CURRENT_FIELDS,
                "daily": DAILY_FIELDS,
                "timezone": "Asia/Taipei",
                "forecast_days": 1,
            },
            timeout=10,
        )

    @patch("app.requests.get")
    def test_invalid_form_never_calls_the_api(self, upstream):
        response = self.client.post("/weather", data={**FORM, "city": "無效縣市"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("請選擇有效的縣市", response.get_data(as_text=True))
        upstream.assert_not_called()

    @patch("app.requests.get")
    def test_timeout_and_connection_error_have_friendly_messages(self, upstream):
        cases = (
            (requests.Timeout("private traceback content"), 504, "回應逾時"),
            (requests.ConnectionError("private traceback content"), 502, "連不上天氣服務"),
        )
        for error, status, message in cases:
            with self.subTest(error=type(error).__name__):
                upstream.side_effect = error
                response = self.client.post("/weather", data=FORM)
                html = response.get_data(as_text=True)
                self.assertEqual(response.status_code, status)
                self.assertIn(message, html)
                self.assertNotIn("private traceback content", html)

    @patch("app.requests.get")
    def test_unexpected_upstream_responses_are_handled(self, upstream):
        missing = forecast()
        del missing["daily"]["uv_index_max"]
        nulls = forecast()
        nulls["daily"]["uv_index_max"] = [None]
        cases = (
            (Mock(status_code=429), "暫時無法提供資料"),
            (Mock(status_code=200, **{"json.side_effect": ValueError("invalid JSON")}), "資料不完整"),
            (Mock(status_code=200, **{"json.return_value": {"error": True}}), "資料不完整"),
            (Mock(status_code=200, **{"json.return_value": missing}), "資料不完整"),
            (Mock(status_code=200, **{"json.return_value": nulls}), "資料不完整"),
        )
        for response, message in cases:
            with self.subTest(message=message):
                upstream.return_value = response
                result = self.client.post("/weather", data=FORM)
                self.assertEqual(result.status_code, 502)
                self.assertIn(message, result.get_data(as_text=True))

    def test_flask_serves_all_assets_and_vercel_copies_match(self):
        paths = ["style.css"]
        paths.extend(asset.path for asset in (*OUTFITS.values(), *ACCESSORIES.values()))
        for path in paths:
            with self.subTest(path=path):
                source = (PROJECT / "static" / path).read_bytes()
                self.assertEqual(source, (PROJECT / "public" / "static" / path).read_bytes())
                with self.client.get(f"/static/{path}") as response:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.data, source)
                    if path.endswith(".svg"):
                        self.assertEqual(response.mimetype, "image/svg+xml")
                        self.assertEqual(ElementTree.fromstring(response.data).tag, "{http://www.w3.org/2000/svg}svg")


if __name__ == "__main__":
    unittest.main()
