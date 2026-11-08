## 1. Bind the v2 scientific contract

- [ ] 1.1 Update `temporal/protocol.py`, staged-entry exports and CLI defaults to v2 / 200 epochs / 3,800 updates / diagnostic epochs 10,50,100,200 / tail cutoff 160. Verify explicit formal 100-epoch requests fail before worker creation while short development fixtures remain labeled overrides.
- [ ] 1.2 Capture and bind both `protocol-v2.md` and its immutable inherited `protocol.md` identities through artifacts, effective conditions, selected weights and recovery metadata. Verify missing/mutated bindings fail with actionable errors, the inherited v1 hash matches the research declaration, and no research document is changed.

## 2. Align training, diagnostics and saved-stage boundaries

- [ ] 2.1 Save all v2 fixed-parameter diagnostic points and enforce the exact ordered 200-epoch completeness contract using frozen controls rather than literal v1 score names. Verify a tiny complete synthetic trajectory has 3,800 updates and each required score block, and a 100-epoch artifact cannot pass completeness.
- [ ] 2.2 Implement the 160-to-200 best-validation tail calculation and correctly named output minima/boundaries. Verify synthetic histories that reverse the old/new interval decisions, exact 1% threshold behavior, both-zero handling and at-least-2/3 aggregation without relaxing any other gate.
- [ ] 2.3 Enforce scientific/document-version compatibility across selection, diagnostics, report, saved checks and resume. Verify equal predictions do not admit mixed v1/v2 evidence, a v1 checkpoint cannot be continued as v2, missing a/b remains incomplete, and an unsupported old saved-only operation returns the documented original-runner reference without modifying inputs or accessing tests.

## 3. Carry forward enforceable cumulative cost

- [ ] 3.1 Extend ledger validation and accounting with an explicitly labeled conservative budget-debit entry and separate measured/replayed, forecast, debited and effective-used totals. Verify existing ledger IDs/history survive loading, unknown/negative/nonfinite entries fail closed, and forecasts remain nonbinding while debits reduce remaining budget.
- [ ] 3.2 Expose the explicit `budget-debit` registration operation with existing-ledger/batch checks, stable identity, seconds and reason. Verify identical replay is idempotent, conflicts cannot replace debit/measured entries, and no dataset/worker is accessed; use temporary ledgers only.
- [ ] 3.3 Apply effective cumulative usage to preflight, watchdog/controller, cost gates, resume, live saved-evidence stages and failure/termination paths; update the v2 estimate to `1.3*(setup+2*200*t)`. Verify carried spending plus debits alone can stop training and live saved checks, and recovery cannot reset them.
- [ ] 3.4 Meter standalone public preflight against a supplied existing ledger and document the narrow helper-cost recording interface. Verify pass/fail durations are billed once, internal fit preflight is not charged twice, and separate measured/debit labels remain correct.

## 4. Verify integrated behavior and hand off

- [ ] 4.1 Update finite nonnegative synthetic fixture generation and affected literal-v1 assertions; exercise a tiny complete v2 fit/select/diagnose/report/recompute/compare flow and interrupted same-v2 resume. Run the recurrent suite and relevant nograph-baseline regression suite, retaining early-best immutable restoration, global chunk weighting, four-window metrics, read-only checks and resource-stop coverage; verify no real dataset or formal research output is used.
- [ ] 4.2 Update README §4.7 and public help with actual v2 controls, diagnostic/output fields, dual-document provenance, debit registration and cumulative accounting, historical limitations and exact staged commands. Verify help/examples match the parser and clearly distinguish software readiness from real execution.
- [ ] 4.3 Write implementation notes linking each completed task to source/tests, commands/results, actual source basis and remaining limitations, including the research-side post-PASS debit/preflight/restart handoff. Verify no research record, historical run, real ledger, T009 or legacy runner changed; leave independent verification and acceptance to their workflows.
