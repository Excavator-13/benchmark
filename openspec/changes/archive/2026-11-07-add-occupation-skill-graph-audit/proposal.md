## Why

P02-T009 needs a reproducible way to derive one shared skill graph from training-period occupational demand and inspect its behavior across contexts. Existing entries consume published graphs; they cannot build these relations or distinguish insufficient local trend evidence from conflicting evidence.

## What Changes

- Add a CPU-only graph construction and audit entry implementing `research/phases/P02/t009-graph-protocol.md` (`P2-occupation-skill-graph-v1`).
- Build two independent candidates from r2 training demand: occupational-support Jaccard and demand-distribution cosine, with deterministic top-10 union sparsification and explicit scores.
- Audit structure, degeneracy, shared-graph mapping to r0/region/r2 identities, and occupational trend heterogeneity; preserve unknown trends and zero-demand skills.
- Save inspectable non-overwriting artifacts, source/protocol identities, costs, progress and failure states, with a saved-only checker.
- Document fixture development and later research execution separately. Do not run published-data graph experiments during implementation/verification or integrate candidate graphs into forecast training.

## Capabilities

### New Capabilities

- `occupation-skill-graph`: Training-only occupational skill relations, deterministic sparsification, target mapping, diagnostic audits and reproducible artifacts.

### Modified Capabilities

None. `graph-value-skeleton` keeps its published binary graph and frozen training contracts; `graph-forecast-data-pipeline` keeps its published weighted export semantics. Their existing specifications were inspected in full; this separate graph-building capability does not replace either.

## Impact

Add `benchmark/occupation_skill_graph/`, fixture tests and a README usage section, using the existing NumPy/pandas/PyArrow CPU environment. Reuse canonical numeric key/month conventions without routing source counts through the old float32 demand loader. No new graph/ML dependency, dataset edits, historical evidence changes, model fitting, hierarchy inference, company/region-source construction, or research acceptance automation.
