"""Copy completed bounded diagnostics byte-for-byte and record pause evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path.cwd().resolve()
REPORT = ROOT / 'research/reports/p02-t002-20261020-01'
COST = ROOT / 'scratch/graph-value-skeleton/p02-t002-20261020-01/cost-runs'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = []
    observations = []
    for seed in range(3):
        run_id = f'p02-t002-20261020-01-cost-r2-shuffled{seed}-s0-diagnostic'
        source = COST / run_id
        status = json.loads((source / 'status.json').read_text(encoding='utf-8'))
        observed = json.loads((source / 'cost-observation.json').read_text(encoding='utf-8'))
        config = json.loads((source / 'config.json').read_text(encoding='utf-8'))
        if seed == 2:
            assert status['state'] == 'failed', status
            assert status['error']['exception_type'] == 'PermissionError', status
            assert 'WinError 5' in status['error']['message'], status
        else:
            assert status['state'] == 'interrupted', status
        assert observed['steps_observed'] == 3
        assert observed['validated_completed_epochs_at_least'] == 2
        assert len(observed['intervals_seconds']) == 2
        assert config['computational']['epochs'] == 200
        assert config['computational']['shuffle_seed'] == seed
        assert not (source / 'models/selected.npz').exists()
        script = REPORT / ('diagnose_training_cost_v1.py' if seed == 0
                           else 'diagnose_training_cost.py')
        assert sha(script) == observed['script_sha256']
        destination = REPORT / 'cost-evidence' / f'r2-shuffle{seed}'
        assert not destination.exists(), 'Never overwrite saved evidence'
        paths = [p for p in source.iterdir() if p.is_file()
                 and p.suffix in ('.json', '.jsonl', '.txt', '.patch', '.md', '.tmp')]
        paths += [p for p in (source / 'code-untracked').rglob('*') if p.is_file()]
        for path in sorted(paths):
            copied = destination / path.relative_to(source)
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, copied)
            digest = sha(path)
            assert sha(copied) == digest
            manifest.append({'source': path.relative_to(ROOT).as_posix(),
                             'saved': copied.relative_to(REPORT).as_posix(),
                             'bytes': copied.stat().st_size, 'sha256': digest})
        observations.append({'shuffle_seed': seed, 'run_id': run_id,
            'actual_run_state': status['state'],
            'intervals_seconds': observed['intervals_seconds'],
            'fastest_interval_seconds': min(observed['intervals_seconds']),
            'peak_working_set_bytes': observed['process_peak_memory']['bytes']})
    deadline = datetime.fromisoformat('2026-10-20T10:23:51+00:00')
    now = datetime.now(timezone.utc)
    projection = sum(item['fastest_interval_seconds'] * 200 * 6 for item in observations)
    remaining = max(0., (deadline - now).total_seconds())
    assert projection / 2 > remaining
    decision = {'task': 'P02-T002', 'batch': 'p02-t002-20261020-01',
        'recorded_at': now.isoformat(), 'deadline_utc': deadline.isoformat(),
        'decision': 'paused_before_formal_scheduling', 'formal_completed_fits': 0,
        'observations': observations, 'forecast_scope': '18 r2 shuffled fits only',
        'excluded_scope': '72 other fits, startup, final prediction, saving and acceptance checks',
        'schedule': 'current verified serial route; one CPU thread per training process',
        'projected_serial_seconds': projection,
        'projected_seconds_at_twice_measured_speed': projection / 2,
        'seconds_until_deadline': remaining,
        'reason': 'Even the twice-speed serial extrapolation for 18 fits misses the deadline.',
        'limitation': 'Two intervals per shuffle seed, model seed 0 only. Assumes stable epoch cost; not a runtime lower bound or completed fit. Parallel throughput unmeasured.',
        'diagnostic_save_failure': 'Seed 2 obtained and saved three steps and two intervals, then WinError 5 replacing its final stop marker. Runner preserved failed status; temporary file retained. This diagnostic writer uses os.replace directly, outside the verified shared atomic writer.',
        'scientific_configuration_changed': False,
        'no_automatic_resume': True}
    for filename, value in [('cost-evidence-manifest.json', manifest),
                            ('cost-decision.json', decision)]:
        path = REPORT / filename
        with path.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
    print(json.dumps(decision, ensure_ascii=True, indent=2))
    print(f'Preserved {len(manifest)} files; original arrays remain in scratch.')


if __name__ == '__main__':
    main()
