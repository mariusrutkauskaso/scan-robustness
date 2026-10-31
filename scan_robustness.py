"""
Measure how far a scanned page can degrade before its QR code stops decoding.

WHY THIS EXISTS
---------------
Document pipelines that read a code off a scanned form are usually built and
demonstrated on a clean, generated PDF. They then meet a real scanner, and the
interesting question turns out not to be "does it work" but "at what point does
it stop working, and does it fail loudly or quietly".

This harness answers that with measurements instead of opinion. It builds a
synthetic form, degrades it the way a cheap scanner or a phone camera would,
and reports where decoding breaks.

No third-party documents are included. The test page is generated, so every
number below is reproducible by anyone running this file.

USAGE
-----
    pip install -r requirements.txt
    python scan_robustness.py
"""

from __future__ import annotations

import io
import math
import random
from dataclasses import dataclass

import qrcode
import zxingcpp
from PIL import Image, ImageDraw, ImageFilter

# A4-ish page rendered at this reference resolution, then scaled down to
# simulate lower scan settings. Starting high and reducing mirrors what a
# scanner actually does to a printed page.
REFERENCE_DPI = 400
PAGE_INCHES = (8.27, 11.69)

# The payload carries a prefix so that any unrelated code that happens to be
# on the page can be ignored rather than mistaken for the document ID.
PAYLOAD = "DEMO-PO:10001"

# Physical size of the printed code. This is the single most important
# variable in the whole exercise: a 24 mm code at 100 dpi is about 94 pixels,
# and that is close to the floor.
QR_SIDE_MM = 24.0


# ----------------------------------------------------------------------
#  Building the test page
# ----------------------------------------------------------------------

def make_page(payload: str = PAYLOAD) -> Image.Image:
    """Generate a synthetic form carrying a QR code, at REFERENCE_DPI."""
    width = int(PAGE_INCHES[0] * REFERENCE_DPI)
    height = int(PAGE_INCHES[1] * REFERENCE_DPI)
    page = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(page)

    # A few ruled boxes, so the page is not a QR code floating in white and
    # the decoder has some competing structure to deal with.
    margin = int(0.6 * REFERENCE_DPI)
    draw.rectangle([margin, margin, width - margin, margin + 180], outline=0, width=4)
    for i in range(6):
        top = margin + 320 + i * 150
        draw.rectangle([margin, top, width - margin, top + 130], outline=0, width=3)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    code = qr.make_image(fill_color="black", back_color="white").convert("L")

    side = int(QR_SIDE_MM / 25.4 * REFERENCE_DPI)
    code = code.resize((side, side), Image.NEAREST)
    page.paste(code, (width - margin - side, margin + 260))
    return page


# ----------------------------------------------------------------------
#  Degrading it
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Scan:
    """One simulated scanning condition."""

    dpi: int
    blur: float = 1.0
    noise: int = 30
    jpeg_quality: int | None = None
    rotate: float = 0.0


def degrade(page: Image.Image, s: Scan, seed: int = 7) -> Image.Image:
    """Apply one scanning condition to the reference page."""
    scale = s.dpi / REFERENCE_DPI
    out = page.resize(
        (max(1, int(page.width * scale)), max(1, int(page.height * scale))),
        Image.LANCZOS,
    )

    if s.rotate:
        out = out.rotate(s.rotate, expand=True, fillcolor=255, resample=Image.BICUBIC)

    if s.blur:
        out = out.filter(ImageFilter.GaussianBlur(s.blur))

    if s.noise:
        rng = random.Random(seed)
        px = out.load()
        for y in range(out.height):
            for x in range(out.width):
                px[x, y] = min(255, max(0, px[x, y] + rng.randint(-s.noise, s.noise)))

    if s.jpeg_quality is not None:
        buf = io.BytesIO()
        out.save(buf, "JPEG", quality=s.jpeg_quality)
        buf.seek(0)
        out = Image.open(buf).convert("L")

    return out


def decode(img: Image.Image) -> str | None:
    """Return the document ID, or None if no matching code could be read."""
    for result in zxingcpp.read_barcodes(img):
        if result.text.startswith("DEMO-PO:"):
            return result.text
    return None


# ----------------------------------------------------------------------
#  Obscuring parts of the code
# ----------------------------------------------------------------------

