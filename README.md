<div align="center">
  <img src="figs/title.png" alt="Title Image">
    <p> 
    	<b>
        Job-SDF: A Multi-Granularity Dataset for Job Skill Demand Forecasting and Benchmarking<a href="https://arxiv.org/pdf/2406.11920" title="PDF">PDF</a>
        </b>
    </p>

---

<p align="center">
  <a href="## 1. Overview">Overview</a> •
  <a href="## 2. Installation">Installation</a> •
  <a href="## 3. Dataset">Dataset</a> •
  <a href="## 4. How to Run">How to Run </a> •
  <a href="## 5. Directory Structure">Directory Structure</a> •
  <a href="## 6. Citation">Citation</a> 
</p>
</div>

Official repository of paper [&#34;Job-SDF: A Multi-Granularity Dataset for Job Skill Demand Forecasting and Benchmarking&#34;](https://arxiv.org/pdf/2406.11920). Please star, watch and fork our repo for the active updates!

Research progress, plans, decisions, and evidence for this fork start at [RESEARCH.md](RESEARCH.md).

## 1. Overview

<!-- <div style="display: flex; justify-content: center;">
  <img src="https://github.com/usail-hkust/UUKG/blob/main/workflow.png" width="400">
  <img src="https://github.com/usail-hkust/UUKG/blob/main/UrbanKG.png" width="300">
</div> -->

In a rapidly evolving job market, skill demand forecasting is crucial as it enables policymakers and businesses to anticipate and adapt to changes, ensuring that workforce skills align with market needs, thereby enhancing productivity and competitiveness. Additionally, by identifying emerging skill requirements, it directs individuals towards relevant training and education opportunities, promoting continuous self-learning and development. However, the absence of comprehensive datasets presents a significant challenge, impeding research and the advancement of this field. To bridge this gap, we present **Job-SDF**, a dataset designed to train and benchmark job-skill demand forecasting models. Based on millions of public job advertisements collected from online recruitment platforms, this dataset encompasses monthly recruitment demand.
Our dataset uniquely enables evaluating skill demand forecasting models at various granularities, including occupation, company, and regional levels. 
We benchmark a range of models on this dataset, evaluating their performance in standard scenarios, in predictions focused on lower value ranges, and in the presence of structural breaks, providing new insights for further research. Our code and dataset are publicly accessible via the https://github.com/Job-SDF/benchmark.
## 2. Installation

Step 1: Create a python 3.8 environment and install dependencies:

```
conda create -n Job-SDF python=3.8
conda activate Job-SDF
```

Step 2: Install library

```bash
pip install -r requirements.txt
```

## 3. Dataset

Our dataset comprises five components for each granularity level: job skill demand sequences, job skill demand proportion sequences, ID mapping index, the indexes of skills with structural breaks, and skill co-occurrence graph, which can be found in dataset.

#### 3.1 Job-SDF Data

|      | L1-Occupation | L2-Occupation | Company | Skill |
| ---- | ------------- | ------------- | ------- | ----- |
| Size | 14            | 52            | 521     | 2324  |

##### 3.1.1 Guidance on data usage and processing

We store the processed files in the **'./dataset'** directory.
The file information in each directory is as follows:

```
./demand    These are presented in tabular files, where each row represents a specific skill, and each column corresponds to a different time slice (month). Each cell within the table contains a numerical value that reflects the demand for the respective skill during that month. This directory backs the public `count` mode.

./entity_map    The specific name index tables of L1 occupations, L2 occupations, regions, and skills are stored here. In order to protect privacy information, we have hidden this part of the data. If you need it, you can contact the first author's email (chenxi0401@mail.ustc.edu.cn).

./proportion    This component is also formatted in tabular files similar to the skill demand sequences. However, each cell in these tables displays a value between 0 and 1, representing the proportion of demand. This directory backs the public `rate` mode.

./structural_breaks_index     In the provided dataset, data concerning skills that have experienced structural breaks are organized in JSON format. Each granularity level is represented by a separate JSON file, which contains a list of indexes. These indexes correspond to the skills that have undergone structural breaks and can be directly mapped to the skill indexes in the skill demand sequences. The purpose of supplying this data is to facilitate research on the demand trends of skills that have exhibited structural breaks, enabling a detailed analysis of their demand dynamics over time.

./graph   Co-occurrence rows in Parquet format, one file per granularity. Each file carries the granularity's context identifier column(s) — for example `r0_id` for `r0`, `r1_id` plus `region_id` for `r1-region` — followed by `row_id` and `col_id`. There is **no** frequency or weight column in the shipped files. A graph endpoint is the ordered tuple of all context identifiers followed by the skill identifier, so the same skill pair under two different contexts is two different graph nodes; the number of identical fully qualified `(row_id, col_id)` rows under the same context is the only multiplicity the data provides.
```

## 4. How to Run

### 4.1 Traditional Methods

```bash
cd benchmark/traditional_method
python main.py [-h] [--data_name {r0, r1,...}]
      [--model {ARIMA, prophet}]
      [--mode {count, rate,...}]
```

### 4.2 Multi-variate time series forecasting

```bash
cd benchmark/multivariate_time_series
python run.py [-h] [--root_path {../../dataset/demand, ../../dataset/proportion}]
      [--data_path {r0.parquet, r1.parquet,...}]
      [--model {LSTM, CHGH, Autoformer,Crossformer,...}]
```

### 4.3 Pre-DyGAE

```bash
run benchmark/predygae/data_process.ipynb
cd benchmark/predygae
sh scripts/stage1.sh {r0,r1,...}
sh scripts/stage2.sh {r0,r1,...} 24 36
sh scripts/stage3.sh {r0,r1,...} 24 36
```

### 4.4 Graph-based time series forecasting

Run every command in this section **from the repository root**; none of them changes the
working directory. Repository data, generated data and results are resolved from the
module location, not from the current directory.

Preparation. All preparation logic lives in `prepare_graph_data.py`:

```bash
conda activate Job-SDF
python benchmark/graph_method/prepare_graph_data.py --help
python benchmark/graph_method/prepare_graph_data.py --mode rate --data_name r0
```

Passing no `--data_name`/`--mode` prepares all seven granularities
(`r0`, `r1`, `r2`, `r1-region`, `r2-region`, `region`, `company`) in both modes.
`count` reads `dataset/demand` and `rate` reads `dataset/proportion`; the generated,
versioned artifacts are written to `benchmark/graph_method/data/<mode>/<granularity>.json`.
`benchmark/graph_method/data_process.ipynb` is only a thin caller of the same CLI.

Training and evaluation. One invocation runs the requested seed exactly once and writes
its results under `benchmark/graph_method/results/<mode>/<data_name>/<model_name>/<seed>/`:

```bash
python benchmark/graph_method/main.py [-h] [--data_name {r0, r1, ...}]
      [--model_name {A3TGCN, DCRNN, DyGrEncoder, EvolveGCNH, EvolveGCNO,
                     GCLSTM, GConvGRU, GConvLSTM, LRGCN, MPNNLSTM, TGCN}]
      [--mode {count, rate}]
      [--device cpu] [--seed 0] [--window_size 6] [--hidden_dim 32]
      [--pred_length 3] [--num_epochs 500]
```

The documented default command is therefore:

```bash
python benchmark/graph_method/main.py --data_name r0 --mode rate --model_name EvolveGCNH
```

`--hidden_dim` applies only to the model families that consume it (A3TGCN, DCRNN,
DyGrEncoder, GCLSTM, GConvGRU, GConvLSTM, LRGCN, MPNNLSTM and TGCN). EvolveGCNH and
EvolveGCNO derive their square graph-convolution weight from `--window_size` and ignore
`--hidden_dim`.

EvolveGCNH summarizes exactly `window_size` nodes for each recurrent weight update.
Equal TopK scores are resolved by canonical node order, including scores saturated
by large count inputs, so CPU and CUDA do not choose different tied nodes.

Temporal splitting reserves `pred_length - 1` omitted windows between training and
validation, and between validation and test. The nominal ratios remain 0.83/0.04/the
remainder: the test period and validation count are preserved, while both gaps are
subtracted from training. This prevents the same target month from appearing in
different splits. With 36 months, `window_size=6` and `pred_length=3`, the 28 windows
yield **19 training, 1 validation and 4 test snapshots**, with 4 windows omitted.
Training targets end in March 2023, validation targets cover April–June 2023, and
test targets cover July–December 2023. Inputs may use earlier known observations.
Configurations that cannot leave all three partitions non-empty fail before training.

Each run trains on the training split, selects the best checkpoint by validation loss
only, and traverses the test split exactly once after restoring that checkpoint. The
result directory contains `checkpoint.pt` (a versioned `model_state_dict` plus the
configuration, seed and best validation loss), `pred_<t>.pt`, `gold_<t>.pt` and
`metrics.json`; prediction files left by an earlier run in the same seed directory are
removed before the new ones are written. Checkpoint **format 2** stores best validation
loss as a float64 scalar tensor, so PyTorch 1.13.1 can load it with `weights_only=True`.
All tensor outputs use Python file handles to support Windows paths containing Unicode.
Checkpoints are not pickled model objects. Legacy `model.pt` and format-1 `checkpoint.pt`
files are intentionally rejected with a rerun hint; retrain to produce format 2 under
the corrected split. Earlier metrics from overlapping target periods are not comparable
to this protocol.

### 4.5 Graph-free CPU baseline (`benchmark.nograph_baseline`)

`benchmark/nograph_baseline/` is an independent CPU entry for the
`P1-count-L6-H3-v3` protocol (see `research/phases/P01/protocol.md`). It computes
the five naive baselines and one shared Ridge model for `r0/count`,
`region/count` and `r2/count` without importing graph methods, PyTorch, PyG or
DGL. Count granularity is selected with `--data-name`; the context key is
`r0_id`, `region_id` or `r2_id` respectively, always paired with `skill_id` to
form the node identity. Its only
required third-party dependencies are NumPy, pandas and PyArrow; scikit-learn is
an optional backend.

Use the dedicated environment and install only the local dependency list (it does
**not** require the root `requirements.txt` CUDA/DGL packages):

```bash
conda activate job-sdf-baseline
python -m pip install --no-cache-dir -r benchmark/nograph_baseline/requirements.txt
```

Commands (run from the repository root; every model run writes a fresh directory
and refuses to overwrite an existing run ID):

```bash
# one formal run per dataset, CPU, seed 0, NumPy backend
python -m benchmark.nograph_baseline run --data-name r0 --mode count --seed 0 \
    --run-id p01-r0-sharedridge-001 --purpose formal
python -m benchmark.nograph_baseline run --data-name region --mode count --seed 0 \
    --run-id p01-region-sharedridge-001 --purpose formal

# an independent same-seed repetition in a fresh directory
python -m benchmark.nograph_baseline run --data-name r0 --mode count --seed 0 \
    --run-id p01-r0-sharedridge-repeat-001 --purpose formal

# a disposable development invocation (ignored scratch/nograph-baseline/, never
# inside research/runs/); add --retain-candidates to keep losing Ridge arrays
python -m benchmark.nograph_baseline run --data-name r0 --mode count --seed 0 \
    --run-id probe-r0 --purpose development --retain-candidates

# the third supported granularity, r2/count (context key r2_id); the same
# development rules apply. A formal r2 run and its research acceptance require
# separate authorization and are not started by implementation/verification work.
python -m benchmark.nograph_baseline run --data-name r2 --mode count --seed 0 \
    --run-id probe-r2 --purpose development

# recompute every metric from saved run artifacts only (no source data, no refit)
python -m benchmark.nograph_baseline recompute \
    --run-dir research/runs/p01-r0-sharedridge-001 \
    --report research/reports/nograph-baseline/p01-r0-recompute-001.json

# compare two same-seed runs under the CPU relative tolerance of 1e-6
python -m benchmark.nograph_baseline compare \
    --run-a research/runs/p01-r0-sharedridge-001 \
    --run-b research/runs/p01-r0-sharedridge-repeat-001 \
    --report research/reports/nograph-baseline/p01-r0-repeat-check-001.json

# align naive results with the sealed v2 diagnostic (read-only reference)
python -m benchmark.nograph_baseline align-v2 \
    --run-dir research/runs/p01-r0-sharedridge-001 \
    --reference research/runs/phase1-20261006-v2-01/naive-baselines.log \
    --report research/reports/nograph-baseline/p01-r0-alignment-001.json
```

`run` always executes all five naive methods and the shared Ridge model. Optional
flags are `--purpose {formal,development}`, `--ridge-backend {numpy,sklearn}`,
`--clip-nonnegative` (which adds a separately labeled `SharedRidgeNonnegative`
report that never influences selection) and `--retain-candidates` (which also
persists every losing Ridge candidate's parameters and validation predictions;
by default only the selected model is persisted and `selection.json` still keeps
the complete scalar candidate score table).

**Development backtest folds.** `--fold {A,B}` selects one of the two fixed
development backtest folds of `research/phases/P01/t007-backtest-guide.md`
section 2; omitting it keeps the unchanged main split and every existing main
artifact. A fold refits the normalization, frozen mean and activity grouping on
its own fitting observations and reports `validation` plus `eval` (never
`test`); 2023-07..12 is not computed. Fold A fits 2021-01..2022-06 (18 months,
`TrainMean18`, `fit18` groups), uses training starts 0..9, validation start 12
targeting 2022-07..09 and eval start 15 targeting 2022-10..12, omits starts 10,
11, 13, 14, 16, 17 and marks 18..27 as outside the fold. Fold B fits
2021-01..2022-09 (21 months, `TrainMean21`, `fit21` groups), uses training
starts 0..12, validation start 15 targeting 2022-10..12 and eval start 18
targeting 2023-01..03, omits starts 13, 14, 16, 17, 19, 20 and marks 21..27 as
outside the fold. Each fold is development evidence about a different forecast
origin, not an additional blind test and not a replacement for the main
2023-07..12 evaluation.

```bash
# one A/B development smoke per dataset (ignored scratch output; no formal run)
python -m benchmark.nograph_baseline run --data-name r0 --mode count --seed 0 \
    --fold A --run-id probe-r0-backtest-a --purpose development
python -m benchmark.nograph_baseline run --data-name r0 --mode count --seed 0 \
    --fold A --run-id probe-r0-backtest-a-repeat --purpose development
python -m benchmark.nograph_baseline run --data-name region --mode count --seed 0 \
    --fold B --run-id probe-region-backtest-b --purpose development

# saved-only fold checks: validation/eval metrics, gains and node errors
python -m benchmark.nograph_baseline recompute \
    --run-dir scratch/nograph-baseline/probe-r0-backtest-a \
    --report scratch/nograph-baseline/reports/probe-r0-backtest-a-recompute.json
python -m benchmark.nograph_baseline compare \
    --run-a scratch/nograph-baseline/probe-r0-backtest-a \
    --run-b scratch/nograph-baseline/probe-r0-backtest-a-repeat \
    --report scratch/nograph-baseline/reports/probe-r0-backtest-a-compare.json
# align-v2 rejects a fold run: the immutable v2 reference has no fold records
python -m benchmark.nograph_baseline align-v2 \
    --run-dir scratch/nograph-baseline/probe-r0-backtest-a \
    --reference research/runs/phase1-20261006-v2-01/naive-baselines.log \
    --report scratch/nograph-baseline/reports/probe-r0-backtest-a-align.json
```

Fold metadata is written consistently to `config.json`, `provenance.json`,
`windows.json` (all 28 roles: train, validation, eval, omitted with reason, or
outside_fold), `selection.json`, `metrics.json` and `audit.json`
(`fit18`/`fit21` statistics; retained 27-month values stay under
`main_protocol_diagnostics` and never feed fold fitting, grouping or
selection). Fold runs save `models/TrainMean18.npz`/`TrainMean21.npz`,
`activity_fit18_*`/`activity_fit21_*` masks, `predictions/<method>/validation.npy`
and `eval.npy`, and `gold/validation.npy`/`gold/eval.npy`; no `test` split is
computed. `recompute` reproduces every fold metric, gain and node-error column
from saved evidence; `compare` additionally requires the same explicit fold,
dataset, demand content identity and seed, so A-versus-B, main-versus-fold,
different data/content or different seed fail even when predictions coincide.
A formal fold run (`--purpose formal`) writes `research/runs/` and records
`evidence_role=development_backtest`, but formal-fold execution/saving and
research acceptance require separate authorization; implementation and
verification use development fixtures only.

**Formal vs development.** `--purpose formal` (the default) writes
`research/runs/<run_id>/`; `--purpose development` writes the ignored
`scratch/nograph-baseline/<run_id>/` and labels the run as development rather
than scientific acceptance evidence. A development invocation is rejected
before any directory is created if its output root resolves inside
`research/runs/`, including through a symlink alias. Purpose never changes
fitting, reference selection or metric definitions.

**Provenance.** Committed runtime source and the protocol are located by fixed
commit and repository-relative path (`git-commit.txt`, `code-source.json`)
instead of copied snapshots; scoped staged/unstaged execution changes are saved
as `git-diff.patch` and necessary untracked runtime/protocol content under
`code-untracked/`. Unrelated research records, tests and caches are excluded,
and an unavailable Git identity is recorded explicitly with a content fallback.
A clean run records commit/path/SHA256 references without copying source.

**Check reports.** `recompute`, `compare` and `align-v2` each write exactly one
exclusive JSON report at the requested `--report` path. The documented legacy
`--run-id ID`/`--runs-root ROOT` flags remain supported as aliases and resolve
to a single `<ROOT>/<ID>.json` report (default root
`research/reports/nograph-baseline/`); supplying both choices fails before
writing. Reports embed the command, checker source identity, consumed-input
identities, documented tolerances, status and recomputed metrics. A report is
never overwritten, checks never read source demand/graph data or fit a model,
and input run directories are left byte-for-byte unchanged. A missing or
invalid saved input still produces a failure report and a nonzero exit; an
invalid output destination produces no output. All three checks accept saved
`r2` results under the same report contract and preserve `r2_id` identities.
`recompute` and `compare` also accept saved fold A/B results (validation plus
eval); `compare` requires the same fold and `align-v2` rejects fold runs
explicitly because the v2 reference has no fold records.
`align-v2` requires the supplied immutable reference to contain records for the
run's dataset: the historical sealed v2 log holds `r0`/`region` records only and
is never rewritten, so `r2` alignment uses a separate v2-format reference that
includes `r2`; a reference without `r2` records fails explicitly rather than
being accepted, and a reference without source identity stays `limited`.

**r2 authorization.** The `r2/count` path reuses the same protocol, selection,
grouping and artifact contract as `r0`/`region`; adding it changes no scientific
definition and no accepted `r0`/`region` evidence. Formal `r2/count` execution,
saving and research acceptance remain separately authorized research actions,
and software/development checks do not constitute a formal r2 experiment or a
scientific conclusion.

Outputs under `research/runs/` are **unsealed and not backed up**: a successful
run records reproducible evidence only and does not imply scientific
acceptance, packaging, Git inclusion or backup completion. Model and check
commands never invoke sealing, Git, network or recovery actions; those
maintenance steps are separately requested.

The T004 archive helper is used only as an explicitly requested maintenance
action:

```bash
# verify the sealed T004 packages against the Git commit recorded in the index
python research/archives/seal_20261007_baseline.py verify
```

It accepts the schema-v2 index (Git commit/path identity plus exclusion
declarations, no sidecars or full member hash tables) and still verifies the
historical schema-v1 index with its checksums. It never overwrites a sealed
package and never restores into `research/runs/`. A package exported outside
Git must be delivered with its own external SHA256; no export framework is
provided.

Automated tests need no GPU and no repository graph data:

```bash
python -m unittest discover -s benchmark/nograph_baseline/tests
```

### 4.6 Graph-value skeleton (`benchmark.graph_value_skeleton`)

#### Epoch checkpoints and explicit recovery

Every fully trained and validated epoch publishes an object-free numeric NPZ
generation under `<run>/checkpoints/`, then atomically publishes `latest.json`
with schema, filename, SHA256, size, completed epoch and previous generation.
The latest two committed generations are retained. The payload contains current
and selected parameters, Adam slots and counters, Python/NumPy/CPU torch RNG,
history, selection and cumulative training/validation time. No pickle is loaded.
Flushed writes and bounded Windows sharing retries preserve the previous pointer
on publication failure; arbitrary hardware power-loss durability is not promised.

Resume an unfinished run explicitly into a **fresh** run ID, repeating its original
data/method/model/shuffle/purpose options and adding:

```bash
python -m benchmark.graph_value_skeleton run --data-name r0 --method graph \
    --model-seed 0 --run-id gvs-r0-graph-s0-recovered \
    --resume-from scratch/graph-value-skeleton/gvs-r0-graph-s0-a/checkpoints
```

Source bytes, runtime, protocol, input identities, graph, masks and ordered chunks
must agree. Invalid or absent checkpoints fail explicitly. Parent evidence stays
unchanged; the recovery input and ancestry are copied into the new run. The next
epoch follows the committed epoch; total training remains 200 epochs. An epoch-200
checkpoint resumes finalization without another update. Successful runs cannot
be resumed. Branches sharing training ancestry cannot count as independent repeats.
Old successful runs without recovery metadata remain readable by saved-only checks.

`training-progress.json` reports `completed_epoch`, checkpoint digest, cumulative
work, `last_epoch_seconds`, rolling `estimate_samples` and
`remaining_seconds_estimate` (null before a full epoch). Its `completion` is always
false; only terminal success artifacts establish completion. Chunk/stage updates
help diagnose a slow first epoch but cannot recover partial epoch gradients.
Downtime is excluded from cumulative work; attempt wall time and checkpoint I/O
are separate. ETA is provisional and excludes final checks and startup.

For an authorized r2 batch, inspect a recovery plan without training:

```bash
python -B research/phases/P02/t002_r2_batch.py plan --batch p02-t002-r2-recovered \
    --recover-from research/reports/p02-t002-r2-20261020-01
```

Use the same `--recover-from` with `prepare`, then `run --batch <new-batch>`.
Preparation fixes the recovery ledger; execution recomputes reused completed fits,
resumes eligible checkpoints or starts fresh replacements. OS ownership locking
and live-worker inspection prevent duplicate controllers; stale reboot records
alone do not block a fresh batch. Defaults pause after 24 hours per fit or 30
minutes without stage progress; override explicitly with `--fit-timeout-seconds`
and `--stall-timeout-seconds`. Failures pause further scheduling and preserve logs
and committed checkpoints. Only 30 completed fits and all 51 original checks permit
completion and optional `--push-on-success`; unmeasured methods have no batch ETA.

The bounded subprocess example used for recovery verification is:

```bash
python -B -m benchmark.graph_value_skeleton.tests.checkpoint_worker \
    scratch/graph-value-skeleton/checkpoint-demo graph interrupted --cut 37
python -B -m benchmark.graph_value_skeleton.tests.checkpoint_worker \
    scratch/graph-value-skeleton/checkpoint-demo graph recovered \
    --resume scratch/graph-value-skeleton/checkpoint-demo/runs/interrupted/checkpoints
```

The first command deliberately exits 73 after publishing epoch 37; the second
completes epoch 38 through 200. These commands use tiny synthetic Parquet fixtures
and never execute a formal research run.

`benchmark/graph_value_skeleton/` is an independent CPU entry that implements
the frozen P02-T001 temporal skeleton on the unchanged `P1-count-L6-H3-v3`
protocol and `P01-records-v2` policy. It reuses the P01 demand identity, main
split, five naive references, fixed masks and metric arithmetic, and adds only
the new model, graph propagation, shuffled control, saved artifacts and
read-only checks. It is software evidence for later authorized comparisons, not
a scientific result.

**Runtime.** Use the dedicated CPU environment and install only the local
dependency list (PyG, DGL, `torch-scatter`, `torch-sparse` and CUDA builds are
not required and are never imported by this entry):

```bash
conda activate job-sdf-baseline
python -m pip install --no-cache-dir -r benchmark/graph_value_skeleton/requirements.txt
```

The pinned runtime used by the tests and documented commands is Python 3.11.17,
PyTorch 2.14.1 (CPU, `torch.version.cuda=None`), NumPy 1.26.4, pandas 2.2.3 and
PyArrow 17.0.0. The default `python` 3.13 environment has no torch and is not a
substitute. BLAS/intra-op/inter-op threads are pinned to 1 and deterministic
algorithms are enabled before the model is created.

**Model and axes.** Each node's six raw monthly counts are encoded by one
shared single-layer unidirectional `GRU(1,32)` with an independent zero hidden
state per node and window; a shared `Linear(32,3)` head produces three raw
predictions. `self` uses the hidden state directly, `graph` adds the unweighted
mean of distinct incoming-neighbour hidden states (exactly zero for zero
in-degree nodes), and `shuffled` uses a context-local degree-preserving
double-edge swap graph. There is no graph-specific trainable parameter; the
measured total is 3459 (GRU 3360 + head 99). Every execution trains for exactly
200 epochs with Adam (`lr=1e-3`, betas 0.9/0.999, eps 1e-8, weight decay 0),
raw-count mean-squared error, one optimizer step per epoch after a
context-chunked global-mean gradient accumulation, and selects the checkpoint
by lowest original-unit validation MSE (earliest epoch on an exact tie). There
is no scheduler, early stopping, clipping or preprocessing search.

The axis flags are explicit: `--method {self,graph,shuffled}`, `--model-seed`
(development profile 0..2, final profile 0..4; the profile never schedules
runs), and `--shuffle-seed 0|1|2` which is required for `shuffled` and forbidden
otherwise. `--purpose` defaults to `development`.

**Commands** (run from the repository root). Development output goes to the
ignored `scratch/graph-value-skeleton/<run-id>/`; every save is exclusive and
never overwrites an existing run ID:

```bash
# one development run per method (self/graph/shuffled); shuffle seeds 0/1/2
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton run \
    --data-name r0 --method self --model-seed 0 --purpose development \
    --run-id gvs-r0-self-s0-a
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton run \
    --data-name r0 --method graph --model-seed 0 --purpose development \
    --run-id gvs-r0-graph-s0-a
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton run \
    --data-name r0 --method shuffled --shuffle-seed 0 --model-seed 0 \
    --purpose development --run-id gvs-r0-shuffled0-s0-a

# an independent same-seed repetition (same axes, fresh run ID)
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton run \
    --data-name r0 --method graph --model-seed 0 --purpose development \
    --run-id gvs-r0-graph-s0-b

# saved-only checks write exactly one exclusive JSON report under ignored
# scratch or a validated temporary root; inputs are never modified
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton recompute \
    --run-dir scratch/graph-value-skeleton/gvs-r0-graph-s0-a \
    --report scratch/graph-value-skeleton/reports/gvs-r0-graph-s0-a-recompute.json
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton compare \
    --run-a scratch/graph-value-skeleton/gvs-r0-graph-s0-a \
    --run-b scratch/graph-value-skeleton/gvs-r0-graph-s0-b \
    --report scratch/graph-value-skeleton/reports/gvs-r0-graph-s0-repeat.json

# the shuffled control for one model seed: the arithmetic mean of the three
# independently trained shuffle-seed MAEs, (MAE0 + MAE1 + MAE2) / 3. It is not
# the MAE of averaged predictions and never selects the weakest graph.
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton summarize-shuffled \
    --run-dirs scratch/graph-value-skeleton/gvs-r0-shuffled0-s0-a \
               scratch/graph-value-skeleton/gvs-r0-shuffled1-s0-a \
               scratch/graph-value-skeleton/gvs-r0-shuffled2-s0-a \
    --report scratch/graph-value-skeleton/reports/gvs-r0-shuffled-s0-summary.json
```

`--output-root` is development-only and must resolve inside the repository's
ignored scratch tree or the system temporary directory; a path that resolves
into `research/`, `experiments_archive/`, the dataset or source tree (including
through a symlink) is rejected before training. `--purpose formal` resolves a
fresh `research/runs/<run-id>/` directory and **requires separate research
authorization**; implementation and independent verification never execute it,
and this chapter does not schedule any formal run.

**Saved evidence.** Each successful execution records purpose/task, scientific
and policy versions with content identity, demand/graph/node identity, resolved
configuration, scoped execution-source identity with necessary uncommitted
content, environment and thread settings, exact commands, stage timings and
peak RSS, terminal status, fixed masks, the actual message and source edge sets,
validation/test gold and predictions (including the five naive methods), the
selected numerical parameters with measured parameter counts, all 200
training/validation score rows with the selection reason, and the complete
metrics/gain report. Failures and interruptions retain available evidence and
an explicit `failed`/`interrupted` state; a leftover `running` record is
classified as unfinished by `check_unfinished` rather than as success.

**Evidence boundaries.** The published graph construction cutoff time is
unknown, so results describe the fixed evaluation period and cannot claim strict
historical or future graph information. Software readiness and a later
archived independent verification `PASS` are evidence for a separate
research-side implementation acceptance decision; they do not change the
protocol, split, selection rule or §6.2 thresholds, do not start a formal
P02-T002 comparison, and do not establish predictive benefit.

Automated tests use small synthetic fixtures and need no GPU or full dataset:

```bash
conda run -n job-sdf-baseline python -m unittest discover -s benchmark/graph_value_skeleton/tests -v
# the existing graph-free entry keeps its own no-torch-compatible suite
conda run -n job-sdf-baseline python -m unittest discover -s benchmark/nograph_baseline/tests -v
```

### Prepared shuffled controls (P02 execution repair)

`dds-v2` retains exactly `10*E_ctx` accepted directed swaps and tests a finite
`500*E_ctx` proposal ceiling. Buffers of 4096 uniform ordered edge-index pairs are
consumed sequentially against the current graph; unused prefetched pairs are not
attempts. Accept this candidate only after all nine published conditions and
independent regenerations pass. A larger ceiling does not guarantee completion
or uniform mixing. Checkers retain the `dds-v1` `10E/100E` contract and reject
unknown versions or inconsistent saved budgets.

Preparation does not initialize, fit or evaluate a model. In the local pinned
environment use `.venv-pinned/Scripts/python.exe` in place of `python`. On Windows
set `PYTHONUTF8=1` for subprocess diagnostic text in paths containing Chinese.
Environment evidence requires `python -m pip freeze` to succeed. If a minimal
virtual environment lacks pip, bootstrap its bundled copy with
`python -m ensurepip --upgrade` before running checks. Windows peak memory uses
`GetProcessMemoryInfo.PeakWorkingSetSize` in bytes; Linux/macOS retain their
native `resource.getrusage` measurements. Both cover the worker process lifetime.
On Windows, `prepare-shuffle` imports the recorded PyTorch runtime before the
pandas/Arrow data modules to avoid a reproduced `c10.dll` initialization failure
in this pinned environment. It still creates no model and performs no training.

```bash
# Always use fresh IDs and report paths.
python -m benchmark.graph_value_skeleton prepare-shuffle \
    --data-name r2 --shuffle-seed 0 --run-id r2-shuffle0-prepared
python -m benchmark.graph_value_skeleton check-shuffle \
    --artifact-dir scratch/graph-value-skeleton/r2-shuffle0-prepared \
    --report scratch/graph-value-skeleton/reports/r2-shuffle0-checked.json

# Reuse the graph; this model invocation still independently trains 200 epochs.
python -m benchmark.graph_value_skeleton run \
    --data-name r2 --method shuffled --shuffle-seed 0 --model-seed 0 \
    --shuffle-artifact scratch/graph-value-skeleton/r2-shuffle0-prepared \
    --purpose development --run-id r2-shuffle0-s0-prepared-run

# Graph-only readiness: r2/seed0 first, all nine conditions independently
# regenerated. This command never schedules a model or formal experiment.
python -m benchmark.graph_value_skeleton.readiness --run-id shuffled-readiness-v2

# Small fixture alternative to the published preparation command:
python -c "from pathlib import Path; from benchmark.graph_value_skeleton.tests.fixtures import build_fixture; build_fixture(Path('scratch/graph-value-skeleton/example-fixture'), 'r0')"
python -m benchmark.graph_value_skeleton prepare-shuffle \
    --data-name r0 --shuffle-seed 0 --run-id fixture-prepared \
    --demand-path scratch/graph-value-skeleton/example-fixture/r0-demand.parquet \
    --graph-path scratch/graph-value-skeleton/example-fixture/r0-graph.parquet
```

Prepared directories contain canonical int64 node/source/result arrays, complete
shuffle audits, generator source/runtime provenance, measurements, checksums and
terminal status. Saved-only `check-shuffle` leaves inputs unchanged and writes
one fresh external report. It checks canonical identity, all directed degrees,
no duplicate/self/cross-context edge, changed edges, context counters and hashes.
It cannot prove the provenance of a forged artifact; independent regeneration
provides separate reproducibility evidence.

`--shuffle-artifact` is shuffled-only. A mismatched source/node/seed/generator
source/runtime/version, damaged file or non-success status fails before training
without fallback generation. Paths, reuse flags and read timing are execution
metadata. Model runs retain complete graph arrays and audits for recomputation
without the external preparation directory. Nine prepared graphs can serve 54
independently trained shuffled runs; three separate MAEs are still averaged for
each model seed and repetition.

`progress.json` (`shuffle-progress.json` in a model run) records context boundaries
and snapshots at most 100,000 consumed proposals apart. Exhaustion retains
`shuffle-failure.json` with prior-context audits and the failing context's target,
limit, accepted/attempted/rejection counts, identities, reason and elapsed time.
Interrupted/unfinished artifacts cannot be reused. Partial chains are diagnostic
recovery points and are not automatically resumed.

On Windows, JSON/text publication retries only sharing/access-denied replacement
errors (WinError 5/32/33), using the same flushed temporary file for at most eight
attempts and 1.05 seconds of backoff. Recovery is recorded as
`atomic_replace_recovered`; persistent denial raises and preserves the previous
checkpoint and temporary bytes. This does not retry graph computation.

The readiness driver pauses at the first failed check or regeneration mismatch,
after 10 minutes per graph or 60 seconds without observable progress, preserving
logs and a paused manifest. These are operational watchdogs, not scientific/RNG
settings. The bounded r2/context12 membership comparison found the tuple/set
backend faster than compact boolean adjacency, so the default stays tuple/set.
The comparison script and measurements accompany the change. Generation and
reuse-read costs are recorded separately; graph costs do not establish training
speed or predictive quality. Formal execution follows independent verification,
archive and research-side acceptance/cost confirmation.

Prepared `measurements.json` retains one `context_timings` record per context
from swap progress elapsed time (zero swap work for empty contexts). These wall
clock measurements stay outside deterministic graph identity. Saved checks also
require consistent generator source hashes and recorded Python/package metadata;
they validate those saved records without reading the original sources.

## 5 Directory Structure

The expected structure of files is:

```
Job-SDF
 |-- benchmark
 |    |-- graph_method
 |    |    |-- prepare_graph_data.py  # preparation CLI for the graph datasets
 |    |    |-- dataset.py             # validated weighted temporal graph loader
 |    |    |-- main.py                # one seeded experiment per invocation
 |    |    |-- data_process.ipynb     # thin caller of prepare_graph_data.py
 |    |    |-- data/                  # generated artifacts (created on demand)
 |    |    |-- results/               # checkpoints, predictions, metrics (created on demand)
 |    |    |-- tests/                 # graph-method unit suite
 |    |-- nograph_baseline            # graph-free CPU baseline entry (P1-count-L6-H3-v3)
 |    |    |-- cli.py                 # run / recompute / compare / align-v2 commands
 |    |    |-- requirements.txt       # NumPy + pandas + PyArrow only
 |    |    |-- tests/                 # CPU unittest suite with synthetic fixtures
 |-- dataset  # Job-SDF_data
 |    |-- demand
 |    |-- entity_map
 |    |-- graph
 |    |-- proportion
 |    |-- structural_breaks_index
 |-- figs
 |-- requirements.txt
 |-- README.md
```

## 6 Citation

If you find our work is useful for your research, please consider citing:

```bash
@article{chen2024job,
  title={Job-SDF: A Multi-Granularity Dataset for Job Skill Demand Forecasting and Benchmarking},
  author={Chen, Xi and Qin, Chuan and Fang, Chuyu and Wang, Chao and Zhu, Chen and Zhuang, Fuzhen and Zhu, Hengshu and Xiong, Hui},
  journal={Advances in neural information processing systems},
  year={2024}
}
```
