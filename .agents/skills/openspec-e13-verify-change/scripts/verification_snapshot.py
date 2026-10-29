#!/usr/bin/env python3
"""Capture file inventories and compare them. Compare exits 0/1/2: same/changed/error."""

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


WORKFLOW_FILES = {"implementation-notes.md", "verification.md", "verification-state.json"}


def excluded(path, patterns):
    return (
        ".git" in Path(path).parts
        or Path(path).name in WORKFLOW_FILES
        or any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)
    )


def inventory(root, patterns):
    git = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        capture_output=True, check=False,
    ) if shutil.which("git") else None
    if git is not None and git.returncode == 0 and git.stdout.strip() == b"true":
        listing = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others",
             "--exclude-standard", "-z", "--", "."],
            capture_output=True, check=True,
        )
        paths = {os.fsdecode(p) for p in listing.stdout.split(b"\0") if p}
        mode = "git-tracked-and-unignored"
    else:
        paths = set()
        for directory, dirs, names in os.walk(root, onerror=raise_error):
            parent = Path(directory).relative_to(root)
            dirs[:] = [d for d in dirs if not excluded((parent / d).as_posix(), patterns)
                       and not excluded((parent / d).as_posix() + "/", patterns)]
            paths.update((parent / name).as_posix() for name in names)
            paths.update((parent / d).as_posix() for d in dirs if (root / parent / d).is_symlink())
        mode = "walk"

    files = {}
    for name in sorted(paths):
        if excluded(name, patterns):
            continue
        path = root / name
        if path.is_dir():
            raise ValueError(f"Directory entry {path}: exclude it and add its contents as a separate --root")
        if path.is_symlink():
            data = b"symlink\0" + os.fsencode(os.readlink(path)) + b"\0"
            data += path.read_bytes() if path.exists() else b"missing-target"
        elif path.exists():
            data = path.read_bytes()
        else:
            continue  # Tracked deletions are absent from the current inventory.
        files[name] = hashlib.sha256(data).hexdigest()
    return {"path": str(root), "inventory": mode, "exclude": patterns, "files": files}


def raise_error(error):
    raise error


def read_state(path):
    state = json.loads(Path(path).read_text(encoding="utf-8"))
    if (not isinstance(state, dict) or state.get("version") != 1
            or not isinstance(state.get("roots"), list) or not state["roots"]):
        raise ValueError(f"Invalid snapshot: {path}")
    roots = {}
    for root in state["roots"]:
        if (not isinstance(root, dict) or not isinstance(root.get("path"), str)
                or root["path"] in roots
                or root.get("inventory") not in {"walk", "git-tracked-and-unignored"}
                or not isinstance(root.get("exclude"), list)
                or not all(isinstance(p, str) for p in root["exclude"])
                or not isinstance(root.get("files"), dict)
                or not all(isinstance(p, str) and isinstance(h, str) and len(h) == 64
                           for p, h in root["files"].items())):
            raise ValueError(f"Invalid root in snapshot: {path}")
        roots[root["path"]] = root
    return roots


def compare(before, after):
    old, new = read_state(before), read_state(after)
    changes = []
    for path in sorted(old.keys() | new.keys()):
        left, right = old.get(path), new.get(path)
        scope_changed = left is None or right is None or any(
            left[key] != right[key] for key in ("inventory", "exclude")
        )
        a, b = (left or {}).get("files", {}), (right or {}).get("files", {})
        added = sorted(b.keys() - a.keys())
        deleted = sorted(a.keys() - b.keys())
        modified = sorted(p for p in a.keys() & b.keys() if a[p] != b[p])
        if scope_changed or added or deleted or modified:
            changes.append({"path": path, "scope_changed": scope_changed,
                            "added": added, "modified": modified, "deleted": deleted})
    print(json.dumps({"changed": bool(changes), "roots": changes}, ensure_ascii=True, indent=2))
    return int(bool(changes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture")
    capture.add_argument("--root", action="append", required=True)
    capture.add_argument("--exclude", action="append", default=[], help="Root-relative glob; repeatable")
    capture.add_argument("--output", required=True)
    diff = commands.add_parser("compare")
    diff.add_argument("before")
    diff.add_argument("after")
    args = parser.parse_args()
    if args.command == "compare":
        return compare(args.before, args.after)

    roots = sorted({Path(p).resolve(strict=True) for p in args.root})
    if any(not p.is_dir() for p in roots):
        raise ValueError("Every --root must be a directory")
    state = {"version": 1, "roots": [inventory(p, sorted(set(args.exclude))) for p in roots]}
    output = Path(args.output)
    if any(output.resolve().is_relative_to(p) for p in roots) and output.name != "verification-state.json":
        raise ValueError("Use a temporary output outside scanned roots, or verification-state.json")
    raw = (json.dumps(state, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode()
    output.write_bytes(raw)
    print(json.dumps({"snapshot": str(output), "sha256": hashlib.sha256(raw).hexdigest(),
                      "files": sum(len(r["files"]) for r in state["roots"])}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Snapshot error: {error}", file=sys.stderr)
        sys.exit(2)
