import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import networkx as nx
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'STHeiti', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

BASE_DIR = Path(__file__).resolve().parent.parent.parent / "dataset"
GRAPH_DIR = BASE_DIR / "graph"
DEMAND_DIR = BASE_DIR / "demand"
LOW_FREQ_DIR = BASE_DIR / "low_frequency_index"
OUTPUT_DIR = Path(__file__).resolve().parent / "figures"
OUTPUT_DIR.mkdir(exist_ok=True)

MONTH_COLS = [
    "2021-01", "2021-02", "2021-03", "2021-04", "2021-05", "2021-06",
    "2021-07", "2021-08", "2021-09", "2021-10", "2021-11", "2021-12",
    "2022-01", "2022-02", "2022-03", "2022-04", "2022-05", "2022-06",
    "2022-07", "2022-08", "2022-09", "2022-10", "2022-11", "2022-12",
    "2023-01", "2023-02", "2023-03", "2023-04", "2023-05", "2023-06",
    "2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12",
]

QUADRANT_COLORS = {
    "Q1": "#e74c3c",
    "Q2": "#2ecc71",
    "Q3": "#3498db",
    "Q4": "#f39c12",
}


def load_demand_raw(granularity: str) -> pd.DataFrame:
    filepath = DEMAND_DIR / f"{granularity}.parquet"
    df = pd.read_parquet(filepath)
    print(f"  [demand/{granularity}] 原始数据: {len(df)} 行, "
          f"skill_id 数={df['skill_id'].nunique()}, "
          f"r2_id 数={df['r2_id'].nunique()}")
    return df


def load_graph(granularity: str) -> nx.Graph:
    filepath = GRAPH_DIR / f"{granularity}.parquet"
    df = pd.read_parquet(filepath)
    print(f"  [graph/{granularity}] 原始数据: {len(df)} 行, 列: {list(df.columns)}")

    df = df[["row_id", "col_id"]].copy()
    df["u"] = df[["row_id", "col_id"]].min(axis=1)
    df["v"] = df[["row_id", "col_id"]].max(axis=1)
    df = df[df["u"] != df["v"]]

    edge_df = df.groupby(["u", "v"]).size().reset_index(name="weight")
    print(f"  [graph/{granularity}] 去重去自环后: {len(edge_df)} 条无向边")

    G = nx.Graph()
    G.add_weighted_edges_from(zip(edge_df["u"], edge_df["v"], edge_df["weight"]))
    print(f"  [graph/{granularity}] 图: {G.number_of_nodes()} 节点, "
          f"{G.number_of_edges()} 边")
    return G


def compute_skill_sparsity(demand_raw: pd.DataFrame) -> pd.Series:
    per_pair_sparsity = (demand_raw[MONTH_COLS] > 0).sum(axis=1) / len(MONTH_COLS)
    demand_raw = demand_raw.copy()
    demand_raw["_sparsity"] = per_pair_sparsity
    skill_sparsity = demand_raw.groupby("skill_id")["_sparsity"].mean()
    print(f"  [sparsity] 技能级平均稀疏度: min={skill_sparsity.min():.4f}, "
          f"median={skill_sparsity.median():.4f}, max={skill_sparsity.max():.4f}")
    return skill_sparsity


def compute_skill_aggregated_demand(demand_raw: pd.DataFrame) -> pd.DataFrame:
    agg = demand_raw.groupby("skill_id")[MONTH_COLS].sum()
    print(f"  [demand] 按 skill_id 聚合后: {agg.shape[0]} 个技能")
    return agg


