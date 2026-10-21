"""Object-free epoch checkpoints with digest-checked atomic publication."""
from __future__ import annotations

import hashlib
import io
import json
import math
import random
import uuid
from pathlib import Path

import torch
import numpy as np

from . import artifacts, protocol

SCHEMA = 1


class CheckpointError(ValueError):
    pass


def rng_state():
    return {"python": random.getstate(), "numpy": np.random.get_state(),
            "torch": torch.get_rng_state()}


def restore_rng(state):
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"])


def encode(payload):
    arrays = {}

    def pack(value):
        if isinstance(value, (torch.Tensor, np.ndarray)):
            array = value.detach().cpu().numpy() if isinstance(value, torch.Tensor) else value
            if array.dtype.hasobject or array.dtype.kind not in 'biuf':
                raise CheckpointError('Unsupported checkpoint array dtype')
            if not np.isfinite(array).all():
                raise CheckpointError('Nonfinite checkpoint array')
            key = f'a{len(arrays)}'
            arrays[key] = array
            return {'tensor' if isinstance(value, torch.Tensor) else 'array': key}
        if isinstance(value, dict):
            return {'dict': [[pack(k), pack(v)] for k, v in value.items()]}
        if isinstance(value, (tuple, list)):
            return {'tuple' if isinstance(value, tuple) else 'list': [pack(v) for v in value]}
        if value is None or type(value) in (str, int, bool, float):
            if isinstance(value, float) and not math.isfinite(value):
                raise CheckpointError('Nonfinite checkpoint scalar')
            return value
        raise CheckpointError(f'Unsupported checkpoint value: {type(value)}')

    tree = pack(payload)
    arrays['metadata'] = np.frombuffer(json.dumps(tree, allow_nan=False).encode(), dtype=np.uint8)
    stream = io.BytesIO()
    np.savez(stream, **arrays)
    return stream.getvalue()


def decode(raw):
    used = set()
    try:
        with np.load(io.BytesIO(raw), allow_pickle=False) as saved:
            if saved['metadata'].dtype != np.uint8 or saved['metadata'].ndim != 1:
                raise CheckpointError('Invalid metadata dtype/shape')
            tree = json.loads(saved['metadata'].tobytes())

            def unpack(value):
                if not isinstance(value, dict):
                    if value is None or type(value) in (str, int, bool, float):
                        if isinstance(value, float) and not math.isfinite(value):
                            raise CheckpointError('Nonfinite scalar')
                        return value
                    raise CheckpointError('Invalid scalar')
                if len(value) != 1:
                    raise CheckpointError('Invalid tagged value')
                tag, item = next(iter(value.items()))
                if tag in ('tensor', 'array'):
                    if item in used or item == 'metadata':
                        raise CheckpointError('Duplicate array reference')
                    used.add(item)
                    array = saved[item].copy()
                    if array.dtype.kind not in 'biuf' or not np.isfinite(array).all():
                        raise CheckpointError('Invalid numeric array')
                    return torch.from_numpy(array) if tag == 'tensor' else array
                if tag == 'dict':
                    result = {}
                    for key, val in item:
                        key = unpack(key)
                        if key in result:
                            raise CheckpointError('Duplicate mapping key')
                        result[key] = unpack(val)
                    return result
                if tag in ('tuple', 'list'):
                    result = [unpack(v) for v in item]
                    return tuple(result) if tag == 'tuple' else result
                raise CheckpointError('Unknown metadata tag')

            result = unpack(tree)
            if set(saved.files) != used | {'metadata'}:
                raise CheckpointError('Unreferenced checkpoint arrays')
            return result
    except CheckpointError:
        raise
    except Exception as exc:
        raise CheckpointError(f'Malformed checkpoint: {exc}') from exc


