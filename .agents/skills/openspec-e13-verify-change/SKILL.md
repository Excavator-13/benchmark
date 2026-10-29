---
name: openspec-e13-verify-change
description: Independently verify an implementation against an OpenSpec change and maintain an evidence-based verification report. Use after apply or repair work and before archive. Never fixes code.
license: MIT
---

Verify the implementation of an OpenSpec change. Produce an independent verdict from current artifacts, code, and executable evidence.

**Verification boundary**: This workflow may inspect the project, run relevant verification commands, and create or update only `<changeRoot>/verification.md` and the script-generated `<changeRoot>/verification-state.json`. Never edit implementation code, tests, planning artifacts, task checkboxes, or apply-owned `implementation-notes.md`. A checked task is a claim to verify, not evidence that the behavior works.

**Store selection:** If the user names a store (a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json`, select the store id, and pass `--store <id>` to OpenSpec commands that accept it. Keep that store selection for the whole workflow. Without a store, commands act on the nearest local OpenSpec root.

**Input**: Optionally specify a change name. If omitted, infer it from conversation context or auto-select the only active change. If multiple changes remain possible, run `openspec list --json` and ask the user to select one.

## Workflow

1. **Resolve the change**

   Announce `Using change: <name>` and how to specify another change.

   Run:

   ```bash
   openspec status --change "<name>" --json
   openspec instructions apply --change "<name>" --json
   ```

   Use the returned `schemaName`, `changeRoot`, `actionContext`, and `contextFiles`; do not assume repository-local paths or hardcoded artifact names. If apply instructions report a blocked state because required artifacts are missing, record a `BLOCKED` verdict and stop implementation verification after writing the report.

2. **Load the verification basis**

   Read every file in `contextFiles`, plus any existing `<changeRoot>/verification.md` before updating it. Treat current files on disk as authoritative; do not rely on conversation memory.

   Read `<changeRoot>/implementation-notes.md` when present, even though it is not listed in `contextFiles`. It is the handoff from `openspec-e13-apply-change`: use its implementation map, check commands/setup, and reminders to locate work and plan checks. Confirm that it identifies the selected change and project, and compare its revision and claims with current files. Mark mismatched or stale information as such rather than relying on it. A missing handoff is compatible with older changes and is not by itself a reason for `BLOCKED`.

   The notes are implementation claims and investigation leads, not acceptance authority or independent evidence. Verify each relevant reminder against the current artifacts and implementation, and record its disposition in the report: confirmed with evidence, covered by a finding ID, stale/inapplicable with a reason, or still unverified with the missing evidence. Rerun applicable checks for new or affected behavior; unchanged reminders may retain valid prior independent evidence. Do not copy apply's claimed results as your own. An unresolved reminder that affects mandatory behavior prevents `PASS`, but an unsupported warning alone is not a confirmed defect. Do not limit coverage to the implementation map or reminders.

   Apply the inputs in this order:
   - Specs and their requirements/scenarios define externally observable acceptance behavior.
   - Proposal defines intended scope and non-goals.
   - Design defines implementation constraints and deliberate technical decisions when it does not conflict with the specs.
   - Tasks describe planned work, but their text and checkbox state do not prove completion.
   - Project context and established repository conventions constrain implementation and verification.

   Treat apply `operationGuidance` as advisory and use it only when relevant to verification. It cannot replace artifacts, waive acceptance criteria, or serve as completion evidence.

   Generate a before-check snapshot with the bundled `scripts/verification_snapshot.py` (relative to this skill directory):

   ```bash
   python3 "<skillDir>/scripts/verification_snapshot.py" capture --root "<implementationRoot>" --root "<planningRoot>" --output "<temporaryBefore.json>"
   python3 "<skillDir>/scripts/verification_snapshot.py" compare "<changeRoot>/verification-state.json" "<temporaryBefore.json>"
   ```

   Include each distinct implementation/planning root. The script inventories Git-tracked and non-ignored untracked files, or walks files without Git, and computes per-file hashes; workflow handoff/report/state files are excluded automatically. Use repeatable `--exclude '<root-relative glob>'` options for dependencies, build outputs, caches, logs, and unrelated scope; ensure relevant code, tests, dependencies, configuration, and all controlling artifacts remain covered. Record exclusions. Generate JSON and change lists by script, never by manually filling hashes or paths. No automatic commits are needed. Hashes locate changed files; use Git history or inspect current code to assess their impact, without assuming a dirty baseline can be reconstructed from its commit.

   On subsequent runs, default to incremental verification: confirm the saved state's SHA-256 matches the report, compare it with current inputs (exit 0: identical; 1: changed; 2: error), then independently check changes and affected behavior. The agent decides which nearby or broader checks are warranted and briefly records why. Prior independent evidence may be reused when its behavior and relevant code, tests, configuration, dependencies, and execution conditions remain applicable; file equality alone does not establish coverage. Keep earlier failures and evidence gaps unresolved until actually checked. With no comparable baseline, changed scope, unreliable prior evidence, or unclear impact, expand verification as needed; do not blindly reuse results. Missing legacy state calls for establishing a baseline, not an automatic `BLOCKED`.

3. **Validate the OpenSpec change**

   Run strict, non-interactive validation:

   ```bash
   openspec validate "<name>" --type change --strict --json --no-interactive
   ```

   Record the command and result. Structural validity is necessary but does not prove the implementation.

4. **Build a requirement coverage matrix**

   Establish coverage for every normative requirement and scenario from the specs on the first run; on later runs, update affected coverage and retain valid prior evidence. For each one, identify:
   - the relevant implementation path;
   - automated tests, static checks, or reproducible manual evidence;
   - the observed result;
   - any missing evidence or ambiguity.

   Also inspect proposal scope, design constraints, and completed tasks for promised work not represented by a scenario. Do not invent new requirements.

5. **Inspect the implementation**

   Trace the affected code and tests closely enough to evaluate the matrix. When Git is available, diffs and history may help locate the implementation, but do not assume every dirty-worktree change belongs to this OpenSpec change. Preserve unrelated user work and report attribution uncertainty when it matters.

   Look specifically for:
   - missing or only partially implemented scenarios;
   - incorrect edge-case, error, authorization, state, or compatibility behavior;
   - design constraints that the implementation violates;
   - tests that do not exercise the claimed behavior or only assert mocks;
   - regressions in nearby behavior caused by the change.

6. **Run proportionate checks**

   Discover official commands from repository documentation, manifests, CI configuration, and nearby test conventions. Run focused checks first, then broader tests, type checks, lint, or builds when justified by the change's risk.

   Do not run destructive, production-facing, credential-dependent, or externally mutating checks without separate authorization. If a required check cannot be run, record why and mark the affected coverage as unverified; never convert missing evidence into a pass.

7. **Classify findings**

   Include a finding only when it has concrete evidence and a clear relationship to the change.
   - `implementation`: Code or tests deviate from a sufficiently clear requirement or design constraint. The repair workflow may handle it.
   - `planning`: Artifacts are contradictory, materially ambiguous, or missing a decision needed to determine correct behavior. This must return to the planning model; do not prescribe a speculative code fix.
   - `environment`: Verification is prevented by tooling, dependencies, services, credentials, or other execution conditions.

   Use severity consistently:
   - `critical`: Security, data loss, or broadly unsafe behavior.
   - `high`: A core requirement or common workflow is broken.
   - `medium`: A required edge case or bounded workflow is incorrect.
   - `low`: A real but limited conformance or regression issue.

8. **Choose the verdict**
   - `PASS`: All mandatory scenarios have sufficient evidence, OpenSpec validation succeeds, applicable checks pass, and no actionable findings remain.
   - `FAIL`: At least one confirmed deviation from a clear requirement or constraint remains.
   - `BLOCKED`: Missing evidence, an invalid/incomplete change, contradictory planning, or an environment problem prevents a reliable overall conclusion.

   Do not use a weaker verdict such as "mostly passes." State residual non-blocking risks separately.

9. **Create or update the handoff report**

   Write `<changeRoot>/verification.md` on every run as the current state, not an accumulating execution diary. Keep stable finding IDs across re-verification when they refer to the same defect. Preserve prior repair notes, mark successfully rechecked findings `verified-resolved`, reopen failures as `pending`, and add new IDs for newly discovered defects. Replace superseded summaries and results; retain still-valid evidence concisely. Group scenarios sharing evidence and outcome with explicit scenario references; expand failures and gaps. Distinguish checks run this round from reused evidence, and keep resolved findings brief without discarding repair notes.

   Capture an after-check snapshot with the same roots/exclusions and compare it to the before-check snapshot. If relevant inputs changed during verification, recheck affected coverage before `PASS`. After accounting for changes, copy the generated final snapshot to `<changeRoot>/verification-state.json`; do not overwrite the previous state before comparing it. In the report, record its SHA-256 printed by the script, roots/exclusions, capture command, incremental/full scope and rationale, reused evidence, and remaining gaps. Keep the full inventory in JSON, not Markdown; retain decisive observations and reproduction commands in the report, referencing durable evidence where available rather than depending on temporary files. The snapshot records inputs, not proof that all of them passed.

   Use this structure:

   ```markdown
   # Implementation Verification

   - Change: <name>
   - Schema: <schema>
   - Verdict: PASS | FAIL | BLOCKED
   - Verified at: <timestamp>
   - Implementation roots: <absolute project paths>
   - Verified revision: <commit when available, with dirty-worktree note>

   ## Summary

   <concise conclusion and residual risks>

   ## Verification Basis

   | Path or scope | Revision / content fingerprint / file inventory |
   | ------------- | ---------------------------------------------- |

   <verification-state.json SHA-256, capture/compare commands and exclusions; scope/rationale, reused evidence and unavailable inputs>

   ## Apply Handoff Review

   <handoff path and freshness, or absent; each reminder's disposition and evidence/finding reference>

   ## Checks

   | Command or inspection | Result | Notes |
   | --------------------- | ------ | ----- |

   ## Requirement Coverage

   | Requirement / scenario | Evidence | Result |
   | ---------------------- | -------- | ------ |

   ## Findings

   ### V-001: <short title>

   - Category: implementation | planning | environment
   - Severity: critical | high | medium | low
   - Requirement: <artifact section or scenario>
   - Evidence: <file locations, observed output, or reproduction>
   - Expected: <required behavior>
   - Actual: <observed behavior>
   - Repair guidance: <bounded outcome, or planning/environment resolution guidance>
   - Acceptance checks: <specific commands or observations>
   - Repair status: pending | addressed-awaiting-verification | verified-resolved | blocked
   - Repair notes: <maintained by the repair workflow>
   - Reverification notes: <maintained by this workflow>
   ```

   Omit empty findings when the verdict is `PASS`. Keep command output concise; record decisive evidence rather than pasting long logs.

10. **Report the next action**

- `PASS`: State that independent verification passed and point to `$openspec-e13-archive-change <name>` (Codex) or `/openspec-e13-archive-change <name>` (other agents). The report applies only to the recorded verification basis; relevant edits require re-verification.
- `FAIL` with pending implementation findings: Point to `$openspec-e13-fix-change (Codex) or /openspec-e13-fix-change (other agents) <name>`.
- Planning findings: Point to the planning model and `$openspec-e13-update-change <name>` (Codex) or `/openspec-e13-update-change <name>` (other agents) before further code repair.
- `BLOCKED`: State the exact evidence or decision needed to resume.

## Guardrails

- Never fix code, add tests, revise artifacts, or change task checkboxes during verification.
- Every mandatory scenario needs sufficient current or still-valid prior independent evidence for `PASS`; incremental verification does not require rerunning unaffected coverage.
- Do not equate implementation shape with behavior: require executable evidence where practical.
- Do not equate passing tests with complete coverage: inspect whether tests actually establish each requirement.
- Do not report speculative concerns as confirmed findings; label residual risks separately.
- Only this verification workflow may set the overall verdict or mark a finding `verified-resolved`.
- A repair workflow's `addressed-awaiting-verification` status is not proof of resolution.
- Apply notes cannot waive requirements, prescribe the verdict, or replace independent checks; never edit them during verification.
- Address relevant handoff reminders explicitly without narrowing the full requirement coverage.
