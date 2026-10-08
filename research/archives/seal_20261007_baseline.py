"""Seal (schema v1) and restore-check (schema v1/v2) the T004 baseline evidence.

`verify` dispatches on the index `schema_version`:

* schema v1: historical behavior. Every package is matched against the recorded
  `sha256`, its `<run>.tar.gz.sha256` sidecar and the full `members` path->sha256
  table, then restored into a fresh temporary directory and compared against the
  recorded evidence basis.
* schema v2: Git-backed packages. The manifest records a `storage_identity`
  (kind `git_commit`) plus, per run, the repository-relative `package` path,
  `bytes` and `member_count`. Each package's byte identity comes from the
  committed Git blob at that commit/path (no sidecars, no member hash table).
  Package members are fully inspected before any extraction, then restored into a
  fresh temporary directory and re-hashed.

`seal` intentionally remains schema v1 and still refuses to overwrite existing
sealed evidence.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "p01-baseline-20261007-manifest.json"
FAMILIES = (
    "sharedridge", "sharedridge-repeat", "recompute-primary",
    "recompute-repeat", "repeat-check", "alignment",
)
RUN_IDS = sorted(
    f"p01-{dataset}-{family}-{version}"
    for dataset in ("r0", "region")
    for family in FAMILIES
    for version in ("001", "002")
)
EXPECTED_INVENTORY = "db042f6104247130bca08595cf192b82e29254b4f32c4d5dc52cffc4fc64276a"
EXPECTED_CONTENT = "0dd5e80a29d0e9767eb7ed981f33b66932ffead3b14c45aadc494227dc945fb5"

# Package exclusions are declared by the index as data (schema v2); the concrete
# rule those declarations stand for is fixed here. Embedded-manifest exclusions
# (`artifacts-sha256.json`, `events.jsonl`) are deliberately NOT part of this set:
# those files are expected to remain present inside the packages.
PACKAGE_EXCLUSION_KEYS = ("package_exclusions", "embedded_artifact_manifest_exclusions")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(hashes):
    paths = sorted(hashes)
    inventory = hashlib.sha256(("\n".join(paths) + "\n").encode()).hexdigest()
    content = hashlib.sha256(
        "".join(f"{path}\0{hashes[path]}\n" for path in paths).encode()
    ).hexdigest()
    return {"files": len(paths), "inventory_sha256": inventory, "content_sha256": content}


def source_inventory():
    hashes = {}
    for run_id in RUN_IDS:
        directory = ROOT / "research/runs" / run_id
        status = json.loads((directory / "status.json").read_text())
        if status["state"] != "success" or status["stage"] != "complete":
            raise ValueError(f"Run is unfinished: {run_id}")
        for path in sorted(directory.rglob("*")):
            if "__pycache__" in path.parts or path.name == ".DS_Store" or path.name.startswith("._"):
                continue
            if path.is_symlink():
                raise ValueError(f"Symlink is not valid evidence: {path}")
            if path.is_file():
                hashes[path.relative_to(ROOT).as_posix()] = sha256(path)
        manifest = json.loads((directory / "artifacts-sha256.json").read_text())
        for relative, expected in manifest["files"].items():
            if hashes[f"research/runs/{run_id}/{relative}"] != expected:
                raise ValueError(f"Source manifest mismatch: {run_id}/{relative}")
    basis = fingerprint(hashes)
    if basis != {"files": 780, "inventory_sha256": EXPECTED_INVENTORY, "content_sha256": EXPECTED_CONTENT}:
        raise ValueError(f"Evidence differs from the independently verified basis: {basis}")
    return hashes


def _git(repo_root, *arguments, capture=True):
    """Run one read-only git command; any failure is an explicit ValueError."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=True, capture_output=capture,
        )
    except FileNotFoundError as error:
        raise ValueError("git executable is unavailable on PATH") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or b"").decode(errors="replace").strip()
        raise ValueError(f"git {' '.join(arguments)} failed: {detail or error.returncode}") from error
    return result.stdout


def _git_present(repo_root, spec):
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "-e", spec],
            capture_output=True,
        )
    except FileNotFoundError as error:
        raise ValueError("git executable is unavailable on PATH") from error
    return result.returncode == 0


def _default_repo_root(archives):
    """Real layout is <repo>/research/archives, so the repo root is two levels up."""
    return archives.parent.parent


def _package_exclusion(path):
    """Return the package-exclusion declaration a member path violates, if any."""
    for part in path.parts:
        if part == "__pycache__" or part == ".DS_Store" or part.startswith("._"):
            return part
    return None


