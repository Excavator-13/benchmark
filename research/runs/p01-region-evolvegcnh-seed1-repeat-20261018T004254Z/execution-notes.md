# 实际执行命令

§5–§7 的 Python 未从交互终端粘贴 heredoc，而是从本 run 的 guide.md 提取为文件后执行，代码逐字相同（§6 已含 2026-10-18 的 torch.cuda.init() 修复）。

- preflight: awk 提取到 preflight.py → python "$T005_RUN/preflight.py"
- training: awk 提取到 train.py → python -u "$T005_RUN/train.py"
- comparison: awk 提取到 compare.py → python "$T005_RUN/compare.py"
- 每个脚本执行前用 python -c 'compile(...)' 做语法检查，行数分别 170 / 121 / 93。
