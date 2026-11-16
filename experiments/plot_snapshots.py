"""Ảnh chụp mô phỏng ở vài thời điểm, so sánh kmeans-equal và calib-ifair trên cùng kịch bản có ba nhóm user.

python experiments/plot_snapshots.py docs/figures/snapshots.png
Hàng trên kmeans-equal, hàng dưới calib-ifair; cột là khe 0, 10, 59. Hình tròn normal, vuông important, thoi viền đỏ
critical; màu = UAV phục vụ; × = dưới ngưỡng QoS của nhóm.
"""
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from uavsim.algorithms import REGISTRY  # noqa: E402
from uavsim.animate import CLASS_MARKER, record  # noqa: E402
from uavsim.config import SimConfig  # noqa: E402
from uavsim.gazebo import UAV_COLORS  # noqa: E402
from uavsim.network import Network  # noqa: E402

CFG = SimConfig(slots=60, demand_mbps=2.0, rate_model="lte", lte_alpha=0.401, lte_se_max=3.514,
                important_frac=0.25, critical_frac=0.15, seed=1)
ALGOS = ["kmeans-equal", "calib-ifair"]
SLOTS = [0, 10, 59]


def main(out):
    cls = Network(CFG).user_class
    colors = np.array([matplotlib.colors.to_rgba(c) for c in UAV_COLORS[:CFG.num_uavs]])
    need = np.minimum(np.array(CFG.class_rmin_mbps)[cls] * 1e6, 0.9 * CFG.demand_mbps * 1e6)
    fig, axes = plt.subplots(len(ALGOS), len(SLOTS), figsize=(11, 7.4), facecolor="white")
    for r, name in enumerate(ALGOS):
        frames = record(CFG, REGISTRY[name]())
        for c, t in enumerate(SLOTS):
            ax, f = axes[r, c], frames[t]
            ax.set(xlim=(0, CFG.area), ylim=(0, CFG.area), aspect="equal", xticks=[], yticks=[])
            for j in range(CFG.num_uavs):
                trail = np.array([g["uav"][j] for g in frames[:t + 1]])
                ax.plot(trail[:, 0], trail[:, 1], color=colors[j], lw=1.2, alpha=0.6)
                for p in f["user"][f["assoc"] == j]:
                    ax.plot(*zip(f["uav"][j], p), color=colors[j], lw=0.5, alpha=0.4)
            ok = f["thr"] >= need
            for g in range(3):
                for good in (True, False):
                    k = (cls == g) & (ok == good)
                    if not k.any():
                        continue
                    col = colors[np.maximum(f["assoc"][k], 0)]
                    if good:
                        ax.scatter(*f["user"][k].T, s=70 if g == 2 else 40, c=col, marker=CLASS_MARKER[g],
                                   edgecolors="#d01010" if g == 2 else "k", lw=1.8 if g == 2 else 0.4, zorder=3)
                    else:
                        ax.scatter(*f["user"][k].T, s=60, c=col, marker="x", lw=2, zorder=3)
            ax.scatter(*f["uav"].T, s=220, c=colors, marker="^", edgecolors="k", zorder=4)
            crit = cls == 2
            ax.set_title(f"{name}, khe {t}\ncritical đạt QoS {np.mean(ok[crit]):.0%} · "
                         f"thr {f['throughput'] / 1e6:.0f} Mbps", fontsize=10)
    fig.suptitle("▲ UAV · ● normal ■ important ◆ critical (viền đỏ) · × dưới ngưỡng QoS · màu = UAV phục vụ · "
                 "đường mảnh = quỹ đạo", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out, dpi=150)
    print(f"Đã ghi {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
