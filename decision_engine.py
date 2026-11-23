"""根據 Open-Meteo 資料與使用者偏好，產出可解釋的規則推論。"""

from dataclasses import dataclass

from outfit_assets import ACCESSORIES, OUTFITS, OutfitAsset


@dataclass(frozen=True)
class Activity:
    label: str
    weights: tuple[float, float, float, float]


# 權重依序是體感、降雨、風速、紫外線。
ACTIVITIES = {
    "scooter": Activity("機車通勤", (0.30, 0.35, 0.30, 0.05)),
    "walking": Activity("校園／上班步行", (0.45, 0.25, 0.15, 0.15)),
    "outdoor": Activity("戶外約會出遊", (0.35, 0.25, 0.15, 0.25)),
}
PREFERENCES = {"hot": "怕熱", "normal": "一般", "cold": "怕冷"}
PREFERENCE_OFFSETS = {"hot": 2, "normal": 0, "cold": -2}

SPREAD_WARNING = 7
RAIN_THRESHOLD = 50
STRONG_WIND_THRESHOLD = 35
UV_PROTECTION_THRESHOLD = 3

# WMO 天氣代碼，包含毛毛雨、雨、陣雨以及雷雨。
WET_CODES = {
    51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77,
    80, 81, 82, 85, 86, 95, 96, 99,
}
WEATHER_LABELS = {
    0: "晴朗", 1: "大致晴朗", 2: "局部多雲", 3: "陰天",
    45: "有霧", 48: "霧淞",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨", 56: "凍毛毛雨", 57: "凍毛毛雨",
    61: "有雨", 63: "有雨", 65: "大雨", 66: "凍雨", 67: "凍雨",
    71: "有雪", 73: "有雪", 75: "大雪", 77: "霰",
    80: "陣雨", 81: "陣雨", 82: "強陣雨", 85: "陣雪", 86: "強陣雪",
    95: "雷雨", 96: "雷雨與冰雹", 99: "雷雨與冰雹",
}
OUTFIT_TIPS = {
    "hot": "選透氣短袖、寬鬆短褲或薄長褲，走在戶外比較不悶。",
    "mild": "薄長袖或短袖搭輕便長褲，步行和進出冷氣房都好活動。",
    "layered": "短袖或薄長袖搭可脫的薄外套，早晚加一層，中午熱了就脫掉。",
    "cold": "用保暖內層、長褲與防風外套擋風，騎車時也可加上手套。",
}


@dataclass(frozen=True)
class Weather:
    temperature: float
    apparent_temperature: float
    humidity: float
    wind_speed: float
    weather_code: int
    temperature_max: float
    temperature_min: float
    rain_probability: float
    uv_max: float
    current_time: str
    date: str

    @property
    def summary(self) -> str:
        return WEATHER_LABELS.get(self.weather_code, f"天氣代碼 {self.weather_code}")


@dataclass(frozen=True)
class Decision:
    score: int
    level: str
    level_style: str
    adjusted_temperature: float
    spread: float
    outfit: OutfitAsset
    outfit_tip: str
    accessories: tuple[OutfitAsset, ...]
    layer_tip: str
    rain_tip: str
    wind_tip: str | None
    uv_tip: str
    easter_egg: str


def evaluate(weather: Weather, activity: str, preference: str) -> Decision:
    """從 100 分扣除依行程加權的天氣負擔，再產生穿搭與配件。"""
    adjusted = weather.apparent_temperature + PREFERENCE_OFFSETS[preference]
    spread = round(weather.temperature_max - weather.temperature_min, 1)
    wet_now = weather.weather_code in WET_CODES
    needs_rain_gear = wet_now or weather.rain_probability >= RAIN_THRESHOLD
    strong_wind = weather.wind_speed >= STRONG_WIND_THRESHOLD
    high_uv = weather.uv_max >= UV_PROTECTION_THRESHOLD

    heat_discomfort = max(0, abs(adjusted - 24) - 2) * 100 / 14
    rain_discomfort = max(weather.rain_probability, 70 if wet_now else 0)
    wind_discomfort = weather.wind_speed * 100 / 45
    uv_discomfort = weather.uv_max * 100 / 11
    penalties = (heat_discomfort, rain_discomfort, wind_discomfort, uv_discomfort)
    weights = ACTIVITIES[activity].weights
    score = round(100 - sum(weight * min(penalty, 100) for weight, penalty in zip(weights, penalties)))
    if score >= 75:
        level, level_style = "綠燈・好出門", "green"
    elif score >= 50:
        level, level_style = "黃燈・準備一下", "amber"
    else:
        level, level_style = "紅燈・多留意天氣", "red"

    if adjusted >= 28:
        outfit = "hot"
    elif adjusted < 17:
        outfit = "cold"
    elif adjusted < 22 or spread >= SPREAD_WARNING:
        outfit = "layered"
    else:
        outfit = "mild"

    accessories = []
    if needs_rain_gear and (activity == "scooter" or strong_wind):
        rain_tip = "今天有降雨機會，帶兩件式雨衣；若要騎車，先確認雨褲與袖口是否完整。"
        accessories.append("raincoat")
    elif needs_rain_gear:
        rain_tip = "今天有降雨機會，包包先放一把折疊傘。"
        accessories.append("umbrella")
    else:
        rain_tip = "目前的降雨訊號偏低，可依回程安排決定是否帶雨具。"

    wind_tip = None
    if strong_wind:
        wind_tip = "目前風較強，撐傘容易開花；需要防雨時可改穿雨衣。"
        accessories.append("windbreaker")
    elif outfit == "cold":
        accessories.append("windbreaker")

    if spread >= SPREAD_WARNING:
        layer_tip = "預報高低溫差達 7°C，早晚適合洋蔥式穿搭。"
    else:
        layer_tip = "預報高低溫差小於 7°C，依目前體感挑選衣服即可。"
    if outfit == "layered" or (spread >= SPREAD_WARNING and outfit != "cold"):
        accessories.append("jacket")

    if high_uv:
        if weather.uv_max >= 6:
            uv_tip = "今日最高紫外線指數達 6 以上，外出可擦防曬、戴帽或墨鏡，並優先走陰影處。"
        else:
            uv_tip = "今日最高紫外線指數達 3，外出可擦防曬並戴帽。"
        accessories.append("sun")
    else:
        uv_tip = "今日預報最高紫外線指數低於 3，長時間在戶外仍可帶帽。"

    if outfit == "hot":
        easter_egg = "台灣出門小撇步：路過早餐店可以補水，手搖飲的冰塊也會跟著今天的氣溫跑得很快。"
    elif needs_rain_gear:
        easter_egg = "台灣出門小撇步：雨天先看一下騎樓能不能一路通到目的地，少淋一段是一段。"
    else:
        easter_egg = "台灣出門小撇步：走到巷口再做一次手機、鑰匙、交通卡的三件套確認。"

    # 配件至少兩項；有三項以上氣象需求時，優先保留風雨與穿搭相關配件。
    essentials = ["water", "shoes"] if outfit == "hot" else ["shoes", "water"]
    if len(accessories) < 2:
        accessories.extend(essentials[:2 - len(accessories)])

    return Decision(
        score=score,
        level=level,
        level_style=level_style,
        adjusted_temperature=adjusted,
        spread=spread,
        outfit=OUTFITS[outfit],
        outfit_tip=OUTFIT_TIPS[outfit],
        accessories=tuple(ACCESSORIES[name] for name in accessories[:3]),
        layer_tip=layer_tip,
        rain_tip=rain_tip,
        wind_tip=wind_tip,
        uv_tip=uv_tip,
        easter_egg=easter_egg,
    )
