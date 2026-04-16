---
name: kirigami-hig-ux
description: >-
  KDE Human Interface Guidelines (HIG) and Kirigami UI/UX patterns for QML:
  lists, delegates, theme colors, dialogs/sheets, sections, and accessibility.
  Use when designing or refactoring Kirigami QML, navigation, sidebars, or
  chrome in Plasma-oriented apps (especially this repo’s src/app/ui).
---

# Kirigami UI/UX (KDE HIG)

Primary sources (prefer reading these when unsure):

- [KDE Human Interface Guidelines](https://hig.kde.org/)
- [Displaying content (HIG)](https://develop.kde.org/hig/displaying_content/)
- [Colors and themes in Kirigami](https://develop.kde.org/docs/getting-started/kirigami/style-colors/)
- [Kirigami overview](https://develop.kde.org/frameworks/kirigami/)
- [Kirigami delegates QML module](https://api.kde.org/org-kde-kirigami-delegates-qmlmodule.html)
- [Kirigami QML types](https://api.kde.org/org-kde-kirigami-qmlmodule.html)

## Principles (HIG)

- **Simple by default, powerful when needed** — scope features to real users; avoid cluttering chrome.
- **Maximize main content** — drop unnecessary frames, padding, and duplication around the central task.
- **Under-promise, over-deliver** — polish fewer flows well instead of many half-finished ones.
- **Bold the active item** in lists/grids where it marks the current selection (HIG lists section).

## Colors and theme (`Kirigami.Theme`)

- Use **`Kirigami.Theme`** (attached) for any **`Rectangle` / chrome / labels** you color by hand. Avoid raw `#hex` / named colors in **toolbars, dialogs, and sidebars** — poor contrast when the user switches light/dark schemes (accessibility).
- Kirigami / QQC2 controls already follow the palette when you do **not** override backgrounds.
- **`Kirigami.Theme.colorSet`** (`Window`, `View`, `Button`, `Selection`, `Tooltip`, `Complementary`) + **`inherit`**: use the right set for sidebars vs content (see style-colors doc). Children inherit unless `inherit: false`.
- For **blends** (e.g. slightly darker sidebar), prefer **`Kirigami.ColorUtils.linearInterpolation`** over **`Qt.darker` / `Qt.lighter`**: those globals are **missing or undefined** in some QML/Qt builds bundled with PySide wheels.
- **Verify properties exist** on your target KF6: consult [Theme QML docs](https://api.kde.org/qml-org-kde-kirigami-platform-theme.html). Do **not** assume names from other toolkits (e.g. use **`separatorColor`**, not a non-existent `dividerColor`).

## Lists and grids

- Prefer **`ListView`** for mostly-text rows; **`GridView`** for mostly visual tiles or wide layouts.
- Implement rows as **`ItemDelegate` / `RadioDelegate` / `SwitchDelegate`** (Qt Quick Controls) so **Breeze / org.kde.desktop** styling and **hover** match System Settings.
- If you need subtitles or richer layout, use **`org.kde.kirigami.delegates`** (`SubtitleDelegate`, `SwitchSubtitleDelegate`, …) instead of reinventing list rows.
- **Alternating / extra columns**: HIG recommends using theme appropriately for items with subtitles or trailing widgets.
- **Add** list actions as **`Kirigami.Action`** on **`Kirigami.InlineViewHeader`**; **remove** actions belong **on the row**, visible (not hover-only surprise).
- **Many tabs** (desktop ≈ >4–5): prefer **sidebar / list navigation** over `NavigationTabBar` (HIG).

### `ListView` **sections** (Plasma / Kirigami gallery pattern)

- **`section.delegate`**: section **title and horizontal rule belong on the same row** — e.g. `RowLayout { Label; Kirigami.Separator { Layout.fillWidth: true } }`, vertically centered. **Do not** stack a full-width line **above** the title unless the design explicitly requires it; Plasma Settings uses **label + trailing line**.
- Keep the first section’s header minimal if it has no title (small top spacing only).

## Page vs OverlaySheet vs Dialog

From HIG *Displaying content*:

- **New full (or nearly full) view** → push a **`Kirigami.Page`** on the stack.
- **Auxiliary, narrow, read-only scrollable** content → **`Kirigami.OverlaySheet`** (not for primary input; not if it never scrolls).
- **User input / confirmations / most modal tasks** → **`Kirigami.Dialog`** (dialogs module).
- **Popups / overlays**: ensure a **visible outline** on dark themes so they don’t melt into the background.

## Icons

- Prefer **`org.kde.kirigami.primitives.Icon`** with **freedesktop icon names** for custom layouts. **`IconImage`** from Qt Quick Controls is **not always** available in the QML types exposed to the app; if you use it, confirm on the minimum Qt target.
- **`fallback`** icon name when the primary name may be missing.

## Tooltips and help

- **Critical** instructions must **not** be tooltip-only (touch / discoverability).
- Short hints: tooltip or inline; longer or must-read: **`Kirigami.ContextualHelpButton`** or inline expandable “Details” (HIG).

## Testing and repo specifics

- After shell or navigation changes, preserve **`objectName`** contracts used in **`tests/`** (see project rule `kirigami-plasma6-qml.mdc`).
- Run **`uv run pytest -m "not hardware"`** when QML structure changes.

## Anti-patterns (this repo learned the hard way)

- Hard **#000** sidebars disconnected from **`Kirigami.Theme`**.
- **Custom** list rows duplicating `ItemDelegate` hover/selection without a strong reason.
- **Section headers**: line on one row, title on another — **wrong** vs Plasma.
- **Unverified** `Kirigami.Theme.*` property names → `undefined` → QColor binding errors at runtime.
- Relying on **`Qt.darker` / `Qt.lighter`** in QML for theme tuning without checking the deployed Qt.

## Related project files

- Rule: [.cursor/rules/kirigami-plasma6-qml.mdc](../../rules/kirigami-plasma6-qml.mdc)
- Rule: [.cursor/rules/kirigami-hig-ux.mdc](../../rules/kirigami-hig-ux.mdc)
- Skill: [kirigami-plasma6-gui](../kirigami-plasma6-gui/SKILL.md) — PySide6, `qml_paths`, CI
