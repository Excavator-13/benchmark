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

Preparation. All preparation logic lives in `prepare_graph_data.py`, and every path is
resolved relative to the repository, so these commands work from any directory:

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
its results under `results/<mode>/<data_name>/<model_name>/<seed>/`:

```bash
cd benchmark/graph_method
python main.py [-h] [--data_name {r0, r1, ...}]
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

Each run trains on the training split, selects the best checkpoint by validation loss
only, and traverses the test split exactly once after restoring that checkpoint. The
result directory contains `checkpoint.pt` (a versioned `model_state_dict` plus the
configuration, seed and best validation loss), `pred_<t>.pt`, `gold_<t>.pt` and
`metrics.json`. Checkpoints are not pickled model objects, and legacy `model.pt` files
are intentionally not loadable: rerun the experiment to produce `checkpoint.pt`.

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
