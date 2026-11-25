#!/usr/bin/env python3
"""Validate the free Agent Desk redacted-error-log workflow (06 only).

Checks importable structure and the absence of embedded credentials.
This repository does not include the paid pack's other workflows.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF_DIR = ROOT / "workflows"

# Actual-looking secrets, not redaction patterns or placeholders
SECRET_VALUE = re.compile(
    r"""(?x)
    (?<!\[)                          # not already redacted
    (
        sk-[A-Za-z0-9_-]{20,}
      | xox[baprs]-[A-Za-z0-9-]{16,}
      | ntn_[A-Za-z0-9]{20,}
      | secret_[A-Za-z0-9]{16,}
      | -----BEGIN[ ][A-Z ]+PRIVATE[ ]KEY-----
    )
    """
)
PLACEHOLDER_OK = re.compile(r"REPLACE_WITH_|REPLACE_AFTER_IMPORT|NOT_YET|\[REDACTED\]")


def fail(errors, msg):
    errors.append(msg)


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"{path.name}: invalid JSON: {e}"]

    if not isinstance(data, dict):
        return [f"{path.name}: top-level value must be an object, not a list"]

    if "id" in data:
        fail(errors, f"{path.name}: omit workflow id so import always creates a copy")

    if data.get("active") is True:
        fail(errors, f"{path.name}: active must be false or omitted")

    for key in ("name", "nodes", "connections", "settings"):
        if key not in data:
            fail(errors, f"{path.name}: missing required key {key!r}")

    if not isinstance(data.get("name"), str) or not data.get("name"):
        fail(errors, f"{path.name}: name must be a non-empty string")

    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        fail(errors, f"{path.name}: nodes must be a non-empty array")
        return errors

    connections = data.get("connections")
    if not isinstance(connections, dict):
        fail(errors, f"{path.name}: connections must be an object")
        return errors

    if not isinstance(data.get("settings"), dict):
        fail(errors, f"{path.name}: settings must be an object")

    names = []
    ids = []
    by_name = {}
    for i, node in enumerate(nodes):
        prefix = f"{path.name} nodes[{i}]"
        if not isinstance(node, dict):
            fail(errors, f"{prefix}: not an object")
            continue
        for req in ("name", "type", "position"):
            if req not in node:
                fail(errors, f"{prefix}: missing {req}")
        name = node.get("name")
        typ = node.get("type")
        pos = node.get("position")
        if not isinstance(name, str) or not name:
            fail(errors, f"{prefix}: name must be a non-empty string")
        else:
            if name in by_name:
                fail(errors, f"{path.name}: duplicate node name {name!r}")
            names.append(name)
            by_name[name] = node
        if not isinstance(typ, str) or not typ:
            fail(errors, f"{prefix}: type must be a non-empty string")
        elif not typ.startswith("n8n-nodes-base."):
            fail(errors, f"{prefix} ({name}): unexpected type {typ!r}")
        if not (isinstance(pos, list) and len(pos) == 2 and all(isinstance(x, (int, float)) for x in pos)):
            fail(errors, f"{prefix} ({name}): position must be [x, y] numbers")
        if "typeVersion" in node and not isinstance(node["typeVersion"], (int, float)):
            fail(errors, f"{prefix} ({name}): typeVersion must be a number")
        if "parameters" in node and not isinstance(node["parameters"], dict):
            fail(errors, f"{prefix} ({name}): parameters must be an object")
        if "id" in node:
            if not isinstance(node["id"], str) or not node["id"]:
                fail(errors, f"{prefix} ({name}): id must be a non-empty string")
            elif node["id"] in ids:
                fail(errors, f"{path.name}: duplicate node id {node['id']}")
            else:
                ids.append(node["id"])
        creds = node.get("credentials")
        if creds:
            if not isinstance(creds, dict):
                fail(errors, f"{prefix} ({name}): credentials must be an object if present")
            else:
                for k, v in creds.items():
                    if not isinstance(v, dict):
                        fail(errors, f"{prefix} ({name}): credentials.{k} must be an object")
                        continue
                    if v.get("id") != "REPLACE_AFTER_IMPORT" or v.get("name") != "REPLACE_AFTER_IMPORT":
                        fail(
                            errors,
                            f"{prefix} ({name}): credentials are not allowed unless id and name are REPLACE_AFTER_IMPORT",
                        )

    for src, bucket in connections.items():
        if src not in by_name:
            fail(errors, f"{path.name}: connections source {src!r} is not a node name")
            continue
        if not isinstance(bucket, dict):
            fail(errors, f"{path.name}: connections[{src!r}] must be an object")
            continue
        for conn_type, outputs in bucket.items():
            if not isinstance(outputs, list):
                fail(errors, f"{path.name}: connections[{src!r}].{conn_type} must be an array")
                continue
            for oi, group in enumerate(outputs):
                if group is None:
                    continue
                if not isinstance(group, list):
                    fail(errors, f"{path.name}: connections[{src!r}].{conn_type}[{oi}] must be an array or null")
                    continue
                for entry in group:
                    if not isinstance(entry, dict):
                        fail(errors, f"{path.name}: connection entry is not an object")
                        continue
                    for req in ("node", "type", "index"):
                        if req not in entry:
                            fail(errors, f"{path.name}: connection entry missing {req}")
                    target = entry.get("node")
                    if target not in by_name:
                        fail(errors, f"{path.name}: connection target {target!r} is not a node name")
                    if not isinstance(entry.get("index"), int) or entry["index"] < 0:
                        fail(errors, f"{path.name}: connection index must be an integer >= 0")

    # Safety checks (no embedded secrets)
    text = json.dumps(data)
    for m in SECRET_VALUE.finditer(text):
        snippet = m.group(0)[:24]
        # allow appearance only inside redaction regex source, which includes {16,} etc.
        if "A-Za-z0-9" in text[max(0, m.start() - 40) : m.end() + 10]:
            continue
        fail(errors, f"{path.name}: possible embedded secret starting {snippet!r}")

    return errors


def main() -> int:
    # This free repo ships a single workflow. Ignore backups such as *.prelive.bak.
    path = WF_DIR / "06-redacted-error-log.json"
    if not path.exists():
        print(f"Expected {path} (this repo only validates workflow 06)", file=sys.stderr)
        return 2
    errs = validate_file(path)
    if errs:
        print("\nFAILED:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"OK  {path.name:36} nodes={len(data['nodes']):2}  {data['name']}")
    print("\nWorkflow 06 passed structure and safety checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
