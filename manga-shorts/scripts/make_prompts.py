"""Turn name.yaml into prompts.md: one vertical (9:16) image prompt per panel.

Each panel becomes its own full-screen image in the video, so it is drawn vertical from the start.
gen_art.py (API) and the browser procedure read the "### コマN" blocks.

Usage: python3 scripts/make_prompts.py <job>
"""

import argparse

from common import job_dir, load_name, set_state

PANEL_RULES = """\
- ONE single manga panel filling the whole image, vertical 9:16 (portrait, like a phone screen). No borders, no multiple panels.
- Keep the main subject in the middle 60% of the height; the top 15% and bottom 25% are quiet background (captions go there).
- Absolutely NO text, letters, numbers, sound effects or logos drawn as text anywhere. No speech bubbles.
- Keep the guide character identical to the attached character reference sheet in every panel.
- Draw the product to match the attached product photo exactly (shape, color, ports, buttons). Do not invent features."""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job")
    args = parser.parse_args()

    path = job_dir(args.job)
    name = load_name(path)

    blocks = []
    for i, p in enumerate(name["panels"], 1):
        prompt = f"""Style: {name.get('style', '')}

Rules:
{PANEL_RULES}

Scene ({i} of 4 in the story): {p['scene']}"""
        blocks.append(f"### コマ{i}\n\n```\n{prompt}\n```")

    character = name.get("character") or "（未設定）"
    out = f"""# 作画プロンプト（Geminiアプリに貼る）

商品: {name['product']['name']}

## 添付するもの
1. 案内役の3面図: `{character}`
2. 商品画像（spec.json の asset_sources に出典がある、利用許諾のあるもの）

## プロンプト（同じチャットで、コマ1から順に1つずつ貼る）

{chr(10).join(blocks)}

## 保存
- 生成画像を `images/panel1.png` 〜 `images/panel4.png` として保存する。
- 横長になった、顔が別人、商品の形が違う、文字が入っている場合はそのコマだけ再生成（最大3回）。
"""
    (path / "prompts.md").write_text(out, encoding="utf-8")
    set_state(path, "awaiting_art", "prompts.md generated")
    print(path / "prompts.md")


if __name__ == "__main__":
    main()
