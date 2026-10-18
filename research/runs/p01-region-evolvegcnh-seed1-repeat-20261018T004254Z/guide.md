# T005：在保留的原 GPU 服务器上受控复跑 EvolveGCN-H

编写日期：2026-10-13。所属任务：P01-T005，任务状态以 [plan.md](plan.md) 为准。
科学协议：[protocol.md](protocol.md)，`P1-count-L6-H3-v3`；保存政策：`P01-records-v2`。

这份指导从原服务器仍保留这一条件出发，集中给出准备、检查、复跑、比较和交接步骤。下面的命令是待执行步骤，不是已完成实验的证据。本次整理指导没有连接服务器、核验远端进程或启动训练。

2026-10-13 后续：用户随后表示该服务器暂时无法开机，T005 暂缓，改做 [T007](t007-backtest-guide.md)；本页保留，等服务器恢复后按原步骤执行。

2026-10-18 后续：用户报告服务器可重新启动，本页恢复正常作为执行入口；页面步骤与断言未改（其本机材料与旧结果自 2026-10-13 未变），仍未连接服务器、未启动实验。旧条件是否可比由 §5 预检与 §5 末尾的条件核对结论决定，不因“能启动”先验成立。

## 1. 本轮回答什么，做到哪里停止

问题：旧 `region/count` 的 seed 1 再执行一次，是否与旧运行近似一致？这一步先区分执行重复性与不同初始化的差异。

| 条件 | 固定值 |
| --- | --- |
| 执行源码基准 | `950a1d8febbf992b8bda061d35f03107d0b18478` |
| 数据 / 模型 | `region/count` / `EvolveGCNH` |
| seed / epoch | `1` / `500` |
| 输入 / 预测长度 | `6` / `3` 月 |
| 训练 / 验证 / 测试窗口起点 | `0..18` / `21` / `24..27` |
| 输入尺度 | 原始 count，不增加标准化或 log1p |
| 优化器 / 学习率 | 原 API 的 Adam / `0.01` |
| 状态 | 每次训练、验证、测试遍历重新初始化，各遍历内部按时间传递 |
| 选模 | 验证 MSE 最低的 checkpoint；不按测试误差选择 |
| 原 GPU / 环境 | Tesla T4，`job-sdf`；实际是否保持一致由下面检查确认 |

旧结果供核对：seed 0 的 MAE/RMSE 为 `41.080686 / 238.957775`，seed 1 为 `96.180772 / 579.504594`。`region/count` 的验证选定 `NaiveRef=LastValue`，测试 MAE/RMSE 为 `35.309850 / 193.846853`。这些数值是已有结果，不能据此调整本次配置。

本轮先完成 seed 1 同条件复跑和关联比较报告。先不补 seed 2/3/4，不做归一化、学习率或状态预热干预。发布图构建时间未知，因此结果只解释为带此限制的固定评测，不能宣称严格无未来图信息或跨时间泛化。

## 2. 在本机把指导和核对材料传到服务器

本机与服务器是两套文件系统。以下小节在 Mac 的仓库根目录执行。先替换 `T005_HOST` 和 `T005_PORT`，不用把本机仓库整体覆盖到服务器。

```bash
cd /Users/watuji/da_chuang/repos/benchmark
export T005_HOST='ubuntu@YOUR_SERVER_IP'
export T005_PORT='22'
export T005_TRANSFER="$(mktemp -d /tmp/t005-materials.XXXXXX)"
cp research/phases/P01/t005-evolvegcnh-guide.md "$T005_TRANSFER/guide.md"
cp research/phases/P01/protocol.md "$T005_TRANSFER/protocol.md"
cp experiments_archive/1st_try_in_phase_fix_origin/logs/pip-freeze.txt "$T005_TRANSFER/old-pip-freeze.txt"
cp experiments_archive/1st_try_in_phase_fix_origin/logs/nvidia-smi.txt "$T005_TRANSFER/old-nvidia-smi.txt"
ssh -p "$T005_PORT" "$T005_HOST" 'mkdir -p ~/t005-materials'
scp -P "$T005_PORT" "$T005_TRANSFER/guide.md" "$T005_TRANSFER/protocol.md" "$T005_TRANSFER/old-pip-freeze.txt" "$T005_TRANSFER/old-nvidia-smi.txt" "$T005_HOST:~/t005-materials/"
```

服务器已有旧 seed 0/1 结果时直接使用它们。若服务器原结果已不在，在本机执行下面命令，把归档副本送到单独位置；不要用它覆盖任何新结果。

```bash
ssh -p "$T005_PORT" "$T005_HOST" 'mkdir -p ~/t005-materials/original'
scp -r -P "$T005_PORT" experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/results/count/region/EvolveGCNH/0 experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/results/count/region/EvolveGCNH/1 "$T005_HOST:~/t005-materials/original/"
```

## 3. 在服务器确认原仓库、环境和进程

从本机登录：

```bash
ssh -p "$T005_PORT" "$T005_HOST"
```