def compute_metrics(graph_nodes: list, skill_sparsity: pd.Series,
                    G: nx.Graph) -> pd.DataFrame:
    degree_map = dict(G.degree())

    sparsity_vals = []
    connectivity_vals = []
    for n in graph_nodes:
        sparsity_vals.append(skill_sparsity.get(n, 0.0))
        connectivity_vals.append(degree_map.get(n, 0))

    metrics = pd.DataFrame({
        "skill_id": graph_nodes,
        "sparsity": sparsity_vals,
        "connectivity": connectivity_vals,
    })

    median_sparsity = metrics["sparsity"].median()
    median_connectivity = metrics["connectivity"].median()

    def assign_quadrant(row):
        high_sparse = row["sparsity"] > median_sparsity
        high_conn = row["connectivity"] > median_connectivity
        if high_sparse and not high_conn:
            return "Q1"
        elif high_sparse and high_conn:
            return "Q2"
        elif not high_sparse and not high_conn:
            return "Q3"
        elif not high_sparse and high_conn:
            return "Q4"

    metrics["quadrant"] = metrics.apply(assign_quadrant, axis=1)

    print(f"\n  稀疏度中位数: {median_sparsity:.4f}")
    print(f"  连接度中位数: {median_connectivity:.1f}")
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        count = (metrics["quadrant"] == q).sum()
        q_med_sp = metrics.loc[metrics["quadrant"] == q, "sparsity"].median()
        q_med_conn = metrics.loc[metrics["quadrant"] == q, "connectivity"].median()
        print(f"  {q}: {count} 个节点, 稀疏度中位数={q_med_sp:.4f}, "
              f"连接度中位数={q_med_conn:.1f}")

    return metrics, median_sparsity, median_connectivity


def load_low_freq_skill_ids(granularity: str, demand_raw: pd.DataFrame) -> set:
    filepath = LOW_FREQ_DIR / f"{granularity}.json"
    with open(filepath, "r") as f:
        row_indices = json.load(f)
    low_freq_skills = set(demand_raw.iloc[row_indices]["skill_id"].unique())
    print(f"  [low_freq/{granularity}] {len(row_indices)} 个低频行索引, "
          f"对应 {len(low_freq_skills)} 个唯一技能")
    return low_freq_skills


def evaluate_signals(agg_demand: pd.DataFrame, G: nx.Graph,
                     graph_nodes: list) -> dict:
    neighbor_cache = {}
    neighbor_weight_cache = {}
    for node in graph_nodes:
        if node in G:
            valid_neighbors = []
            valid_weights = []
            for n in G.neighbors(node):
                if n in agg_demand.index:
                    valid_neighbors.append(n)
                    valid_weights.append(G[node][n].get("weight", 1))
            neighbor_cache[node] = valid_neighbors
            neighbor_weight_cache[node] = valid_weights
        else:
            neighbor_cache[node] = []
            neighbor_weight_cache[node] = []

    results = {}
    for skill_id in graph_nodes:
        if skill_id not in agg_demand.index:
            continue
        ts = agg_demand.loc[skill_id].values.astype(float)
        train = ts[:24]
        test = ts[24:]

        train_mean = train.mean()
        if train_mean == 0:
            train_mean = 1.0

        signal_a_pred = np.full(12, train[-1])

        neighbors = neighbor_cache.get(skill_id, [])
        weights = neighbor_weight_cache.get(skill_id, [])
        if neighbors:
            neighbor_train = agg_demand.loc[neighbors].values[:, :24].astype(float)
            neighbor_last = neighbor_train[:, -1]
            neighbor_mean = neighbor_train.mean(axis=1)
            neighbor_mean = np.where(neighbor_mean == 0, 1.0, neighbor_mean)
            neighbor_rates = neighbor_last / neighbor_mean - 1.0
            weights_arr = np.array(weights, dtype=float)
            avg_trend = np.average(neighbor_rates, weights=weights_arr)
            signal_b_pred = np.full(12, train[-1] * (1 + avg_trend))
        else:
            signal_b_pred = np.full(12, train[-1])

        mae_a = np.mean(np.abs(test - signal_a_pred))
        mae_b = np.mean(np.abs(test - signal_b_pred))

        mae_a_rel = mae_a / train_mean
        mae_b_rel = mae_b / train_mean

        results[skill_id] = {
            "mae_a": mae_a,
            "mae_b": mae_b,
            "mae_a_rel": mae_a_rel,
            "mae_b_rel": mae_b_rel,
            "winner": "A" if mae_a < mae_b else "B",
            "winner_rel": "A" if mae_a_rel < mae_b_rel else "B",
            "n_neighbors": len(neighbors),
            "train_mean": train_mean,
        }

    return results


