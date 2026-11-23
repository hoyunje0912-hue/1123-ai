from datetime import date, datetime
from math import isfinite

import requests
from flask import Flask, redirect, render_template, request, url_for

from cities import CITIES
from decision_engine import ACTIVITIES, PREFERENCES, Weather, evaluate
from outfit_assets import OUTFITS

app = Flask(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CURRENT_FIELDS = "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code"
DAILY_FIELDS = "temperature_2m_max,temperature_2m_min,precipitation_probability_max,uv_index_max"
DEFAULT_SELECTION = {"city": "台北市", "activity": "walking", "preference": "normal"}


class ForecastUnavailable(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _number(value):
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError("Invalid forecast number")
    return value


def _today(daily, field):
    values = daily[field]
    if not isinstance(values, list) or not values:
        raise ValueError("Missing daily forecast values")
    return values[0]


def _parse_forecast(payload) -> Weather:
    current, daily = payload["current"], payload["daily"]
    if not isinstance(current, dict) or not isinstance(daily, dict):
        raise ValueError("Invalid forecast sections")

    current_time = current["time"]
    forecast_date = _today(daily, "time")
    if not isinstance(current_time, str) or not isinstance(forecast_date, str):
        raise ValueError("Invalid forecast date")
    if datetime.fromisoformat(current_time).date() != date.fromisoformat(forecast_date):
        raise ValueError("Mismatched current and daily dates")
    if type(current["weather_code"]) is not int:
        raise ValueError("Invalid weather code")

    weather = Weather(
        temperature=_number(current["temperature_2m"]),
        apparent_temperature=_number(current["apparent_temperature"]),
        humidity=_number(current["relative_humidity_2m"]),
        wind_speed=_number(current["wind_speed_10m"]),
        weather_code=current["weather_code"],
        temperature_max=_number(_today(daily, "temperature_2m_max")),
        temperature_min=_number(_today(daily, "temperature_2m_min")),
        rain_probability=_number(_today(daily, "precipitation_probability_max")),
        uv_max=_number(_today(daily, "uv_index_max")),
        current_time=current_time,
        date=forecast_date,
    )
    if not (
        0 <= weather.humidity <= 100
        and 0 <= weather.rain_probability <= 100
        and weather.wind_speed >= 0
        and weather.uv_max >= 0
        and weather.temperature_min <= weather.temperature_max
    ):
        raise ValueError("Forecast values out of range")
    return weather


def get_forecast(city: str) -> Weather:
    latitude, longitude = CITIES[city]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_FIELDS,
        "daily": DAILY_FIELDS,
        "timezone": "Asia/Taipei",
        "forecast_days": 1,
    }
    try:
        response = requests.get(FORECAST_URL, params=params, timeout=10)
    except requests.Timeout as error:
        raise ForecastUnavailable("天氣服務回應逾時，請稍等一下再試。", 504) from error
    except requests.RequestException as error:
        raise ForecastUnavailable("暫時連不上天氣服務，請稍後再試。") from error

    if response.status_code != 200:
        raise ForecastUnavailable("天氣服務暫時無法提供資料，請稍後再試。")
    try:
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("error"):
            raise ValueError("Invalid forecast response")
        return _parse_forecast(payload)
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ForecastUnavailable("這次收到的天氣資料不完整，請稍後再查詢。") from error


def render_page(selection, *, weather=None, decision=None, error=None):
    return render_template(
        "index.html",
        cities=CITIES,
        activities=ACTIVITIES,
        preferences=PREFERENCES,
        selection=selection,
        weather=weather,
        decision=decision,
        error=error,
        preview=OUTFITS["mild"],
    )


@app.get("/")
def index():
    return render_page(DEFAULT_SELECTION)


@app.route("/weather", methods=["GET", "POST"])
def query_weather():
    options = {"city": CITIES, "activity": ACTIVITIES, "preference": PREFERENCES}
    inputs = request.form if request.method == "POST" else request.args
    submitted = {field: inputs.get(field) for field in options}
    if request.method != "POST" and all(value is None for value in submitted.values()):
        return redirect(url_for("index"))
    selection = {
        field: value if value in options[field] else DEFAULT_SELECTION[field]
        for field, value in submitted.items()
    }
    if selection != submitted:
        return render_page(selection, error="請選擇有效的縣市、行程和體感偏好。"), 400

    try:
        weather = get_forecast(selection["city"])
    except ForecastUnavailable as error:
        return render_page(selection, error=str(error)), error.status_code
    decision = evaluate(weather, selection["activity"], selection["preference"])
    return render_page(selection, weather=weather, decision=decision)
