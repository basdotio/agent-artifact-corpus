"""Weather API module for fetching weather data from Open-Meteo API."""

import requests


class WeatherAPI:
    """Weather API client that fetches weather data from Open-Meteo API."""

    def __init__(self, base_url: str = "https://api.open-meteo.com/v1"):
        self._base_url = base_url

    def get_weather(
        self,
        latitude: float | int,
        longitude: float | int,
    ):
        """
        Return the current weather as well as a forecast for the next 7 days for the specified location.

        Parameters
        ----------
        latitude : float|int
            Latitude WSG84 coordinate
        longitude : float|int
            Longitude WSG84 coordinate

        Returns
        -------
        dict
            Weather data including current weather and daily forecast
        """
        current_weather = True
        daily = [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "apparent_temperature_max",
            "apparent_temperature_min",
            "sunrise",
            "sunset",
            "daylight_duration",
            "sunshine_duration",
            "uv_index_max",
            "uv_index_clear_sky_max",
            "rain_sum",
            "showers_sum",
            "precipitation_sum",
            "snowfall_sum",
            "precipitation_hours",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "wind_gusts_10m_max",
            "wind_direction_10m_dominant",
            "shortwave_radiation_sum",
            "et0_fao_evapotranspiration",
            "relative_humidity_2m_min",
            "relative_humidity_2m_max",
            "relative_humidity_2m_mean",
            "temperature_2m_mean",
            "apparent_temperature_mean",
            "cloud_cover_max",
            "cloud_cover_min",
            "cloud_cover_mean",
            "dew_point_2m_mean",
            "dew_point_2m_max",
            "dew_point_2m_min",
            "precipitation_probability_min",
            "precipitation_probability_mean",
            "surface_pressure_mean",
            "surface_pressure_max",
            "surface_pressure_min",
            "visibility_mean",
            "visibility_min",
            "visibility_max",
        ]
        response = requests.get(
            url=f"{self._base_url}/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": daily,
                "current_weather": current_weather,
            },
            timeout=100,
        )
        return response.json()
