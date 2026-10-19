"""Exclusive graph-only preparation, saved-only validation and immutable reuse."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
import numpy as np

from . import artifacts, data, graph, protocol, shuffle
from .config import resolve_output_root

FILES = ('nodes.npy', 'source-edges.npy', 'edges.npy', 'shuffle-audit.json',
         'provenance.json', 'environment.json', 'source.json', 'measurements.json', 'status.json')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def generator_identity():
    """Only the generator's numerical source and runtime, independent of paths."""
    import pandas
    import pyarrow
    return {'source_sha256': {name: sha(Path(__file__).parent / name)
                             for name in ('shuffle.py', 'graph.py', 'protocol.py')},
            'python': list(sys.version_info[:3]), 'numpy': np.__version__,
            'pandas': pandas.__version__, 'pyarrow': pyarrow.__version__}


def peak_memory():
    memory = artifacts.measure_peak_rss()
    memory['scope'] = 'graph worker process lifetime'
    return memory


def prepare(config):
    """A development RunConfig supplies paths/identity, never a model invocation."""
    if config.purpose != protocol.PURPOSE_DEVELOPMENT or config.method != protocol.METHOD_SHUFFLED:
        raise ValueError('graph preparation requires development shuffled configuration')
    if config.shuffle_artifact:
        raise ValueError('preparation cannot consume another prepared artifact')
    root = resolve_output_root(Path(config.repo_root), config.purpose, Path(config.output_root))
    run = artifacts.run_directory(root, config.run_id, 'prepare-shuffle').reserve()
    started = time.perf_counter()
    stage = 'source_capture'
    durations = {}
    try:
        run.write_json('progress.json', {'stage': stage, 'updated': artifacts.now()})
        run.write_json('command.json', {'argv': list(config.command), 'cwd': os.getcwd()})
        run.write_json('config.json', config.to_dict())
        source = artifacts.capture_source(run, Path(config.repo_root), protocol_path=protocol.PROTOCOL_PATH)
        environment = artifacts.capture_environment(Path(config.repo_root))
        run.write_json('environment.json', environment)
        stage = 'demand_read'
        run.write_json('progress.json', {'stage': stage, 'updated': artifacts.now()})
        before = time.perf_counter()
        dataset = data.load_dataset(config.data_name,
            demand_path=Path(config.demand_path) if config.demand_path else None, published=config.published)
        durations[stage] = time.perf_counter() - before
        stage = 'graph_read'
        before = time.perf_counter()
        source_graph = graph.load_graph(config.data_name, dataset.key_array,
            graph_path=Path(config.graph_path) if config.graph_path else None,
            published=config.graph_path is None)
        durations[stage] = time.perf_counter() - before
        stage = 'shuffle'
        before = time.perf_counter()
        result = shuffle.shuffle_graph(config.data_name, dataset.key_array, source_graph.edges,
            config.shuffle_seed, progress=lambda payload: run.write_json('progress.json',
                {**payload, 'stage': stage, 'updated': artifacts.now()}))
        durations[stage] = time.perf_counter() - before
        run.save_npy('nodes.npy', dataset.key_array)
        run.save_npy('source-edges.npy', source_graph.edges)
        run.save_npy('edges.npy', result.edges)
        run.write_json('shuffle-audit.json', result.audit)
        run.write_json('provenance.json', {'schema': 'prepared-shuffle-v1',
            'purpose': 'development', 'data_name': config.data_name,
            'shuffle_seed': config.shuffle_seed, 'generator': generator_identity(),
            'demand': dataset.identity_payload(), 'graph': source_graph.identity_payload(),
            'shuffle': result.identity_payload()})
        problems = artifacts.verify_captured_source(source, Path(config.repo_root))
        if problems:
            raise ValueError(f'execution source changed: {problems}')
        durations['total'] = time.perf_counter() - started
        run.write_json('measurements.json', {'durations_seconds': durations,
            'peak_memory': peak_memory(), 'purpose': 'development graph-only',
            'nodes': len(dataset.key_array), 'edges': len(result.edges)})
        run.set_status('success', stage='complete', purpose='development')
        run.write_json('checksums.json', {'schema': 'prepared-shuffle-v1',
                       'files': {name: sha(run.path / name) for name in FILES}})
        # A completed artifact must satisfy the same independent saved audit oracle.
        load(run.path)
        return {'status': 'success', 'artifact_dir': str(run.path),
                'result_sha256': result.edges_sha256, 'durations_seconds': durations}
    except BaseException as exc:
        if isinstance(exc, shuffle.ShuffleError):
            run.write_json('shuffle-failure.json', exc.diagnostics)
        run.set_status('interrupted' if isinstance(exc, (KeyboardInterrupt, SystemExit)) else 'failed',
                       stage=stage, reason=f'{type(exc).__name__}: {exc}',
                       elapsed_seconds=time.perf_counter() - started)
        raise


