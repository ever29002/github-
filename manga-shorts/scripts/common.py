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


def load_name(path: Path) -> dict:
    name_file = path / "name.yaml"
    if not name_file.exists():
        sys.exit(f"missing {name_file}")
    name = yaml.safe_load(name_file.read_text(encoding="utf-8"))
    panels = name.get("panels") or []
    if len(panels) != 4:
        sys.exit(f"name.yaml must have exactly 4 panels (found {len(panels)})")
    for i, panel in enumerate(panels, 1):
        if not panel.get("scene"):
            sys.exit(f"panel {i}: scene is required")
        if not panel.get("caption"):
            sys.exit(f"panel {i}: caption is required")
    return name


def narration_of(panel: dict) -> str:
    return panel.get("narration") or panel["caption"]
