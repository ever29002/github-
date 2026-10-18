"""Write prompts.md for the optional manga images (scenes with `draw` in name.yaml).

The product itself is always shown with its official photo, so the manga only
illustrates a situation (e.g. the hook's everyday problem) and never draws the
product. Paste each prompt into the Gemini app (free) and save the image to the
path in its heading. When no scene has `draw`, there is nothing to generate.

Usage: python3 scripts/make_prompts.py <job>
"""

import argparse

from common import job_dir, load_name, set_state

RULES = """\
- ONE single illustration in portrait orientation (3:4) for a smartphone screen. No panel grid.
- Friendly, warm and simple. Medium shot or close-up so faces read clearly on a phone.
- Do NOT draw the product or any brand, logo or appliance that could be mistaken for it.
- Absolutely NO text, letters, numbers or speech bubbles.
- Keep the guide character identical to the attached character reference sheet (face, hair, outfit)."""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job")
    args = parser.parse_args()

    path = job_dir(args.job)
    name = load_name(path)
    todo = [s for s in name["scenes"] if s.get("draw")]
    for scene in todo:
        if not scene.get("image"):
            raise SystemExit(f"scene with draw needs image: (e.g. images/manga1.png): {scene['draw']}")

    blocks = "\n\n".join(
        f"## {s['image']}\n\n```\nStyle: {name.get('style') or 'soft, friendly Japanese manga style, warm colors'}"
        f"\n\nRules:\n{RULES}\n\nDraw: {s['draw']}\n```" for s in todo)
    character = name.get("character") or "assets/characters/guide.png"
    out = f"""# 作画プロンプト（任意の漫画イラスト）

商品は公式写真で見せるので、ここでは商品を描かない。Gemini アプリ（無料）に貼って生成し、見出しのパスに保存する。
添付するもの: 案内役の3面図 `{character}`（あれば）

{blocks or "（draw のあるシーンが無いので、作画は不要）"}
"""
    (path / "prompts.md").write_text(out, encoding="utf-8")
    # The official photos (and any drawn images) still go through art-checker.
    set_state(path, "awaiting_art", f"prompts.md: {len(todo)} image(s) to draw")
    print(path / "prompts.md")


if __name__ == "__main__":
    main()
