"""Generate images with the Gemini API instead of pasting prompts into the Gemini app.

  character  → assets/characters/guide.png from the prompt in assets/characters/guide-prompt.md
  <job>      → each optional manga image listed in <job>/prompts.md ("## images/manga1.png"
               followed by a ``` prompt block), 3:4 portrait, attaching the character sheet.
               The product is never drawn: videos show its official photo.

This is optional and paid: the Gemini API is billed separately from a Google AI Pro
subscription (set GEMINI_API_KEY). The default 0-yen flow pastes prompts.md into the
Gemini app instead. A replaced image is kept as images/rejected-<name>-<n>.png.

Retry hints: a line "- retry: <hint>" at the end of prompts.md is added to every prompt.

Usage:
  python3 scripts/gen_art.py character
  python3 scripts/gen_art.py <job> [--model MODEL]
"""

import argparse
import io
import os
import re
import sys
from pathlib import Path

from common import ROOT, job_dir

DEFAULT_MODEL = "gemini-2.5-flash-image"
CHARACTER_DIR = ROOT / "assets" / "characters"
FENCE = re.compile(r"```\n(.*?)\n```", re.S)
IMAGE = re.compile(r"^## (\S+\.png)\s*\n+```\n(.*?)\n```", re.S | re.M)
RETRY = re.compile(r"^- retry:\s*(.+)$", re.M)


def character_prompt(path: Path) -> str:
    found = FENCE.search(path.read_text(encoding="utf-8"))
    if not found:
        sys.exit(f"no ``` prompt block in {path}")
    return found.group(1)


def image_prompts(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    hints = "".join(f"\nFix from the last attempt: {h.strip()}" for h in RETRY.findall(text))
    return {out: body + hints for out, body in IMAGE.findall(text)}


def generate(prompt: str, images: list[Path], aspect: str, model: str, out: Path) -> None:
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
    except ImportError:
        sys.exit("pip install google-genai pillow")
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY is not set (Google AI Studio → Get API key).")

    client = genai.Client()
    response = client.models.generate_content(
        model=model,
        contents=[prompt, *[Image.open(p) for p in images]],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=aspect)),
    )
    for candidate in response.candidates or []:
        for part in candidate.content.parts if candidate.content else []:
            if part.inline_data and part.inline_data.data:
                if out.exists():
                    n = len(list(out.parent.glob(f"rejected-{out.stem}-*.png"))) + 1
                    out.rename(out.parent / f"rejected-{out.stem}-{n}.png")
                out.parent.mkdir(parents=True, exist_ok=True)
                Image.open(io.BytesIO(part.inline_data.data)).save(out)
                print(out)
                return
    reason = response.candidates[0].finish_reason if response.candidates else response.prompt_feedback
    sys.exit(f"no image returned ({reason}); adjust the prompt or retry")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help='"character" or a job')
    parser.add_argument("--model", default=os.environ.get("GEMINI_IMAGE_MODEL", DEFAULT_MODEL))
    args = parser.parse_args()

    if args.target == "character":
        generate(character_prompt(CHARACTER_DIR / "guide-prompt.md"), [], "16:9", args.model,
                 CHARACTER_DIR / "guide.png")
        return

    path = job_dir(args.target)
    prompts = image_prompts(path / "prompts.md")
    if not prompts:
        sys.exit("prompts.md lists no images to draw")
    guide = CHARACTER_DIR / "guide.png"
    for out, prompt in prompts.items():
        generate(prompt, [guide] if guide.exists() else [], "3:4", args.model, path / out)


if __name__ == "__main__":
    main()