def validate_state(state, model, optimizer, *, train_elements=None, validation_elements=None):
    """Validate the entire epoch boundary before changing model or optimizer."""
    expected = {'epoch', 'model', 'optimizer', 'rng', 'history', 'best_epoch',
                'best_mse', 'best_state', 'training_seconds', 'validation_seconds'}
    if not isinstance(state, dict) or set(state) != expected:
        raise CheckpointError('Invalid training state keys')
    epoch = state['epoch']
    if type(epoch) is not int or not 1 <= epoch <= protocol.EPOCHS:
        raise CheckpointError('Invalid completed epoch')
    for key in ('model', 'best_state'):
        if set(state[key]) != set(model.state_dict()):
            raise CheckpointError('Invalid model tensor keys')
        for name, template in model.state_dict().items():
            tensor = state[key][name]
            if (not isinstance(tensor, torch.Tensor) or tensor.shape != template.shape
                    or tensor.dtype != template.dtype or not bool(torch.isfinite(tensor).all())):
                raise CheckpointError(f'Invalid model tensor {name}')
    history = state['history']
    if not isinstance(history, list) or len(history) != epoch:
        raise CheckpointError('Invalid epoch history length')
    best, score = 0, float('inf')
    for i, row in enumerate(history, 1):
        keys = {'epoch', 'optimizer_step', 'train_elements', 'validation_elements',
                'train_MSE_original_units_before_update', 'train_MAE_original_units_before_update',
                'validation_MSE_original_units_after_update', 'validation_MAE_original_units_after_update',
                'selected_so_far'}
        if not isinstance(row, dict) or set(row) != keys:
            raise CheckpointError('Invalid history row keys')
        if (type(row.get('epoch')) is not int or type(row.get('optimizer_step')) is not int
                or row['epoch'] != i or row['optimizer_step'] != i):
            raise CheckpointError('Nonconsecutive history')
        for key in ('train_elements', 'validation_elements'):
            if type(row[key]) is not int or row[key] <= 0:
                raise CheckpointError('Invalid history element count')
        if ((train_elements is not None and row['train_elements'] != train_elements)
                or (validation_elements is not None and row['validation_elements'] != validation_elements)):
            raise CheckpointError('History computation element count mismatch')
        for key in keys - {'epoch', 'optimizer_step', 'train_elements', 'validation_elements', 'selected_so_far'}:
            if type(row[key]) not in (int, float) or not math.isfinite(row[key]) or row[key] < 0:
                raise CheckpointError('Invalid history score')
        if type(row['selected_so_far']) is not bool:
            raise CheckpointError('Invalid selection flag')
        value = row['validation_MSE_original_units_after_update']
        if not math.isfinite(value):
            raise CheckpointError('Nonfinite history')
        if value < score:
            best, score = i, value
        if row.get('selected_so_far') != (best == i):
            raise CheckpointError('Invalid selection history')
    if (type(state['best_epoch']) is not int or type(state['best_mse']) not in (float, int)
            or state['best_epoch'] != best or state['best_mse'] != score):
        raise CheckpointError('Inconsistent best selection')
    for key in ('training_seconds', 'validation_seconds'):
        if type(state[key]) not in (float, int) or not math.isfinite(state[key]) or state[key] < 0:
            raise CheckpointError('Invalid cumulative timing')
    saved = state['optimizer']
    baseline = optimizer.state_dict()
    if set(saved) != {'state', 'param_groups'} or saved['param_groups'] != baseline['param_groups']:
        raise CheckpointError('Optimizer configuration mismatch')
    params = list(model.parameters())
    ids = baseline['param_groups'][0]['params']
    if set(saved['state']) != set(ids):
        raise CheckpointError('Missing Adam state')
    for index, parameter in zip(ids, params):
        slots = saved['state'][index]
        if set(slots) != {'step', 'exp_avg', 'exp_avg_sq'}:
            raise CheckpointError('Invalid Adam slots')
        for key in ('exp_avg', 'exp_avg_sq'):
            val = slots[key]
            if not isinstance(val, torch.Tensor) or val.shape != parameter.shape or val.dtype != parameter.dtype or not bool(torch.isfinite(val).all()):
                raise CheckpointError('Invalid Adam moment')
        step = slots['step']
        if not isinstance(step, torch.Tensor) or step.ndim != 0 or step.dtype != torch.float32 or float(step) != epoch:
            raise CheckpointError('Invalid Adam step')
        if bool((slots['exp_avg_sq'] < 0).any()):
            raise CheckpointError('Negative Adam second moment')
    # Validate RNG using isolated generators so rejection cannot mutate globals.
    rng = state['rng']
    if set(rng) != {'python', 'numpy', 'torch'}:
        raise CheckpointError('Invalid RNG keys')
    try:
        random.Random().setstate(rng['python'])
        np.random.RandomState().set_state(rng['numpy'])
        torch.Generator().set_state(rng['torch'])
    except Exception as exc:
        raise CheckpointError('Invalid RNG state') from exc