其后所有命令均在服务器执行，使用 Bash。建议在 tmux 内进行；断开 SSH 不会因此结束训练。

```bash
bash
tmux new -s p01-t005 bash
```

已有该 tmux 会话时用 `tmux attach -t p01-t005`，确认里面使用 Bash。tmux 内再执行：

```bash
conda activate job-sdf
export T005_REPO="$HOME/benchmark"
export T005_MATERIALS="$HOME/t005-materials"
export T005_ORIGINAL="$T005_REPO/benchmark/graph_method/results/count/region/EvolveGCNH"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
cd "$T005_REPO"
git rev-parse HEAD
git status --short
nvidia-smi
python --version
python -m pip --version
pgrep -af 'main.py|train_experiment|prepare_graph_data|t005' || true
```

若 `conda activate` 提示 shell 尚未初始化，先执行 `source "$(conda info --base)/etc/profile.d/conda.sh"` 再激活原环境；不要因此重建或升级环境。`T005_REPO` 改成原服务器的实际仓库路径。若使用上传的旧结果，改为：

```bash
export T005_ORIGINAL="$T005_MATERIALS/original"
```

先确认进程列表中没有另一项正在使用这个仓库/结果目录的训练。搜索命令自身可能被匹配，不能据此断言有训练。

预期 HEAD 为原提交。若服务器仓库已经切到其他提交，不在它里面切回或丢弃改动；检查工作区后，在单独 worktree 准备原提交：

```bash
git worktree add --detach "$HOME/benchmark-t005-origin" 950a1d8febbf992b8bda061d35f03107d0b18478
export T005_REPO="$HOME/benchmark-t005-origin"
cd "$T005_REPO"
```

`T005_ORIGINAL` 仍指向旧结果，不跟随新 worktree 自动改变。新 worktree 没有 ignored 的生成 JSON 是正常情况。

不要先升级依赖或重装环境。本轮优先沿用原环境，先用历史清单核对；环境名相同不等于依赖相同。原核心依赖是：

| 包 | 旧版本 |
| --- | --- |
| torch | `2.3.0+cu121` |
| torch_geometric | `2.4.0` |
| torch_geometric_temporal | `0.54.0` |
| torch_scatter | `2.1.2+pt23cu121` |
| torch_sparse | `0.6.18+pt23cu121` |
| numpy / pandas / pyarrow | `1.22.4` / `1.3.5` / `14.0.1` |

原驱动记录为 `535.216.01`，GPU 显存为 15,360 MiB。`nvidia-smi` 显示的 CUDA 12.2 是驱动能力，PyTorch wheel 使用 CUDA 12.1，两者不要求字面相同。Python 版本和完整环境以实际保存材料为准；旧安装指南的 Python 3.8 不能单独证明旧运行的精确补丁版本。

## 4. 创建唯一记录目录，只在缺失时准备 region 数据

继续在同一个 tmux Bash 内执行。本轮目录放在服务器原仓库之外，避免改动旧检出或旧结果。ID 带时间戳，后续下载到当前仓库的 `research/runs/`。

```bash
export T005_RUN_ID="p01-region-evolvegcnh-seed1-repeat-$(date -u +%Y%m%dT%H%M%SZ)"
export T005_RUN="$HOME/t005-runs/$T005_RUN_ID"
python - <<'PY'
import os
import shutil
from pathlib import Path

run = Path(os.environ['T005_RUN'])
materials = Path(os.environ['T005_MATERIALS'])
run.mkdir(parents=True, exist_ok=False)
for name in ('guide.md', 'protocol.md', 'old-pip-freeze.txt', 'old-nvidia-smi.txt'):
    shutil.copy2(materials / name, run / name)
print('run:', run)
PY
```

目录已存在就停止，换新 ID，不复用失败目录。文档快照保存本次准确命令；若修改下面的 Python 代码，应另存实际脚本到这个 run 中，并记录实际命令。

仅当 JSON 不存在时生成，不覆盖服务器原生成数据：

```bash
set -o pipefail
if [ ! -f benchmark/graph_method/data/count/region.json ]; then
  python benchmark/graph_method/prepare_graph_data.py --mode count --data_name region 2>&1 | tee "$T005_RUN/prepare.log"
  T005_PREPARE_EXIT=${PIPESTATUS[0]}
  if [ "$T005_PREPARE_EXIT" -ne 0 ]; then
    printf 'Preparation failed: %s\n' "$T005_PREPARE_EXIT"
  fi
fi
```

生成失败就停在这里。不要继续训练或批量生成其他粒度。

## 5. 训练前检查：源码、环境、节点、窗口和旧标签

下面检查不训练模型。它会保存当前环境、输入 SHA256、节点/月份/分组、五项朴素预测和旧结果身份，并拒绝明显不匹配的核心条件。一次执行；失败后保留报告，修正原因并用新的 run ID 重走准备，不覆盖失败记录。

