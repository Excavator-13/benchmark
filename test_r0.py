import pandas as pd
from pathlib import Path

# 指向你的 graph 目录
GRAPH_DIR = Path("/Users/watuji/大创/代码仓库/benchmark/dataset/graph")

# 我们要看的粒度
granularities = ["r0", "r1", "r2"]

for g in granularities:
    file_path = GRAPH_DIR / f"{g}.parquet"
    df = pd.read_parquet(file_path)
    
    # 这一列的名字就是 r0_id, r1_id, r2_id
    id_col = f"{g}_id"
    
    print(f"\n{'='*50}")
    print(f"文件: {g}.parquet")
    print(f"总行数: {len(df)}")
    print(f"列名: {list(df.columns)}")
    
    # 检查 ID 列的具体情况
    unique_vals = df[id_col].unique()
    print(f"'{id_col}' 的唯一值个数: {len(unique_vals)}")
    print(f"'{id_col}' 的最小值: {df[id_col].min()}")
    print(f"'{id_col}' 的最大值: {df[id_col].max()}")
    
    # 看看前 10 个值长什么样
    print(f"前10个值: {df[id_col].head(10).tolist()}")
    
    # 判断是否全是 0
    if df[id_col].nunique() == 1 and df[id_col].iloc[0] == 0:
        print("✅ 结论: 这一列全是 0！")
    else:
        print(f"⚠️ 结论: 这一列有 {df[id_col].nunique()} 种不同的 ID。")

    # 顺便看看核心的边数据（row_id, col_id）是否一致
    # 为了更有趣，可以随机抽一条边的 row_id, col_id 看看
    
print("\n" + "="*50)
print("检查完毕！")