def pick_representatives(metrics: pd.DataFrame, eval_results: dict,
                         n_per_quadrant: int = 5) -> dict:
    representatives = {}
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        q_nodes = metrics[metrics["quadrant"] == q]["skill_id"].tolist()
        candidates = []
        for nid in q_nodes:
            if nid in eval_results:
                r = eval_results[nid]
                margin = abs(r["mae_a_rel"] - r["mae_b_rel"])
                candidates.append((nid, r["mae_a"], r["mae_b"],
                                   r["mae_a_rel"], r["mae_b_rel"], margin))
        candidates.sort(key=lambda x: x[5], reverse=True)
        reps = candidates[:n_per_quadrant]
        representatives[q] = reps
        print(f"\n  {q} 代表节点 (共 {len(candidates)} 个候选):")
        for nid, mae_a, mae_b, mae_a_r, mae_b_r, margin in reps:
            winner_r = "A" if mae_a_r < mae_b_r else "B"
            print(f"    skill_{nid}: MAE_A={mae_a:.1f}, MAE_B={mae_b:.1f}, "
                  f"Rel: MAE_A={mae_a_r:.4f}, MAE_B={mae_b_r:.4f}, "
                  f"胜者(Rel)={winner_r}")
    return representatives


def plot_quadrant_scatter(metrics: pd.DataFrame, median_sparsity: float,
                          median_connectivity: float, low_freq_skills: set,
                          granularity: str):
    fig, ax = plt.subplots(figsize=(10, 8))

    for q, color in QUADRANT_COLORS.items():
        mask = metrics["quadrant"] == q
        ax.scatter(
            metrics.loc[mask, "sparsity"],
            metrics.loc[mask, "connectivity"],
            c=color, alpha=0.6, s=40, edgecolors="white", linewidth=0.5,
            label=f"{q} (n={mask.sum()})",
        )

    ax.axvline(x=median_sparsity, color="gray", linestyle="--",
               linewidth=1.2, alpha=0.7)
    ax.axhline(y=median_connectivity, color="gray", linestyle="--",
               linewidth=1.2, alpha=0.7)

    low_mask = metrics["skill_id"].isin(low_freq_skills)
    if low_mask.any():
        ax.scatter(
            metrics.loc[low_mask, "sparsity"],
            metrics.loc[low_mask, "connectivity"],
            marker="*", s=80, c="black", alpha=0.8,
            edgecolors="white", linewidth=0.3,
            label=f"低频索引标记 (n={low_mask.sum()})",
        )

    ax.set_xlabel("稀疏度 (各子类非零月份占比均值)", fontsize=13)
    ax.set_ylabel("连接度 (邻居数量)", fontsize=13)
    ax.set_title(f"四象限分布分析 — {granularity} 粒度", fontsize=15, fontweight="bold")

    q_labels = {
        "Q1": "高稀疏·低连接",
        "Q2": "高稀疏·高连接\n(图信号预期优)",
        "Q3": "低稀疏·低连接\n(自身时序预期优)",
        "Q4": "低稀疏·高连接",
    }
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()

    q_positions = {
        "Q1": (x_min + 0.02, y_max - 0.02),
        "Q2": (x_max - 0.02, y_max - 0.02),
        "Q3": (x_min + 0.02, y_min + 0.02),
        "Q4": (x_max - 0.02, y_min + 0.02),
    }
    q_align = {
        "Q1": ("left", "top"),
        "Q2": ("right", "top"),
        "Q3": ("left", "bottom"),
        "Q4": ("right", "bottom"),
    }

    for q, (x, y) in q_positions.items():
        ha, va = q_align[q]
        ax.text(x, y, q_labels[q], fontsize=10, ha=ha, va=va,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor=QUADRANT_COLORS[q], alpha=0.85))

    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "quadrant_scatter.png", dpi=150, bbox_inches="tight")
    print(f"\n四象限散点图已保存至: {OUTPUT_DIR / 'quadrant_scatter.png'}")
    plt.close(fig)