def verify_v1(archives, manifest):
    if sorted(manifest["runs"]) != RUN_IDS:
        raise ValueError("Archive manifest does not cover exactly the 24 runs")
    restored_hashes = {}
    with tempfile.TemporaryDirectory(prefix="p01-baseline-restore-") as temporary:
        destination = Path(temporary)
        for run_id, record in sorted(manifest["runs"].items()):
            package = archives / f"{run_id}.tar.gz"
            if sha256(package) != record["sha256"] or package.stat().st_size != record["bytes"]:
                raise ValueError(f"Package identity mismatch: {package}")
            expected_checksum = f"{record['sha256']}  research/archives/{package.name}\n"
            if package.with_name(package.name + ".sha256").read_text() != expected_checksum:
                raise ValueError(f"External checksum mismatch: {package}")
            members_seen = set()
            with tarfile.open(package, "r:gz") as archive:
                for member in archive:
                    path = PurePosixPath(member.name)
                    if (not member.isfile() or path.is_absolute() or ".." in path.parts
                            or len(path.parts) < 2 or path.parts[0] != run_id
                            or member.name in members_seen or member.name not in record["members"]):
                        raise ValueError(f"Unsafe or unexpected package member: {member.name}")
                    members_seen.add(member.name)
                    restored = destination.joinpath(*path.parts)
                    restored.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as source, restored.open("xb") as output:
                        shutil.copyfileobj(source, output)
                    digest = sha256(restored)
                    if digest != record["members"][member.name]:
                        raise ValueError(f"Restored content mismatch: {member.name}")
                    restored_hashes[f"research/runs/{member.name}"] = digest
            if members_seen != set(record["members"]):
                raise ValueError(f"Incomplete archive: {run_id}")
        basis = fingerprint(restored_hashes)
        if basis != manifest["verified_evidence_basis"] or basis["content_sha256"] != EXPECTED_CONTENT:
            raise ValueError("Restored evidence differs from the verification basis")
    print(f"Verified 24 packages and restored {len(restored_hashes)} byte-identical files")


def _resolve_package(archives, repo_root, run_id, record):
    """Return (repository-relative posix path, absolute on-disk path)."""
    declared = record.get("package")
    if declared is None:
        declared = os.path.relpath(archives / f"{run_id}.tar.gz", repo_root)
    path = PurePosixPath(declared)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Invalid package path for {run_id}: {declared!r}")
    return path.as_posix(), repo_root.joinpath(*path.parts)


def _restore_package(package, run_id, record, destination):
    """Inspect every member, then restore it; return the number of files written."""
    members = {}
    with tarfile.open(package, "r:gz") as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if not member.isfile():
                raise ValueError(f"Non-regular package member: {member.name}")
            if (path.is_absolute() or ".." in path.parts or len(path.parts) < 2
                    or path.parts[0] != run_id):
                raise ValueError(f"Unsafe package member path: {member.name}")
            if member.name in members:
                raise ValueError(f"Duplicate package member: {member.name}")
            excluded = _package_exclusion(path)
            if excluded is not None:
                raise ValueError(
                    f"Package member violates declared exclusion {excluded!r}: {member.name}"
                )
            members[member.name] = member
        if len(members) != record["member_count"]:
            raise ValueError(
                f"Member count mismatch for {run_id}: "
                f"inspected {len(members)} != recorded {record['member_count']}"
            )
        restored = 0
        for name in sorted(members):
            member = members[name]
            with archive.extractfile(member) as source:
                content = source.read()
            expected = hashlib.sha256(content).hexdigest()
            target = destination.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as output:
                output.write(content)
            if sha256(target) != expected:
                raise ValueError(f"Restored content mismatch: {name}")
            restored += 1
    return restored


