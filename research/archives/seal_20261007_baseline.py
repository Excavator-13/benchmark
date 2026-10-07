"""Seal and restore-check the 24 immutable T004 baseline evidence directories."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
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


def verify(archives):
    manifest = json.loads((archives / MANIFEST).read_text())
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
    args = parser.parse_args()
    (seal if args.action == "seal" else verify)(args.archives_root.resolve())
