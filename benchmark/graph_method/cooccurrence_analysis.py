import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'STHeiti', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

DATASET_DIR = Path(__file__).resolve().parent.parent.parent / "dataset" / "graph"

GRANULARITIES = ["r0", "r1", "r2", "r1-region", "r2-region", "region", "company"]
GRANULARITY_LABELS = {
    "r0": "r0 (粗)",
    "r1": "r1 (中)",
    "r2": "r2 (细)",
    "r1-region": "r1-region",
    "r2-region": "r2-region",
    "region": "region",
    "company": "company (最细)",
}

COLORS = ["#e74c3c", "#f39c12", "#2ecc71", "#3498db", "#9b59b6", "#1abc9c", "#e67e22"]


def load_and_build_graph(granularity: str) -> nx.Graph:
    filepath = DATASET_DIR / f"{granularity}.parquet"
    df = pd.read_parquet(filepath)

    print(f"  [{granularity}] 原始数据: {len(df)} 行, 列: {list(df.columns)}")

    df = df[["row_id", "col_id"]].copy()

    df["u"] = df[["row_id", "col_id"]].min(axis=1)
    df["v"] = df[["row_id", "col_id"]].max(axis=1)

    df = df[df["u"] != df["v"]]

    edge_df = df.groupby(["u", "v"]).size().reset_index(name="weight")
    print(f"  [{granularity}] 去重去自环后: {len(edge_df)} 条无向边")

    G = nx.Graph()
    G.add_weighted_edges_from(
        zip(edge_df["u"], edge_df["v"], edge_df["weight"])
    )
    return G


def analyze_graph(G: nx.Graph, granularity: str):
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    degrees = [d for _, d in G.degree()]
    avg_degree = np.mean(degrees) if degrees else 0.0
    median_degree = np.median(degrees) if degrees else 0.0
    max_degree = max(degrees) if degrees else 0

    weights = np.array([d["weight"] for _, _, d in G.edges(data=True)])
    mean_weight = np.mean(weights) if len(weights) > 0 else 0.0
    median_weight = np.median(weights) if len(weights) > 0 else 0.0
    max_weight = np.max(weights) if len(weights) > 0 else 0

    low_weight_1 = np.sum(weights <= 1) / len(weights) * 100 if len(weights) > 0 else 0
    low_weight_2 = np.sum(weights <= 2) / len(weights) * 100 if len(weights) > 0 else 0
    low_weight_5 = np.sum(weights <= 5) / len(weights) * 100 if len(weights) > 0 else 0

    print(f"\n{'='*60}")
    print(f"  粒度: {GRANULARITY_LABELS[granularity]}")
    print(f"{'='*60}")
    print(f"  节点数:            {n_nodes}")
    print(f"  边总数:            {n_edges}")
    print(f"  平均节点度:         {avg_degree:.2f}")
    print(f"  中位数节点度:       {median_degree:.1f}")
    print(f"  最大节点度:         {max_degree}")
    print(f"  边权重均值:         {mean_weight:.2f}")
    print(f"  边权重中位数:       {median_weight:.1f}")
    print(f"  边权重最大值:       {max_weight}")
    print(f"  权重≤1 的边占比:    {low_weight_1:.1f}%")
    print(f"  权重≤2 的边占比:    {low_weight_2:.1f}%")
    print(f"  权重≤5 的边占比:    {low_weight_5:.1f}%")

    return {
        "granularity": granularity,
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "avg_degree": avg_degree,
        "median_degree": median_degree,
        "max_degree": max_degree,
        "mean_weight": mean_weight,
        "median_weight": median_weight,
        "max_weight": max_weight,
        "low_weight_1_pct": low_weight_1,
        "low_weight_2_pct": low_weight_2,
        "low_weight_5_pct": low_weight_5,
        "weights": weights,
        "degrees": np.array(degrees),
    }


