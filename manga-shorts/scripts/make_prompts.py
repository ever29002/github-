"""Turn name.yaml into prompts.md for pasting into the Gemini app (manual art step).

Usage: python3 scripts/make_prompts.py <job>
"""

import argparse

from common import job_dir, load_name, set_state

PAGE_RULES = """\
- Japanese 4-koma manga page, portrait orientation.
- EXACTLY 4 panels stacked vertically, equal height, full width, separated by clear white gutters.
- Thin black panel borders. Plain white margin around the page.
- Absolutely NO text, letters, numbers, sound effects or logos drawn as text anywhere. No speech bubbles.
- Keep the guide character identical to the attached character reference sheet in every panel.
- Draw the product to match the attached product photo exactly (shape, color, ports, buttons). Do not invent features."""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job")
    args = parser.parse_args()

    path = job_dir(args.job)
    name = load_name(path)

    panels = "\n".join(
        f"Panel {i} (top to bottom: {i}/4): {p['scene']}"
        for i, p in enumerate(name["panels"], 1))
    prompt = f"""Style: {name.get('style', '')}

Rules:
{PAGE_RULES}

{panels}"""

    character = name.get("character") or "（未設定）"
    out = f"""# 作画プロンプト（Geminiアプリに貼る）

商品: {name['product']['name']}

## 添付するもの
1. 案内役の3面図: `{character}`
2. 商品画像（spec.json の asset_sources に出典がある、利用許諾のあるもの）

## プロンプト（このブロックをそのまま貼る）

```
{prompt}
```

## 保存
- 生成画像を `images/page1.png` として保存する。
- 4コマになっていない、顔が別人、商品の形が違う、文字が入っている場合は同じプロンプトで再生成（最大3回）。
"""
    (path / "prompts.md").write_text(out, encoding="utf-8")
    set_state(path, "awaiting_art", "prompts.md generated")
    print(path / "prompts.md")


if __name__ == "__main__":
    main()
