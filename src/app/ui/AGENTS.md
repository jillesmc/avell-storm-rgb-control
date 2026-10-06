# AGENTS.md — `src/app/ui/` (QML, Kirigami, KDE HIG)

Applies to `src/app/ui/**/*.qml`. It wins over [`../AGENTS.md`](../AGENTS.md) on QML components and theming;
the Python side follows `../AGENTS.md`. Repo-wide rules: [`/AGENTS.md`](../../../AGENTS.md).

Official references: [KDE HIG](https://hig.kde.org/) ·
[Displaying content](https://develop.kde.org/hig/displaying_content/) ·
[Kirigami colours](https://develop.kde.org/docs/getting-started/kirigami/style-colors/) ·
[Kirigami QML types](https://api.kde.org/org-kde-kirigami-qmlmodule.html) ·
[Theme properties](https://api.kde.org/qml-org-kde-kirigami-platform-theme.html)

## Component choice (in order)

1. **Kirigami** (`org.kde.kirigami`) when it has a fitting control: `ScrollablePage`, `Page`, `FormLayout`,
   `Heading`, `Separator`, `InlineMessage`, `Chip`, `AboutPage`, `org.kde.kirigami.delegates` (`SubtitleDelegate`, …).
2. **Qt Quick Controls 2** for the rest (`Slider`, `SpinBox`, `ComboBox`, …). Never set `QtQuick.Controls.Universal` globally.
3. **Custom** only in `components/` when 1–2 don't fit (keyboard layout, colour well, busy overlay).

The QQC2 style is chosen in `../qml_paths.py`: `org.kde.desktop` (Breeze) if present, else `Fusion`.
Respect `QT_QUICK_CONTROLS_STYLE` / `AVELL_RGB_QQC2_STYLE`.

## Theme and layout

- Colour hand-drawn `Rectangle`s and labels with **`Kirigami.Theme`**. No raw hex in chrome (sidebars, toolbars, dialogs).
- Use `Kirigami.Theme.colorSet` / `inherit` when sidebars and content should differ.
- Blend with **`Kirigami.ColorUtils.linearInterpolation`**, not `Qt.darker` / `Qt.lighter` (missing in some PySide Qt builds).
- **Check a `Kirigami.Theme.*` property exists before binding it** (e.g. `separatorColor`, not `dividerColor`).
  Undefined values cause QColor binding errors.
- Spacing from **`Kirigami.Units`**, not magic numbers.

## Lists, navigation, overlays

- Rows: `ItemDelegate` / `SwitchDelegate` / Kirigami delegates, so hover and selection match Breeze. Don't re-implement them.
- **`ListView` section headers:** title and `Kirigami.Separator` on the **same row** (`RowLayout { Label; Separator { Layout.fillWidth: true } }`),
  vertically centred. No full-width line above the title.
- More than ~4–5 destinations on desktop: use sidebar/list navigation, not `NavigationTabBar`.
- Full view → push a `Kirigami.Page`. Read-only auxiliary scroll → `OverlaySheet`. Input or confirmation → `Kirigami.Dialog`.
  Give overlays a visible outline on dark themes.
- Icons: `org.kde.kirigami.primitives.Icon` with freedesktop names and a `fallback`.
- Critical information must **not** live only in a tooltip. Use inline text or `Kirigami.ContextualHelpButton`.

## Contract with Python

- QML talks to Python only through `App` (`App.keyboard`, `App.ledBar`, `App.state`, `App.devices`). Never USB.
- Debounce rapid control changes (pattern: 200 ms `Timer` + dirty flag, see `pages/KeyboardPage.qml`).
- Re-read backend state through epoch properties (`keyGridEpoch`, `deviceConnectionEpoch`) instead of polling.

## Tests (gate)

- Keep `objectName`s that tests look up (`primarySidebar`, `keyboardSubNav`, `ledSubNav`, `deviceContentStack`, …).
- Changing `main.qml` or a shared page: add or update a test in `tests/` (`test_gui_shell.py`, `test_gui_pages.py`).
  Go red → green → refactor.
- Run `uv run pytest -m "not hardware"`. Without Kirigami, GUI tests skip; that is not a regression.
- On a Plasma machine, smoke-test manually with `make gui` (tabs, scroll, device list).

## Anti-patterns this repo already hit

- Hard `#000` sidebars disconnected from `Kirigami.Theme`.
- Custom list rows duplicating `ItemDelegate` hover/selection.
- Section header line on one row and title on another.
- Unverified `Kirigami.Theme.*` names → `undefined` → QColor errors.
- `Qt.darker` / `Qt.lighter` for theme tuning.
