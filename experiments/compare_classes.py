"""So sánh theo ba nhóm user (normal, important, critical), đo bằng NS-3 LTE.

python experiments/compare_classes.py experiments/results/classes
Nhóm user cố định theo seed (uavsim.network.user_classes) và không làm đổi vị trí user, nên run cũ của baseline vẫn dùng
được: chỉ số từng nhóm được tính lại từ ns3_slots.csv (byte nhận, gói, độ trễ của từng user từng khe).
Nguồn: ns3-demand-lte (kmeans-equal, PF), ns3-demand-wpf-lte (kmeans-maxmin, WPF), ns3-proposed-lte (calib-ifair cũ, tức
bỏ qua nhóm, WPF), ns3-wmaxmin-lte (kmeans-wmaxmin: max-min có trọng số nhóm, baseline biết nhóm, WPF), ns3-classes-lte (calib-ifair có trọng
số nhóm và bản Shannon, WPF). Ghi <out>.csv, <out>.png.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from uavsim.config import SimConfig  # noqa: E402
from uavsim.network import CLASS_NAMES, user_classes  # noqa: E402

R = Path(__file__).parent / "results"
IMPORTANT, CRITICAL = 0.25, 0.15
# (thư mục, tên thuật toán trong thư mục) -> tên hiển thị
SOURCES = [("ns3-demand-lte", "kmeans-equal", "kmeans-equal"), ("ns3-demand-wpf-lte", "kmeans-maxmin", "kmeans-maxmin"),
           ("ns3-wmaxmin-lte", "kmeans-wmaxmin", "kmeans-wmaxmin"),
           ("ns3-proposed-lte", "calib-ifair", "calib-ifair-noclass"),
           ("ns3-classes-lte", "calib-ifair-shannon", "calib-ifair-shannon"),
           ("ns3-classes-lte", "calib-ifair", "calib-ifair")]
COLORS = {"kmeans-equal": "#2a78d6", "kmeans-maxmin": "#eb6834", "kmeans-wmaxmin": "#6250d6", "calib-ifair-noclass": "#1baf7a",
          "calib-ifair-shannon": "#eda100", "calib-ifair": "#e34948"}


def run_metrics(d: Path, seed: int, demand_mbps: float) -> dict:
    cfg = SimConfig(num_users=20, slots=60, demand_mbps=demand_mbps, seed=seed,
                    important_frac=IMPORTANT, critical_frac=CRITICAL)
    cls = user_classes(cfg)
    with open(d / "ns3_slots.csv") as f:
        rows = list(csv.DictReader(f))
    K, S = cfg.num_users, cfg.slots
    thr, rx, tx, dsum = (np.zeros((S, K)) for _ in range(4))
    for r in rows:
        s, k = int(r["slot"]), int(r["user"])
        thr[s, k] = int(r["rx_bytes"]) * 8 / cfg.dt
        rx[s, k], tx[s, k], dsum[s, k] = int(r["rx_pkts"]), int(r["tx_pkts"]), float(r["delay_sum_s"])
    out = {"thr_mbps": thr.sum(1).mean() / 1e6, "loss": 1 - rx.sum() / tx.sum()}
    for c, name in enumerate(CLASS_NAMES):
        k = cls == c
        need = min(cfg.class_rmin_mbps[c], 0.9 * demand_mbps) * 1e6
        out[f"min_{name}"] = thr[:, k].min(1).mean() / 1e6
        out[f"sat_{name}"] = float(np.mean(thr[:, k] >= need))
        out[f"delay_{name}"] = 1e3 * dsum[:, k].sum() / max(rx[:, k].sum(), 1)
    return out


def load():
    rows = defaultdict(dict)  # label -> (demand, seed) -> metrics
    for folder, algo, label in SOURCES:
        root = R / folder
        for d in sorted(root.glob(f"{algo}_load*_seed*")):
            load_s, seed_s = d.name[len(algo) + 5:].split("_seed")
            if not (d / "ns3_slots.csv").exists():
                continue
            rows[label][(float(load_s), int(seed_s))] = run_metrics(d, int(seed_s), float(load_s))
    return rows


def main(out):
    rows = load()
    keys = sorted(rows["calib-ifair"])
    for label in rows:
        missing = set(keys) - set(rows[label])
        assert not missing, f"{label}: thiếu run {sorted(missing)}"
    demands = sorted({d for d, _ in keys})
    labels = [s[2] for s in SOURCES]
    metric_keys = ["thr_mbps", "loss"] + [f"{m}_{n}" for n in CLASS_NAMES for m in ("min", "sat", "delay")]
    mean = lambda lab, d, m: float(np.mean([rows[lab][k][m] for k in keys if k[0] == d]))
    with open(Path(out).with_suffix(".csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["algo", "demand_mbps", *metric_keys])
        for lab in labels:
            for d in demands:
                w.writerow([lab, d, *[f"{mean(lab, d, m):.4g}" for m in metric_keys]])

    panels = [("sat_critical", "Critical đạt QoS (%)", 100), ("min_critical", "Min throughput critical (Mbps)", 1),
              ("min_normal", "Min throughput normal (Mbps)", 1), ("thr_mbps", "Throughput tổng (Mbps)", 1)]
    fig, axes = plt.subplots(1, 4, figsize=(17, 4.4), facecolor="#fcfcfb")
    for ax, (m, title, scale) in zip(axes, panels):
        for lab in labels:
            ax.plot(demands, [mean(lab, d, m) * scale for d in demands], marker="o", ms=5,
                    lw=2.6 if lab == "calib-ifair" else 1.6, color=COLORS[lab], label=lab)
        ax.set(title=title, xlabel="lưu lượng mỗi user (Mbps)", facecolor="#fcfcfb")
        ax.grid(color="#e4e3df", lw=0.8)
        ax.spines[["top", "right"]].set_visible(False)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=6, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.suptitle(f"NS-3 LTE, 3 UAV, 20 user ({CRITICAL:.0%} critical, {IMPORTANT:.0%} important), 60 khe, 3 seed",
                 y=0.9, fontsize=10, color="#52514e")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.savefig(Path(out).with_suffix(".png"), dpi=150, facecolor=fig.get_facecolor())
    print(f"Đã ghi {Path(out).with_suffix('.csv')} và {Path(out).with_suffix('.png')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
