from __future__ import annotations

import base64
from pathlib import Path

import pytest
from PIL import Image

from wardrobe_rag.images import ImageLoader


def test_loads_frontend_data_url_and_restricted_uploaded_file(tmp_path, image_data_url):
    public_root = tmp_path / "public"
    uploads = tmp_path / "uploads"
    public_root.mkdir()
    uploads.mkdir()
    target = uploads / "photo.png"
    target.write_bytes(base64.b64decode(image_data_url.split(",", 1)[1]))
    loader = ImageLoader(public_root, uploads)
    assert loader.load(image_data_url).mode == "RGB"
    assert loader.load(str(target)).size == (24, 32)


def test_rasterizes_all_ten_actual_frontend_svg_assets():
    repo = Path(__file__).resolve().parents[2]
    loader = ImageLoader(repo / "public")
    assets = list((repo / "public" / "clothes").glob("*.svg"))
    assert len(assets) == 10
    for asset in assets:
        image = loader.load("/clothes/" + asset.name)
        assert image.mode == "RGB"
        assert image.width > 0 and image.height > 0


@pytest.mark.parametrize("source", ["https://example.com/image.png", "http://127.0.0.1/image.png", "file:///C:/Windows/win.ini"])
def test_remote_and_file_urls_are_not_fetchable(tmp_path, source):
    with pytest.raises(ValueError):
        ImageLoader(tmp_path).load(source)


def test_path_cannot_escape_public_or_upload_root(tmp_path):
    public_root = tmp_path / "public"
    public_root.mkdir()
    secret = tmp_path / "outside.png"
    Image.new("RGB", (4, 4)).save(secret)
    loader = ImageLoader(public_root)
    for source in (str(secret), "/../outside.png", "/clothes/../../outside.png"):
        with pytest.raises(ValueError):
            loader.load(source)


def test_rejects_oversized_upload_and_malformed_image(tmp_path, image_data_url):
    with pytest.raises(ValueError):
        ImageLoader(tmp_path, max_bytes=8).load(image_data_url)
    malformed = "data:image/png;base64," + base64.b64encode(b"not-a-png").decode("ascii")
    with pytest.raises((OSError, ValueError)):
        ImageLoader(tmp_path).load(malformed)


def test_svg_cannot_load_external_resources(tmp_path):
    target = tmp_path / "unsafe.svg"
    target.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
        '<image href="https://example.com/private.png" width="20" height="20"/>'
        '</svg>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        ImageLoader(tmp_path).load(str(target))
