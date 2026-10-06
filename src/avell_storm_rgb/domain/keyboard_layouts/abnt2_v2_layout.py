"""ABNT2 laptop visual v2 layout definition (fractional u, gaps)."""

from __future__ import annotations

from avell_storm_rgb.domain.keyboard_layouts.visual_geometry import (
    RectU,
    VisualLayoutSpec,
    place_row,
)

SPEC = VisualLayoutSpec(key_gap=0.15, wide_gap=1.0, row_count=7)

_STD = 1.0
_TAB = 1.5
_CAPS = 1.75
_LSHIFT = 1.25
_RSHIFT = 2.75
_BS = 2.0
_SPACE = 6.0
_MOD_WIDE = 1.25
_MOD_NARROW = 1.0
_KP0 = 2.0

# Keys placed in the main block (numpad is positioned separately).
_MAIN_KEY_IDS = frozenset({
    "esc", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "scrlk", "prtsc", "delete", "grave", "digit_1", "digit_2", "digit_3", "digit_4", "digit_5",
    "digit_6", "digit_7", "digit_8", "digit_9", "digit_0", "minus", "equal", "backspace",
    "tab", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "bracket_left",
    "bracket_square", "caps_lock", "a", "s", "d", "f", "g", "h", "j", "k", "l", "cedilla",
    "semicolon", "bracket_right", "shift_left", "backslash", "z", "x", "c", "v", "b", "n",
    "m", "comma", "dot", "slash", "shift_right", "ctrl_left", "fn", "meta_left", "alt_left",
    "space", "alt_right", "menu", "up", "left", "down", "right",
})


def _ncol(x0: float, col: int, g: float) -> float:
    return x0 + col * (_STD + g)


def _main_right_edge(simple: dict[str, RectU]) -> float:
    return max(simple[k].x + simple[k].w for k in _MAIN_KEY_IDS if k in simple)


def _delete_right_edge(simple: dict[str, RectU]) -> float:
    delete = simple["delete"]
    return delete.x + delete.w


def _align_main_block_right_edge(
    simple: dict[str, RectU],
    parts: dict[str, list[RectU]],
    *,
    key_gap: float,
) -> None:
    """Extend backspace, enter, and right shift to the same right edge as Del."""
    g = key_gap
    right = _delete_right_edge(simple)

    bs = simple["backspace"]
    simple["backspace"] = RectU(x=bs.x, y=bs.y, w=round(right - bs.x, 4), h=bs.h)

    sr = simple["shift_right"]
    simple["shift_right"] = RectU(x=sr.x, y=sr.y, w=round(right - sr.x, 4), h=sr.h)

    bsquare = simple["bracket_square"]
    br = simple["bracket_right"]
    enter_top_x = bsquare.x + bsquare.w + g
    enter_bot_x = br.x + br.w + g
    parts["enter"] = [
        RectU(x=enter_top_x, y=2.0, w=round(right - enter_top_x, 4), h=1.0),
        RectU(x=enter_bot_x, y=3.0, w=round(right - enter_bot_x, 4), h=1.0),
    ]


def _place_numpad_block(simple: dict[str, RectU], pad_x: float, g: float) -> None:
    """Numeric keypad section (separate from main body)."""
    simple["home"] = RectU(x=_ncol(pad_x, 0, g), y=0.0, w=_STD, h=1.0)
    simple["page_up"] = RectU(x=_ncol(pad_x, 1, g), y=0.0, w=_STD, h=1.0)
    simple["page_down"] = RectU(x=_ncol(pad_x, 2, g), y=0.0, w=_STD, h=1.0)
    simple["end"] = RectU(x=_ncol(pad_x, 3, g), y=0.0, w=_STD, h=1.0)

    simple["num_lock"] = RectU(x=_ncol(pad_x, 0, g), y=1.0, w=_STD, h=1.0)
    simple["kp_div"] = RectU(x=_ncol(pad_x, 1, g), y=1.0, w=_STD, h=1.0)
    simple["kp_mul"] = RectU(x=_ncol(pad_x, 2, g), y=1.0, w=_STD, h=1.0)
    simple["kp_minus"] = RectU(x=_ncol(pad_x, 3, g), y=1.0, w=_STD, h=1.0)

    simple["kp_7"] = RectU(x=_ncol(pad_x, 0, g), y=2.0, w=_STD, h=1.0)
    simple["kp_8"] = RectU(x=_ncol(pad_x, 1, g), y=2.0, w=_STD, h=1.0)
    simple["kp_9"] = RectU(x=_ncol(pad_x, 2, g), y=2.0, w=_STD, h=1.0)

    simple["kp_4"] = RectU(x=_ncol(pad_x, 0, g), y=3.0, w=_STD, h=1.0)
    simple["kp_5"] = RectU(x=_ncol(pad_x, 1, g), y=3.0, w=_STD, h=1.0)
    simple["kp_6"] = RectU(x=_ncol(pad_x, 2, g), y=3.0, w=_STD, h=1.0)

    simple["kp_1"] = RectU(x=_ncol(pad_x, 0, g), y=4.0, w=_STD, h=1.0)
    simple["kp_2"] = RectU(x=_ncol(pad_x, 1, g), y=4.0, w=_STD, h=1.0)
    simple["kp_3"] = RectU(x=_ncol(pad_x, 2, g), y=4.0, w=_STD, h=1.0)

    # Bottom numpad row aligns with space bar row (y=5)
    simple["kp_0"] = RectU(x=_ncol(pad_x, 0, g), y=5.0, w=_KP0, h=1.0)
    simple["kp_dot"] = RectU(x=_ncol(pad_x, 2, g), y=5.0, w=_STD, h=1.0)


