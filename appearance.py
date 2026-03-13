APPEARANCE_PRESETS = {
    "light": {
        "label": "Light",
        "bg": "#f1f0ec",
        "text": "#2f3438",
        "text_bright": "#11161b",
        "text_muted": "#8a8f95",
        "divider": "#dfddd8",
        "code_bg": "#e6e4df",
        "accent": "#0f2237",
    },
    "dark": {
        "label": "Dark",
        "bg": "#07131c",
        "text": "#dde4e8",
        "text_bright": "#fafbfb",
        "text_muted": "#99a6af",
        "divider": "#152431",
        "code_bg": "#0d1b26",
        "accent": "#86b3ff",
    },
    "cool": {
        "label": "Cool",
        "bg": "#dde6ea",
        "text": "#32434f",
        "text_bright": "#1b2831",
        "text_muted": "#75848f",
        "divider": "#ccd6dc",
        "code_bg": "#d3dce1",
        "accent": "#476f88",
    },
    "warm": {
        "label": "Warm",
        "bg": "#f1dfcf",
        "text": "#4b382d",
        "text_bright": "#2c1d14",
        "text_muted": "#927b6d",
        "divider": "#e3cfbe",
        "code_bg": "#e7d4c3",
        "accent": "#ca7a34",
    },
}

DEFAULT_APPEARANCE = "light"


def get_appearance_preset(site):
    preset = site.get("theme") or DEFAULT_APPEARANCE
    return preset if preset in APPEARANCE_PRESETS else DEFAULT_APPEARANCE


def get_appearance_vars(site):
    return APPEARANCE_PRESETS[get_appearance_preset(site)]