def plot_signal_comparison(representatives: dict, granularity: str):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes_flat = axes.flatten()
    q_order = ["Q1", "Q2", "Q3", "Q4"]

    for idx, q in enumerate(q_order):
        ax = axes_flat[idx]
        reps = representatives[q]
        if not reps:
            ax.set_title(f"{q} (无代表节点)")
            ax.text(0.5, 0.5, "无数据", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14, color="gray")
            continue

        n_reps = len(reps)
        x = np.arange(n_reps)
        width = 0.35

        mae_a = [r[3] for r in reps]
        mae_b = [r[4] for r in reps]
        labels = [f"skill_{r[0]}" for r in reps]

        bars_a = ax.bar(x - width / 2, mae_a, width, label="信号A (自身时序)",
                        color="#e74c3c", alpha=0.85)
        bars_b = ax.bar(x + width / 2, mae_b, width, label="信号B (图邻居趋势)",
                        color="#3498db", alpha=0.85)

        y_max = max(max(mae_a), max(mae_b)) * 1.15 if (mae_a or mae_b) else 1
        for bar in bars_a:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., h + y_max * 0.01,
                    f"{h:.3f}", ha="center", va="bottom", fontsize=7, color="#e74c3c")
        for bar in bars_b:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., h + y_max * 0.01,
                    f"{h:.3f}", ha="center", va="bottom", fontsize=7, color="#3498db")

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("相对 MAE (MAE/均值)", fontsize=11)
        ax.set_title(f"{q}", fontsize=13, fontweight="bold", color=QUADRANT_COLORS[q])
        ax.legend(fontsize=8)

    fig.suptitle(f"四象限代表节点信号对比 (相对MAE) — {granularity} 粒度",
                 fontsize=15, fontweight="bold")
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "signal_comparison.png", dpi=150, bbox_inches="tight")
    print(f"信号对比图已保存至: {OUTPUT_DIR / 'signal_comparison.png'}")
    plt.close(fig)