def build_abnt2_placements() -> tuple[dict[str, RectU], dict[str, list[RectU]]]:
    """Return simple rects and multi-part rects for ABNT2 visual v2."""
    g = SPEC.key_gap
    w = SPEC.wide_gap
    simple: dict[str, RectU] = {}
    parts: dict[str, list[RectU]] = {}

    def row(y: int, segments: list) -> None:
        simple.update(place_row(float(y), segments, key_gap=g, wide_gap=w))

    # --- Main body ---
    row(
        0,
        [
            ("esc", _STD),
            ("f1", _STD),
            ("f2", _STD),
            ("f3", _STD),
            ("f4", _STD),
            ("f5", _STD),
            ("f6", _STD),
            ("f7", _STD),
            ("f8", _STD),
            ("f9", _STD),
            ("f10", _STD),
            ("f11", _STD),
            ("f12", _STD),
            ("scrlk", _STD),
            ("prtsc", _STD),
            ("delete", _STD),
        ],
    )

    row(
        1,
        [
            ("grave", _STD),
            ("digit_1", _STD),
            ("digit_2", _STD),
            ("digit_3", _STD),
            ("digit_4", _STD),
            ("digit_5", _STD),
            ("digit_6", _STD),
            ("digit_7", _STD),
            ("digit_8", _STD),
            ("digit_9", _STD),
            ("digit_0", _STD),
            ("minus", _STD),
            ("equal", _STD),
            ("backspace", _BS),
        ],
    )

    row(
        2,
        [
            ("tab", _TAB),
            ("q", _STD),
            ("w", _STD),
            ("e", _STD),
            ("r", _STD),
            ("t", _STD),
            ("y", _STD),
            ("u", _STD),
            ("i", _STD),
            ("o", _STD),
            ("p", _STD),
            ("bracket_left", _STD),
            ("bracket_square", _STD),
        ],
    )

    row(
        3,
        [
            ("caps_lock", _CAPS),
            ("a", _STD),
            ("s", _STD),
            ("d", _STD),
            ("f", _STD),
            ("g", _STD),
            ("h", _STD),
            ("j", _STD),
            ("k", _STD),
            ("l", _STD),
            ("cedilla", _STD),
            ("semicolon", _STD),
            ("bracket_right", _STD),
        ],
    )

    row(
        4,
        [
            ("shift_left", _LSHIFT),
            ("backslash", _STD),
            ("z", _STD),
            ("x", _STD),
            ("c", _STD),
            ("v", _STD),
            ("b", _STD),
            ("n", _STD),
            ("m", _STD),
            ("comma", _STD),
            ("dot", _STD),
            ("slash", _STD),
            ("shift_right", _RSHIFT),
        ],
    )

    row(
        5,
        [
            ("ctrl_left", _MOD_WIDE),
            ("fn", _MOD_NARROW),
            ("meta_left", _MOD_NARROW),
            ("alt_left", _MOD_WIDE),
            ("space", _SPACE),
            ("alt_right", _MOD_WIDE),
            ("menu", _MOD_NARROW),
        ],
    )

    _align_main_block_right_edge(simple, parts, key_gap=g)

    shift = simple["shift_right"]
    cluster_w = 3 * _STD + 2 * g
    arrow_x = round(shift.x + (shift.w - cluster_w) / 2, 4)
    down_x = arrow_x + _STD + g
    simple["up"] = RectU(x=down_x, y=5.0, w=_STD, h=1.0)
    simple["down"] = RectU(x=down_x, y=6.0, w=_STD, h=1.0)
    simple["left"] = RectU(x=arrow_x, y=6.0, w=_STD, h=1.0)
    simple["right"] = RectU(x=arrow_x + 2 * (_STD + g), y=6.0, w=_STD, h=1.0)

    # --- Numeric keypad (standard key_gap after main block) ---
    pad_x = _main_right_edge(simple) + g
    _place_numpad_block(simple, pad_x, g)

    parts["kp_plus"] = [
        RectU(x=_ncol(pad_x, 3, g), y=2.0, w=_STD, h=2.0),
    ]
    kp_ent_x = _ncol(pad_x, 3, g)
    simple["kp_enter_top"] = RectU(x=kp_ent_x, y=4.0, w=_STD, h=2.0)

    return simple, parts


