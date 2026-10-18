"""Research a product in NotebookLM and save cited facts for the script writer.

Creates (or reuses) one notebook per job, adds the product's official pages as
sources, asks fixed questions, and writes the answers to research.md. When an
answer parses as JSON, the specs are also merged into spec.json.

Runs where the `nlm` CLI (notebooklm-mcp-cli) is installed and logged in, i.e.
on your PC. `nlm` uses NotebookLM's undocumented internal API: it can break
without notice, and the session needs `nlm login` again when it expires.

Usage:
  python3 scripts/nlm_research.py <job> [--source URL ...] [--studio infographic|slides|video]
"""

import argparse
import json
import re
import shutil
import subprocess

from common import job_dir

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

QUESTIONS = {
    "specs": (
        "この商品の公式な仕様を、ソースに書かれている内容だけで列挙してください。"
        "推測や一般論は入れないでください。次のJSON配列だけを返してください: "
        '[{"item": "仕様（日本語で短く）", "source": "根拠になったソースのタイトル"}]'
    ),
    "usage": (
        "この商品の基本的な使い方を、初めて使う人向けに3〜5ステップで説明してください。"
        "ソースに書かれている手順だけを使い、各ステップに根拠のソースを添えてください。"
    ),
    "limits": (
        "この商品でできないこと、使う上での注意点、対象外の使い方を、ソースに書かれている範囲で挙げてください。"
        "書かれていなければ「記載なし」と答えてください。"
    ),
    "hooks": (
        "忙しい子育て中の家庭が、この商品で手間を減らせる場面を3つ挙げてください。"
        "ソースに書かれた機能に基づくものだけにし、効果を誇張しないでください。"
    ),
}


def nlm(*args: str, timeout: int = 300) -> str:
    result = subprocess.run(["nlm", *args], capture_output=True, text=True,
                            encoding="utf-8", timeout=timeout)
    if result.returncode != 0:
        raise SystemExit(f"nlm {' '.join(args[:2])} failed:\n{result.stderr or result.stdout}\n"
                         "If this is an auth error, run `nlm login` and retry.")
    return result.stdout.strip()


def parse_json_list(text: str):
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("job")
    parser.add_argument("--source", action="append", default=[],
                        help="extra source URL (official page, manual PDF); repeatable")
    parser.add_argument("--studio", choices=["infographic", "slides", "video"],
                        help="also start a NotebookLM studio artifact (experimental)")
    args = parser.parse_args()

    if not shutil.which("nlm"):
        raise SystemExit("nlm not found. Install notebooklm-mcp-cli and run `nlm login`.")

    path = job_dir(args.job)
    spec_file = path / "spec.json"
    spec = json.loads(spec_file.read_text(encoding="utf-8"))

    notebook = spec.get("notebook_id")
    if not notebook:
        out = nlm("notebook", "create", f"manga-shorts: {spec['product']}")
        found = UUID.search(out)
        if not found:
            raise SystemExit(f"could not read the notebook id from:\n{out}")
        notebook = found.group(0)
        spec["notebook_id"] = notebook

    added = set(spec.get("notebook_sources", []))
    for url in [spec.get("url"), *args.source]:
        if url and url not in added:
            nlm("source", "add", notebook, "--url", url)
            added.add(url)
    spec["notebook_sources"] = sorted(added)
    if not added:
        raise SystemExit("no sources: set url in spec.json or pass --source")

    answers = {key: nlm("notebook", "query", notebook, question)
               for key, question in QUESTIONS.items()}

    specs = parse_json_list(answers["specs"])
    if specs:
        known = {s.get("item") for s in spec.get("official_specs", [])}
        for s in specs:
            if s.get("item") and s["item"] not in known:
                spec.setdefault("official_specs", []).append(
                    {"item": s["item"], "source": f"NotebookLM: {s.get('source', '')}",
                     "note": "NotebookLMの回答。公開前に出典を目で確認"})

    spec_file.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sections = [f"# NotebookLM 調査: {spec['product']}", "",
                f"- notebook: `{notebook}`",
                *[f"- source: {u}" for u in spec["notebook_sources"]], ""]
    titles = {"specs": "公式仕様", "usage": "使い方", "limits": "注意点・できないこと",
              "hooks": "手間が減る場面（ネタ候補）"}
    for key, title in titles.items():
        sections += [f"## {title}", "", answers[key], ""]
    (path / "research.md").write_text("\n".join(sections), encoding="utf-8")

    if args.studio:
        print(nlm(args.studio, "create", notebook, "--confirm"))
        print(f"started {args.studio}; check with: nlm studio status {notebook}")

    print(path / "research.md")


if __name__ == "__main__":
    main()
