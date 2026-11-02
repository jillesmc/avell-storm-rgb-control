"""Visual v2 geometry: fractional units, gaps, overlap checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

WIDE_GAP_TOKEN = "__wide_gap__"


@dataclass(frozen=True)
class VisualLayoutSpec:
    version: int = 2
    key_gap: float = 0.15
    wide_gap: float = 1.0
    row_count: int = 7

    @classmethod
    def from_document(cls, doc: dict[str, Any]) -> VisualLayoutSpec | None:
        block = doc.get("visualLayout")
        if not isinstance(block, dict):
            return None
        version = int(block.get("version", 0))
        if version != 2:
            return None
        return cls(
            version=2,
            key_gap=float(block.get("keyGap", 0.15)),
            wide_gap=float(block.get("wideGap", 1.0)),
            row_count=int(block.get("rowCount", 7)),
        )


@dataclass(frozen=True)
class RectU:
    x: float
    y: float
    w: float
    h: float

    def overlaps(self, other: RectU, eps: float = 1e-6) -> bool:
        if self.x + self.w <= other.x + eps or other.x + other.w <= self.x + eps:
            return False
        if self.y + self.h <= other.y + eps or other.y + other.h <= self.y + eps:
            return False
        return True


def _as_float(value: Any, field: str, key_id: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key_id}: {field} must be a number") from exc


def rect_from_visual_v2(key_id: str, block: dict[str, Any]) -> RectU:
    for field in ("x", "y", "w", "h"):
        if field not in block:
            raise ValueError(f"{key_id}: visualV2 missing {field}")
    w = _as_float(block["w"], "w", key_id)
    h = _as_float(block["h"], "h", key_id)
    if w <= 0 or h <= 0:
        raise ValueError(f"{key_id}: visualV2 w and h must be > 0")
    return RectU(
        x=_as_float(block["x"], "x", key_id),
        y=_as_float(block["y"], "y", key_id),
        w=w,
        h=h,
    )


def rects_from_visual_parts_v2(key_id: str, parts: list[dict[str, Any]]) -> list[RectU]:
    if not parts:
        raise ValueError(f"{key_id}: visualPartsV2 must be non-empty")
    out: list[RectU] = []
    for i, part in enumerate(parts):
        for field in ("x", "y", "w", "h"):
            if field not in part:
                raise ValueError(f"{key_id}: visualPartsV2[{i}] missing {field}")
        w = _as_float(part["w"], "w", key_id)
        h = _as_float(part["h"], "h", key_id)
        if w <= 0 or h <= 0:
            raise ValueError(f"{key_id}: visualPartsV2[{i}] w and h must be > 0")
        out.append(
            RectU(
                x=_as_float(part["x"], "x", key_id),
                y=_as_float(part["y"], "y", key_id),
                w=w,
                h=h,
            )
        )
    return out


def collect_visual_rects(
    doc: dict[str, Any],
) -> list[tuple[str, RectU]]:
    spec = VisualLayoutSpec.from_document(doc)
    if spec is None:
        return []
    placed: list[tuple[str, RectU]] = []
    for row in doc.get("keys", []):
        if not isinstance(row, list):
            continue
        for entry in row:
            if not isinstance(entry, dict):
                continue
            key_id = str(entry.get("keyId", ""))
            if not key_id or key_id == "_spacer":
                continue
            if entry.get("visualHidden") is True:
                continue
            parts_v2 = entry.get("visualPartsV2")
            v2 = entry.get("visualV2")
            if parts_v2 is not None and v2 is not None:
                raise ValueError(f"{key_id}: use visualV2 or visualPartsV2, not both")
            if parts_v2 is not None:
                for rect in rects_from_visual_parts_v2(key_id, parts_v2):
                    placed.append((key_id, rect))
            elif v2 is not None:
                placed.append((key_id, rect_from_visual_v2(key_id, v2)))
    return placed


def _same_rect(a: RectU, b: RectU, eps: float = 1e-6) -> bool:
    return (
        abs(a.x - b.x) < eps
        and abs(a.y - b.y) < eps
        and abs(a.w - b.w) < eps
        and abs(a.h - b.h) < eps
    )


def find_overlaps(placed: list[tuple[str, RectU]]) -> list[str]:
    errors: list[str] = []
    for i, (id_a, rect_a) in enumerate(placed):
        for id_b, rect_b in placed[i + 1 :]:
            if _same_rect(rect_a, rect_b):
                continue
            if rect_a.overlaps(rect_b):
                errors.append(f"visual overlap: {id_a} and {id_b}")
    return errors


def layout_bounds(placed: list[tuple[str, RectU]]) -> tuple[float, float, float, float]:
    if not placed:
        return (0.0, 0.0, 21.0, 6.0)
    min_x = min(r.x for _, r in placed)
    min_y = min(r.y for _, r in placed)
    max_x = max(r.x + r.w for _, r in placed)
    max_y = max(r.y + r.h for _, r in placed)
    return (min_x, min_y, max_x, max_y)


RowSegment: TypeAlias = "tuple[str, float] | str"


def place_row(
    y: float,
    segments: list[RowSegment],
    *,
    key_gap: float,
    wide_gap: float,
) -> dict[str, RectU]:
    """Place keys left-to-right; segment WIDE_GAP_TOKEN inserts wide_gap."""
    x = 0.0
    out: dict[str, RectU] = {}
    for seg in segments:
        if seg == WIDE_GAP_TOKEN:
            x += wide_gap
            continue
        key_id, width = seg
        out[key_id] = RectU(x=x, y=y, w=width, h=1.0)
        x += width + key_gap
    return out


def merge_parts(
    base: dict[str, RectU],
    parts: dict[str, list[RectU]],
) -> dict[str, RectU | list[RectU]]:
    merged: dict[str, RectU | list[RectU]] = dict(base)
    for key_id, rects in parts.items():
        merged[key_id] = rects
    return merged
