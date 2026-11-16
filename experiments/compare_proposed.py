"""So sánh thuật toán đề xuất (calib-ifair) và hai bản tách thành phần với các baseline, đo bằng NS-3 LTE.

python experiments/compare_proposed.py experiments/results/proposed
Đọc summary_ns3.csv của: ns3-demand-lte (kmeans-equal, PF), ns3-demand-wpf-lte (kmeans-maxmin, hover-maxmin, WPF),
ns3-proposed-lte (calib-ifair, kmeans-ifair, calib-equal, WPF). Cùng cấu hình (3 UAV, 20 user, 60 khe, 3 seed),
cùng lưu lượng, nên ghép cặp được theo (lưu lượng, seed). Ghi <out>.csv, <out>.png.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = Path(__file__).parent / "results"
SOURCES = {"ns3-demand-lte": ["kmeans-equal"], "ns3-demand-wpf-lte": ["kmeans-maxmin"],
           "ns3-proposed-lte": ["kmeans-ifair", "calib-equal", "calib-ifair"]}
BASE = "kmeans-equal"
ORDER = ["kmeans-equal", "kmeans-maxmin", "kmeans-ifair", "calib-equal", "calib-ifair"]
LABEL = {"kmeans-equal": "kmeans-equal (PF)", "kmeans-maxmin": "kmeans-maxmin (WPF)",
         "kmeans-ifair": "kmeans-ifair (WPF)", "calib-equal": "calib-equal (WPF)", "calib-ifair": "calib-ifair (WPF, đề xuất)"}
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e34948"]
METRICS = [("ns3_min_mbps", "Min throughput (Mbps)", False), ("ns3_sum_mbps", "Throughput tổng (Mbps)", False),
           ("ns3_delay_ms", "Độ trễ (ms, thang log)", True), ("ns3_loss", "Mất gói (%)", False)]


def load():
    rows = defaultdict(dict)  # (algo, demand, seed) -> row
    for d, algos in SOURCES.items():
        with open(R / d / "summary_ns3.csv") as f:
            for r in csv.DictReader(f):
                if r["algo"] in algos:
                    rows[r["algo"]][(float(r["offered_per_user_mbps"]), int(r["seed"]))] = {k: float(r[k]) for k in r
                                                                                           if k not in ("algo",)}
    return rows


def main(out):
    rows = load()
    keys = sorted(rows[BASE])
    for a in ORDER:
        assert set(rows[a]) == set(keys), f"{a}: thiếu run so với {BASE}"
    demands = sorted({d for d, _ in keys})
    with open(Path(out).with_suffix(".csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["algo", "demand_mbps", *[m for m, *_ in METRICS], "min_ratio_vs_base", "min_wins_vs_base"])
        for a in ORDER:
            for d in demands:
                ks = [k for k in keys if k[0] == d]
                mean = [np.mean([rows[a][k][m] for k in ks]) for m, *_ in METRICS]
                ratio = np.mean([rows[a][k]["ns3_min_mbps"] / rows[BASE][k]["ns3_min_mbps"] for k in ks])
                wins = sum(rows[a][k]["ns3_min_mbps"] > rows[BASE][k]["ns3_min_mbps"] for k in ks)
                w.writerow([a, d, *[f"{v:.4g}" for v in mean], f"{ratio:.3f}", f"{wins}/{len(ks)}"])

    fig, axes = plt.subplots(1, 4, figsize=(17, 4.4), facecolor="#fcfcfb")
    for ax, (m, title, log) in zip(axes, METRICS):
        for i, a in enumerate(ORDER):
            y = [np.mean([rows[a][k][m] for k in keys if k[0] == d]) * (100 if m == "ns3_loss" else 1) for d in demands]
            ax.plot(demands, y, marker="o", ms=5, lw=2.6 if a == "calib-ifair" else 1.6, color=COLORS[i], label=LABEL[a])
        ax.set(title=title, xlabel="lưu lượng mỗi user (Mbps)", facecolor="#fcfcfb")
        if log:
            ax.set_yscale("log")
        ax.grid(color="#e4e3df", lw=0.8)
        ax.spines[["top", "right"]].set_visible(False)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.suptitle("NS-3 LTE, 3 UAV, 20 user, 60 khe, trung bình 3 seed", y=0.9, fontsize=10, color="#52514e")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.savefig(Path(out).with_suffix(".png"), dpi=150, facecolor=fig.get_facecolor())
    print(f"Đã ghi {Path(out).with_suffix('.csv')} và {Path(out).with_suffix('.png')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