```bash
if [ -e "$T005_RUN/preflight.log" ]; then
  printf 'Preflight was already attempted; preserve this run and use a new ID.\n'
else
python - <<'PY' 2>&1 | tee "$T005_RUN/preflight.log"
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

repo = Path(os.environ['T005_REPO']).resolve()
run = Path(os.environ['T005_RUN']).resolve()
old = Path(os.environ['T005_ORIGINAL']).resolve()
base = '950a1d8febbf992b8bda061d35f03107d0b18478'
sys.path.insert(0, str(repo / 'benchmark/graph_method'))
import main

def command(args):
    return subprocess.check_output(args, cwd=str(repo), text=True).strip()

def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()

def write(name, value):
    (run / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

freeze = command([sys.executable, '-m', 'pip', 'freeze'])
(run / 'pip-freeze.txt').write_text(freeze + '\n')
(run / 'git-status.txt').write_text(command(['git', 'status', '--short']) + '\n')
(run / 'git-commit.txt').write_text(command(['git', 'rev-parse', 'HEAD']) + '\n')
(run / 'nvidia-smi.txt').write_text(command(['nvidia-smi']) + '\n')
assert command(['git', 'rev-parse', 'HEAD']) == base, 'Wrong source commit'
assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'

sources = [
    'benchmark/graph_method/main.py', 'benchmark/graph_method/dataset.py',
    'benchmark/graph_method/prepare_graph_data.py',
    'benchmark/graph_method/models/__init__.py',
    'benchmark/graph_method/models/evolvegcnh.py',
    'dataset/demand/region.parquet', 'dataset/graph/region.parquet',
]
inputs = {}
for relative in sources:
    path = repo / relative
    assert command(['git', 'hash-object', str(path)]) == command(
        ['git', 'rev-parse', base + ':' + relative]), 'Changed source/input: ' + relative
    inputs[relative] = {'sha256': digest(path), 'bytes': path.stat().st_size}
generated = repo / 'benchmark/graph_method/data/count/region.json'
inputs[str(generated)] = {'sha256': digest(generated), 'bytes': generated.stat().st_size}
for name in ('guide.md', 'protocol.md'):
    path = run / name
    inputs[str(path)] = {'sha256': digest(path), 'bytes': path.stat().st_size}
write('inputs.json', inputs)

expected = {
    'torch': '2.3.0+cu121', 'torch-geometric': '2.4.0',
    'torch-geometric-temporal': '0.54.0', 'torch-scatter': '2.1.2+pt23cu121',
    'torch-sparse': '0.6.18+pt23cu121', 'numpy': '1.22.4',
    'pandas': '1.3.5', 'pyarrow': '14.0.1',
}
actual = {name: metadata.version(name) for name in expected}
assert torch.cuda.is_available(), 'No CUDA device'
device = torch.device('cuda:0')
gpu_name = torch.cuda.get_device_name(device)
environment = {
    'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
    'packages': actual, 'gpu': gpu_name, 'torch_cuda': torch.version.cuda,
    'cublas_workspace_config': os.environ['CUBLAS_WORKSPACE_CONFIG'],
}
write('environment.json', environment)
assert actual == expected, 'Core dependency versions differ; inspect saved environment'
assert 'T4' in gpu_name, 'GPU differs from old Tesla T4'

payload = json.loads(generated.read_text())
keys = np.asarray(payload['node_keys'], dtype=np.int64)
months = ['%04d-%02d' % (year, month)
          for year in range(2021, 2024) for month in range(1, 13)]
frame = pd.read_parquet(repo / 'dataset/demand/region.parquet')
assert [str(c) for c in frame.columns if str(c)[:4].isdigit()] == months
frame = frame.sort_values(['region_id', 'skill_id']).reset_index(drop=True)
assert not frame.duplicated(['region_id', 'skill_id']).any()
assert np.array_equal(keys, frame[['region_id', 'skill_id']].to_numpy())
values = frame[months].to_numpy(dtype=np.float64)
assert values.shape == (16345, 36)
assert np.isfinite(values).all() and (values >= 0).all()
assert np.array_equal(np.asarray(payload['features'], dtype=np.float32).T, values.astype(np.float32))
from prepare_graph_data import build_graph_dataset
assert payload == build_graph_dataset(
    frame, pd.read_parquet(repo / 'dataset/graph/region.parquet'), 'region', 'count'), 'Generated graph differs from source data'
activity = (values[:, :27] > 0).mean(axis=1)
edges = np.asarray(payload['edges'], dtype=np.int64).reshape(-1, 2)
covered = np.zeros(len(keys), dtype=bool)
nonself = edges[edges[:, 0] != edges[:, 1]]
covered[np.unique(nonself)] = True
masks = {
    'inactive': activity == 0,
    'low': (activity > 0) & (activity <= 1 / 3),
    'medium': (activity > 1 / 3) & (activity <= 2 / 3),
    'high': activity > 2 / 3,
    'has_neighbor': covered, 'isolated': ~covered,
}
assert int(covered.sum()) == 2185, 'Unexpected neighbor coverage'
np.savez_compressed(run / 'identity-and-groups.npz', node_keys=keys,
                    months=np.asarray(months), activity=activity, **masks)

config = main.ExperimentConfig(data_name='region', mode='count', model_name='EvolveGCNH',
                               device='cuda:0', seed=1, window_size=6,
                               pred_length=3, num_epochs=500)
dataset = main.load_dataset(config)
train, validation, test = main.temporal_signal_split(dataset, config.train_ratio, config.eval_ratio)
assert [part.snapshot_count for part in (train, validation, test)] == [19, 1, 4]
starts = {'train': list(range(19)), 'validation': [21], 'test': [24, 25, 26, 27]}
for name, part in [('train', train), ('validation', validation), ('test', test)]:
    for start, snapshot in zip(starts[name], part):
        assert np.array_equal(snapshot.x.numpy(), values[:, start:start + 6].astype(np.float32))
        assert np.array_equal(snapshot.y.numpy(), values[:, start + 6:start + 9].astype(np.float32))

naive_scores = {}
for name in ('validation', 'test'):
    positions = starts[name]
    gold = np.stack([values[:, start + 6:start + 9] for start in positions])
    predictions = {
        'Zero': np.zeros_like(gold),
        'LastValue': np.stack([np.repeat(values[:, start + 5:start + 6], 3, axis=1) for start in positions]),
        'WindowMean6': np.stack([np.repeat(values[:, start:start + 6].mean(axis=1, keepdims=True), 3, axis=1) for start in positions]),
        'TrainMean27': np.broadcast_to(values[:, :27].mean(axis=1)[None, :, None], gold.shape).copy(),
        'SeasonalNaive12': np.stack([values[:, start - 6:start - 3] for start in positions]),
    }
    np.save(run / (name + '-gold.npy'), gold.astype(np.float32))
    np.savez_compressed(run / (name + '-naive.npz'), **predictions)
    naive_scores[name] = {method: {'MSE': float(np.mean((pred - gold) ** 2)),
                                  'MAE': float(np.mean(np.abs(pred - gold)))}
                          for method, pred in predictions.items()}
selected = min(naive_scores['validation'], key=lambda method: naive_scores['validation'][method]['MSE'])
assert selected == 'LastValue'
write('naive-selection.json', {'criterion': 'validation MSE', 'NaiveRef': selected,
                               'scores': naive_scores})

old_identity = {}
canonical = np.load(run / 'test-gold.npy')
for seed in (0, 1):
    folder = old / str(seed)
    checkpoint = torch.load(folder / 'checkpoint.pt', map_location='cpu', weights_only=True)
    assert checkpoint['seed'] == seed
    assert checkpoint['config']['model_name'] == 'EvolveGCNH'
    assert checkpoint['config']['window_size'] == 6 and checkpoint['config']['pred_length'] == 3
    pred = [torch.load(folder / ('pred_%d.pt' % i), map_location='cpu', weights_only=True) for i in range(4)]
    gold = [torch.load(folder / ('gold_%d.pt' % i), map_location='cpu', weights_only=True) for i in range(4)]
    assert all(torch.isfinite(p).all() for p in pred)
    assert all(np.array_equal(g.numpy(), canonical[i]) for i, g in enumerate(gold))
    recalculated = main.regression_metrics(pred, gold)
    recorded = json.loads((folder / 'metrics.json').read_text())
    assert all(abs(recalculated[key] - recorded[key]) <= 0.01 for key in ('MAE', 'RMSE'))
    old_identity[str(seed)] = {
        'path': str(folder), 'recorded_metrics': recorded, 'recalculated': recalculated,
        'files': {p.name: digest(p) for p in sorted(folder.iterdir()) if p.is_file()},
    }
write('original-results.json', old_identity)
write('preflight.json', {'status': 'passed', 'source_commit': base, 'nodes': len(keys),
                       'splits': starts, 'activity_counts': {k: int(v.sum()) for k, v in masks.items()},
                       'environment_review_required': True})
print(json.dumps(environment, indent=2))
print('Preflight passed. Review the complete environment before training.')
PY
T005_PREFLIGHT_EXIT=${PIPESTATUS[0]}
printf 'Preflight exit: %s\n' "$T005_PREFLIGHT_EXIT" | tee "$T005_RUN/preflight-exit.txt"
fi
```

