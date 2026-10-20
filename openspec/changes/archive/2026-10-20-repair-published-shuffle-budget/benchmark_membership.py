"""Bounded development comparison; no model calls or full graph preparation."""
import json
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from benchmark.graph_value_skeleton.shuffle import _swap_edges
from benchmark.graph_value_skeleton.graph import edge_set_sha256

rows = pd.read_parquet(ROOT / 'dataset/graph/r2.parquet')
edges = list(map(tuple, rows.loc[rows.r2_id == 12, ['row_id', 'col_id']].to_numpy().tolist()))
results = []
for repeat in range(3):
    for backend in ('set', 'dense'):
        start = time.perf_counter()
        result = _swap_edges(edges, seed_sequence=[0,12], accept_factor=1,
                             attempt_factor=500, backend=backend)
        results.append(dict(backend=backend, repeat=repeat, seconds=time.perf_counter()-start,
                            attempts=result['attempts'], accepted=result['accepted'],
                            rejections=result['rejections'], result_sha256=edge_set_sha256(result['result_edges'])))
assert len({r['result_sha256'] for r in results}) == 1
assert len({r['attempts'] for r in results}) == 1
output = {'purpose':'development membership benchmark', 'dataset':'r2', 'context':[12],
          'target_factor':1, 'nodes_with_edges':len({n for e in edges for n in e}),
          'active_bool_adjacency_bytes': len({n for e in edges for n in e})**2,
          'results': results, 'command':sys.argv, 'python':sys.version}
destination=ROOT/'openspec/changes/repair-published-shuffle-budget/evidence/membership.json'
destination.parent.mkdir(exist_ok=True)
with destination.open('x',encoding='utf-8') as handle: json.dump(output,handle,indent=2)
print(json.dumps(output))
