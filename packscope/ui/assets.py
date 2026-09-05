"""Image assets loader for the UI.

Loads PNGs from ``packscope/assets`` as CTkImage, scaled by height (aspect
kept), with an optional monochrome tint (recolour opaque pixels to one colour,
preserving the alpha shape) so a logo reads cleanly on the dark surfaces. Results
are cached. Missing files / missing Pillow degrade to None (callers fall back).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_cache: dict = {}


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _autocrop(img):
    """Trim a uniform border (transparent or solid, judged by the top-left pixel)."""
    from PIL import Image, ImageChops
    bg = Image.new("RGBA", img.size, img.getpixel((0, 0)))
    bbox = ImageChops.difference(img, bg).getbbox()
    return img.crop(bbox) if bbox else img


def load(name: str, height: int, tint: Optional[str] = None, crop: bool = False):
    """Return a CTkImage for assets/<name>, scaled to ``height`` px (aspect kept).
    ``tint`` (hex) recolours opaque pixels; ``crop`` trims a uniform border.
    Returns None if unavailable."""
    key = (name, height, tint, crop)
    if key in _cache:
        return _cache[key]
    path = _ASSETS / name
    try:
        import customtkinter as ctk
        from PIL import Image
    except Exception:  # pragma: no cover - env dependent
        return None
    if not path.exists():
        return None
    img = Image.open(path).convert("RGBA")
    if crop:
        img = _autocrop(img)
    if tint:
        r, g, b = _hex_to_rgb(tint)
        img.putdata([(r, g, b, a) for (_, _, _, a) in img.getdata()])
    w, h = img.size
    size = (max(1, round(w * height / h)), height)
    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
    _cache[key] = ctk_img
    return ctk_img


def exists(name: str) -> bool:
    return (_ASSETS / name).exists()
