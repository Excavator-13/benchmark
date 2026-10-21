"""Regression reproductions for independent findings V-001 through V-003."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import torch
from benchmark.graph_value_skeleton import checkpoints as cp, checks
from benchmark.graph_value_skeleton.tests.test_checkpoints import CodecTest
from benchmark.graph_value_skeleton.tests.test_batch_recovery import batch
from unittest import mock


class StrictScalarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        CodecTest.setUpClass()

    def test_boolean_and_float_counters_rejected(self):
        for key, value in (('best_epoch', True), ('best_epoch', 1.), ('best_mse', True),
                           ('training_seconds', True), ('validation_seconds', True)):
            with self.subTest(key=key, value=value):
                state = copy.deepcopy(CodecTest.state)
                state[key] = value
                with self.assertRaises(cp.CheckpointError):
                    cp.validate_state(state, CodecTest.model, CodecTest().optimizer())
        for key in ('epoch', 'optimizer_step'):
            for value in (True, 1.):
                state = copy.deepcopy(CodecTest.state)
                state['history'][0][key] = value
                with self.assertRaises(cp.CheckpointError):
                    cp.validate_state(state, CodecTest.model, CodecTest().optimizer())


class ParentLineageTest(unittest.TestCase):
    def test_parent_payload_binds_prefix(self):
        root = Path(tempfile.mkdtemp(prefix='gvs-parent-lineage-'))
        raw = cp.encode({'schema': 1, 'lineage': ['root', 'parent'],
                         'state': {'epoch': 1}, 'identity': {}})
        cp.atomic_bytes(root / 'recovery/input.npz', raw)
        digest = hashlib.sha256(raw).hexdigest()
        manifest = {'schema': 1, 'sha256': digest, 'size': len(raw), 'epoch': 1}
        cp.atomic_bytes(root / 'recovery/input-manifest.json', json.dumps(manifest).encode())
        def ancestry(values):
            record = {'schema': 1, 'run_id': 'child', 'ancestry': values,
                      'parent_checkpoint': digest, 'completed_epoch_at_start': 1}
            cp.atomic_bytes(root / 'recovery.json', json.dumps(record).encode())
            loaded = SimpleNamespace(run_dir=root, provenance={'run_id': 'child', 'recovery': record})
            return checks._recovery_ancestry(loaded)
        self.assertEqual(ancestry(['root', 'parent', 'child']), {'root', 'parent', 'child'})
        for values in (['invented', 'child'], ['root', 'child'], ['parent', 'root', 'child']):
            with self.subTest(ancestry=values):
                with self.assertRaises(checks.CheckError):
                    ancestry(values)


class CompletedQualificationTest(unittest.TestCase):
    def test_current_identity_and_axis_are_required(self):
        # Use metadata shaped like a real loaded saved run; numeric consistency
        # remains a separate recompute gate in Controller.run.
        from benchmark.graph_value_skeleton.config import computational_identity
        axis = {'dataset': 'r2', 'method': 'self', 'model_seed': 0, 'shuffle_seed': None}
        spec = {**axis, 'data_name': 'r2', 'purpose': 'formal'}
        identity = computational_identity(data_name='r2', method='self', model_seed=0, shuffle_seed=None)
        loaded = SimpleNamespace(config={'spec': spec, 'computational': identity},
            source={'files': {'training.py': {'sha256': 'source'}}, 'protocol': {'sha256': 'protocol'}},
            environment={'packages': {'torch': 'pinned'}},
            provenance={'demand': {'source_sha256': 'data'}, 'masks': {'array_sha256': {'active': 'mask'}},
                'graph': {'source_sha256': 'graph'}, 'graph_used': {'message_edges_sha256': 'empty'},
                'environment': {'execution_settings': {'torch_seed': 0}}})
        expected = {'dataset': loaded.provenance['demand'], 'masks': {'active': 'mask'},
            'graph': {'source_sha256': 'graph'}, 'message_edges': {'self': 'empty'},
            'source': {'training.py': 'source'}, 'protocol_sha256': 'protocol',
            'runtime': checks._environment_identity(loaded.environment), 'execution': {'torch_seed': 0}}
        with mock.patch.object(checks, 'load_run', return_value=loaded):
            self.assertTrue(batch.qualify_completed(Path('unused'), axis, expected))
        mutations = [lambda x: x.config['spec'].update(data_name='r0'),
            lambda x: x.config['spec'].update(method='graph'),
            lambda x: x.config['spec'].update(model_seed=1),
            lambda x: x.config['spec'].update(shuffle_seed=0),
            lambda x: x.config['spec'].update(purpose='development'),
            lambda x: x.source['files']['training.py'].update(sha256='old-source'),
            lambda x: x.environment['packages'].update(torch='different-runtime'),
            lambda x: x.provenance['demand'].update(source_sha256='other-data'),
            lambda x: x.provenance['graph'].update(source_sha256='other-graph'),
            lambda x: x.provenance['masks']['array_sha256'].update(active='other-mask'),
            lambda x: x.provenance['graph_used'].update(message_edges_sha256='other-message')]
        for mutate in mutations:
            changed = copy.deepcopy(loaded)
            mutate(changed)
            with mock.patch.object(checks, 'load_run', return_value=changed):
                with self.assertRaisesRegex(ValueError, 'mismatch'):
                    batch.qualify_completed(Path('unused'), axis, expected)
