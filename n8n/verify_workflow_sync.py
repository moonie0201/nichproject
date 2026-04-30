"""repo workflow JSON 과 live n8n workflow 상태가 일치하는지 검증한다.

사용 예:
    python3 n8n/verify_workflow_sync.py
    python3 n8n/verify_workflow_sync.py --workflow-file n8n/workflows/shorts_auto_daily.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path


DEFAULT_WORKFLOW_FILE = Path("/home/mh/ocstorage/workspace/nichproject/n8n/workflows/shorts_auto_daily.json")
DEFAULT_CONTAINER = "n8n-n8n-1"
DB_PATH_IN_CONTAINER = "/home/node/.n8n/database.sqlite"


def _normalized_json(value: str | None) -> object:
    if not value:
        return None
    return json.loads(value)


def _copy_live_db(container: str, dest: Path) -> None:
    subprocess.run(
        ["docker", "cp", f"{container}:{DB_PATH_IN_CONTAINER}", str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )


def verify_workflow(workflow_file: Path, container: str) -> list[str]:
    repo = json.loads(workflow_file.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="n8n-workflow-verify-") as tmpdir:
        db_copy = Path(tmpdir) / "database.sqlite"
        _copy_live_db(container, db_copy)

        conn = sqlite3.connect(db_copy)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "select id, name, active, nodes, connections, settings from workflow_entity where id = ?",
            (repo["id"],),
        )
        row = cur.fetchone()
        conn.close()

    if row is None:
        return [f"live workflow missing: {repo['id']}"]

    mismatches: list[str] = []
    if row["name"] != repo["name"]:
        mismatches.append(f"name mismatch: live={row['name']!r} repo={repo['name']!r}")
    if bool(row["active"]) != bool(repo.get("active", False)):
        mismatches.append(
            f"active mismatch: live={bool(row['active'])!r} repo={bool(repo.get('active', False))!r}"
        )
    if _normalized_json(row["nodes"]) != repo["nodes"]:
        mismatches.append("nodes mismatch")
    if _normalized_json(row["connections"]) != repo["connections"]:
        mismatches.append("connections mismatch")
    if _normalized_json(row["settings"]) != repo.get("settings"):
        mismatches.append("settings mismatch")
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify repo workflow JSON matches live n8n workflow")
    parser.add_argument("--workflow-file", type=Path, default=DEFAULT_WORKFLOW_FILE)
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    args = parser.parse_args()

    mismatches = verify_workflow(args.workflow_file, args.container)
    if mismatches:
        print("workflow drift detected:")
        for item in mismatches:
            print(f" - {item}")
        return 1

    print(f"workflow sync OK: {args.workflow_file.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