def plot_results(results: list[dict]):
    n = len(results)
    output_dir = Path(__file__).resolve().parent / "figures"
    output_dir.mkdir(exist_ok=True)

    ncols = 4
    nrows_hist = (n + ncols - 1) // ncols

    fig1, axes1 = plt.subplots(nrows_hist * 2, ncols, figsize=(4 * ncols, 4 * nrows_hist * 2))
    for i, (res, color) in enumerate(zip(results, COLORS)):
        row = (i // ncols) * 2
        col = i % ncols
        label = GRANULARITY_LABELS[res["granularity"]]

        ax_log = axes1[row, col]
        ax_log.hist(res["weights"], bins=80, color=color, alpha=0.75,
                    edgecolor="white", log=True)
        ax_log.axvline(x=1, color="black", linestyle="--", linewidth=1, alpha=0.4)
        ax_log.axvline(x=2, color="black", linestyle="--", linewidth=1, alpha=0.4)
        ax_log.set_title(f"{label}\n边权重分布 (log scale)", fontsize=10)
        ax_log.set_xlabel("边权重")
        ax_log.set_ylabel("边数量 (log)")
        ax_log.set_xlim(0, max(50, np.percentile(res["weights"], 99)))

        ax_zoom = axes1[row + 1, col]
        ax_zoom.hist(res["weights"], bins=80, color=color, alpha=0.75,
                     edgecolor="white", range=(0, 20))
        ax_zoom.axvline(x=1, color="black", linestyle="--", linewidth=1, alpha=0.4)
        ax_zoom.axvline(x=2, color="black", linestyle="--", linewidth=1, alpha=0.4)
        ax_zoom.set_title(f"{label}\n边权重分布 (0-20 局部)", fontsize=10)
        ax_zoom.set_xlabel("边权重")
        ax_zoom.set_ylabel("边数量")

    for j in range(i + 1, nrows_hist * ncols):
        row = (j // ncols) * 2
        col = j % ncols
        axes1[row, col].set_visible(False)
        axes1[row + 1, col].set_visible(False)

    plt.tight_layout()
    fig1.savefig(output_dir / "edge_weight_distribution.png", dpi=150)
    print(f"\n边权重分布图已保存至: {output_dir / 'edge_weight_distribution.png'}")
    plt.close(fig1)

    nrows_cdf = (n + ncols - 1) // ncols
    fig2, axes2 = plt.subplots(nrows_cdf, ncols, figsize=(4 * ncols, 3.5 * nrows_cdf))
    if nrows_cdf == 1:
        axes2 = np.array([axes2])
    for i, (res, color) in enumerate(zip(results, COLORS)):
        row = i // ncols
        col = i % ncols
        ax = axes2[row, col]
        label = GRANULARITY_LABELS[res["granularity"]]
        weights = res["weights"]
        cumulative = np.arange(1, len(weights) + 1) / len(weights) * 100
        sorted_weights = np.sort(weights)
        ax.plot(sorted_weights, cumulative, color=color, linewidth=2)
        ax.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.4)
        ax.axhline(y=90, color="gray", linestyle="--", linewidth=0.8, alpha=0.4)
        ax.set_title(f"{label}\n边权重累计分布 (CDF)", fontsize=10)
        ax.set_xlabel("边权重")
        ax.set_ylabel("累计占比 (%)")
        ax.set_xlim(0, 50)
    for j in range(i + 1, nrows_cdf * ncols):
        axes2[j // ncols, j % ncols].set_visible(False)
    plt.tight_layout()
    fig2.savefig(output_dir / "edge_weight_cdf.png", dpi=150)
    print(f"边权重CDF图已保存至: {output_dir / 'edge_weight_cdf.png'}")
    plt.close(fig2)

    fig3, ax3 = plt.subplots(figsize=(14, 5))
    x = np.arange(n)
    width = 0.25

    low1 = [r["low_weight_1_pct"] for r in results]
    low2 = [r["low_weight_2_pct"] for r in results]
    low5 = [r["low_weight_5_pct"] for r in results]

    bars1 = ax3.bar(x - width, low1, width, label="权重≤1", color="#e74c3c", alpha=0.85)
    bars2 = ax3.bar(x, low2, width, label="权重≤2", color="#f39c12", alpha=0.85)
    bars3 = ax3.bar(x + width, low5, width, label="权重≤5", color="#2ecc71", alpha=0.85)

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0.5:
                ax3.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + 0.5,
                    f"{height:.1f}%",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                )

    ax3.set_xticks(x)
    ax3.set_xticklabels([GRANULARITY_LABELS[g] for g in GRANULARITIES], fontsize=9)
    ax3.set_ylabel("占比 (%)")
    ax3.set_title("低权重边占比对比 (全粒度)")
    ax3.legend()
    ax3.set_ylim(0, 105)

    plt.tight_layout()
    fig3.savefig(output_dir / "low_weight_comparison.png", dpi=150)
    print(f"低权重边对比图已保存至: {output_dir / 'low_weight_comparison.png'}")
    plt.close(fig3)


def main():
    print("=" * 60)
    print("  多粒度共现图统计分析 (全 7 个粒度)")
    print("  粒度: r0 → r1 → r2 → r1-region → r2-region → region → company")
    print("=" * 60)

    results = []
    for granularity in GRANULARITIES:
        print(f"\n--- 加载 {granularity} ---")
        G = load_and_build_graph(granularity)
        res = analyze_graph(G, granularity)
        results.append(res)

    print("\n" + "=" * 90)
    print("  汇总对比表")
    print("=" * 90)
    header = f"{'指标':<22}"
    for g in GRANULARITIES:
        header += f" {GRANULARITY_LABELS[g]:<16}"
    print(header)
    print("-" * (22 + 16 * len(GRANULARITIES)))

    rows = [
        ("节点数", "n_nodes"),
        ("边总数", "n_edges"),
        ("平均节点度", "avg_degree"),
        ("边权重均值", "mean_weight"),
        ("边权重中位数", "median_weight"),
        ("权重≤1占比(%)", "low_weight_1_pct"),
        ("权重≤2占比(%)", "low_weight_2_pct"),
        ("权重≤5占比(%)", "low_weight_5_pct"),
    ]
    for label, key in rows:
        line = f"{label:<22}"
        for r in results:
            v = r[key]
            if isinstance(v, float):
                line += f" {v:<16.2f}"
            else:
                line += f" {str(v):<16}"
        print(line)

    plot_results(results)

    print("\n分析完成。")


if __name__ == "__main__":
    main()