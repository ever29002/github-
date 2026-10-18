"""Generate the art with the Gemini API instead of pasting prompts into the Gemini app.

  character  → assets/characters/guide.png from the prompt in assets/characters/guide-prompt.md
  <job>      → <job>/images/page1.png from <job>/prompts.md, attaching the character sheet and
               the product photos placed at <job>/images/product*.png|jpg

The Gemini API is billed separately from a Google AI Pro subscription: set GEMINI_API_KEY
(Google AI Studio → Get API key, on a project with billing enabled). A previous page1.png is
kept as images/rejected-<n>.png so retries after a failed QC don't lose it.

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


def prompt_block(path: Path) -> str:
    """The prompt is the first fenced block; anything after the block (retry hints) is appended."""
    text = path.read_text(encoding="utf-8")
    found = FENCE.search(text)
    if not found:
        sys.exit(f"no ``` prompt block in {path}")
    hints = [line.removeprefix("- retry:").strip() for line in text[found.end():].splitlines()
             if line.startswith("- retry:")]
    return "\n".join([found.group(1), *[f"Fix from the last attempt: {h}" for h in hints]])


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
                    n = len(list(out.parent.glob("rejected-*.png"))) + 1
                    out.rename(out.parent / f"rejected-{n}.png")
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
        generate(prompt_block(CHARACTER_DIR / "guide-prompt.md"), [], "16:9", args.model,
                 CHARACTER_DIR / "guide.png")
        return

    path = job_dir(args.target)
    guide = CHARACTER_DIR / "guide.png"
    if not guide.exists():
        sys.exit("missing assets/characters/guide.png: run `gen_art.py character` first")
    products = sorted(p for p in (path / "images").glob("product*")
                      if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    if not products:
        print("warning: no images/product*.png|jpg; the product will be drawn from the prompt only",
              file=sys.stderr)
    generate(prompt_block(path / "prompts.md"), [guide, *products], "9:16", args.model,
             path / "images" / "page1.png")


if __name__ == "__main__":
    main()
