"""Vẽ lại kết quả E10, E11 cho slide: chữ to, ít ô hơn hình trong báo cáo.

python experiments/plot_slides.py
Đọc experiments/results/proposed.csv và classes.csv (đã tổng hợp sẵn), ghi proposed_slide.png và classes_slide.png
cùng thư mục.
"""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = Path(__file__).parent / "results"
plt.rcParams.update({"font.size": 13, "axes.titlesize": 14, "legend.fontsize": 12})


def load(name):
    d = defaultdict(dict)
    for r in csv.DictReader(open(R / name)):
        d[r["algo"]][float(r["demand_mbps"])] = {k: float(v) for k, v in r.items() if k not in ("algo", "min_wins_vs_base")}
    return d


def draw(data, series, panels, out, ncols):
    rows = (len(panels) + ncols - 1) // ncols
    fig, axes = plt.subplots(rows, ncols, figsize=(6.2 * ncols, 3.9 * rows), facecolor="white", squeeze=False)
    for ax, (key, title, scale) in zip(axes.flat, panels):
        for algo, label, color, lw in series:
            xs = sorted(data[algo])
            ax.plot(xs, [data[algo][x][key] * scale for x in xs], marker="o", ms=5, lw=lw, color=color, label=label)
        ax.set(title=title, xlabel="lưu lượng mỗi user (Mbps)")
        ax.grid(color="#e4e3df", lw=0.8)
        ax.spines[["top", "right"]].set_visible(False)
    h, l = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=len(series), frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(R / out, dpi=150)
    print("Đã ghi", R / out)


draw(load("proposed.csv"),
     [("kmeans-equal", "kmeans-equal", "#2a78d6", 1.8), ("kmeans-maxmin", "kmeans-maxmin", "#eb6834", 1.8),
      ("kmeans-ifair", "chỉ ifair", "#1baf7a", 1.8), ("calib-equal", "chỉ calib", "#eda100", 1.8),
      ("calib-ifair", "calib-ifair", "#e34948", 3.2)],
     [("ns3_min_mbps", "Min throughput (Mbps)", 1), ("ns3_sum_mbps", "Throughput tổng (Mbps)", 1)],
     "proposed_slide.png", 2)

draw(load("classes.csv"),
     [("kmeans-equal", "kmeans-equal", "#2a78d6", 1.8), ("kmeans-wmaxmin", "kmeans-wmaxmin (biết nhóm)", "#6250d6", 1.8),
      ("calib-ifair-noclass", "calib-ifair bỏ nhóm", "#1baf7a", 1.8), ("calib-ifair", "calib-ifair", "#e34948", 3.2)],
     [("sat_critical", "Critical đạt QoS (%)", 100), ("min_critical", "Min throughput critical (Mbps)", 1),
      ("min_normal", "Min throughput normal (Mbps)", 1), ("thr_mbps", "Throughput tổng (Mbps)", 1)],
     "classes_slide.png", 2)