def rect_to_visual_v2(rect: RectU) -> dict[str, float]:
    return {"x": round(rect.x, 4), "y": rect.y, "w": rect.w, "h": rect.h}


def parts_to_visual_parts_v2(rects: list[RectU]) -> list[dict[str, float]]:
    return [rect_to_visual_v2(r) for r in rects]


LAYOUT_LABEL_OVERRIDES: dict[str, dict[str, str]] = {
    "scrlk": {"label": "SC", "secondaryLabel": ""},
    "prtsc": {"label": "PrtSc", "secondaryLabel": ""},
    "delete": {"label": "Del", "secondaryLabel": ""},
    "grave": {"label": "'", "secondaryLabel": '"'},
    "digit_1": {"label": "1", "secondaryLabel": "!¹"},
    "digit_2": {"label": "2", "secondaryLabel": "@²"},
    "digit_3": {"label": "3", "secondaryLabel": "#³"},
    "digit_4": {"label": "4", "secondaryLabel": "$£"},
    "digit_5": {"label": "5", "secondaryLabel": "%¢"},
    "digit_6": {"label": "6", "secondaryLabel": "^¬"},
    "digit_7": {"label": "7", "secondaryLabel": "&{"},
    "digit_8": {"label": "8", "secondaryLabel": "*"},
    "digit_9": {"label": "9", "secondaryLabel": "("},
    "digit_0": {"label": "0", "secondaryLabel": ")"},
    "minus": {"label": "-", "secondaryLabel": "_"},
    "equal": {"label": "=", "secondaryLabel": "+§"},
    "backspace": {"label": "Backspace", "secondaryLabel": ""},
    "q": {"label": "Q", "secondaryLabel": "/"},
    "w": {"label": "W", "secondaryLabel": "?"},
    "e": {"label": "E", "secondaryLabel": "°"},
    "bracket_left": {"label": "´", "secondaryLabel": "`"},
    "bracket_square": {"label": "[", "secondaryLabel": "{ª"},
    "enter": {"label": "Enter", "secondaryLabel": ""},
    "caps_lock": {"label": "Fixa", "secondaryLabel": ""},
    "semicolon": {"label": "~", "secondaryLabel": "^"},
    "bracket_right": {"label": "]", "secondaryLabel": "}º"},
    "shift_left": {"label": "Shift", "secondaryLabel": ""},
    "backslash": {"label": "\\", "secondaryLabel": "|"},
    "comma": {"label": ",", "secondaryLabel": "<"},
    "dot": {"label": ".", "secondaryLabel": ">"},
    "slash": {"label": ";", "secondaryLabel": ":"},
    "shift_right": {"label": "Shift", "secondaryLabel": ""},
    "ctrl_left": {"label": "Ctrl", "secondaryLabel": ""},
    "meta_left": {"label": "Win", "secondaryLabel": ""},
    "alt_left": {"label": "Alt", "secondaryLabel": ""},
    "alt_right": {"label": "AltGr", "secondaryLabel": ""},
    "menu": {"label": "Menu", "secondaryLabel": ""},
    "up": {"label": "Up", "secondaryLabel": ""},
    "left": {"label": "Left", "secondaryLabel": ""},
    "down": {"label": "Down", "secondaryLabel": ""},
    "right": {"label": "Right", "secondaryLabel": ""},
    "home": {"label": "Home", "secondaryLabel": ""},
    "page_up": {"label": "PgUp", "secondaryLabel": ""},
    "page_down": {"label": "PgDn", "secondaryLabel": ""},
    "end": {"label": "End", "secondaryLabel": ""},
    "num_lock": {"label": "Num", "secondaryLabel": ""},
    "kp_div": {"label": "/", "secondaryLabel": ""},
    "kp_mul": {"label": "*", "secondaryLabel": ""},
    "kp_minus": {"label": "-", "secondaryLabel": ""},
    "kp_plus": {"label": "+", "secondaryLabel": ""},
    "kp_enter_top": {"label": "NEnt", "secondaryLabel": ""},
    "kp_dot": {"label": ",", "secondaryLabel": ""},
}
for _n in range(1, 13):
    LAYOUT_LABEL_OVERRIDES[f"f{_n}"] = {"secondaryLabel": ""}
