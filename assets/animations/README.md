🇺🇸 English · [🇧🇷 Português](README.pt-BR.md)

# Animation file format

⏱️ **Reading time:** ~3 min

> **TL;DR**
> - Plain text, **one instruction per line**. It edits a **colour map** (position → colour), and `apply` sends it to the keyboard.
> - Coordinates are **device coordinates**: `(row 0, col 0)` is the **bottom-left** corner.
> - Run with `avell-storm-rgb keyboard play-animation --file <script>` (or pipe into stdin).

**Read this if…** you want to write or understand a per-key animation script.

---

## 🛠️ Commands

| Command | Effect |
|---------|--------|
| `pos R C r,g,b` | Set the colour of (row `R`, column `C`) to `r,g,b` in the colour map |
| `apply` | Actually set the keyboard backlight from the current colour map |
| `clear` | Clear the colour map |
| `wait N` | Wait `N` seconds (`N` may be a float) |
| `brightness B` | Set backlight brightness to `B` (integer **0–50**) |
| `shift Rdiff Cdiff` | Add `Rdiff` to the row and `Cdiff` to the column of every entry (entries pushed off the grid are dropped) |

## ⚠️ Notes

- **Comments:** lines starting with `#` are ignored. A line starting with `/*` opens a comment block and `*/` closes it. Blocks may be nested.
- **`shift 0 -1`** moves everything one column to the left.
- **`(row 0, col 0)` is the bottom-left corner.** This is the *device* orientation; the GUI per-key grid shows row 0 at the top.
- The examples were made for **16 × 6** positions (XMG Fusion 15). The controller grid is 6 × 21.

## 🧭 Examples in this folder

| File | Shows |
|------|-------|
| `gaming_mode` | WASD and arrow keys in red (like the *Gaming mode* in XMG Control Center) |
| `xmg_f15` | The text `XMG F15` |
| `manjaro_i3` | Static map: Fn / F-keys and i3 mod keys in white, everything else in Manjaro blue-green (QWERTZ) |
| `sine_wave.py` | Generates a sine wave; pipe its output into the CLI |

```bash
python assets/animations/sine_wave.py | avell-storm-rgb keyboard play-animation
```

Run it from the repo root, in the environment that has the CLI installed (e.g. `uv run`).
