# occupation-skill-graph Specification

## Purpose

Provide reproducible shared skill relations from training-period occupational demand, with context-preserving target mapping and diagnostic evidence suitable for a separate research acceptance decision.

## Requirements

### Requirement: Construction uses only canonical occupational training observations
The entry SHALL implement `P2-occupation-skill-graph-v1` using r2/count observations from the 27 unique months 2021-01 through 2023-03. It SHALL validate integer unique context/skill keys, a complete grid, the expected continuous 36-month source schema, and finite nonnegative training values. Published inputs SHALL assert occupations 0..51 and skills 0..2334; fixture inputs SHALL support smaller non-dense numeric IDs. It SHALL accumulate in float64 without first narrowing source values to float32. Held-out values SHALL NOT enter construction or trend diagnostics. File identity SHALL be distinct from canonical training-content identity. Unsupported sources, modes, folds and protocol versions SHALL fail explicitly.

#### Scenario: Held-out values cannot affect graphs
- **WHEN** valid inputs differ only in 2023-04 through 2023-12 values
- **THEN** training-content identity, graph choices, scores and numeric audits are unchanged, although source-file hashes can differ

#### Scenario: Row order cannot affect semantics
- **WHEN** a complete fixture with non-dense occupation and skill IDs is reordered
- **THEN** canonical numeric keys, training arrays, graph edges and numerical audits are identical under the same computation settings

#### Scenario: Invalid source fails before construction
- **WHEN** keys are duplicated or fractional, a grid cell or month is absent, or training demand is negative or nonfinite
- **THEN** the entry returns nonzero with the identity or value problem and never publishes completed graphs

### Requirement: Two explicit relation scores preserve inactive skills
The entry SHALL create occupational-support Jaccard and demand-distribution cosine as two independent candidates. For x[s,c] equal to training demand summed over unique months, support SHALL be x>0. Jaccard SHALL be intersection size divided by union size, with empty union zero. Cosine SHALL compare p[s]=x[s]/sum(x[s]), with zero-demand vectors assigned zero similarity to every skill. Scores SHALL be symmetric, finite and in [0,1] allowing only rounding-level clipping. All source skills SHALL remain in the node table, including zero-demand isolated skills. The entry SHALL NOT combine scores or use trends, published edges or test rankings to choose candidates.

#### Scenario: Hand-computable candidate differences
- **WHEN** fixture skill vectors are A=(1,1,0), B=(2,0,0), C=(0,0,0)
- **THEN** Jaccard(A,B)=1/2, cosine(A,B)=1/sqrt(2), C has no positive relations, and all three skills remain present

### Requirement: Sparsification is deterministic and retains explicit weights
Each candidate SHALL choose up to 10 positive-score other skills per skill, ordered by descending score and ascending numeric skill ID for exact ties, then retain the undirected union of selections. It SHALL save directed selections and canonical unique undirected edges with their original float64 scores. Self-loops, duplicate pairs and zero-score edges SHALL NOT be present. It SHALL report cutoff ties; union degree SHALL NOT be described as bounded by 10. Graph arrays SHALL be reproducible under row permutation and the recorded computation settings, without random tie-breaking or silent candidate expansion.

#### Scenario: Ties and asymmetric selections
- **WHEN** more than 10 neighbors tie at a selection boundary and one endpoint selects another without reciprocal selection
- **THEN** lower numeric skill IDs win exact ties, the one-sided selection is retained in the union, tie diagnostics are saved, and union degrees are computed from the final graph

#### Scenario: Empty relations remain explicit
- **WHEN** all fixture skills have zero demand or no positive pair score
- **THEN** candidate edge arrays are empty with the complete node table and explicit empty/null audit fields rather than fabricated fallback edges

### Requirement: A shared relation maps within target contexts without changing population
The entry SHALL audit r0, region and r2 target key tables by lifting each shared edge into each target context with unchanged score and both directions. It SHALL preserve canonical context/skill identities and SHALL NOT introduce cross-context edges or filter by target demand. Every context SHALL contain exactly the source skill set; missing, extra or duplicate keys SHALL fail instead of taking an intersection. It SHALL save target key identities, per-context mapped edge counts and an inspectable mapping without requiring full duplicated edge storage. Target value columns SHALL NOT enter mapping.

#### Scenario: Same graph in distinct contexts
- **WHEN** two target contexts share the source skills in arbitrary row order
- **THEN** each receives exactly the same skill relations and scores mapped to its own canonical nodes, with no edge between contexts

#### Scenario: Population mismatch is explicit
- **WHEN** one target context lacks a skill or has an extra skill
- **THEN** the entry rejects that target identity and does not publish a complete successful audit