退出码必须为 0，且 `preflight.json` 为 `passed`。然后查看完整依赖与驱动差异：

```bash
diff -u "$T005_RUN/old-pip-freeze.txt" "$T005_RUN/pip-freeze.txt" || true
diff -u "$T005_RUN/old-nvidia-smi.txt" "$T005_RUN/nvidia-smi.txt" || true
```

日期、利用率和进程列表不同是正常的。其他依赖、驱动或设备变化需解释后再运行；上面的核心检查通过不代表完整旧环境已被证明。

用编辑器建立 `$T005_RUN/condition-review.md`，写下实际观察及判断，不写无法确认的“完全一致”。至少写：原服务器仍保留（用户陈述）、实际 GPU/驱动、完整依赖差异、Python 版本可比性、是否同一物理 GPU 能确认、源码与数据检查、结论属于“可比旧条件”还是“跨条件”。同一云实例不保证云平台从未迁移物理 GPU。

例如可运行 `nano "$T005_RUN/condition-review.md"`，填入以下条目中的实际观察（不要原样保留占位内容）：

```markdown
# 条件核对

- 原服务器保留情况及本次核对时间：...
- HEAD 与源码/原始数据检查：...
- GPU 型号 / 驱动 / torch CUDA：...
- 同一物理 GPU 是否能确认：...（无法确认可如实记录）
- 完整 pip freeze 差异及 Python 版本限制：...
- 判断：可比旧条件 / 跨条件；理由与限制：...
```

