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
}

ACCENT_COLORS = [
    "#28915a",
    "#3878b2",
    "#c05838",
    "#b45478",
    "#7868ae",
    "#28867a",
    "#b07528",
    "#63707e",
]

DEFAULT_APPEARANCE = "light"


def get_appearance_preset(site):
    preset = site.get("theme") or DEFAULT_APPEARANCE
    return preset if preset in APPEARANCE_PRESETS else DEFAULT_APPEARANCE


def get_appearance_vars(site):
    preset = dict(APPEARANCE_PRESETS[get_appearance_preset(site)])
    if site.get("accent_color"):
        preset["accent"] = site["accent_color"]
    return preset