def atomic_bytes(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = artifacts.RunDirectory(path.parent, 'checkpoint-writer', 'checkpoint')
    writer.path = path.parent
    writer.events_path = path.parent / 'checkpoint-events.jsonl'
    writer.write_bytes(path.name, raw)


def publish(directory, state, identity, lineage):
    directory = Path(directory)
    previous = json.loads((directory / 'latest.json').read_text()) if (directory / 'latest.json').exists() else None
    payload = {'schema': SCHEMA, 'identity': identity, 'lineage': lineage, 'state': state}
    raw = encode(payload)
    name = f'epoch-{state["epoch"]:03d}-{uuid.uuid4().hex}.npz'
    manifest = {'schema': SCHEMA, 'file': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                'size': len(raw), 'epoch': state['epoch'],
                'previous': previous['file'] if previous else None}
    atomic_bytes(directory / name, raw)
    atomic_bytes(directory / 'latest.json', json.dumps(manifest, sort_keys=True).encode())
    # Cleanup happens only after the new pointer commits.
    keep = {name, manifest['previous']}
    for old in directory.glob('epoch-*.npz'):
        if old.name not in keep:
            old.unlink(missing_ok=True)
    return manifest


def load(path, identity=None):
    path = Path(path)
    if path.is_dir():
        path = path / 'latest.json'
    try:
        manifest = json.loads(path.read_text(encoding='utf-8'))
        if set(manifest) != {'schema', 'file', 'sha256', 'size', 'epoch', 'previous'} or manifest['schema'] != SCHEMA:
            raise CheckpointError('Unknown checkpoint manifest schema')
        if (type(manifest['schema']) is not int or type(manifest['epoch']) is not int
                or not 1 <= manifest['epoch'] <= protocol.EPOCHS
                or type(manifest['size']) is not int or manifest['size'] <= 0):
            raise CheckpointError('Invalid checkpoint manifest scalar types')
        name = manifest['file']
        if not isinstance(name, str) or Path(name).name != name or not name.startswith('epoch-') or not name.endswith('.npz'):
            raise CheckpointError('Invalid checkpoint filename')
        raw = (path.parent / name).read_bytes()
        if len(raw) != manifest['size'] or hashlib.sha256(raw).hexdigest() != manifest['sha256']:
            raise CheckpointError('Checkpoint integrity mismatch')
        payload = decode(raw)
        if (set(payload) != {'schema', 'identity', 'lineage', 'state'}
                or type(payload['schema']) is not int or payload['schema'] != SCHEMA):
            raise CheckpointError('Unknown checkpoint payload schema')
        if payload['state']['epoch'] != manifest['epoch']:
            raise CheckpointError('Epoch manifest mismatch')
        if identity is not None and payload['identity'] != identity:
            raise CheckpointError('Checkpoint computation/input/source/runtime identity mismatch')
        lineage = payload['lineage']
        if not isinstance(lineage, list) or not lineage or any(not isinstance(v, str) or not v for v in lineage) or len(set(lineage)) != len(lineage):
            raise CheckpointError('Invalid checkpoint lineage')
        return payload, manifest, raw
    except CheckpointError:
        raise
    except Exception as exc:
        raise CheckpointError(f'Cannot load committed checkpoint: {exc}') from exc