def plot_summary(metrics: pd.DataFrame, eval_results: dict, granularity: str):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    q_order = ["Q1", "Q2", "Q3", "Q4"]
    q_mae_a = []
    q_mae_b = []
    q_win_rate_b = []

    for q in q_order:
        q_nodes = metrics[metrics["quadrant"] == q]["skill_id"].tolist()
        mae_a_vals = []
        mae_b_vals = []
        b_wins = 0
        total = 0
        for nid in q_nodes:
            if nid in eval_results:
                r = eval_results[nid]
                mae_a_vals.append(r["mae_a_rel"])
                mae_b_vals.append(r["mae_b_rel"])
                if r["winner_rel"] == "B":
                    b_wins += 1
                total += 1
        q_mae_a.append(np.mean(mae_a_vals) if mae_a_vals else 0)
        q_mae_b.append(np.mean(mae_b_vals) if mae_b_vals else 0)
        q_win_rate_b.append(b_wins / total * 100 if total > 0 else 0)

    x = np.arange(4)
    width = 0.3

    ax1 = axes[0]
    bars_a = ax1.bar(x - width / 2, q_mae_a, width, label="信号A (自身时序)",
                     color="#e74c3c", alpha=0.85)
    bars_b = ax1.bar(x + width / 2, q_mae_b, width, label="信号B (图邻居趋势)",
                     color="#3498db", alpha=0.85)
    y_max_mae = max(max(q_mae_a), max(q_mae_b)) * 1.15 if (q_mae_a or q_mae_b) else 1
    for bar in bars_a:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2., h + y_max_mae * 0.01,
                 f"{h:.3f}", ha="center", va="bottom", fontsize=8, color="#e74c3c")
    for bar in bars_b:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2., h + y_max_mae * 0.01,
                 f"{h:.3f}", ha="center", va="bottom", fontsize=8, color="#3498db")
    ax1.set_xticks(x)
    ax1.set_xticklabels(q_order, fontsize=11)
    ax1.set_ylabel("平均相对 MAE", fontsize=12)
    ax1.set_title("各象限平均相对 MAE 对比", fontsize=13, fontweight="bold")
    ax1.legend(fontsize=9)

    ax2 = axes[1]
    bar_colors = [QUADRANT_COLORS[q] for q in q_order]
    bars = ax2.bar(q_order, q_win_rate_b, color=bar_colors, alpha=0.85,
                   edgecolor="white")
    for bar, rate in zip(bars, q_win_rate_b):
        ax2.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 1,
                 f"{rate:.1f}%", ha="center", va="bottom", fontsize=11,
                 fontweight="bold")
    ax2.axhline(y=50, color="gray", linestyle="--", linewidth=1, alpha=0.5)
    ax2.set_ylabel("信号B胜出比例 (%)", fontsize=12)
    ax2.set_title("各象限信号B胜出比例 (相对MAE)", fontsize=13, fontweight="bold")
    ax2.set_ylim(0, 110)

    fig.suptitle(f"四象限汇总分析 (相对MAE) — {granularity} 粒度",
                 fontsize=15, fontweight="bold")
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "summary_table.png", dpi=150, bbox_inches="tight")
    print(f"汇总图已保存至: {OUTPUT_DIR / 'summary_table.png'}")
    plt.close(fig)


