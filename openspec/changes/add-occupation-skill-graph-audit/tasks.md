## 1. Canonical training inputs

- [ ] 1.1 Add the isolated occupation_skill_graph package and train-only Parquet loading with native-to-float64 precision, canonical keys and separate file/training identities; verify shuffled non-dense fixtures and held-out perturbations yield identical training arrays and no held-out value reads.
- [ ] 1.2 Implement published r2 assertions, complete-grid/invalid-key/month/value rejection and explicit unsupported scope errors; verify negative fixtures fail before graph computation and old loader/global constants remain unchanged.

## 2. Relation scores and sparse graphs

- [ ] 2.1 Implement blockwise Jaccard and distribution cosine with zero-vector handling; verify independently hand-calculated scores including A=(1,1,0), B=(2,0,0), inactive C, disjoint supports and scale invariance within float64 tolerance.
- [ ] 2.2 Implement deterministic top-10 positive selections and undirected union with scores and tie diagnostics; verify fixtures with more than 10 tied neighbors, one-sided selection, no self/duplicate/zero edges, unchanged row-permutation results and degree accounting after union.
- [ ] 2.3 Produce structural summaries and candidate overlap with explicit denominators and null reasons; verify all-zero, disconnected, equal-support and zero-variance fixtures against independent counts/components/statistics.

## 3. Target mapping and local trends

- [ ] 3.1 Add key-only target mapping for r0/region/r2 and inspectable lazy per-context edge expansion; verify multiple non-dense contexts preserve exact skill/score identity and reject absent/extra/duplicate target skills without reading target demand values.
- [ ] 3.2 Implement blockwise diagnostic first-difference correlations and eligibility/null reasons on shared candidate edges; verify opposing occupational signs, insufficient histories, constant differences, common zeros and entirely unknown edges, with graph bytes unchanged by diagnostics.

## 4. Evidence and bounded execution

- [ ] 4.1 Add exclusive build artifacts, embedded protocol/source identity, canonical numeric payloads, checksum inventory and explicit terminal states using readable research filenames; verify non-pickle reload, refusal to overwrite and recoverable completed-stage evidence after injected failures.
- [ ] 4.2 Add isolated worker/supervisor, recorded CPU thread settings, stage progress, default time/RSS limits and platform-aware measurement; verify short-budget, memory-limit, unsupported-monitor and cancellation fixtures produce non-success outcomes with scope/units and no automatic retry or silent workload reduction.
- [ ] 4.3 Expose build/check CLI with development scratch/temp paths and explicit research-purpose resolution; verify help without ML imports, invalid purpose/scope, collisions, and forbidden direct/traversal/symlink output locations, including a checkout under the temporary root.
- [ ] 4.4 Implement saved-only checking that rederives scientific arrays/audits and validates identities/inventory without reopening sources; verify source removal, input-byte preservation, 1e-12 numerical agreement, exclusive external report behavior, and rejection of corrupt scores, counts, key identities and incomplete status.

## 5. Integration and verification handoff

- [ ] 5.1 Add a README section with fixture build/check examples, actual runtime requirements, graph-score semantics and separate research acceptance/real-data audit/T010 integration steps; verify documented fixture commands run in the existing pinned CPU environment without torch or graph dependencies.
- [ ] 5.2 Run the new fixture suite and relevant old no-graph/published-graph compatibility checks; verify old help/imports and existing scientific computation remain unchanged, and keep all software evidence outside research records and published-data experiment outputs.
- [ ] 5.3 Write implementation-notes.md mapping all new requirements to files and exact verification commands/results, listing measured fixture costs and limitations; verify the handoff supports independent e13 verification without claiming research graph freezing or predictive benefit.
