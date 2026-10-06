# Research Handoff

For research work, start with `RESEARCH.md`, then read `research/state.md` and the linked phase plan. Use the bundled `research-maintainer` skill at `.agents/skills/research-maintainer/SKILL.md`; its references are included in the repository. For this project, the versioned repository copy is authoritative when a global copy differs. The repository records remain sufficient to recover progress without the previous chat.

Task and phase status belongs to the phase plan. Record proposed advice separately from accepted decisions. Preserve sealed runs and legacy archives; update later storage and backup status in `research/archives/index.md`. Runtime source commits do not need to match current HEAD.

Update the recovery point and next action after meaningful progress and before handing off. Research bookkeeping does not authorize experiments, scientific protocol changes, commits, or pushes beyond current or existing user authorization. Use the existing OpenSpec workflows for implementation and independent verification when applicable.

## Cross-skill delegation pointer

Delegations from the research records to the OpenSpec workflows are tracked in `DELEGATION.md` at the repository root. That file holds mutable state; this file holds the stable rules for it.

- Read `DELEGATION.md` at the start of every session, before any skill's workflow, and honour it whichever skill is running.
- It has exactly one writer: a research-side (research-maintainer) turn. The OpenSpec workflows — propose, apply, verify, fix, archive — neither read nor write it and are never responsible for updating it.
- Register a delegation before invoking an OpenSpec workflow, never from inside one. Record the change name (name only, not path: archiving adds a date prefix and moves the directory), the research task ID, the completion criterion, and the research-side wrap-up the recycle owes. Keep at most one delegation in flight.
- While a delegation is `open`, a research turn checks its completion criterion read-only and then either reminds the user that the change is unfinished, or — when the evidence shows it has finished — performs the research-side wrap-up and closes the pointer. It must not run apply, verify, fix, or archive workflows on the user's behalf, edit code, move directories, or commit or push.
- The pointer is a pointer, not a progress table: never mirror OpenSpec task checkboxes into it, into `research/state.md`, or into a phase plan. Research task status stays in the phase plan; change-level progress stays in the change directory. An OpenSpec `PASS` is evidence for a research acceptance decision, not the acceptance itself.
- Nothing here changes a skill. The skills under `.agents/skills/` stay unmodified and remain authoritative for their own workflows.