def main():
    granularity = "r2"

    print("=" * 60)
    print(f"  四象限分布分析 — {granularity} 粒度")
    print("  验证假设: 稀疏节点依赖图邻居, 稠密节点依赖自身历史")
    print("=" * 60)

    print("\n[1/6] 加载数据...")
    demand_raw = load_demand_raw(granularity)
    G = load_graph(granularity)

    graph_nodes = sorted(G.nodes())
    print(f"\n  图节点数: {len(graph_nodes)}")
    print(f"  需求数据中技能数: {demand_raw['skill_id'].nunique()}")
    graph_in_demand = [n for n in graph_nodes
                       if n in demand_raw["skill_id"].values]
    print(f"  图中且在需求数据中的技能: {len(graph_in_demand)}")

    print("\n[2/6] 计算技能级稀疏度 (每子类稀疏度 → 按技能平均)...")
    skill_sparsity = compute_skill_sparsity(demand_raw)

    print("\n[3/6] 聚合需求数据 (按 skill_id 求和)...")
    agg_demand = compute_skill_aggregated_demand(demand_raw)

    print("\n[4/6] 计算四象限指标 (仅图中的 314 个节点)...")
    metrics, median_sparsity, median_connectivity = compute_metrics(
        graph_nodes, skill_sparsity, G)

    print("\n[5/6] 加载低频索引并评估信号...")
    low_freq_skills = load_low_freq_skill_ids(granularity, demand_raw)
    eval_results = evaluate_signals(agg_demand, G, graph_nodes)

    print(f"  评估完成: {len(eval_results)} 个节点")

    print("\n[6/6] 挑选代表节点并生成可视化...")
    representatives = pick_representatives(metrics, eval_results, n_per_quadrant=5)

    plot_quadrant_scatter(metrics, median_sparsity, median_connectivity,
                          low_freq_skills, granularity)
    plot_signal_comparison(representatives, granularity)
    plot_summary(metrics, eval_results, granularity)

    print("\n" + "=" * 60)
    print("  分析结论 (相对 MAE = MAE / 训练集均值)")
    print("=" * 60)

    q_order = ["Q1", "Q2", "Q3", "Q4"]
    q_labels_full = {
        "Q1": "高稀疏·低连接",
        "Q2": "高稀疏·高连接 (预期: 信号B > 信号A)",
        "Q3": "低稀疏·低连接 (预期: 信号A > 信号B)",
        "Q4": "低稀疏·高连接",
    }

    for q in q_order:
        q_nodes = metrics[metrics["quadrant"] == q]["skill_id"].tolist()
        mae_a_vals = []
        mae_b_vals = []
        b_wins = 0
        total = 0
        for nid in q_nodes:
            if nid in eval_results:
                r = eval_results[nid]
                mae_a_vals.append(r["mae_a_rel"])
                mae_b_vals.append(r["mae_b_rel"])
                if r["winner_rel"] == "B":
                    b_wins += 1
                total += 1
        avg_a = np.mean(mae_a_vals) if mae_a_vals else 0
        avg_b = np.mean(mae_b_vals) if mae_b_vals else 0
        win_rate = b_wins / total * 100 if total > 0 else 0
        better = "信号B" if avg_b < avg_a else "信号A"
        print(f"\n  {q} ({q_labels_full[q]}):")
        print(f"    节点数: {total}")
        print(f"    平均 Rel_MAE_A: {avg_a:.4f}, 平均 Rel_MAE_B: {avg_b:.4f}")
        print(f"    信号B 胜出: {b_wins}/{total} ({win_rate:.1f}%)")
        print(f"    整体更优: {better}")

    print("\n" + "=" * 60)
    print("  假设验证")
    print("=" * 60)

    q2_nodes = metrics[metrics["quadrant"] == "Q2"]["skill_id"].tolist()
    q3_nodes = metrics[metrics["quadrant"] == "Q3"]["skill_id"].tolist()

    q2_b_wins_rel = sum(1 for nid in q2_nodes
                        if nid in eval_results and eval_results[nid]["winner_rel"] == "B")
    q2_total = sum(1 for nid in q2_nodes if nid in eval_results)

    q3_a_wins_rel = sum(1 for nid in q3_nodes
                        if nid in eval_results and eval_results[nid]["winner_rel"] == "A")
    q3_total = sum(1 for nid in q3_nodes if nid in eval_results)

    if q2_total > 0:
        print(f"\n  Q2 (高稀疏·高连接):")
        print(f"    信号B 胜出 {q2_b_wins_rel}/{q2_total} "
              f"({q2_b_wins_rel/q2_total*100:.1f}%)")

    if q3_total > 0:
        print(f"  Q3 (低稀疏·低连接):")
        print(f"    信号A 胜出 {q3_a_wins_rel}/{q3_total} "
              f"({q3_a_wins_rel/q3_total*100:.1f}%)")

    if q2_total > 0 and q3_total > 0:
        q2_b_rate = q2_b_wins_rel / q2_total
        q3_a_rate = q3_a_wins_rel / q3_total
        if q2_b_rate > 0.5 and q3_a_rate > 0.5:
            print("\n  ✅ 假设成立: 稀疏节点依赖图邻居, 稠密节点依赖自身历史")
        elif q2_b_rate > 0.5:
            print("\n  ⚠️ 部分成立: 稀疏节点依赖图邻居得到验证, "
                  "但稠密节点自身时序优势不明显")
        elif q3_a_rate > 0.5:
            print("\n  ⚠️ 部分成立: 稠密节点依赖自身历史得到验证, "
                  "但稀疏节点图邻居优势不明显")
        else:
            print("\n  ❌ 假设未得到支持, 需要进一步分析")
    elif q2_total == 0:
        print("\n  ⚠️ Q2 无节点, 无法验证稀疏节点假设。")
    elif q3_total == 0:
        print("\n  ⚠️ Q3 无节点, 无法验证稠密节点假设。")

    print("\n完成!")


if __name__ == "__main__":
    main()