若核心依赖/GPU检查失败，不删断言强行继续这份默认同条件脚本。先查明原因。若接受使用新条件，另建新 run，明确差异，并在该新条件下至少运行两次 seed 1；把两次新运行互比，与旧结果的比较另列。无需为换条件本身改变科学协议，改变尺度/训练/状态规则则是另一项单独命名的实验。

## 6. 开始 seed 1 的 500 epoch 复跑

只有第 5 节检查和环境判断完成后执行。输出目录固定在本 run 内，存在旧输出或已有训练状态就拒绝重复启动。脚本调用原 `train_experiment`；只在其 `run_split` 外层记录已计算的损失，不改变损失、优化器、状态或选模行为。训练结束后独立重建已选模型，补存验证预测，不重训、不用测试结果选模。

```bash
if [ -e "$T005_RUN/training.log" ]; then
  printf 'Training was already attempted; preserve this run and use a new ID.\n'
else
python -u - <<'PY' 2>&1 | tee "$T005_RUN/training.log"
import datetime
import hashlib
import json
import os
import resource
import sys
import time
import traceback
from pathlib import Path

import torch

repo = Path(os.environ['T005_REPO']).resolve()
run = Path(os.environ['T005_RUN']).resolve()
sys.path.insert(0, str(repo / 'benchmark/graph_method'))
import main

def write(name, value):
    (run / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

assert json.loads((run / 'preflight.json').read_text())['status'] == 'passed'
assert (run / 'condition-review.md').is_file(), 'Write the environment review first'
assert not (run / 'status.json').exists(), 'Already attempted; use a new run ID'
assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
inputs = json.loads((run / 'inputs.json').read_text())
for name, record in inputs.items():
    path = Path(name) if Path(name).is_absolute() else repo / name
    checksum = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            checksum.update(chunk)
    assert checksum.hexdigest() == record['sha256'], 'Input/source changed since preflight: ' + name

config = main.ExperimentConfig(data_name='region', mode='count', model_name='EvolveGCNH',
                               device='cuda:0', seed=1, window_size=6,
                               pred_length=3, num_epochs=500, results_dir=run / 'outputs')
output = main.result_dir(config)
assert not output.exists(), 'Refusing to overwrite ' + str(output)
parsed = dict(config.__dict__)
parsed['results_dir'] = str(config.results_dir)
parsed['data_dir'] = None
parsed['learning_rate'] = main.DEFAULT_LEARNING_RATE
parsed['optimizer'] = 'Adam'
parsed['input_scale'] = 'raw count'
write('config.json', parsed)
write('status.json', {'status': 'running', 'started_at': now()})
write('provenance.json', {
    'task_id': 'P01-T005', 'run_id': run.name, 'source_commit': json.loads((run / 'preflight.json').read_text())['source_commit'],
    'scientific_protocol': 'P1-count-L6-H3-v3', 'records_policy': 'P01-records-v2',
    'protocol_snapshot': 'protocol.md', 'executed_commands': 'guide.md sections 5-7',
    'inputs': 'inputs.json', 'environment': 'environment.json', 'condition_review': 'condition-review.md',
    'config': 'config.json', 'training_trace': 'training-trace.jsonl',
    'limitations': ['Published graph construction cutoff unknown; fixed-period evidence only'],
})
started = now()
clock_start = time.perf_counter()
trace = []
original_run_split = main.run_split

try:
    device = main.resolve_device(config.device)
    torch.cuda.init()
    torch.cuda.reset_peak_memory_stats(device)
    load_start = time.perf_counter()
    dataset = main.load_dataset(config)
    train, validation, test = main.temporal_signal_split(dataset, config.train_ratio, config.eval_ratio)
    load_seconds = time.perf_counter() - load_start

    def recorded_run_split(model, iterator, device, **kwargs):
        result = original_run_split(model, iterator, device, **kwargs)
        if iterator is train or iterator is validation:
            row = {'stage': 'train' if iterator is train else 'validation',
                   'epoch': len(trace) // 2 + 1, 'MSE': result.loss,
                   'optimizer_steps': result.optimizer_steps}
            trace.append(row)
            with (run / 'training-trace.jsonl').open('a') as handle:
                handle.write(json.dumps(row, allow_nan=False) + '\n')
        return result

    main.run_split = recorded_run_split
    torch.cuda.synchronize(device)
    train_start = time.perf_counter()
    metrics = main.train_experiment(config, train, validation, test, device=device)
    torch.cuda.synchronize(device)
    training_and_test_seconds = time.perf_counter() - train_start
    main.run_split = original_run_split

    validation_rows = [row for row in trace if row['stage'] == 'validation']
    assert len(validation_rows) == 500 and len(trace) == 1000
    selected = min(validation_rows, key=lambda row: row['MSE'])
    restored = main.load_checkpoint(output / 'checkpoint.pt', device)
    assert abs(restored.best_val_loss - selected['MSE']) <= 1e-8
    result = original_run_split(restored.model, validation, device, collect_predictions=True)
    for i, (pred, gold) in enumerate(zip(result.predictions, result.golds)):
        torch.save(pred, output / ('validation_pred_%d.pt' % i))
        torch.save(gold, output / ('validation_gold_%d.pt' % i))
    write('selection.json', {'criterion': 'validation MSE', 'tie_rule': 'first minimum',
                              'selected_epoch': selected['epoch'], 'best_validation_MSE': selected['MSE'],
                              'reloaded_validation_MSE': result.loss,
                              'reloaded_validation_metrics': main.regression_metrics(result.predictions, result.golds)})
    torch.cuda.synchronize(device)
    write('cost.json', {
        'load_seconds': load_seconds, 'training_and_test_seconds': training_and_test_seconds,
        'total_seconds_including_extra_validation': time.perf_counter() - clock_start,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'peak_cuda_allocated_bytes': torch.cuda.max_memory_allocated(device),
        'peak_cuda_reserved_bytes': torch.cuda.max_memory_reserved(device),
        'device': torch.cuda.get_device_name(device), 'RSS_unit_basis': 'Linux ru_maxrss in KiB',
    })
    write('status.json', {'status': 'succeeded', 'started_at': started, 'ended_at': now()})
    print(json.dumps(metrics, indent=2))
    print('Output:', output)
except BaseException as error:
    main.run_split = original_run_split
    write('status.json', {'status': 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
                          'started_at': started, 'ended_at': now(), 'error': repr(error)})
    traceback.print_exc()
    raise
PY
T005_TRAIN_EXIT=${PIPESTATUS[0]}
printf 'Training exit: %s\n' "$T005_TRAIN_EXIT" | tee "$T005_RUN/training-exit.txt"
fi
```

