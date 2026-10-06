# Research Handoff

For research work, start with `RESEARCH.md`, then read `research/state.md` and the linked phase plan. Use the bundled `research-maintainer` skill at `.agents/skills/research-maintainer/SKILL.md`; its references are included in the repository. For this project, the versioned repository copy is authoritative when a global copy differs. The repository records remain sufficient to recover progress without the previous chat.

Task and phase status belongs to the phase plan. Record proposed advice separately from accepted decisions. Preserve sealed runs and legacy archives; update later storage and backup status in `research/archives/index.md`. Runtime source commits do not need to match current HEAD.

Update the recovery point and next action after meaningful progress and before handing off. Research bookkeeping does not authorize experiments, scientific protocol changes, commits, or pushes beyond current or existing user authorization. Use the existing OpenSpec workflows for implementation and independent verification when applicable.

## Cross-skill delegation pointer

The single handoff between the research records and the OpenSpec workflows is the pointer table at the end of this file. This file is workspace-level guidance, so it is present at the start of every session regardless of which skill is used: read the pointer before starting any workflow, and honour it whichever skill is running.

Rules:

- **Register before starting.** A delegation is registered by a research-side turn, before invoking any OpenSpec workflow — never from inside propose, apply, verify, fix, or archive, which have their own boundaries. Set `Status` to `open` and fill the change name (name only, not path: archiving adds a date prefix and moves the directory), the research task ID, the recycle condition, and the research-side wrap-up that recycle must trigger. Keep at most one `open` delegation.
- **Close only from read-only evidence.** Set `Status` to `returned` only when `openspec/changes/<change-name>` no longer exists and `openspec/changes/archive/*-<change-name>/verification.md` records `Verdict: PASS` whose verification basis still matches the current implementation. Record the evidence, then do the research-side wrap-up in a research turn.
- **While `open` is unresolved, a research turn reports and stops.** When maintaining research records, an unresolved `open` delegation means the change is not finished: say so with the read-only evidence and let the user decide. From a research turn, do not run apply, verify, fix, or archive workflows on the user's behalf, do not edit code or move directories, and do not commit or push. This never blocks the change itself: when the user explicitly starts that change's OpenSpec workflow, the session doing that work proceeds normally and leaves the pointer alone.
- **This is a pointer, not a progress table.** Never mirror OpenSpec task checkboxes here, in `research/state.md`, or in a phase plan. Research task status stays in the phase plan; change-level progress stays in the change directory. An OpenSpec `PASS` is evidence for a research acceptance decision, not the acceptance itself.
- **Nothing here changes a skill.** Editing this pointer touches project records only. The skills under `.agents/skills/` stay unmodified and remain authoritative for their own workflows.

<!-- Keep exactly one active entry below; use `none` and em dashes when nothing is in flight. -->

| Field | Value |
| --- | --- |
| Status | `none` |
| Change name | — |
| Research task | — |
| Registered (timestamp) | — |
| Delegated to | — |
| Recycle condition | — |
| Research-side wrap-up | — |
| Recycle record | — |
