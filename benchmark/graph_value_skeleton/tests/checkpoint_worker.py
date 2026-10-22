"""Fresh-process fixture runner; crash injection is confined to test code."""
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'
import argparse
from dataclasses import replace
from pathlib import Path
import torch
from benchmark.graph_value_skeleton import checkpoints, runner
from benchmark.graph_value_skeleton.tests import fixtures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('method')
    parser.add_argument('run_id')
    parser.add_argument('--cut', type=int)
    parser.add_argument('--resume')
    parser.add_argument('--public', action='store_true')
    args = parser.parse_args()
    fixture = fixtures.build_fixture(args.root / 'fixture', 'r0')
    config = fixtures.make_config(args.root, fixture, method=args.method,
        shuffle_seed=0 if args.method == 'shuffled' else None, run_id=args.run_id)
    config = replace(config, resume_from=args.resume)
    original = checkpoints.publish

    def publish(*a, **kw):
        result = original(*a, **kw)
        if result['epoch'] == args.cut:
            os._exit(73)
        return result

    checkpoints.publish = publish
    if args.public:
        from benchmark.graph_value_skeleton import cli
        arguments = ['run', '--data-name', 'r0', '--method', args.method,
            '--model-seed', '0', '--run-id', args.run_id, '--output-root', str(args.root / 'runs'),
            '--demand-path', str(fixture['demand_path']), '--graph-path', str(fixture['graph_path'])]
        if args.method == 'shuffled':
            arguments += ['--shuffle-seed', '0']
        if args.resume:
            arguments += ['--resume-from', args.resume]
        raise SystemExit(cli.main(arguments))
    runner.execute_run(config)


if __name__ == '__main__':
    main()