> 2026-10-18 实机修复：首次实机运行时 `torch.cuda.reset_peak_memory_stats(device)` 抛 `RuntimeError: Invalid device argument`。torch 2.3 的该函数没有 `is_initialized()` 保护，而调用点之前没有任何操作初始化该设备的缓存分配器。上面已在重置前补 `torch.cuda.init()`；最小诊断确认裸调用失败、`init()` 后与一次分配后均成功。该行只决定成本统计的起点，不改变损失、优化器、状态传递、选模或数据。首次失败 run `p01-region-evolvegcnh-seed1-repeat-20261018T003044Z` 保留（`status.json=failed`，无训练产物）。

退出码非 0 时保留已形成的日志、状态和 checkpoint，不把失败写成完成。被系统直接杀掉可能来不及更新 `status.json`，此时 `running` 仅表示最后一次写入状态；根据进程、退出码和日志记录实际中断。当前脚本没有恢复优化器中途续训能力，重试用新 run，不能把仅加载最佳 checkpoint 当成继续原 500 epoch。

成功应产生：`status.json=succeeded`、1000 条 train/validation 记录、选中 epoch、耗时和峰值内存、checkpoint、四个测试预测/标签及一个验证预测/标签。不要仅凭 tqdm 到 500 判断成功。

## 7. 从保存预测重算指标并比较旧 seed 1

这一步不重训、不重新推理模型。用 float64 统一重算旧/新预测，保存总体、逐窗口、horizon、活跃度、邻居、上下文、负预测比例，以及单列的非负裁剪诊断。主要比较保留原始预测，裁剪不会替换主结果。