### Requirement: Structural diagnostics expose coverage and score degeneracy
For each candidate the entry SHALL report source identities and cutoff, zero-demand skills, occupational support counts, pre-sparsification positive pair count/density and score summaries, boundary ties, final edge/isolated counts, degree and weight distributions, connected components, and associations of degree with total demand and occupational breadth. It SHALL distinguish all-skill from training-active coverage denominators, include candidate edge-set overlap, and explicitly represent empty or zero-variance statistics as null with reasons. It SHALL NOT interpret structural coverage as predictive benefit.

#### Scenario: Dense equal supports are visible
- **WHEN** many active skills have identical occupational support and Jaccard scores tie at one
- **THEN** the report exposes full-score concentration, tie-dependent neighbor choices and their coverage/degree consequences rather than claiming high-confidence predictive relations

### Requirement: Trends are diagnostic and insufficient histories remain unknown
For selected edges in every source occupation, the entry SHALL compute Pearson correlation of the 26 first differences only when both endpoints have at least 12 positive-demand training months and both difference variances are nonzero. Otherwise it SHALL report null with history-insufficient or constant-difference reason, prioritizing insufficient history. It SHALL retain per-edge eligible/insufficient/constant counts and eligible correlation summaries, aggregate positive/zero/negative counts and common-zero month fractions. Trends SHALL NOT change graph edges, weights or candidate selection. Eligibility SHALL be described as a diagnostic convention, not a significance or reliability test.

#### Scenario: Sparse and constant histories
- **WHEN** an edge has too few positive months in one occupation and eligible-but-constant differences in another
- **THEN** both correlations are null with distinct reasons, neither is counted as zero or negative correlation, and the graph edge and score are unchanged

#### Scenario: Occupational heterogeneity
- **WHEN** eligible first-difference sequences agree in one occupation and oppose in another
- **THEN** both signs are represented in the audit without averaging unknown contexts as zeros or automatically deleting the edge

### Requirement: CPU costs and incomplete work are observable and bounded
The entry SHALL operate without model or graph-learning packages, expose stage/block progress, and record construction, mapping and trend durations, dimensions and process peak RSS with byte units and measurement scope. Construction and trend stages SHALL each default to a 30-minute wall-clock limit; process RSS SHALL default to 2 GiB. It SHALL enforce limits with a monitored worker and preserve completed-stage evidence on failure, interruption or resource termination. It SHALL NOT silently reduce the node/month scope, alter candidate rules or restart work to satisfy a budget. A hard-killed worker SHALL remain detectably unfinished rather than successful.

#### Scenario: Resource limit or interruption
- **WHEN** a fixture worker exceeds an injected short budget, raises an error, or receives interruption
- **THEN** execution exits nonzero, retains available progress and a non-success terminal state or detectable unfinished state, and never publishes a completed manifest

### Requirement: Artifacts are exclusive self-contained and checkable without source data
The entry SHALL save unique non-overwriting artifacts including actual protocol contents/hash, canonical nodes and training observations/profiles, candidate choices/edges/scores, target keys/mapping, audits, exact command, code baseline and necessary execution differences, environment, costs and terminal status. Numeric arrays SHALL load without pickle. A saved-only check SHALL validate checksums, identities, dimensions, score/selection/mapping invariants and numerical audits from saved evidence without reading source demand files, fitting a model or modifying inputs. It SHALL reject missing, corrupt, contradictory and incomplete evidence, use normalized float64 tolerance 1e-12 for recalculated numeric values and exact checks for keys/counts/null reasons, and write only an exclusive external report.

#### Scenario: Self-contained saved check
- **WHEN** original data files are unavailable after a successful fixture execution
- **THEN** checking reproduces the scientific arrays and audits from saved training evidence, leaves input bytes unchanged and writes only the requested report

#### Scenario: Corruption or collision
- **WHEN** an edge score, identity, audit count or array is damaged, or the requested output already exists
- **THEN** checking or construction fails explicitly without repairing, replacing or overwriting evidence

### Requirement: Development and research acceptance remain separate
The public entry SHALL default to development output under ignored scratch or a validated temporary directory, refuse unsafe output overrides including resolved symlink destinations, and require explicit research purpose for a fresh research/runs audit directory. Purpose SHALL NOT change scientific computation. Implementation and verification SHALL use fixtures and SHALL NOT execute published-data construction, prediction training, modify research records, datasets or historical evidence, change existing published-graph/forecasting behavior, or declare graph freezing or scientific benefit. Usage documentation SHALL explain separate research software acceptance, real-data auditing and later T010 training integration.

#### Scenario: Fixture readiness
- **WHEN** implementation or independent verification exercises the public entry
- **THEN** only development fixture evidence is created and existing no-graph and published-graph interfaces retain their behavior

#### Scenario: Unsafe output override
- **WHEN** development output resolves into research, dataset, source or historical evidence through direct paths, traversal or symlinks
- **THEN** execution fails before reserving the output directory
