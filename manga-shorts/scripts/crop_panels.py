"""Split images/page1.png into 4 panel images by detecting the white gutters.

If the art was made one image per panel (images/panel1.png .. panel4.png, the vertical
format), those are copied to panels/ as they are.

Handles a vertical 4-koma strip (top to bottom) and a 2x2 grid (right to left,
then top to bottom, as manga is read). Falls back to an equal vertical split.

Usage: python3 scripts/crop_panels.py <job> [--image images/page1.png]
"""

import argparse
import json

from PIL import Image

from common import job_dir

WHITE = 235          # a pixel at or above this luminance counts as background
GUTTER_RATIO = 0.97  # a row/column this white is treated as a gutter
MIN_BAND = 0.08      # bands thinner than this fraction of the page are ignored


def bands(profile: list[float], length: int) -> list[tuple[int, int]]:
    """Return (start, end) runs where the profile is not gutter."""
    runs, start = [], None
    for i, white in enumerate(profile + [1.0]):
        if white < GUTTER_RATIO and start is None:
            start = i
        elif white >= GUTTER_RATIO and start is not None:
            if i - start >= length * MIN_BAND:
                runs.append((start, i))
            start = None
    return runs


def white_profile(img: Image.Image, axis: str) -> list[float]:
    mask = img.point(lambda v: 255 if v >= WHITE else 0)
    w, h = mask.size
    if axis == "rows":
        col = mask.resize((1, h), Image.Resampling.BOX)
        return [col.getpixel((0, y)) / 255 for y in range(h)]
    row = mask.resize((w, 1), Image.Resampling.BOX)
    return [row.getpixel((x, 0)) / 255 for x in range(w)]


def detect(page: Image.Image) -> tuple[list[tuple[int, int, int, int]], str]:
    gray = page.convert("L")
    w, h = gray.size
    rows = bands(white_profile(gray, "rows"), h)
    boxes = []
    for top, bottom in rows:
        strip = gray.crop((0, top, w, bottom))
        cols = bands(white_profile(strip, "cols"), w)
        # Manga reads right to left within a row.
        for left, right in sorted(cols, reverse=True):
            boxes.append((left, top, right, bottom))
    if len(boxes) == 4:
        return boxes, "detected"
    step = h / 4
    return [(0, round(i * step), w, round((i + 1) * step)) for i in range(4)], "equal-split"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job")
    parser.add_argument("--image", default="images/page1.png")
    args = parser.parse_args()

    path = job_dir(args.job)
    singles = [path / "images" / f"panel{i}.png" for i in range(1, 5)]
    if all(p.exists() for p in singles):
        for i, src in enumerate(singles, 1):
            img = Image.open(src).convert("RGB")
            # drop the plain white margin some generations leave around the panel border
            ink = img.convert("L").point(lambda v: 255 if v < WHITE else 0).getbbox()
            (img.crop(ink) if ink else img).save(path / "panels" / f"{i}.png")
        (path / "panels" / "boxes.json").write_text(
            json.dumps({"method": "single-panels"}) + "\n", encoding="utf-8")
        print("single-panels: copied images/panel1-4.png")
        return
    page = Image.open(path / args.image).convert("RGB")
    boxes, method = detect(page)
    for i, box in enumerate(boxes, 1):
        page.crop(box).save(path / "panels" / f"{i}.png")
    (path / "panels" / "boxes.json").write_text(
        json.dumps({"method": method, "boxes": boxes}) + "\n", encoding="utf-8")
    print(f"{method}: {boxes}")
    if method != "detected":
        print("warning: gutters not found, used equal split; check panels/*.png")


if __name__ == "__main__":
    main()
