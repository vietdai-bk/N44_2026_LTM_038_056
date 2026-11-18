"""Animation so sánh thuật toán cạnh nhau: UAV bay, user tô màu theo UAV phục vụ, kích thước điểm theo rate.

python -m uavsim.animate --algos hover-equal kmeans-equal random-equal --set user_speed=3
Có nhóm user (--set critical_frac=0.15 --set important_frac=0.25): normal tròn, important vuông, critical thoi viền đỏ,
tiêu đề thêm tỷ lệ user critical đạt QoS.
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.animation import FuncAnimation  # noqa: E402

from .algorithms import REGISTRY  # noqa: E402
from .config import SimConfig  # noqa: E402
from .gazebo import UAV_COLORS  # noqa: E402
from .network import Network  # noqa: E402

CLASS_MARKER = ("o", "s", "D")  # normal, important, critical
from .run import parse_set  # noqa: E402


def record(cfg: SimConfig, algo) -> list[dict]:
    net = Network(cfg)
    algo.reset(net)
    frames = []
    while not net.done:
        a = algo.act(net)
        uav, user = net.uav_xy.copy(), net.user_xy.copy()
        m = net.step(a)
        thr = m.get("thr_per_user", m["rates"])  # có lưu lượng thì chấm theo throughput, giống NS-3
        frames.append({"uav": uav, "user": user, "assoc": a.assoc.copy(), "thr": thr, **m})
    return frames


def animate(cfg: SimConfig, names: list[str], out: Path, every: int = 2, fps: int = 10):
    runs = {n: record(cfg, REGISTRY[n]()) for n in names}
    fig, axes = plt.subplots(1, len(names), figsize=(4.6 * len(names), 5), squeeze=False)
    axes = axes[0]
    colors = np.array([matplotlib.colors.to_rgba(UAV_COLORS[j % len(UAV_COLORS)]) for j in range(cfg.num_uavs)])
    cls = Network(cfg).user_class
    has_cls = bool(cfg.important_frac or cfg.critical_frac)
    r_scale = max(f["thr"].max() for fr in runs.values() for f in fr) or 1.0
    need = np.asarray(cfg.class_rmin_mbps)[cls] * 1e6 if has_cls else np.full(cfg.num_users, cfg.r_min)
    if cfg.demand_mbps is not None:
        need = np.minimum(need, 0.9 * cfg.demand_mbps * 1e6)

    def draw(i):
        for ax, (name, fr) in zip(axes, runs.items()):
            f = fr[i]
            ax.clear()
            ax.set(xlim=(0, cfg.area), ylim=(0, cfg.area), aspect="equal", xticks=[], yticks=[])
            for j in range(cfg.num_uavs):
                trail = np.array([g["uav"][j] for g in fr[: i + 1]])
                ax.plot(trail[:, 0], trail[:, 1], color=colors[j], lw=1, alpha=0.5)
                served = f["assoc"] == j
                for p in f["user"][served]:
                    ax.plot(*zip(f["uav"][j], p), color=colors[j], lw=0.4, alpha=0.35)
            ucol = np.where(f["assoc"][:, None] >= 0, colors[np.maximum(f["assoc"], 0)], (0.6, 0.6, 0.6, 1))
            ok = f["thr"] >= need
            for c in range(3) if has_cls else (0,):
                k = (cls == c) if has_cls else np.ones(cfg.num_users, bool)
                good, bad = k & ok, k & ~ok
                edge = "#d01010" if c == 2 else "k"
                if good.any():
                    ax.scatter(*f["user"][good].T, s=(14 if c == 2 else 10) + 70 * f["thr"][good] / r_scale, c=ucol[good],
                               marker=CLASS_MARKER[c], edgecolors=edge, lw=1.4 if c == 2 else 0.3, zorder=3)
                if bad.any():
                    ax.scatter(*f["user"][bad].T, s=30, c=ucol[bad], marker="x", zorder=3)  # dưới ngưỡng QoS / r_min
            ax.scatter(*f["uav"].T, s=160, c=colors, marker="^", edgecolors="k", zorder=4)
            title = f"{name}   t={f['t']}\n"
            if "throughput" in f:
                title += f"thr {f['throughput'] / 1e6:.0f} Mbps · min {f['min_throughput'] / 1e6:.2f} Mbps"
            else:
                title += f"sum {f['sum_rate'] / 1e6:.0f} Mbps · min {f['min_rate'] / 1e6:.2f} Mbps · cov {f['coverage']:.0%}"
            if has_cls:
                for pcls in ("critical", "important", "normal"):
                    if f"sat_{pcls}" in f:
                        title += f"\n{pcls} đạt QoS {f[f'sat_{pcls}']:.0%} · min {pcls} {f[f'min_{pcls}'] / 1e6:.2f} Mbps"
                        break
            ax.set_title(title, fontsize=9)

    idx = list(range(0, cfg.slots, every))
    if idx[-1] != cfg.slots - 1:
        idx.append(cfg.slots - 1)
    legend = "▲ UAV · ● user (to = rate cao) · × dưới r_min · màu = UAV phục vụ"
    if has_cls:
        legend += " · ● normal ■ important ◆ critical (viền đỏ)"
    fig.suptitle(legend, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    anim = FuncAnimation(fig, draw, frames=idx)
    anim.save(out, writer="pillow" if out.suffix == ".gif" else "ffmpeg", fps=fps, dpi=80)
    plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--algos", nargs="+", default=["hover-equal", "kmeans-equal", "random-equal"], choices=list(REGISTRY))
    p.add_argument("--set", action="append", default=[], metavar="KEY=VAL")
    p.add_argument("--every", type=int, default=2, help="lấy 1 frame mỗi N khe")
    p.add_argument("--out", default="experiments/results/anim.gif", help=".gif hoặc .mp4")
    args = p.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    animate(SimConfig(**parse_set(args.set)), args.algos, out, args.every)
    print(f"Đã lưu: {out.resolve()}")


if __name__ == "__main__":
    main()
