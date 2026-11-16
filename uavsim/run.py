"""Chạy và so sánh thuật toán.

python -m uavsim.run --algos hover-equal kmeans-equal kmeans-maxmin --seeds 3
python -m uavsim.run --config experiments/default.json --set num_uavs=5 --set channel=los
"""
import argparse
import csv
import json
import time
from dataclasses import fields
from pathlib import Path

import numpy as np

from .algorithms import REGISTRY
from .config import SimConfig
from .network import Network

SCALARS = ["sum_rate", "min_rate", "jain", "coverage", "energy"]
QUEUE = ["throughput", "min_throughput", "delay_ms", "loss", "queue_bits"]  # chỉ có khi cfg.demand_mbps khác None


def scalars(cfg: SimConfig) -> list[str]:
    return SCALARS + (QUEUE if cfg.demand_mbps is not None else [])


def run_episode(cfg: SimConfig, algo) -> tuple[list[dict], np.ndarray]:
    net = Network(cfg)
    algo.reset(net)
    rows, traj = [], [net.uav_xy.copy()]
    while not net.done:
        m = net.step(algo.act(net))
        rows.append({k: m[k] for k in ["t", *scalars(cfg)]})
        traj.append(net.uav_xy.copy())
    return rows, np.array(traj)


def summarize(rows, cfg: SimConfig) -> dict:
    s = {k: float(np.nanmean([r[k] for r in rows])) for k in scalars(cfg)}
    if cfg.demand_mbps is not None:  # delay trung bình theo bit phục vụ, mất gói trên cả episode
        thr = np.array([r["throughput"] for r in rows])
        s["delay_ms"] = float(np.nansum(np.array([r["delay_ms"] for r in rows]) * thr) / thr.sum()) if thr.sum() else float("nan")
        s["loss"] = float(np.mean([r["loss"] for r in rows]))
    total_bits = sum(r["sum_rate"] for r in rows) * cfg.dt
    total_energy = sum(r["energy"] for r in rows)
    s["energy_eff"] = total_bits / total_energy  # bit/J
    return s


def episode_loss(rows, cfg: SimConfig) -> float:
    """Mất gói trên cả episode theo định nghĩa của NS-3 (1 - nhận/gửi): bit còn trong hàng đợi lúc kết thúc cũng là mất."""
    arrivals = cfg.demand_mbps * 1e6 * cfg.dt * cfg.num_users * len(rows)
    return float(np.mean([r["loss"] for r in rows]) + rows[-1]["queue_bits"] / arrivals)


def parse_set(items):
    names = {f.name for f in fields(SimConfig)}
    out = {}
    for item in items:
        key, _, val = item.partition("=")
        if key not in names:
            raise SystemExit(f"--set: không có tham số {key}")
        try:
            out[key] = json.loads(val)  # số, true/false, null
        except json.JSONDecodeError:
            out[key] = val  # chuỗi, vd. channel=los
    return out


def plot(out: Path, series: dict, trajs: dict, net0: Network):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for name, rows in series.items():
        t = [r["t"] for r in rows]
        axes[0].plot(t, [r["sum_rate"] / 1e6 for r in rows], label=name)
        axes[1].plot(t, [r["min_rate"] / 1e6 for r in rows], label=name)
    axes[0].set(title="Sum rate (seed đầu)", xlabel="khe", ylabel="Mbps")
    axes[1].set(title="Min rate (seed đầu)", xlabel="khe", ylabel="Mbps")
    axes[0].legend(fontsize=8)
    ax = axes[2]
    ax.scatter(*net0.user_xy.T, s=12, c="gray", label="user")
    for i, (name, tr) in enumerate(trajs.items()):
        for j in range(tr.shape[1]):
            ax.plot(tr[:, j, 0], tr[:, j, 1], lw=1, color=f"C{i}", label=name if j == 0 else None)
    ax.scatter(*trajs[next(iter(trajs))][0].T, marker="^", c="k", label="UAV xuất phát")
    ax.set(title="Quỹ đạo UAV (seed đầu)", xlabel="x (m)", ylabel="y (m)", aspect="equal")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out / "compare.png", dpi=130)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="file JSON ghi đè SimConfig")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VAL")
    p.add_argument("--algos", nargs="+", default=list(REGISTRY), choices=list(REGISTRY))
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--out", default=None, help="mặc định experiments/results/<thời gian>")
    p.add_argument("--no-plot", action="store_true")
    args = p.parse_args(argv)

    overrides = parse_set(args.set)
    base = SimConfig.from_json(args.config, **overrides) if args.config else SimConfig(**overrides)
    out = Path(args.out or f"experiments/results/{time.strftime('%Y%m%d-%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps({**base.to_dict(), "algos": args.algos, "seeds": args.seeds}, indent=2))

    summary, first_series, first_traj = [], {}, {}
    with open(out / "timeseries.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["algo", "seed", "t", *scalars(base)])
        w.writeheader()
        for name in args.algos:
            for s in range(args.seeds):
                cfg = SimConfig(**{**base.to_dict(), "seed": base.seed + s})
                rows, traj = run_episode(cfg, REGISTRY[name]())
                w.writerows({"algo": name, "seed": cfg.seed, **r} for r in rows)
                summary.append({"algo": name, "seed": cfg.seed, **summarize(rows, cfg)})
                if s == 0:
                    first_series[name], first_traj[name] = rows, traj

    keys = [*scalars(base), "energy_eff"]
    with open(out / "summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["algo", "seed", *keys])
        w.writeheader()
        w.writerows(summary)

    print(f"{'algo':16}" + "".join(f"{k:>22}" for k in keys))
    for name in args.algos:
        vals = [[r[k] for r in summary if r["algo"] == name] for k in keys]
        print(f"{name:16}" + "".join(f"{np.mean(v):>13.4g} ±{np.std(v):<8.2g}" for v in vals))
    print("Đơn vị: rate/throughput bit/s (TB theo khe), energy J/khe (tổng các UAV), energy_eff bit/J, delay ms")

    if not args.no_plot:
        plot(out, first_series, first_traj, Network(base))
    print(f"Kết quả: {out.resolve()}")


if __name__ == "__main__":
    main()
