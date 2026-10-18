"""Generate the art with the Gemini API instead of pasting prompts into the Gemini app.

  character  → assets/characters/guide.png from the prompt in assets/characters/guide-prompt.md
  <job>      → <job>/images/panel1.png .. panel4.png (vertical 9:16) from the "### コマN" blocks
               in <job>/prompts.md, attaching the character sheet and the product photos placed
               at <job>/images/product*.png|jpg

The Gemini API is billed separately from a Google AI Pro subscription: set GEMINI_API_KEY
(Google AI Studio → Get API key, on a project with billing enabled). A replaced image is kept
as images/rejected-<n>.png so retries after a failed QC don't lose it.

Retry hints: a line "- retry: <hint>" in prompts.md applies to every panel, "- retry3: <hint>"
only to panel 3. --panel limits generation to the listed panels.

Usage:
  python3 scripts/gen_art.py character
  python3 scripts/gen_art.py <job> [--panel 2 --panel 4] [--model MODEL]
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
PANEL = re.compile(r"### コマ(\d)\s*\n+```\n(.*?)\n```", re.S)
RETRY = re.compile(r"^- retry(\d?):\s*(.+)$", re.M)


def character_prompt(path: Path) -> str:
    found = FENCE.search(path.read_text(encoding="utf-8"))
    if not found:
        sys.exit(f"no ``` prompt block in {path}")
    return found.group(1)


def panel_prompts(path: Path) -> dict[int, str]:
    text = path.read_text(encoding="utf-8")
    prompts = {int(n): body for n, body in PANEL.findall(text)}
    if sorted(prompts) != [1, 2, 3, 4]:
        sys.exit(f"{path} needs ### コマ1..4 blocks; rerun make_prompts.py")
    for n, hint in RETRY.findall(text):
        for i in ([int(n)] if n else prompts):
            prompts[i] += f"\nFix from the last attempt: {hint.strip()}"
    return prompts


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
    parser.add_argument("--panel", type=int, action="append", choices=[1, 2, 3, 4])
    parser.add_argument("--model", default=os.environ.get("GEMINI_IMAGE_MODEL", DEFAULT_MODEL))
    args = parser.parse_args()

    if args.target == "character":
        generate(character_prompt(CHARACTER_DIR / "guide-prompt.md"), [], "16:9", args.model,
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
    prompts = panel_prompts(path / "prompts.md")
    first = path / "images" / "panel1.png"
    for i in args.panel or sorted(prompts):
        # panel 1 is the style and character reference for the other three
        refs = [guide, *products, *([first] if i > 1 and first.exists() else [])]
        generate(prompts[i], refs, "9:16", args.model, path / "images" / f"panel{i}.png")


if __name__ == "__main__":
    main()
