"""Create a job folder for one product.

Usage: python3 scripts/new_job.py <slug> --product "商品名" [--url URL] [--pr]
"""

import argparse
import json
import shutil
from datetime import date

from common import JOBS_DIR, ROOT, set_state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="short ascii id, e.g. ugreen-charger")
    parser.add_argument("--product", required=True)
    parser.add_argument("--url", default="")
    parser.add_argument("--pr", action="store_true",
                        help="provided/sponsored item (shows a PR badge)")
    args = parser.parse_args()

    path = JOBS_DIR / f"{date.today().isoformat()}-{args.slug}"
    if path.exists():
        raise SystemExit(f"already exists: {path}")
    for sub in ("images", "panels", "audio"):
        (path / sub).mkdir(parents=True)

    spec = {
        "product": args.product,
        "url": args.url,
        "pr": args.pr,
        "official_specs": [],   # 公式ページから転記した仕様（出典URL付き）
        "asset_sources": [],    # 使う商品画像の出典と許諾
    }
    (path / "spec.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    template = (ROOT / "templates" / "name.yaml").read_text(encoding="utf-8")
    (path / "name.yaml").write_text(
        template.replace("{{product}}", args.product).replace("{{url}}", args.url)
        .replace("{{pr}}", "true" if args.pr else "false"),
        encoding="utf-8")
    shutil.copy(ROOT / "templates" / "captions.md", path / "captions.md")

    set_state(path, "candidate", "job created")
    print(path)


if __name__ == "__main__":
    main()
