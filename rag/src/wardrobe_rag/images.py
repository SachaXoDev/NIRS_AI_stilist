"""Bounded, local-only image input. SVG is rasterized; no external resources."""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import re
from pathlib import Path
from urllib.parse import unquote

from PIL import Image, ImageOps


class ImageLoader:
    def __init__(self, public_root: Path, upload_root: Path | None = None,
                 max_bytes: int = 10 * 1024 * 1024, max_pixels: int = 25_000_000):
        self.public_root = Path(public_root).resolve()
        self.upload_root = Path(upload_root).resolve() if upload_root else None
        self.max_bytes = max_bytes
        self.max_pixels = max_pixels

    def _read(self, source: str) -> tuple[bytes, bool]:
        if not source or len(source) > self.max_bytes * 2:
            raise ValueError("Image is empty or exceeds the input limit")
        if source.startswith("data:"):
            match = re.fullmatch(r"data:image/(png|jpeg|jpg|webp);base64,([A-Za-z0-9+/=\r\n]+)", source)
            if not match:
                raise ValueError("Only base64 PNG/JPEG/WebP image data is allowed")
            try:
                raw = base64.b64decode(match.group(2), validate=True)
            except (ValueError, binascii.Error) as exc:
                raise ValueError("Invalid image base64") from exc
            is_svg = False
        else:
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", source) or source.startswith("\\\\"):
                raise ValueError("Remote image fetching is disabled; upload the image first")
            source = unquote(source)
            raw_path = Path(source)
            # UI assets use /clothes/file.svg; native absolute paths stay native.
            if source.startswith("/") and not raw_path.exists():
                candidate = self.public_root / source.lstrip("/")
            elif raw_path.is_absolute():
                candidate = raw_path
            else:
                candidate = (self.upload_root or self.public_root) / raw_path
            candidate = candidate.resolve()
            roots = [self.public_root] + ([self.upload_root] if self.upload_root else [])
            if not any(candidate.is_relative_to(root) for root in roots):
                raise ValueError("Image path is outside configured public/upload roots")
            if candidate.stat().st_size > self.max_bytes:
                raise ValueError("Image exceeds byte limit")
            raw = candidate.read_bytes()
            is_svg = candidate.suffix.lower() == ".svg"
        if len(raw) > self.max_bytes:
            raise ValueError("Image exceeds byte limit")
        return raw, is_svg

    def load(self, source: str) -> Image.Image:
        raw, is_svg = self._read(source)
        if is_svg:
            svg = raw.decode("utf-8")
            # No XML entity expansion or network/local resources in uploaded SVG.
            if re.search(r"<!DOCTYPE|<!ENTITY|<\s*(?:script|image|use|foreignObject)\b|(?:href|src)\s*=|url\(\s*['\"]?(?!#)", svg, re.I):
                raise ValueError("SVG external resources and active content are forbidden")
            from resvg_py import svg_to_bytes
            raw = svg_to_bytes(svg_string=svg, width=448, height=560)
        try:
            with Image.open(io.BytesIO(raw)) as opened:
                if opened.width * opened.height > self.max_pixels:
                    raise ValueError("Image exceeds pixel limit")
                opened.load()
                image = ImageOps.exif_transpose(opened).convert("RGBA")
                background = Image.new("RGBA", image.size, "white")
                background.alpha_composite(image)
                return background.convert("RGB")
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ValueError("Image exceeds safe dimensions") from exc

    __call__ = load

    def digest(self, source: str) -> str:
        raw, _ = self._read(source)
        return hashlib.sha256(raw).hexdigest()
