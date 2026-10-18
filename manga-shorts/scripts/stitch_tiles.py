"""Rebuild a Gemini image from browser screenshots (the Gemini app gives no file to download here).

The image is shown at its natural size at the top-left of the viewport and captured in vertical
tiles: the first at offset 0, the next at the given CSS offsets. Screenshots are scaled from CSS
pixels by screenshot_width / viewport_css_width.

Usage:
  python3 scripts/stitch_tiles.py OUT --size 572x1024 --viewport 1536x834 TILE0 [TILE1 --offset 190]
"""

import argparse

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out")
    parser.add_argument("tiles", nargs="+")
    parser.add_argument("--size", required=True, help="image size in CSS px, WxH")
    parser.add_argument("--viewport", required=True, help="viewport size in CSS px, WxH")
    parser.add_argument("--offset", type=int, action="append", default=[],
                        help="CSS y offset of each tile after the first")
    args = parser.parse_args()

    width, height = map(int, args.size.split("x"))
    view_w, _ = map(int, args.viewport.split("x"))
    tiles = [Image.open(t).convert("RGB") for t in args.tiles]
    offsets = [0, *args.offset]
    if len(offsets) != len(tiles):
        parser.error("give one --offset per tile after the first")

    scale = tiles[0].width / view_w
    w, h = round(width * scale), round(height * scale)
    page = Image.new("RGB", (w, h), "white")
    filled = 0
    for tile, offset in zip(tiles, offsets):
        top = round(offset * scale)
        start = filled - top
        page.paste(tile.crop((0, start, w, min(tile.height, h - top))), (0, filled))
        filled = min(h, top + tile.height)
    page.save(args.out)
    print(args.out, page.size)


if __name__ == "__main__":
    main()
