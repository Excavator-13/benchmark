"""Read-only checks for the 2026-10-06 research-record migration."""

import ast
import hashlib
import re
import subprocess
import tarfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE = "f66959b3dd868ba97a330cf46147212b83a4524b"
RUN_ID = "phase1-20261006-v2-01"


def original(path):
    return subprocess.check_output(
        ["git", "show", f"{BASE}:{path}"], cwd=ROOT
    )


def heading_ids(text):
    ids = set()
    counts = {}
    for heading in re.findall(r"^#+\s+(.+)$", text, re.M):
        heading = heading.replace("`", "").lower()
        slug = "".join(
            char for char in heading
            if char in "-_ " or not unicodedata.category(char).startswith(("P", "S"))
        ).replace(" ", "-")
        count = counts.get(slug, 0)
        ids.add(f"{slug}-{count}" if count else slug)
        counts[slug] = count + 1
    return ids


def main():
    archive = ROOT / "experiments_archive/phase1" / f"{RUN_ID}.tar.gz"
    sidecar = Path(str(archive) + ".sha256")
    expected, recorded_path = sidecar.read_text().strip().split(maxsplit=1)
    assert ROOT / recorded_path == archive
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected
    assert archive.read_bytes() == original(str(archive.relative_to(ROOT)))
    assert sidecar.read_bytes() == original(str(sidecar.relative_to(ROOT)))

    run = ROOT / "research/runs" / RUN_ID
    with tarfile.open(archive) as bundle:
        files = [m for m in bundle.getmembers()
                 if m.isfile() and not Path(m.name).name.startswith("._")]
        names = set()
        for member in files:
            name = Path(member.name)
            assert not name.is_absolute() and ".." not in name.parts
            assert name.parts[0] == RUN_ID
            relative = Path(*name.parts[1:])
            data = bundle.extractfile(member).read()
            assert data == (run / relative).read_bytes(), str(relative)
            assert data == original(f"experiments_phase1/{member.name}")
            names.add(str(relative))
        assert names == {str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()}
        assert len(files) == 13
    print("PASS: legacy archive, sidecar and all 13 migrated run files are unchanged.")

    # Science definitions exclude the administrative storage section 6.1.
    old = original("research_planning/02_phase_one_plan.md").decode()
    new = (ROOT / "research/phases/P01/protocol.md").read_text()
    for start, end in [
        ("### 3.1 节点身份和信号", "### 6.1 保存与归档"),
        ("### 6.2 可执行的重复性与收益判据", "## 7. 诊断已归档的 EvolveGCN-H"),
    ]:
        assert old.split(start, 1)[1].split(end, 1)[0] == new.split(start, 1)[1].split(end, 1)[0]
    print("PASS: v3 scientific definitions and gain criteria equal v2.")

    docs = [ROOT / "RESEARCH.md", ROOT / "AGENTS.md",
            ROOT / "experiments_archive/README.md"]
    docs += [p for p in (ROOT / "research").rglob("*.md") if "runs" not in p.parts]
    links = 0
    # The live documents use inline links with at most one nested parenthesis.
    pattern = r"\[[^\]]+\]\(((?:[^()]|\([^()]*\))+)\)"
    for document in docs:
        text = document.read_text()
        assert text.endswith("\n")
        assert all(line == line.rstrip() for line in text.splitlines()), str(document)
        for destination in re.findall(pattern, text):
            if "://" in destination:
                continue
            filename, _, anchor = destination.partition("#")
            target = document.parent / filename if filename else document
            assert target.exists(), f"{document}: {destination}"
            if anchor:
                assert anchor in heading_ids(target.read_text()), f"{document}: {destination}"
            links += 1
    print(f"PASS: {links} live local links/anchors and document whitespace.")

    guide = (ROOT / "research/phases/P01/execution-guide.md").read_text()
    python_blocks = re.findall(r"python - <<'PY'[^\n]*\n(.*?)\nPY", guide, re.S)
    for block in python_blocks:
        ast.parse(block)
    bash_blocks = re.findall(r"```bash\n(.*?)\n```", guide, re.S)
    for block in bash_blocks:
        subprocess.run(["bash", "-n"], input=block, text=True, check=True)
    print(f"PASS: syntax of {len(python_blocks)} Python and {len(bash_blocks)} shell examples; none executed.")

    protected = ["benchmark", "dataset", "openspec", "guides", "not_in_origin",
                 "experiments_archive/1st_try_in_phase_fix_origin"]
    changes = subprocess.check_output(
        ["git", "diff", BASE, "--", *protected], cwd=ROOT
    )
    assert not changes, "Unexpected change to code, data or historical evidence."
    print("PASS: code, data, OpenSpec and historical GPU evidence unchanged.")


if __name__ == "__main__":
    main()