def load(directory, *, keys=None, source_edges=None, data_name=None, shuffle_seed=None,
         require_current_generator=False):
    """Fail closed on damaged, partial, incompatible or noncanonical evidence."""
    from .checks import validate_shuffle_audit
    directory = Path(directory)
    manifest = read_json(directory / 'checksums.json')
    if manifest.get('schema') != 'prepared-shuffle-v1' or set(manifest.get('files', {})) != set(FILES):
        raise ValueError('incomplete prepared checksum manifest')
    for name in FILES:
        if sha(directory / name) != manifest['files'][name]:
            raise ValueError(f'prepared checksum mismatch: {name}')
    if read_json(directory / 'status.json').get('state') != 'success':
        raise ValueError('prepared artifact is failed, interrupted or unfinished')
    provenance = read_json(directory / 'provenance.json')
    if provenance.get('schema') != 'prepared-shuffle-v1' or provenance.get('purpose') != 'development':
        raise ValueError('unsupported prepared artifact schema/purpose')
    protocol.validate_dataset_name(provenance.get('data_name'))
    protocol.validate_shuffle_seed(protocol.METHOD_SHUFFLED, provenance.get('shuffle_seed'))
    arrays = {name: np.load(directory / name, allow_pickle=False)
              for name in ('nodes.npy', 'source-edges.npy', 'edges.npy')}
    saved_keys = arrays['nodes.npy']
    if (saved_keys.dtype != np.int64 or saved_keys.ndim != 2 or saved_keys.shape[1] < 2
        or len(saved_keys) == 0 or (saved_keys < 0).any()
        or not np.array_equal(saved_keys, np.unique(saved_keys, axis=0))):
        raise ValueError('prepared node keys must be canonical unique nonnegative int64 keys')
    original, result_edges = arrays['source-edges.npy'], arrays['edges.npy']
    for name, edges in (('source', original), ('result', result_edges)):
        if (edges.dtype != np.int64 or edges.ndim != 2 or edges.shape[1] != 2
            or (edges.size and (edges.min() < 0 or edges.max() >= len(saved_keys)))
            or not np.array_equal(edges, graph.canonical_edge_array(edges))
            or len(edges) != len(np.unique(edges, axis=0))
            or (edges[:, 0] == edges[:, 1]).any()):
            raise ValueError(f'invalid canonical prepared {name} edges')
    if len(original) != len(result_edges):
        raise ValueError('prepared edge count changed')
    shuffle._assert_preserved(provenance['data_name'], saved_keys, original, result_edges)
    if original.size and not np.array_equal(saved_keys[original[:,0], :-1], saved_keys[original[:,1], :-1]):
        raise ValueError('prepared source has cross-context edges')
    audit = read_json(directory / 'shuffle-audit.json')
    problems = []
    validate_shuffle_audit(saved_keys, original, result_edges, audit, provenance['shuffle_seed'], problems)
    if problems:
        raise ValueError('; '.join(problems))
    shuffled = shuffle.ShuffledGraph(provenance['data_name'], provenance['shuffle_seed'], original, result_edges, audit)
    if provenance.get('shuffle') != shuffled.identity_payload():
        raise ValueError('prepared shuffle provenance mismatch')
    if provenance.get('demand', {}).get('node_keys_sha256') != graph.node_keys_sha256(saved_keys):
        raise ValueError('prepared node provenance mismatch')
    if provenance.get('graph', {}).get('edges_sha256') != graph.edge_set_sha256(original):
        raise ValueError('prepared source provenance mismatch')
    for label, expected, actual in (('dataset', data_name, provenance['data_name']),
                                    ('shuffle seed', shuffle_seed, provenance['shuffle_seed'])):
        if expected is not None and expected != actual:
            raise ValueError(f'prepared {label} mismatch')
    if keys is not None and not np.array_equal(keys, saved_keys):
        raise ValueError('prepared node identity mismatch')
    if source_edges is not None and not np.array_equal(source_edges, original):
        raise ValueError('prepared source edge identity mismatch')
    if require_current_generator and (audit['algorithm_version'] != protocol.SHUFFLE_VERSION
                                     or provenance.get('generator') != generator_identity()):
        raise ValueError('prepared generator source/runtime/version is incompatible')
    return shuffled, provenance


def check(directory, report, repo_root, command):
    from .checks import validate_report_destination, _write_report
    destination = validate_report_destination(repo_root, report, [directory])
    payload = {'command': list(command), 'artifact_dir': str(directory),
               'checker_source': artifacts.checker_source_identity(repo_root)}
    try:
        result, provenance = load(directory)
        payload.update(status='ok', identity=result.identity_payload(),
                       generator=provenance['generator'])
    except Exception as exc:
        payload.update(status='failed', reason=f'{type(exc).__name__}: {exc}')
    _write_report(destination, payload)
    return payload
