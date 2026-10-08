# EvolveGCN 路径已核实的问题

优先级含义如下：**致命**会阻止程序运行或使模型不再是论文所称方法；**高**会使实验指标失去可信度或在常用配置下失败；**中**会造成结果、可复现性或维护风险；**可选**主要是文档和代码质量问题。

## 致命

### 1. `DatasetLoader` 不存在，主程序无法启动

- 位置：[benchmark/graph_method/main.py:5](benchmark/graph_method/main.py#L5)
- 代码导入 `from dataset import DatasetLoader`，但仓库没有 `dataset.py`、`dataset/` 包或 `DatasetLoader` 定义，依赖文件也没有提供该模块。
- 因此 fresh clone 执行主程序会在导入阶段抛出 `ModuleNotFoundError`，后续训练逻辑无法到达。

### 2. 图预处理读取了不存在的目录

- 位置：[benchmark/graph_method/data_process.ipynb](benchmark/graph_method/data_process.ipynb)
- notebook 使用 `../../dataset/rate` 和 `../../dataset/count`；仓库实际目录是 `dataset/proportion` 和 `dataset/demand`。
- 按 README 运行预处理会直接产生 `FileNotFoundError`。

### 3. 预处理只生成 `company`，与默认运行参数不匹配

- notebook 将 `data_name` 硬编码为 `['company']`。
- 主程序默认 `--data_name r0`，README 也宣称支持多个粒度；因此默认命令没有对应的图数据。

### 4. 预处理没有创建输出目录

- notebook 直接写入 `data/{mode}/{data_name}.json`，仓库没有 `data/` 目录，也没有 `os.makedirs`。
- 在目录不存在的 fresh clone 中，写文件会抛出 `FileNotFoundError`。

### 5. EvolveGCNH 丢弃了 GRU 产生的新权重

- 位置：[benchmark/graph_method/models/evolvegcnh.py:95-102](benchmark/graph_method/models/evolvegcnh.py#L95)
- `W` 由 GRU 更新后只传给当前卷积，没有写回 `self.weight`。下一次 forward 又从同一个初始权重开始。
- 实际行为是 `W_t = GRU(H_t, W_0)`，而不是 EvolveGCN-H 要求的 `W_t = GRU(H_t, W_{t-1})`；模型没有实现跨时间的权重演化。

### 6. `initial_weight.data` 切断了初始权重的梯度

- 位置：[benchmark/graph_method/models/evolvegcnh.py:95-97](benchmark/graph_method/models/evolvegcnh.py#L95)
- `self.initial_weight` 是 `Parameter`，但首次 forward 使用 `self.initial_weight.data`。`.data` 脱离 autograd，导致该参数不获得训练梯度；优化器虽然包含它，却无法学习初始权重。

## 高

### 7. 使用测试集选择最佳模型，造成测试集泄漏

- 位置：[benchmark/graph_method/main.py:145-164](benchmark/graph_method/main.py#L145)
- 每个 epoch 都在 `test_dataset` 上计算损失，并用该损失决定是否保存 checkpoint；训练结束又在同一测试集上报告 RMSE/MAE。
- 测试集不再是独立评估集，报告指标会产生选择偏差。应使用 `eval_dataset` 选模，测试集只评估一次。

### 8. `eval_dataset` 被切分但完全没有使用

- 位置：[benchmark/graph_method/main.py:46](benchmark/graph_method/main.py#L46)
- 这直接导致上一条测试集选模问题，也使验证集形同虚设。

### 9. 训练、测试和最终评估的设备迁移不一致

- 训练循环把 snapshot 移到 `args.device`，测试循环和最终评估没有执行 `.to(args.device)`。
- 使用 `--device cuda` 时，模型参数在 GPU 而测试张量仍在 CPU，会触发 device mismatch。

### 10. 命令行 `--seed` 被覆盖且没有设置随机源

- 位置：[benchmark/graph_method/main.py:37,115-116](benchmark/graph_method/main.py#L37)
- 用户传入的 seed 被 `for seed in range(2): args.seed = seed` 覆盖，只会运行 0 和 1。
- 代码没有设置 Python、NumPy、Torch 或 CUDA 随机种子，因此两个运行结果不可复现；`range(2)` 也把实验次数硬编码为 2。

## 中

### 11. 图共现频率在预处理阶段被丢弃

- 位置：[benchmark/graph_method/data_process.ipynb](benchmark/graph_method/data_process.ipynb)
- README 将图描述为带共现频率的三元组，但 notebook 只保留 `row_id`、`col_id` 并写入 `edges`，没有保存频率或 `edge_weight`。
- 因而即使后续 loader 存在，也无法从该预处理产物恢复 README 所述的加权图；模型实际使用的图与数据说明不一致。

### 12. 模型状态 `self.weight` 没有被注册或序列化

- 位置：[benchmark/graph_method/models/evolvegcnh.py:47](benchmark/graph_method/models/evolvegcnh.py#L47)
- `self.weight` 是普通 Python 属性，不是 `Parameter` 或 registered buffer，不会出现在 `state_dict`，也不会被 `reset_parameters()` 或 `.to(device)` 管理。
- 当前代码因上一问题尚未更新它；一旦修复权重演化，状态会跨 epoch、验证和测试继续累积，且标准 checkpoint 会丢失该状态，必须提供显式 reset 和保存/加载方案。

### 13. 直接保存整个模型对象，加载依赖源码路径和运行环境

- 位置：[benchmark/graph_method/main.py:161,166](benchmark/graph_method/main.py#L161)
- 使用 `torch.save(model, ...)` / `torch.load(...)`，而不是 `state_dict`；模型类定义在脚本的 `__main__` 中，代码移动或环境变化后可能无法反序列化。
- `torch.load` 也没有 `map_location`，跨 CPU/GPU 环境加载存在设备错误风险。

## 可选

### 14. README 参数名与实现不一致

- README 示例使用 `--model`，而 [main.py:35](benchmark/graph_method/main.py#L35) 只定义 `--model_name`；按文档执行会得到 `unrecognized arguments`。

### 15. README 的 Conda 创建命令错误

- README 使用 `conda create -n python3.8 Job-SDF`，这会把 `Job-SDF` 当作待安装包，而不是创建 Python 3.8 环境。
- 应明确写成类似 `conda create -n Job-SDF python=3.8`。

### 16. `hidden_dim` 对 EvolveGCNH 不生效

- [main.py:39](benchmark/graph_method/main.py#L39) 暴露 `--hidden_dim`，但 [main.py:64](benchmark/graph_method/main.py#L64) 构造 EvolveGCNH 时只传入 `num_nodes` 和 `periods`；其 GRU hidden size 固定为 `periods`。
- 该参数对 EvolveGCNH 是误导性的，应删除、传递或在文档中明确说明。

### 17. `temporal_signal_split` 的 docstring 与实际返回值不一致

- 文档写返回两个 iterator，函数实际返回 train、eval、test 三个 iterator。
- 这是维护性问题，不改变当前运行结果。