```bash
if [ -e "$T005_RUN/comparison.log" ]; then
  printf 'Comparison was already attempted; preserve the report and log.\n'
else
python - <<'PY' 2>&1 | tee "$T005_RUN/comparison.log"
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import torch

run = Path(os.environ['T005_RUN']).resolve()
output = run / 'outputs/count/region/EvolveGCNH/1'
assert json.loads((run / 'status.json').read_text())['status'] == 'succeeded'
assert not (run / 'comparison.json').exists(), 'Comparison already exists; preserve the original report'
old_record = json.loads((run / 'original-results.json').read_text())['1']
old = Path(old_record['path'])
for name, expected in old_record['files'].items():
    assert hashlib.sha256((old / name).read_bytes()).hexdigest() == expected, 'Old result changed: ' + name
groups = np.load(run / 'identity-and-groups.npz')
keys = groups['node_keys']

def tensors(folder, stem, count):
    values = [torch.load(folder / (stem + '_%d.pt' % i), map_location='cpu', weights_only=True).numpy()
              for i in range(count)]
    result = np.stack(values).astype(np.float64)
    assert result.shape == (count, len(keys), 3) and np.isfinite(result).all()
    return result

def basic(pred, gold):
    error = pred - gold
    return {'MAE': float(np.mean(np.abs(error))), 'MSE': float(np.mean(error ** 2)),
            'RMSE': float(np.sqrt(np.mean(error ** 2))), 'elements': int(error.size),
            'negative_prediction_fraction': float(np.mean(pred < 0))}

def report(pred, gold, reference):
    activity = {}
    for name in ('inactive', 'low', 'medium', 'high'):
        mask = groups[name]
        row = {'nodes': int(mask.sum()), 'status': 'ok' if mask.any() else 'empty'}
        if mask.any():
            row.update(basic(pred[:, mask], gold[:, mask]))
            ref_mae = basic(reference[:, mask], gold[:, mask])['MAE']
            row['NaiveRef_MAE'] = ref_mae
            row['relative_MAE_gain'] = (ref_mae - row['MAE']) / ref_mae if ref_mae else None
        activity[name] = row
    return {
        'overall': basic(pred, gold),
        'windows': [basic(pred[i], gold[i]) for i in range(len(pred))],
        'horizons': [basic(pred[:, :, h], gold[:, :, h]) for h in range(3)],
        'activity_groups': activity,
        'balanced_activity_group_MAE': float(np.mean([row['MAE'] for row in activity.values() if row['status'] == 'ok'])),
        'neighbor_groups': {name: basic(pred[:, groups[name]], gold[:, groups[name]])
                            for name in ('has_neighbor', 'isolated')},
        'contexts': {str(context): basic(pred[:, keys[:, 0] == context], gold[:, keys[:, 0] == context])
                     for context in np.unique(keys[:, 0])},
        'nonnegative_clipped_diagnostic': basic(np.maximum(pred, 0), gold),
    }

new_pred = tensors(output, 'pred', 4)
new_gold = tensors(output, 'gold', 4)
old_pred = tensors(old, 'pred', 4)
old_gold = tensors(old, 'gold', 4)
canonical = np.load(run / 'test-gold.npy').astype(np.float64)
assert np.array_equal(new_gold, old_gold) and np.array_equal(new_gold, canonical)
naive = np.load(run / 'test-naive.npz')
selected = json.loads((run / 'naive-selection.json').read_text())['NaiveRef']
reference = naive[selected]
new_metrics = basic(new_pred, new_gold)
old_metrics = basic(old_pred, old_gold)
for folder, metrics in ((output, new_metrics), (old, old_metrics)):
    recorded = json.loads((folder / 'metrics.json').read_text())
    assert all(abs(recorded[name] - metrics[name]) <= 0.01 for name in ('MAE', 'RMSE'))
relative_mae = abs(new_metrics['MAE'] - old_metrics['MAE']) / max(1, new_metrics['MAE'], old_metrics['MAE'])
val_pred = tensors(output, 'validation_pred', 1)
val_gold = tensors(output, 'validation_gold', 1)
assert np.array_equal(val_gold, np.load(run / 'validation-gold.npy').astype(np.float64))
val_reference = np.load(run / 'validation-naive.npz')[selected]
result = {
    'basis': 'saved predictions only; float64 recomputation', 'source_data_read': False, 'model_refit': False,
    'same_seed': 1, 'CUDA_relative_MAE_tolerance': 1e-4,
    'relative_MAE_difference': relative_mae, 'within_MAE_tolerance': relative_mae <= 1e-4,
    'max_absolute_prediction_difference': float(np.max(np.abs(new_pred - old_pred))),
    'per_window_max_absolute_prediction_difference': [float(np.max(np.abs(new_pred[i] - old_pred[i]))) for i in range(4)],
    'exact_prediction_match': bool(np.array_equal(new_pred, old_pred)), 'labels_identical': True,
    'old_seed1': report(old_pred, old_gold, reference),
    'new_seed1': report(new_pred, new_gold, reference),
    'validation': report(val_pred, val_gold, val_reference),
    'test_naive_baselines': {name: report(naive[name], new_gold, reference) for name in naive.files},
    'limits': ['Environment comparability requires condition-review.md',
               'MAE tolerance alone does not prove predictions or execution conditions are identical',
               'Node groups and overlapping windows are not independent trials'],
}
(run / 'comparison.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
print(json.dumps({name: result[name] for name in ('relative_MAE_difference', 'within_MAE_tolerance',
      'max_absolute_prediction_difference', 'exact_prediction_match', 'labels_identical')}, indent=2))
PY
T005_COMPARE_EXIT=${PIPESTATUS[0]}
printf 'Comparison exit: %s\n' "$T005_COMPARE_EXIT" | tee "$T005_RUN/comparison-exit.txt"
fi
```

## 8. 如何判断结果，何时进入下一项

