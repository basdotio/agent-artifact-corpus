"""Curated deep-link entries built from public Android intent actions and well-known URI schemes."""

from __future__ import annotations

from typing import Any

# Generic entries: valid on any Android device; probed with resolve-activity at query time.
GENERIC: list[dict[str, Any]] = [
    {"label": "Dial a number", "uri_template": "tel:{number}", "example": "tel:+15551234567"},
    {"label": "Compose an SMS", "uri_template": "smsto:{number}", "example": "smsto:+15551234567"},
    {"label": "Compose an email", "uri_template": "mailto:{address}", "example": "mailto:a@b.com"},
    {
        "label": "Open a web page",
        "uri_template": "https://{host}/{path}",
        "example": "https://example.com/",
    },
    {
        "label": "Search Google",
        "uri_template": "https://www.google.com/search?q={query}",
        "example": "https://www.google.com/search?q=weather",
    },
    {"label": "Map search", "uri_template": "geo:0,0?q={query}", "example": "geo:0,0?q=coffee"},
    {
        "label": "WhatsApp chat",
        "uri_template": "https://wa.me/{number}?text={text}",
        "example": "https://wa.me/15551234567?text=hi",
        "requires_confirmation": True,
    },
    {
        "label": "Play Store app page",
        "uri_template": "market://details?id={package}",
        "example": "market://details?id=com.android.chrome",
    },
]

SETTINGS_ACTIONS: list[tuple[str, str]] = [
    ("Settings home", "android.settings.SETTINGS"),
    ("Wi-Fi settings", "android.settings.WIFI_SETTINGS"),
    ("Bluetooth settings", "android.settings.BLUETOOTH_SETTINGS"),
    ("Display settings", "android.settings.DISPLAY_SETTINGS"),
    ("Sound settings", "android.settings.SOUND_SETTINGS"),
    ("Battery saver", "android.settings.BATTERY_SAVER_SETTINGS"),
    ("Apps settings", "android.settings.APPLICATION_SETTINGS"),
    ("Location settings", "android.settings.LOCATION_SOURCE_SETTINGS"),
    ("Airplane mode", "android.settings.AIRPLANE_MODE_SETTINGS"),
    ("Date and time", "android.settings.DATE_SETTINGS"),
    ("Accessibility settings", "android.settings.ACCESSIBILITY_SETTINGS"),
    ("Developer options", "android.settings.APPLICATION_DEVELOPMENT_SETTINGS"),
]

PER_APP: dict[str, list[dict[str, Any]]] = {
    "com.android.settings": [{"label": label, "uri": action} for label, action in SETTINGS_ACTIONS],
    "com.whatsapp": [
        {
            "label": "Open chat with number",
            "uri_template": "https://wa.me/{number}",
            "example": "https://wa.me/15551234567",
            "requires_confirmation": True,
        }
    ],
    "com.google.android.youtube": [
        {
            "label": "Search YouTube",
            "uri_template": "https://www.youtube.com/results?search_query={query}",
            "example": "https://www.youtube.com/results?search_query=lofi",
        },
        {
            "label": "Open a video",
            "uri_template": "https://www.youtube.com/watch?v={video_id}",
            "example": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        },
    ],
    "com.google.android.apps.maps": [
        {
            "label": "Search a place",
            "uri_template": "https://www.google.com/maps/search/{query}",
            "example": "https://www.google.com/maps/search/coffee",
        },
        {
            "label": "Directions",
            "uri_template": "https://www.google.com/maps/dir/?api=1&destination={place}",
            "example": "https://www.google.com/maps/dir/?api=1&destination=Cairo",
        },
    ],
    "com.facebook.katana": [
        {
            "label": "Open a profile by id",
            "uri_template": "fb://profile/{id}",
            "example": "fb://profile/4",
        }
    ],
    "com.instagram.android": [
        {
            "label": "Open a profile",
            "uri_template": "https://www.instagram.com/{username}/",
            "example": "https://www.instagram.com/instagram/",
        }
    ],
    "com.twitter.android": [
        {
            "label": "Open a profile",
            "uri_template": "https://x.com/{username}",
            "example": "https://x.com/x",
        }
    ],
}


def entries_for(package: str) -> list[dict[str, Any]]:
    return PER_APP.get(package, [])
