"""Prefab weather dashboard UI."""

from typing import Any

from prefab_ui.actions import SetState, ShowToast
from prefab_ui.actions.mcp import CallTool
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Badge,
    Button,
    Card,
    CardContent,
    CardHeader,
    Column,
    ForEach,
    Form,
    Heading,
    Input,
    Metric,
    Row,
    Separator,
    Text,
)
from prefab_ui.rx import RESULT, Rx


def build_dashboard(
    get_weather: Any,
    location: str,
    forecast_days: int = 5,
    temperature_unit: str = "celsius",
) -> PrefabApp:
    """Build an interactive weather dashboard."""
    weather_data = get_weather(location, forecast_days, temperature_unit)
    unit_symbol = "°F" if temperature_unit == "fahrenheit" else "°C"
    with PrefabApp(
        state={
            "location": location,
            "forecast_days": forecast_days,
            "temperature_unit": temperature_unit,
            "unit_symbol": unit_symbol,
            "weather": weather_data,
        }
    ) as app:
        with Column(gap=4, css_class="p-6 max-w-3xl"):
            with Row(gap=3, align="center"):
                Heading("Weather")
                Badge(Rx("weather.location.country"))
            with Form(
                on_submit=CallTool(
                    "get_weather",
                    arguments={
                        "location": Rx("location"),
                        "forecast_days": Rx("forecast_days"),
                        "temperature_unit": Rx("temperature_unit"),
                    },
                    on_success=SetState("weather", RESULT),
                    on_error=ShowToast("Unable to load that location", variant="error"),
                )
            ):
                with Row(gap=2, align="end"):
                    Input(
                        name="location",
                        label="Location",
                        placeholder="Search for a city",
                        required=True,
                    )
                    Button("Search")
            with Row(gap=2, align="center"):
                Text(Rx("weather.location.name"), css_class="text-lg font-semibold")
                Text(
                    Rx("weather.forecast.timezone"),
                    css_class="text-sm text-muted-foreground",
                )
                with Row(gap=1, css_class="ml-auto"):
                    _unit_button("°C", "celsius")
                    _unit_button("°F", "fahrenheit")
            with Card():
                with CardHeader():
                    Text("Current conditions")
                with CardContent():
                    with Row(gap=6, align="center"):
                        Text(
                            Rx("weather.current_condition.symbol"),
                            css_class="text-3xl w-10",
                        )
                        Metric(
                            label="Temperature",
                            value=Rx("weather.forecast.current.temperature_2m"),
                        )
                        Text(
                            Rx("unit_symbol"), css_class="text-sm text-muted-foreground"
                        )
                        _metric(
                            "weather.forecast.current.apparent_temperature",
                            "Feels like",
                        )
                        _metric(
                            "weather.forecast.current.relative_humidity_2m", "Humidity"
                        )
                        _metric("weather.forecast.current.wind_speed_10m", "Wind")
                    Text(
                        Rx("weather.current_condition.description"),
                        css_class="text-sm text-muted-foreground",
                    )
            Separator()
            Heading("Forecast", level=2)
            with Column(gap=2):
                with ForEach("weather.days") as day:
                    with Card():
                        with CardContent():
                            with Row(gap=3, align="center"):
                                Text(day["date"], css_class="font-medium w-28")
                                Text(day["symbol"], css_class="text-xl w-8")
                                Text(day["description"], css_class="w-36")
                                Text(day.high)
                                Text(day.low, css_class="text-muted-foreground")
                                Text(day.rain_chance)
                                Text(
                                    "% rain", css_class="text-sm text-muted-foreground"
                                )
    return app


def _unit_button(label: str, unit: str) -> Button:
    return Button(
        label,
        variant="outline",
        on_click=[
            SetState("temperature_unit", unit),
            SetState("unit_symbol", label),
            CallTool(
                "get_weather",
                arguments={
                    "location": Rx("location"),
                    "forecast_days": Rx("forecast_days"),
                    "temperature_unit": unit,
                },
                on_success=SetState("weather", RESULT),
            ),
        ],
    )


def _metric(value: str, label: str) -> None:
    with Column(gap=1):
        Text(Rx(value))
        Text(label, css_class="text-sm text-muted-foreground")
