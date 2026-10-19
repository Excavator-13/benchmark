"""Preparation never fits a model; corrupt/reused controls fail closed."""
from dataclasses import replace
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
import numpy as np
from benchmark.graph_value_skeleton import cli, prepared, protocol, checks, shuffle, training, runner
from benchmark.graph_value_skeleton.tests import fixtures


class PreparedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        training.configure_determinism(0)
        cls.root = Path(tempfile.mkdtemp(prefix='gvs-prepared-'))
        cls.fixture = fixtures.build_fixture(cls.root, 'r0')
        cls.config = fixtures.make_config(cls.root, cls.fixture, method='shuffled',
                                         shuffle_seed=0, run_id='prepared')
        with mock.patch('benchmark.graph_value_skeleton.model.build_model', side_effect=AssertionError('model called')):
            prepared.prepare(cls.config)
        cls.directory = cls.config.run_dir

    def test_prepare_and_saved_only_check(self):
        self.assertFalse((self.directory/'models').exists())
        before={p.name: prepared.sha(p) for p in self.directory.iterdir() if p.is_file()}
        with mock.patch.object(prepared.data, 'load_dataset', side_effect=AssertionError('source read')):
            result=prepared.check(self.directory,self.root/'check.json',protocol.REPO_ROOT,['test'])
        self.assertEqual(result['status'],'ok',result)
        self.assertEqual(before,{p.name:prepared.sha(p) for p in self.directory.iterdir() if p.is_file()})
        with self.assertRaises(Exception): prepared.prepare(self.config)
        with self.assertRaises(Exception):
            prepared.check(self.directory,self.directory/'bad-report.json',protocol.REPO_ROOT,['test'])
        with self.assertRaises(ValueError): prepared.prepare(replace(self.config,purpose='formal'))

    def test_prepare_cli_and_unsafe_destination(self):
        argv=['prepare-shuffle','--data-name','r0','--shuffle-seed','0','--run-id','cli-graph',
              '--output-root',str(self.root/'cli'), '--demand-path',str(self.fixture['demand_path']),
              '--graph-path',str(self.fixture['graph_path'])]
        with mock.patch('benchmark.graph_value_skeleton.model.build_model',side_effect=AssertionError('model called')):
            self.assertEqual(cli.main(argv),0)
        self.assertNotEqual(cli.main(argv),0)
        unsafe=list(argv); unsafe[unsafe.index('--output-root')+1]=str(protocol.REPO_ROOT/'research')
        self.assertNotEqual(cli.main(unsafe),0)

    def test_corruption_with_recomputed_checksums(self):
        mutations={
            'count':('shuffle-audit.json',lambda a:a['contexts'][0].update(accepted=0)),
            'hash':('shuffle-audit.json',lambda a:a.update(result_edges_sha256='bad')),
            'version':('shuffle-audit.json',lambda a:a.update(algorithm_version='dds-unknown')),
            'seed':('provenance.json',lambda a:a.update(shuffle_seed=2)),
            'state':('status.json',lambda a:a.update(state='running')),
        }
        for label,(filename,mutate) in mutations.items():
            directory=self.root/label
            shutil.copytree(self.directory,directory)
            value=prepared.read_json(directory/filename); mutate(value)
            (directory/filename).write_text(json.dumps(value),encoding='utf-8')
            manifest=prepared.read_json(directory/'checksums.json')
            manifest['files'][filename]=prepared.sha(directory/filename)
            (directory/'checksums.json').write_text(json.dumps(manifest),encoding='utf-8')
            with self.subTest(label=label), self.assertRaises(ValueError): prepared.load(directory)
        directory=self.root/'numeric'; shutil.copytree(self.directory,directory)
        np.save(directory/'edges.npy',np.zeros((1,2),dtype=np.int64))
        with self.assertRaises(ValueError): prepared.load(directory)
        (directory/'nodes.npy').unlink()
        with self.assertRaises((ValueError,OSError)): prepared.load(directory)

    def test_mismatch_fails_before_training_without_fallback(self):
        with mock.patch.object(training,'train',side_effect=AssertionError('training called')), \
             mock.patch.object(shuffle,'shuffle_graph',side_effect=AssertionError('regenerated')):
            for seed in (1,2):
                config=replace(self.config,shuffle_seed=seed,run_id=f'mismatch-{seed}',
                               shuffle_artifact=str(self.directory))
                with self.assertRaises(ValueError): runner.execute_run(config)
        graph,_=prepared.load(self.directory)
        dataset,source=fixtures.load_fixture(self.fixture)
        for kwargs in ({'keys':dataset.key_array[::-1]}, {'source_edges':source.edges[::-1]},
                       {'data_name':'region'}, {'shuffle_seed':1}):
            with self.assertRaises(ValueError): prepared.load(self.directory,**kwargs)
        for method in ('self','graph'):
            with self.assertRaises(ValueError): replace(self.config,method=method,shuffle_seed=None,
                                                       shuffle_artifact=str(self.directory))
        with mock.patch.object(prepared,'generator_identity',return_value={'bad':'identity'}):
            with self.assertRaises(ValueError): prepared.load(self.directory,require_current_generator=True)

    def test_cached_and_fresh_fit_independently_and_recompute_without_artifact(self):
        fresh=replace(self.config,run_id='fresh-fit')
        reused=replace(self.config,run_id='reused-fit',shuffle_artifact=str(self.directory))
        a=runner.execute_run(fresh); b=runner.execute_run(reused)
        comparison=checks.command_compare(run_a=Path(a['run_dir']),run_b=Path(b['run_dir']),
                repo_root=protocol.REPO_ROOT,command=['test'],report_path=self.root/'repeat.json')
        self.assertEqual(comparison['status'],'ok',comparison)
        for config in (fresh,reused):
            history=prepared.read_json(config.run_dir/'training-history.json')
            self.assertEqual(history['epochs'],200)
        hidden=self.root/'hidden-prepared'
        self.directory.rename(hidden)
        try:
            result=checks.command_recompute(run_dir=reused.run_dir,repo_root=protocol.REPO_ROOT,
                    command=['test'],report_path=self.root/'recompute.json')
            self.assertEqual(result['status'],'ok',result)
        finally: hidden.rename(self.directory)

    def test_failure_and_interruption_retain_evidence(self):
        for name,error in [('failed',shuffle.ShuffleError('budget',{'attempts':1})),
                            ('interrupted',KeyboardInterrupt())]:
            config=replace(self.config,run_id=name)
            with mock.patch.object(shuffle,'shuffle_graph',side_effect=error):
                with self.assertRaises(BaseException): prepared.prepare(config)
            self.assertEqual(prepared.read_json(config.run_dir/'status.json')['state'],name)
            with self.assertRaises(OSError): prepared.load(config.run_dir)

    def test_legacy_audit_contract_unchanged_and_unknown_rejected(self):
        # Generate with genuine scalar v1 budget/stream, then check under v2 defaults.
        dataset,source=fixtures.load_fixture(self.fixture)
        original=shuffle._swap_edges
        def scalar_call(*args,**kwargs):
            return original(*args,**kwargs,proposal_batch_size=1)
        with mock.patch.object(protocol,'SHUFFLE_VERSION','dds-v1'), \
             mock.patch.object(shuffle,'_swap_edges',side_effect=scalar_call):
            result=shuffle.shuffle_graph('r0',dataset.key_array,source.edges,0,
                                         accept_factor=10,attempt_factor=100)
        audit=result.audit; audit.pop('proposal_batch_size')
        before=copy.deepcopy(audit); problems=[]
        checks.validate_shuffle_audit(dataset.key_array,source.edges,result.edges,audit,0,problems)
        self.assertEqual(problems,[]); self.assertEqual(audit,before)
        for version,limit in [('dds-unknown',100),('dds-v1',500)]:
            audit=copy.deepcopy(before);audit.update(algorithm_version=version,attempt_limit_factor=limit)
            problems=[]; checks.validate_shuffle_audit(dataset.key_array,source.edges,result.edges,audit,0,problems)
            self.assertTrue(problems)

    def test_legacy_saved_run_recomputes_under_current_defaults(self):
        original = shuffle._swap_edges
        original_graph = shuffle.shuffle_graph
        def scalar_call(*args, **kwargs):
            return original(*args, **kwargs, proposal_batch_size=1)
        def legacy_graph(*args, **kwargs):
            return original_graph(*args, **kwargs, accept_factor=10, attempt_factor=100)
        config = replace(self.config, run_id='legacy-saved-fit')
        with mock.patch.object(protocol, 'SHUFFLE_VERSION', 'dds-v1'), \
             mock.patch.object(protocol, 'SHUFFLE_ATTEMPT_LIMIT_FACTOR', 100), \
             mock.patch.object(protocol, 'SHUFFLE_PROPOSAL_BATCH', 1), \
             mock.patch.object(shuffle, 'shuffle_graph', side_effect=legacy_graph), \
             mock.patch.object(shuffle, '_swap_edges', side_effect=scalar_call):
            runner.execute_run(config)
        before = {p.relative_to(config.run_dir).as_posix(): prepared.sha(p)
                  for p in config.run_dir.rglob('*') if p.is_file()}
        with mock.patch.object(training, 'train', side_effect=AssertionError('refit')):
            result = checks.command_recompute(
                run_dir=config.run_dir, repo_root=protocol.REPO_ROOT,
                command=['test', 'legacy-recompute'], report_path=self.root/'legacy-recompute.json')
        self.assertEqual(result['status'], 'ok', result)
        self.assertEqual(before, {p.relative_to(config.run_dir).as_posix(): prepared.sha(p)
                                 for p in config.run_dir.rglob('*') if p.is_file()})
