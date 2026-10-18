"""Shared helpers for the manga-shorts pipeline: job paths, status tracking, name.yaml loading."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
JOBS_DIR = ROOT / "jobs"

# Job states in order. "作画待ち" and "公開前確認" are human gates.
STATES = [
    "candidate",      # 候補
    "reviewed",       # 審査OK
    "named",          # ネーム済
    "awaiting_art",   # 作画待ち【人】
    "qc_passed",      # 検品OK
    "rendered",       # 動画済
    "awaiting_check", # 公開前確認【人】
    "published",      # 公開済
    "analyzed",       # 分析済
]


def job_dir(job: str) -> Path:
    path = Path(job)
    if not path.is_absolute() and not path.exists():
        path = JOBS_DIR / job
    if not path.is_dir():
        sys.exit(f"job not found: {job}")
    return path


def load_status(path: Path) -> dict:
    status_file = path / "status.json"
    if status_file.exists():
        return json.loads(status_file.read_text(encoding="utf-8"))
    return {"state": "candidate", "history": []}


def set_state(path: Path, state: str, note: str = "") -> None:
    if state not in STATES:
        sys.exit(f"unknown state: {state}")
    status = load_status(path)
    status["state"] = state
    status["history"].append({
        "state": state,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": note,
    })
    (path / "status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


SCENE_TYPES = {"hook", "product", "point", "steps", "outro"}
REQUIRED = {"hook": ["text"], "product": [], "point": ["big", "spec"], "steps": ["steps"],
            "outro": []}


def load_name(path: Path) -> dict:
    """Load name.yaml and check it against the scene types and spec.json's official_specs."""
    name_file = path / "name.yaml"
    if not name_file.exists():
        sys.exit(f"missing {name_file}")
    name = yaml.safe_load(name_file.read_text(encoding="utf-8"))
    product = name.get("product") or {}
    if not product.get("name"):
        sys.exit("name.yaml: product.name is required")
    scenes = name.get("scenes") or []
    types = [s.get("type") for s in scenes]
    if not scenes or types[0] != "hook" or "product" not in types or types[-1] != "outro":
        sys.exit(f"name.yaml: scenes must start with hook, include product, end with outro ({types})")

    spec_file = path / "spec.json"
    official = set()
    if spec_file.exists():
        official = {s.get("item") for s in
                    json.loads(spec_file.read_text(encoding="utf-8")).get("official_specs", [])}
    for i, scene in enumerate(scenes, 1):
        kind = scene.get("type")
        if kind not in SCENE_TYPES:
            sys.exit(f"scene {i}: unknown type {kind!r} (use {sorted(SCENE_TYPES)})")
        for key in REQUIRED[kind]:
            if not scene.get(key):
                sys.exit(f"scene {i} ({kind}): {key} is required")
        if kind == "point" and scene["spec"] not in official:
            sys.exit(f"scene {i} (point): spec is not an official_specs item in spec.json: "
                     f"{scene['spec']!r}")
        if kind == "steps" and not all(scene["steps"]):
            sys.exit(f"scene {i} (steps): empty step")
        if not narration_of(scene, product):
            sys.exit(f"scene {i} ({kind}): narration is required")
    return name


def narration_of(scene: dict, product: dict) -> str:
    if scene.get("narration"):
        return scene["narration"]
    if scene.get("type") == "product":
        return f"{product.get('maker', '')}の{product['name']}！".lstrip("の")
    return scene.get("text") or ""
