"""Dataset routing and success gates; no formal training in these tests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import torch

spec = importlib.util.spec_from_file_location('remaining', Path(__file__).with_name('t002_remaining_batch.py'))
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class RemainingTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='t002-remaining-'))
        from benchmark.nograph_baseline.artifacts import RunDirectory
        batch.core.WRITER = RunDirectory
        for module in (batch, batch.core):
            patch = mock.patch.object(module, 'ROOT', self.root)
            patch.start()
            self.addCleanup(patch.stop)

    def test_two_full_disjoint_matrices(self):
        ids = set()
        for dataset in ('region', 'r0'):
            batch.configure(dataset)
            axes = batch.schedule('new')
            self.assertEqual(len(axes), 30)
            self.assertEqual({a['dataset'] for a in axes}, {dataset})
            self.assertEqual({a['model_seed'] for a in axes}, {0, 1, 2})
            self.assertEqual(sum(a['method'] == 'shuffled' for a in axes), 18)
            self.assertTrue(all(f'-{dataset}-' in a['run_id'] for a in axes))
            ids.update(a['run_id'] for a in axes)
        self.assertEqual(len(ids), 60)

    def test_public_cli_dataset_and_prepared_routing(self):
        for dataset in ('region', 'r0'):
            batch.configure(dataset)
            controller = batch.Controller(self.root/'saved', self.root/'scratch', 'new')
            for axis in batch.schedule('new')[:10]:
                axis = {**axis, 'action': 'fresh'}
                directory = self.root/'research/runs'/axis['run_id']
                def invoke(args, rid, training):
                    self.assertTrue(training)
                    self.assertEqual(args[args.index('--data-name')+1], dataset)
                    if axis['method'] == 'shuffled':
                        self.assertEqual(Path(args[-1]).name, f'{dataset}-shuffle{axis["shuffle_seed"]}-a')
                    else:
                        self.assertNotIn('--shuffle-artifact', args)
                    batch.core.write(directory/'status.json', {'state':'success'})
                    batch.core.write(directory/'measurements.json', {'input':{'epochs':200}})
                    batch.core.write(directory/'training-history.json', {'rows':[{}]*200})
                    batch.core.write(directory/'training-progress.json', {'estimate_samples':5,'last_epoch_seconds':1.5})
                    return {'elapsed_seconds':300.}
                with mock.patch.object(controller, 'invoke', side_effect=invoke):
                    self.assertEqual(controller.fit(axis, directory)['full_fit_seconds_estimate'], 300.)

    def test_finish_requires_exact_checks_and_routes_summaries(self):
        for dataset in ('region','r0'):
            batch.configure(dataset)
            saved=self.root/dataset
            controller=batch.Controller(saved,self.root/'scratch','new')
            axes=batch.schedule('new')
            controller.completed=[a['run_id'] for a in axes]
            controller.effective={a['run_id']:a['run_id'] for a in axes}
            for i in range(45):
                batch.core.write(saved/'checks'/f'base{i}.json',{'status':'ok'})
            def check(args,name):
                self.assertEqual(args[0],'summarize-shuffled')
                self.assertTrue(all(f'-{dataset}-shuffled' in str(p) for p in args[2:]))
                batch.core.write(saved/'checks'/f'{name}.json',{'status':'ok'})
            with mock.patch.object(controller,'check',side_effect=check), mock.patch.object(batch,'verify_frozen'):
                controller.finish()
            self.assertEqual(batch.core.read(saved/'completion.json')['successful_checks'],51)
            batch.core.write(saved/'checks'/'extra.json',{'status':'ok'})
            with mock.patch.object(controller,'check'), mock.patch.object(batch,'verify_frozen'):
                with self.assertRaises(AssertionError):
                    controller.finish()

    def test_missing_group_cannot_publish(self):
        batch.configure('r0')
        controller=batch.Controller(self.root/'saved',self.root/'scratch','new',True)
        with mock.patch.object(batch.subprocess,'run') as run, mock.patch.object(batch,'__file__',str(self.root/'adapter.py')):
            with self.assertRaises(FileNotFoundError):
                controller.publish()
            run.assert_not_called()

    def test_changed_adapter_rejected(self):
        batch.configure('region')
        batch.core.write(self.root/'saved/preflight.json',{'dataset_name':'region','adapter_sha256':'wrong'})
        with mock.patch.object(batch,'ORIGINAL_VERIFY'):
            with self.assertRaisesRegex(AssertionError,'adapter changed'):
                batch.verify_frozen(self.root/'saved')


if __name__=='__main__':
    unittest.main()