def verify_v2(archives, manifest, repo_root):
    identity = manifest.get("storage_identity")
    if not isinstance(identity, dict) or identity.get("kind") != "git_commit":
        raise ValueError("Schema-v2 manifest requires storage_identity.kind == 'git_commit'")
    commit = identity.get("commit")
    if not isinstance(commit, str) or not commit.strip():
        raise ValueError("Schema-v2 manifest requires a non-empty storage_identity.commit")
    commit = commit.strip()
    if not repo_root.is_dir():
        raise ValueError(f"Git working tree does not exist: {repo_root}")
    _git(repo_root, "rev-parse", "--git-dir")
    if not _git_present(repo_root, f"{commit}^{{commit}}"):
        raise ValueError(
            f"Unresolvable Git identity: {commit} is not a commit in {repo_root}"
        )
    for key in PACKAGE_EXCLUSION_KEYS:
        value = manifest.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(f"Schema-v2 manifest requires a non-empty {key} list")
    runs = manifest.get("runs")
    if not isinstance(runs, dict) or not runs:
        raise ValueError("Schema-v2 manifest requires at least one run record")
    if manifest.get("task_id") == "P01-T004" and sorted(runs) != RUN_IDS:
        raise ValueError(
            "Schema-v2 T004 manifest does not cover exactly the 24 runs"
        )

    packages = 0
    restored_files = 0
    with tempfile.TemporaryDirectory(prefix="p01-baseline-restore-") as temporary:
        destination = Path(temporary)
        for run_id, record in sorted(runs.items()):
            if not isinstance(record, dict):
                raise ValueError(f"Invalid run record: {run_id}")
            for key in ("bytes", "member_count"):
                value = record.get(key)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ValueError(f"Run record {run_id} requires a non-negative integer {key}")
            package_path, package = _resolve_package(archives, repo_root, run_id, record)
            blob_spec = f"{commit}:{package_path}"
            if not _git_present(repo_root, blob_spec):
                raise ValueError(
                    f"Package identity missing at commit {commit}: {package_path}"
                )
            expected_blob = _git(repo_root, "cat-file", "-p", blob_spec)
            if not package.is_file():
                raise ValueError(f"Package is missing on disk: {package}")
            on_disk_bytes = package.stat().st_size
            if on_disk_bytes != record["bytes"]:
                raise ValueError(
                    f"Package size mismatch for {run_id}: on-disk {on_disk_bytes} "
                    f"!= recorded {record['bytes']}"
                )
            if len(expected_blob) != record["bytes"]:
                raise ValueError(
                    f"Package size mismatch for {run_id}: git blob {len(expected_blob)} "
                    f"!= recorded {record['bytes']}"
                )
            if on_disk_bytes != len(expected_blob):
                raise ValueError(f"Changed package {package_path}: size differs from git blob")
            if sha256(package) != hashlib.sha256(expected_blob).hexdigest():
                raise ValueError(f"Changed package {package_path}: sha256 differs from git blob")
            restored_files += _restore_package(package, run_id, record, destination)
            packages += 1
    print(f"Verified {packages} git-backed packages and restored {restored_files} byte-identical files")
    return {"packages": packages, "files": restored_files}


def verify(archives, repo_root=None):
    manifest = json.loads((archives / MANIFEST).read_text())
    schema_version = manifest.get("schema_version")
    if schema_version == 1:
        return verify_v1(archives, manifest)
    if schema_version == 2:
        resolved = Path(repo_root).resolve() if repo_root is not None else _default_repo_root(archives)
        return verify_v2(archives, manifest, resolved)
    raise ValueError(f"Unsupported archive manifest schema_version: {schema_version!r}")


def seal(archives):
    targets = [archives / MANIFEST]
    for run_id in RUN_IDS:
        targets.extend((archives / f"{run_id}.tar.gz", archives / f"{run_id}.tar.gz.sha256"))
    if any(path.exists() for path in targets):
        raise FileExistsError("Refusing to overwrite existing sealed evidence")
    hashes = source_inventory()
    manifest = {
        "schema_version": 1,
        "task_id": "P01-T004",
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "verified_evidence_basis": fingerprint(hashes),
        "runs": {},
    }
    for run_id in RUN_IDS:
        prefix = f"research/runs/{run_id}/"
        members = {path.removeprefix("research/runs/"): digest
                   for path, digest in hashes.items() if path.startswith(prefix)}
        package = archives / f"{run_id}.tar.gz"
        with tarfile.open(package, "x:gz", format=tarfile.PAX_FORMAT) as archive:
            for member in sorted(members):
                archive.add(ROOT / "research/runs" / member, arcname=member, recursive=False)
        digest = sha256(package)
        with package.with_name(package.name + ".sha256").open("x") as output:
            output.write(f"{digest}  research/archives/{package.name}\n")
        manifest["runs"][run_id] = {
            "package": f"research/archives/{package.name}",
            "sha256": digest,
            "bytes": package.stat().st_size,
            "members": members,
        }
    if source_inventory() != hashes:
        raise ValueError("Source evidence changed during sealing")
    with (archives / MANIFEST).open("x") as output:
        json.dump(manifest, output, indent=2, sort_keys=True)
        output.write("\n")
    verify(archives)
    print(f"Sealed {sum(item['bytes'] for item in manifest['runs'].values())} compressed bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "verify"))
    parser.add_argument("--archives-root", type=Path, default=ROOT / "research/archives")
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="Git working tree containing the archives root "
             "(default: the archives root's grandparent directory)",
    )
    args = parser.parse_args()
    archives_root = args.archives_root.resolve()
    if args.action == "seal":
        seal(archives_root)
    else:
        verify(archives_root, args.repo_root.resolve() if args.repo_root is not None else None)
