"""Development graph-only matrix with finite watchdogs; never schedules models."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from . import artifacts, protocol
from .config import resolve_output_root
from . import prepared


def stop_tree(process):
    """Stop the owned subprocess tree, including the Windows venv launcher."""
    if process.poll() is not None:
        return
    if os.name == 'nt':
        result = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode and process.poll() is None:
            raise RuntimeError('could not terminate owned graph worker tree')
    else:
        process.terminate()
    process.wait(timeout=15)


def monitor(process, directory, *, max_seconds=600, idle_seconds=60,
            clock=time.monotonic, sleeper=time.sleep):
    started=last_progress=clock()
    previous=None
    while process.poll() is None:
        signatures=[]
        for name in ('progress.json','status.json','source.json','environment.json'):
            path=directory/name
            if path.exists():
                stat=path.stat(); signatures.append((name,stat.st_mtime_ns,stat.st_size))
        if signatures and signatures != previous:
            previous=signatures; last_progress=clock()
        current=clock()
        reason=('per-graph elapsed limit' if current-started >= max_seconds else
                'no observable progress' if current-last_progress >= idle_seconds else None)
        if reason:
            timeout = TimeoutError(f'{reason}; elapsed={current-started:.1f}s')
            try:
                stop_tree(process)
            except Exception as cleanup_error:
                timeout.add_note(f'worker termination failed: {cleanup_error}')
                raise timeout from cleanup_error
            raise timeout
        sleeper(0.25)
    if process.returncode:
        raise RuntimeError(f'graph worker exited {process.returncode}')
    return clock()-started


def run_matrix(run_id, output_root=None, probe_only=False):
    root=resolve_output_root(protocol.REPO_ROOT,'development',output_root)
    run=artifacts.run_directory(root,run_id,'shuffle-readiness').reserve()
    run.write_json('command.json',{'argv':[sys.executable,*sys.argv], 'cwd':os.getcwd()})
    members=[]
    # The former failure is always reached first, never hidden behind an r0 result.
    conditions=[('r2',0)]+[(data,seed) for data in ('r0','region','r2')
                          for seed in range(3) if (data,seed)!=('r2',0)]
    if probe_only: conditions=conditions[:1]
    manifest={'purpose':'development graph-only','state':'running','members':members,
              'max_seconds':600,'idle_seconds':60,'generator':prepared.generator_identity()}
    child=None
    try:
        for data_name,seed in conditions:
            hashes=[]
            for repeat in ('a','b'):
                name=f'{data_name}-shuffle{seed}-{repeat}'
                directory=run.path/'graphs'/name
                command=[sys.executable,'-B','-m','benchmark.graph_value_skeleton','prepare-shuffle',
                    '--data-name',data_name,'--shuffle-seed',str(seed),'--run-id',name,
                    '--output-root',str(directory.parent)]
                env=dict(os.environ, PYTHONUTF8='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                         MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1')
                print(f'START {name}',flush=True)
                log_path=run.path/(name+'.log')
                with log_path.open('x',encoding='utf-8') as log:
                    child=subprocess.Popen(command,cwd=protocol.REPO_ROOT,env=env,
                        stdout=log,stderr=subprocess.STDOUT)
                    elapsed=monitor(child,directory)
                report_path=run.path/'checks'/(name+'.json')
                report=prepared.check(directory,report_path,protocol.REPO_ROOT,['readiness','check-shuffle',name])
                if report['status']!='ok': raise ValueError(f'artifact check failed: {report}')
                result,_=prepared.load(directory,require_current_generator=True)
                hashes.append(result.edges_sha256)
                members.append({'dataset':data_name,'shuffle_seed':seed,'repeat':repeat,
                    'command':command,'artifact_dir':str(directory),'report':str(report_path),
                    'report_sha256':prepared.sha(report_path),'result_sha256':result.edges_sha256,
                    'checksums_sha256':prepared.sha(directory/'checksums.json'),
                    'elapsed_seconds':elapsed,'measurements':prepared.read_json(directory/'measurements.json')})
                run.write_json('readiness.json',manifest)
                print(f'DONE {name} {elapsed:.1f}s {result.edges_sha256}',flush=True)
            if hashes[0]!=hashes[1]: raise ValueError(f'regeneration mismatch: {data_name}/{seed}')
        manifest.update(state='probe_success' if probe_only else 'success',
                        matching_regenerations=len(conditions))
        run.write_json('readiness.json',manifest)
        run.set_status(manifest['state'])
        return manifest
    except BaseException as exc:
        manifest.update(state='paused',reason=f'{type(exc).__name__}: {exc}')
        if child is not None:
            try:
                stop_tree(child)
            except Exception as cleanup_error:
                manifest['cleanup_error'] = f'{type(cleanup_error).__name__}: {cleanup_error}'
                manifest['worker_pid'] = child.pid
                manifest['worker_may_be_running'] = True
        run.write_json('readiness.json',manifest)
        run.set_status('paused',reason=manifest['reason'],
                       cleanup_error=manifest.get('cleanup_error'))
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--output-root',type=Path)
    parser.add_argument('--probe-only',action='store_true')
    args=parser.parse_args()
    run_matrix(args.run_id,args.output_root,args.probe_only)


if __name__=='__main__': main()
