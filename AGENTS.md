# Research Handoff

For research work, start with `RESEARCH.md`, then read `research/state.md` and the linked phase plan. Use the bundled `research-maintainer` skill at `.agents/skills/research-maintainer/SKILL.md`; its references are included in the repository. For this project, the versioned repository copy is authoritative when a global copy differs. The repository records remain sufficient to recover progress without the previous chat.

Record authority, templates and what belongs in each file follow the bundled skill. This file adds only the project conventions below and does not restate the skill's rules. Implementation and independent verification use the existing OpenSpec workflows when applicable.

## Storage and save status

Storage and backup status entries describe artifacts — runs, sealed packages, delivered analyses, implementation and acceptance batches — not the record files themselves. Index, state, plan and decision files are ordinary versioned documents whose commit identity is read from Git history: when a commit is part of the same authorized action, write save status without that commit's own hash (for example "saved by this document commit; identity traced from Git history"), and keep the concrete save-status commit hash only in `research/archives/index.md`. Never add a follow-up commit whose only purpose is to restate that a record was committed.

## Cross-skill delegation pointer

Delegations from the research records to the OpenSpec workflows are tracked in `DELEGATION.md` at the repository root. That file holds mutable state; this file holds the stable rules for it.

- A research-side turn reads `DELEGATION.md` at the start of every session, before running its workflow, and honours it.
- It has exactly one writer: a research-side (research-maintainer) turn. The OpenSpec workflows — propose, apply, verify, fix, archive — neither read nor write it and are never responsible for updating it.
- Register a delegation before invoking an OpenSpec workflow, never from inside one. Record the change name (name only, not path: archiving adds a date prefix and moves the directory), the research task ID, the completion criterion, and the research-side wrap-up the recycle owes. Keep at most one delegation in flight.
- While a delegation is `open`, a research turn checks its completion criterion read-only and then either reminds the user that the change is unfinished, or — when the evidence shows it has finished — performs the research-side wrap-up and closes the pointer. It must not run apply, verify, fix, or archive workflows on the user's behalf, edit code, move directories, or commit or push.
- The pointer is a pointer, not a progress table: never mirror OpenSpec task checkboxes into it, into `research/state.md`, or into a phase plan. Research task status stays in the phase plan; change-level progress stays in the change directory. An OpenSpec `PASS` is evidence for a research acceptance decision, not the acceptance itself.
- These rules govern the pointer only. They do not change any skill: skills under `.agents/skills/` are updated through their own changes and stay authoritative for their workflows.
