# Occupation-skill graph audit

- Protocol: `P2-occupation-skill-graph-v1`
- Run: `p02-t009-occupation-20261107-01` (research)
- Fixture mode: `False`
- Training months: 27 (2021-01..2023-03)
- Occupations: 52
- Skills: 2335
- Top-k per candidate: 10

## Candidate structure

| candidate | edges | isolated | components | max degree | boundary-tie nodes |
| --- | --- | --- | --- | --- | --- |
| jaccard | 19649 | 27 | 28 | 117 | 1426 |
| cosine | 17629 | 27 | 28 | 37 | 11 |

Candidate edge overlap: 914 shared of 36364 union edges (Jaccard 0.025134748652513476).

## Target mapping

| target | contexts | skills | undirected edges per context |
| --- | --- | --- | --- |
| r0 | 1 | 2335 | 19649 |
| region | 7 | 2335 | 19649 |
| r2 | 52 | 2335 | 19649 |

## Trend diagnostics

| candidate | eligible contexts | insufficient | constant | unknown edges |
| --- | --- | --- | --- | --- |
| jaccard | 237763 | 783985 | 0 | 3814 |
| cosine | 158832 | 757876 | 0 | 2885 |

## Costs and limits

- Stage seconds: {"construct": 1.2119633330003126, "source": 0.10436091700103134, "targets": 0.06118404200060468, "trends": 0.5058943330004695}
- Peak RSS: 472743936 bytes (resource.getrusage(RUSAGE_SELF).ru_maxrss; worker process lifetime)
- Build stage timeout: 1800.0 s
- Trend stage timeout: 1800.0 s
- Process RSS limit: 2147483648 bytes

This is software evidence only. It does not freeze a graph, accept a scientific candidate, run prediction training or claim predictive benefit. Real published-data construction and research acceptance are separate research-side actions.
