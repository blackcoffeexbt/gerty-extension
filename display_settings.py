"""Display profiles and named palettes stored in Gerty preferences."""

DISPLAY_PROFILES = {
    "epaper_960x540": {
        "label": "Epaper 960 x 540",
        "width": 960,
        "height": 540,
        "mode": "L",
    },
    "colour_480x320": {
        "label": "Colour 480 x 320",
        "width": 480,
        "height": 320,
        "mode": "RGB",
    },
}

COLOUR_THEMES = {
    "Cypherpunk": {
        "background": "#100D20",
        "surface": "#201833",
        "text": "#F4EDFF",
        "muted": "#BFB1D5",
        "accent": "#53FFD1",
        "secondary": "#FF70D4",
        "border": "#53446C",
        "positive": "#53FFD1",
        "negative": "#FF718C",
    },
    "Bright day": {
        "background": "#EAF1F7",
        "surface": "#FFFFFF",
        "text": "#14283D",
        "muted": "#486278",
        "accent": "#005DA8",
        "secondary": "#7951AA",
        "border": "#A8BECE",
        "positive": "#087746",
        "negative": "#BE2639",
    },
    "Orange Pill": {
        "background": "#15120F",
        "surface": "#29221A",
        "text": "#FFF4E5",
        "muted": "#C8B9A3",
        "accent": "#FF9C31",
        "secondary": "#FFD18A",
        "border": "#63503A",
        "positive": "#9DDD89",
        "negative": "#FF8174",
    },
}


def get_display_settings(preferences):
    display = preferences.get("_display", {})
    if not isinstance(display, dict):
        raise ValueError("Display preferences must be an object.")
    profile = display.get("profile", "epaper_960x540")
    theme = display.get("theme", "Orange Pill")
    if not isinstance(profile, str) or profile not in DISPLAY_PROFILES:
        raise ValueError("Unknown display profile.")
    if not isinstance(theme, str) or theme not in COLOUR_THEMES:
        raise ValueError("Unknown colour theme.")
    return profile, theme
