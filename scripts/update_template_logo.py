"""Embed a high-resolution, aspect-correct logo in the ShimentoX template."""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageChops


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPOSITORY_ROOT / "templates" / "shimentox.docx"
BRAND_ASSET = REPOSITORY_ROOT / "assets" / "shimento_logo.png"
EMBEDDED_IMAGE = "word/media/image1.png"
HEADER_XML = "word/header1.xml"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _content_crop(image: Image.Image, tolerance: int = 18, padding: int = 4) -> Image.Image:
    """Remove the large solid border without altering any logo pixels."""
    rgba = image.convert("RGBA")
    background = Image.new("RGBA", rgba.size, rgba.getpixel((0, 0)))
    difference = ImageChops.difference(rgba, background).convert("RGB")
    mask = difference.point(lambda value: 255 if value > tolerance else 0).convert("L")
    box = mask.getbbox()
    if box is None:
        raise ValueError("The supplied image contains no visible logo content")
    left, top, right, bottom = box
    box = (
        max(0, left - padding),
        max(0, top - padding),
        min(rgba.width, right + padding),
        min(rgba.height, bottom + padding),
    )
    return rgba.crop(box)


def update(source: Path) -> tuple[int, int]:
    source = source.resolve()
    cropped = _content_crop(Image.open(source))
    BRAND_ASSET.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(BRAND_ASSET, format="PNG", optimize=True)
    logo_bytes = io.BytesIO()
    cropped.save(logo_bytes, format="PNG", optimize=True)

    with tempfile.TemporaryDirectory(prefix="resume-logo-") as directory:
        unpacked = Path(directory) / "docx"
        with zipfile.ZipFile(TEMPLATE) as archive:
            archive.extractall(unpacked)

        (unpacked / EMBEDDED_IMAGE).write_bytes(logo_bytes.getvalue())
        header_path = unpacked / HEADER_XML
        tree = ET.parse(header_path)
        root = tree.getroot()
        inline_extent = root.find(f".//{{{WP_NS}}}extent")
        picture_extent = root.find(f".//{{{A_NS}}}xfrm/{{{A_NS}}}ext")
        if inline_extent is None or picture_extent is None:
            raise ValueError("Template header image dimensions were not found")

        width_emu = int(inline_extent.attrib["cx"])
        height_emu = round(width_emu * cropped.height / cropped.width)
        for extent in (inline_extent, picture_extent):
            extent.set("cx", str(width_emu))
            extent.set("cy", str(height_emu))
        tree.write(header_path, encoding="UTF-8", xml_declaration=True)

        replacement = Path(directory) / "shimentox.docx"
        with zipfile.ZipFile(replacement, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(unpacked.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(unpacked).as_posix())
        shutil.copyfile(replacement, TEMPLATE)

    return cropped.size


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: update_template_logo.py path/to/logo.png")
    width, height = update(Path(sys.argv[1]))
    print(f"Embedded {width}x{height} logo into {TEMPLATE}")