def qr_box(img: Image.Image) -> tuple[int, int, int, int] | None:
    """Locate the code on the page so that parts of it can be covered."""
    found = zxingcpp.read_barcodes(img)
    if not found:
        return None
    p = found[0].position
    pts = [p.top_left, p.top_right, p.bottom_right, p.bottom_left]
    xs = [pt.x for pt in pts]
    ys = [pt.y for pt in pts]
    return min(xs), min(ys), max(xs), max(ys)


def cover(img: Image.Image, box, region: str, fraction: float) -> Image.Image:
    """
    Black out part of the code, imitating handwriting or a stamp.

    `region` is "centre" for the data area, or one of the corner names. The
    distinction matters: the three corner squares are the finder patterns the
    decoder uses to locate the code at all.
    """
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    side = math.sqrt(fraction)
    out = img.copy()
    draw = ImageDraw.Draw(out)

    if region == "centre":
        cx, cy = x0 + w / 2, y0 + h / 2
        draw.rectangle(
            [cx - w * side / 2, cy - h * side / 2, cx + w * side / 2, cy + h * side / 2],
            fill=0,
        )
    elif region == "top-left":
        draw.rectangle([x0, y0, x0 + w * side, y0 + h * side], fill=0)
    elif region == "bottom-left":
        draw.rectangle([x0, y1 - h * side, x0 + w * side, y1], fill=0)
    elif region == "bottom-right":
        draw.rectangle([x1 - w * side, y1 - h * side, x1, y1], fill=0)
    else:
        raise ValueError(f"unknown region: {region}")

    return out


# ----------------------------------------------------------------------
#  Reporting
# ----------------------------------------------------------------------

def _row(label: str, detail: str, result: str | None) -> str:
    verdict = f"`{result}`" if result else "**not decoded**"
    return f"| {label} | {detail} | {verdict} |"


def main() -> None:
    page = make_page()
    qr_px_at = lambda dpi: round(QR_SIDE_MM / 25.4 * dpi)

    print(f"Reference page: {page.width}x{page.height} px at {REFERENCE_DPI} dpi")
    print(f"Printed code size: {QR_SIDE_MM:.0f} mm square\n")

    print("## Scan resolution\n")
    print("| Scan setting | Code size | Result |")
    print("|---|---|---|")
    for dpi in (75, 100, 150, 200, 300):
        img = degrade(page, Scan(dpi=dpi))
        print(_row(f"{dpi} dpi", f"{qr_px_at(dpi)} px", decode(img)))

    print("\n## Adverse conditions\n")
    print("| Condition | Detail | Result |")
    print("|---|---|---|")
    cases = [
        ("Cheap scanner", "150 dpi, JPEG quality 40", Scan(150, blur=1.2, noise=35, jpeg_quality=40)),
        ("Cheap scanner", "200 dpi, JPEG quality 40", Scan(200, blur=1.2, noise=35, jpeg_quality=40)),
        ("Page fed askew", "200 dpi, rotated 7 degrees", Scan(200, rotate=7)),
        ("Page fed upside-down", "200 dpi, rotated 180 degrees", Scan(200, rotate=180)),
        ("Out of focus", "150 dpi, heavy blur", Scan(150, blur=2.5)),
    ]
    for label, detail, s in cases:
        print(_row(label, detail, decode(degrade(page, s))))

    print("\n## Parts of the code obscured\n")
    print("Tested at 300 dpi, so that resolution is not the limiting factor.\n")
    clean = degrade(page, Scan(dpi=300, blur=0.4, noise=5))
    box = qr_box(clean)
    if box is None:
        print("Reference scan did not decode; cannot run occlusion tests.")
        return

    print("| Area covered | Share of the code | Result |")
    print("|---|---|---|")
    for frac in (0.05, 0.10, 0.15, 0.25):
        img = cover(clean, box, "centre", frac)
        print(_row("Data area (centre)", f"{int(frac * 100)}%", decode(img)))
    for region in ("top-left", "bottom-left", "bottom-right"):
        img = cover(clean, box, region, 0.05)
        note = "finder pattern" if region != "bottom-right" else "no finder pattern here"
        print(_row(f"Corner: {region}", f"5% — {note}", decode(img)))


if __name__ == "__main__":
    main()