| 观察 | 判断与下一动作 |
| --- | --- |
| 标签不一致、指标重算不符、源码/输入不符 | 先调查数据、排序、路径和保存结果；不解释为初始化差异 |
| 可比旧条件下，归一化 MAE 差不超过 `1e-4` | 满足协议 CUDA 同 seed 的 MAE 门槛；结合预测最大差、逐窗口结果和条件记录判断重复性 |
| MAE 在容差内，但预测差明显或窗口间抵消 | 不能只报“可复现”；记录差异并调查，协议没有另定预测最大差的硬阈值 |
| 同 seed 超过容差 | 先核对环境、设备、确定性设置和警告；不把这次差异并入初始化方差 |
| 旧环境不能恢复 | 明确原因；在固定新环境做两次同 seed 重复，旧/新跨条件比较单列 |
| 同 seed 稳定，旧 seed 0/1 仍相差很大 | 可以讨论是否按协议补 seed 2/3/4；本指导不自动启动它们 |
| 模型仍差于 LastValue | 保留该结果；分别诊断负预测、尺度、TopK 饱和和测试冷启动，每次只改变一个因素 |

T005 的验收是“受控复跑与条件清楚”，不要求 EvolveGCN-H 优于 LastValue。实验成功不自动等于研究接受或 P01 完成。若有尚未解释的执行差异，保留部分完成状态；不为了完成任务而只挑相近的一次。

## 9. 保存、取回和交接

在服务器 run 内用编辑器写 `summary.md`。可按下面结构填写实际值：

```markdown
# Run: <本次 run ID>

所属任务：P01-T005。状态：succeeded / failed / interrupted。
开始与结束：见 status.json。科学协议与保存政策：见 provenance.json。

## 实际过程

原服务器、源码、依赖与设备核对结论：见 condition-review.md。
准确步骤：guide.md；如有改动，链接实际脚本与命令。
执行到哪里、退出码、耗时/内存：training.log、cost.json。

## 结果与证据

选中 epoch / 验证 MSE：selection.json；完整轨迹：training-trace.jsonl。
总体 MAE/RMSE、负预测、逐窗口/horizon/分组：comparison.json。
同 seed 归一化 MAE 差、预测最大差、标签一致性：comparison.json。
checkpoint 与预测/标签：outputs/count/region/EvolveGCNH/1/。

## 限制和下一动作

条件差异与仍未解释的问题；发布图构建时间未知。
只说明本次已证明什么，不由两个 seed 估计稳定平均性能。
下一项建议与是否获准执行分开记录。
```

本轮无需默认打包。成功、失败或中断材料均可用 rsync 取回；不使用删除选项。先在 Mac 设置服务器端实际 run ID，创建不存在的新本地目录：

```bash
cd /Users/watuji/da_chuang/repos/benchmark
export T005_HOST='ubuntu@YOUR_SERVER_IP'
export T005_PORT='22'
export T005_RUN_ID='REPLACE_WITH_ACTUAL_RUN_ID'
export T005_LOCAL="$(pwd)/research/runs/$T005_RUN_ID"
python - <<'PY'
import os
from pathlib import Path
Path(os.environ['T005_LOCAL']).mkdir(parents=True, exist_ok=False)
PY
rsync -av -e "ssh -p $T005_PORT" "$T005_HOST:~/t005-runs/$T005_RUN_ID/" "$T005_LOCAL/"
```

本地目录创建失败时不继续 rsync。下载中断后先确认目录只属于本次 run，再针对该目录恢复传输；不要覆盖其他 run。取回后检查 `summary.md`、状态、比较报告和所链接的模型产物确实存在。传输成功只表示形成了本机副本，不代表 Git 提交、push、封存或恢复核验已经完成。

最后由研究侧依据证据更新任务验收、恢复位置与下一动作；实际产物保存位置和备份状态写入 `research/archives/index.md`。记录维护不自动运行 OpenSpec 流程，也不自动 commit/push。若后续需要参数化正式模型入口，再按项目约定登记实现委托并使用 OpenSpec。

交接时提供本次 run ID、`summary.md`、`condition-review.md`、`status.json`、`selection.json`、`cost.json` 和 `comparison.json`。做到这里本轮结束；是否补 seed 或做干预另行确定。

## 编写时的检查范围

本机已检查 Bash 命令语法及内嵌 Python 的 Python 3.8 语法兼容性。数据/分组/窗口核对和 saved-only 比较段已用当前原始数据、归档预测与临时目录检查，未拟合或推理模型。临时比较以旧预测副本作同值输入，确认预测差为 0，重算 seed 1 MAE 约 96.180772、LastValue MAE 约 35.309850；这验证的是指导脚本，不是新的同 seed 实验结论。GPU 训练段、SSH/传输与服务器完整条件尚未实机核验。2026-10-18 首次实机运行暴露并修复了 §6 成本测量行的 CUDA 初始化顺序问题（见 §6 注）；该修复尚无一次完整成功训练作为依据，仍以各 run 的实际日志为准。
