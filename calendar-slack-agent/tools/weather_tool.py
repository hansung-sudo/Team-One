import requests
from langchain.tools import tool
from pydantic import BaseModel, Field

_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

_WMO_CODES = {
    0: "맑음", 1: "대체로 맑음", 2: "부분 흐림", 3: "흐림",
    45: "안개", 48: "착빙 안개",
    51: "가벼운 이슬비", 53: "이슬비", 55: "강한 이슬비",
    61: "가벼운 비", 63: "비", 65: "강한 비",
    71: "가벼운 눈", 73: "눈", 75: "강한 눈",
    77: "싸락눈",
    80: "소나기", 81: "강한 소나기", 82: "폭우",
    85: "약한 눈보라", 86: "눈보라",
    95: "뇌우", 96: "우박 동반 뇌우", 99: "강한 우박 동반 뇌우",
}


class WeatherInput(BaseModel):
    city: str = Field(description="날씨를 조회할 도시 이름 (영문 권장, 예: Seoul, Tokyo, New York)")


@tool(args_schema=WeatherInput)
def get_weather(city: str) -> str:
    """도시의 현재 날씨(기온·체감·습도·풍속·날씨 상태)를 조회합니다."""
    try:
        geo = requests.get(
            _GEO_URL,
            params={"name": city, "count": 1, "language": "ko"},
            timeout=8,
        ).json()

        if not geo.get("results"):
            return f"'{city}' 도시를 찾을 수 없습니다."

        result = geo["results"][0]
        lat = result["latitude"]
        lon = result["longitude"]
        city_name = result.get("name", city)
        country = result.get("country", "")

        weather = requests.get(
            _WEATHER_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,windspeed_10m,weathercode",
                "timezone": "auto",
            },
            timeout=8,
        ).json()

        cur = weather["current"]
        code = cur.get("weathercode", 0)
        desc = _WMO_CODES.get(code, f"코드 {code}")

        return (
            f"{city_name}, {country}\n"
            f"날씨: {desc}\n"
            f"기온: {cur['temperature_2m']}°C  (체감 {cur['apparent_temperature']}°C)\n"
            f"습도: {cur['relative_humidity_2m']}%  바람: {cur['windspeed_10m']} km/h"
        )
    except Exception as e:
        return f"날씨 조회 실패 ({city}): {e}"
