"""Phát lại kế hoạch của thuật toán trong NS-3 LTE và đo ở mức gói tin.

Python (uavsim) quyết định vị trí UAV, liên kết user-UAV, rate cấp cho mỗi user theo từng khe;
NS-3 (ns3/scratch/uav_lte/uav-lte.cc) phát lại đúng kế hoạch đó với eNB/UE/EPC/UDP thật và đo
throughput, delay, mất gói. Kết quả được đặt cạnh số liệu của mô hình để so sánh.

python -m uavsim.ns3 --algos hover-equal kmeans-equal --set slots=30
"""
import argparse
import csv
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from .algorithms import REGISTRY
from .config import ENVIRONMENTS, SimConfig
from .network import Network, jain
from .run import episode_loss, parse_set, scalars

NS3_DIR = Path(os.environ.get("NS3_DIR", Path.home() / "simulation/ns-3.47"))
BIN = NS3_DIR / "build/scratch/uav_lte/ns3.47-uav-lte-default"
LTE_RB = {1.4e6: 6, 3e6: 15, 5e6: 25, 10e6: 50, 15e6: 75, 20e6: 100}  # băng thông -> số resource block


class PlanRecorder:
    """Ghi kế hoạch theo từng khe (uavs.csv/users.csv cho NS-3) và chỉ số mô hình từng khe.

    Dùng chung cho export_plan (thuật toán chạy hết episode) và uavsim.live (điều khiển tay theo thời gian thực).
    Lưu lượng gửi cho user trong NS-3: demand_mbps (CBR) nếu có, ngược lại là rate mô hình cấp cho user.
    """

    def __init__(self, cfg: SimConfig):
        self.cfg, self.uavs, self.users, self.model = cfg, [], [], []

    def add(self, s: int, uav_xy, user_xy, a, m: dict):
        c = self.cfg
        self.uavs += [(s, j, *uav_xy[j]) for j in range(c.num_uavs)]
        send = np.full(c.num_users, c.demand_mbps * 1e6) if c.demand_mbps is not None else m["rates"]
        cap = m.get("capacity", m["rates"])
        self.users += [(s, k, *user_xy[k], int(a.assoc[k]), float(send[k]), float(a.bw[k]), float(cap[k]))
                       for k in range(c.num_users)]
        self.model.append({k: m[k] for k in ["t", *scalars(c)]})

    def write(self, plan_dir: Path, s: int, uav_xy, user_xy):
        """s, uav_xy, user_xy: vị trí cuối để NS-3 nội suy khe cuối."""
        c = self.cfg
        plan_dir.mkdir(parents=True, exist_ok=True)
        uavs = self.uavs + [(s, j, *uav_xy[j]) for j in range(c.num_uavs)]
        users = self.users + [(s, k, *user_xy[k], -1, 0.0, 0.0, 0.0) for k in range(c.num_users)]
        for name, header, rows in [("uavs.csv", "slot,uav,x,y", uavs),
                                   ("users.csv", "slot,user,x,y,serving,rate_bps,bw,cap_bps", users)]:
            with open(plan_dir / name, "w") as f:
                f.write(header + "\n")
                f.writelines(",".join(f"{v:.6g}" if isinstance(v, float) else str(v) for v in r) + "\n" for r in rows)


def export_plan(cfg: SimConfig, algo, plan_dir: Path) -> list[dict]:
    """Chạy thuật toán trên mô hình, ghi kế hoạch cho NS-3, trả về chỉ số mô hình từng khe."""
    net = Network(cfg)
    algo.reset(net)
    rec = PlanRecorder(cfg)
    while not net.done:
        s, uav_xy, user_xy = net.t, net.uav_xy.copy(), net.user_xy.copy()
        a = algo.act(net)
        rec.add(s, uav_xy, user_xy, a, net.step(a))
    rec.write(plan_dir, net.t, net.uav_xy, net.user_xy)
    return rec.model


def ns3_command(cfg: SimConfig, plan: Path, out: Path, scheduler: str, load: float, traces: bool = False,
                link: str = "lte") -> list[str]:
    if link == "lte" and cfg.bandwidth not in LTE_RB:
        raise ValueError(f"LTE chỉ hỗ trợ băng thông {sorted(LTE_RB)} Hz")
    a, b, eta_los, eta_nlos = ENVIRONMENTS[cfg.environment]
    args = {
        "plan": plan, "out": out, "numUavs": cfg.num_uavs, "numUsers": cfg.num_users, "slots": cfg.slots,
        "dt": cfg.dt, "altitude": cfg.altitude, "rb": LTE_RB.get(cfg.bandwidth, 50),
        "link": link, "bufferBytes": cfg.buffer_bytes,
        "txPowerDbm": 10 * np.log10(cfg.p_max * 1e3),
        "noiseFigure": cfg.noise_psd_dbm + 174,  # LTE PHY: N0 = -174 dBm/Hz + NF
        "fc": cfg.fc, "channel": cfg.channel, "a": a, "b": b, "etaLos": eta_los, "etaNlos": eta_nlos,
        "beta0Db": cfg.beta0_db, "scheduler": scheduler, "load": load, "seed": cfg.seed + 1,
        # interference=False: mỗi eNB một kênh riêng, giống mô hình không nhiễu
        "reuse1": str(cfg.interference).lower(), "traces": str(traces).lower(),
    }
    return [str(BIN), *(f"--{k}={v}" for k, v in args.items())]


def run_ns3(cmd: list[str], out: Path, timeout: float) -> str:
    out.mkdir(parents=True, exist_ok=True)
    if not BIN.exists():
        raise FileNotFoundError(f"Chưa build kịch bản NS-3: {BIN}. Chạy ns3/install.sh")
    env = {**os.environ, "LD_LIBRARY_PATH": str(NS3_DIR / "build/lib")}
    t0 = time.time()
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    log = f"$ {' '.join(cmd)}\n{p.stdout}{p.stderr}\nexit={p.returncode} wall={time.time() - t0:.1f}s\n"
    (out / "ns3.log").write_text(log)
    if p.returncode != 0:
        raise RuntimeError(f"NS-3 lỗi (exit {p.returncode}), xem {out / 'ns3.log'}")
    return log


def ns3_metrics(out: Path, cfg: SimConfig) -> list[dict]:
    """Chỉ số NS-3 từng khe, cùng tên với chỉ số mô hình (sum_rate... là throughput đo được)."""
    with open(out / "ns3_slots.csv") as f:
        rows = list(csv.DictReader(f))
    res = []
    for s in range(cfg.slots):
        r = [x for x in rows if int(x["slot"]) == s]
        thr = np.array([int(x["rx_bytes"]) * 8 / cfg.dt for x in r])
        tx = sum(int(x["tx_pkts"]) for x in r)
        rx = sum(int(x["rx_pkts"]) for x in r)
        plan = np.array([int(x["plan_cell"]) for x in r])
        actual = np.array([int(x["actual_cell"]) for x in r])
        res.append({
            "t": s,
            "sum_rate": float(thr.sum()),
            "min_rate": float(thr.min()),
            "jain": jain(thr),
            "coverage": float(np.mean(thr >= cfg.r_min)),
            "delay_ms": 1e3 * sum(float(x["delay_sum_s"]) for x in r) / rx if rx else float("nan"),
            "loss": max(0.0, 1 - rx / tx) if tx else 0.0,
            "tx_pkts": tx,
            "rx_pkts": rx,
            "cell_match": float(np.mean(plan[plan >= 0] == actual[plan >= 0])) if np.any(plan >= 0) else 1.0,
        })
    return res


WARMUP = 0.5  # s, khớp với uav-lte.cc
TRACE_KEYS = ["sinr_db_p10", "sinr_db_median", "sinr_db_p90", "mcs_mean", "bler_first_tx", "harq_retx_frac",
              "active_cells", "cell_busy_frac", "phy_goodput_mbps", "se_per_cell"]


def _load(path: Path, cols):
    if not path.exists() and path.with_suffix(path.suffix + ".gz").exists():
        path = path.with_suffix(path.suffix + ".gz")  # trace đã nén bằng gzip
    if not path.exists():  # NS-3 chỉ tạo file khi có sự kiện đầu tiên, vd. UE mất kết nối thì không có DlRxPhyStats
        return np.zeros((0, len(cols)))
    a = np.loadtxt(path, comments="%", usecols=cols, ndmin=2)
    return a if a.size else np.zeros((0, len(cols)))


def trace_stats(d: Path, cfg: SimConfig) -> dict:
    """Chỉ số từ trace LTE downlink trong khoảng đo [warmup, warmup + slots*dt)."""
    t0, t1 = WARMUP, WARMUP + cfg.slots * cfg.dt
    sinr = _load(d / "DlRsrpSinrStats.txt", (0, 5))       # time, sinr tuyến tính
    sinr = sinr[(sinr[:, 0] >= t0) & (sinr[:, 0] < t1), 1]
    rx = _load(d / "DlRxPhyStats.txt", (0, 1, 6, 7, 8, 10))  # time (ms!), cellId, mcs, size(byte), rv, correct
    rx[:, 0] /= 1000.0  # DlRxPhyStats ghi thời gian theo ms, hai file kia theo s
    rx = rx[(rx[:, 0] >= t0) & (rx[:, 0] < t1)]
    mac = _load(d / "DlMacStats.txt", (0, 1))              # time, cellId: mỗi dòng là một cấp phát
    mac = mac[(mac[:, 0] >= t0) & (mac[:, 0] < t1)]
    first = rx[rx[:, 4] == 0]
    nan = float("nan")
    # chỉ tính cell có lưu lượng: UAV không phục vụ ai thì không làm loãng hiệu suất phổ
    n_cells = max(len(np.unique(mac[:, 1])), 1)
    goodput = rx[rx[:, 5] == 1, 3].sum() * 8 / (t1 - t0)
    sinr_db = 10 * np.log10(np.maximum(sinr, 1e-12))
    busy_ttis = len({(round(t * 1000), c) for t, c in mac})  # (TTI, cell) có ít nhất một cấp phát
    return {
        "sinr_db_p10": float(np.percentile(sinr_db, 10)),
        "sinr_db_median": float(np.median(sinr_db)),
        "sinr_db_p90": float(np.percentile(sinr_db, 90)),
        "mcs_mean": float(first[:, 2].mean()) if len(first) else nan,
        "bler_first_tx": float(1 - first[:, 5].mean()) if len(first) else nan,
        "harq_retx_frac": float(np.mean(rx[:, 4] > 0)) if len(rx) else nan,
        "active_cells": n_cells,
        "cell_busy_frac": busy_ttis / (n_cells * (t1 - t0) * 1000),  # trên các cell có lưu lượng
        "phy_goodput_mbps": goodput / 1e6,
        "se_per_cell": goodput / (n_cells * cfg.bandwidth),  # bit/s/Hz mỗi cell có lưu lượng
    }


def run_one(cfg: SimConfig, name: str, root: Path, scheduler: str, load: float, timeout: float,
            traces: bool = False, link: str = "lte") -> dict:
    d = root / f"{name}_load{load:g}_seed{cfg.seed}"
    queue = cfg.demand_mbps is not None
    if queue:  # load nhân vào demand ngay trong kế hoạch, để mô hình hàng đợi và NS-3 thấy cùng lưu lượng
        cfg = SimConfig(**{**cfg.to_dict(), "demand_mbps": cfg.demand_mbps * load})
    model = export_plan(cfg, REGISTRY[name](), d / "plan")
    run_ns3(ns3_command(cfg, d / "plan", d, scheduler, 1.0 if queue else load, traces, link), d, timeout)
    ns3 = ns3_metrics(d, cfg)
    with open(d / "compare_slots.csv", "w", newline="") as f:
        w = csv.writer(f)
        keys = ["sum_rate", "min_rate", "jain", "coverage"]
        w.writerow(["slot", *(f"model_{k}" for k in keys), *(f"ns3_{k}" for k in keys),
                    "ns3_delay_ms", "ns3_loss", "cell_match"])
        for mo, ns in zip(model, ns3):
            w.writerow([mo["t"], *(mo[k] for k in keys), *(ns[k] for k in keys), ns["delay_ms"], ns["loss"], ns["cell_match"]])
    tx, rx = sum(x["tx_pkts"] for x in ns3), sum(x["rx_pkts"] for x in ns3)
    delays = [x["delay_ms"] * x["rx_pkts"] for x in ns3 if x["rx_pkts"]]
    offered = cfg.demand_mbps * cfg.num_users if queue else load * np.mean([x["sum_rate"] for x in model]) / 1e6
    qm = {}
    if queue:
        thr = np.array([x["throughput"] for x in model])
        qm = {
            "offered_per_user_mbps": cfg.demand_mbps,
            "model_thr_mbps": thr.mean() / 1e6,
            "model_min_thr_mbps": np.mean([x["min_throughput"] for x in model]) / 1e6,
            "model_delay_ms": float(np.nansum(np.array([x["delay_ms"] for x in model]) * thr) / thr.sum()) if thr.sum() else np.nan,
            "model_loss": episode_loss(model, cfg),  # cùng định nghĩa với ns3_loss
        }
    return {
        **qm,
        **(trace_stats(d, cfg) if traces else {}),
        "algo": name, "load": load, "seed": cfg.seed,
        "model_sum_mbps": np.mean([x["sum_rate"] for x in model]) / 1e6,
        "ns3_sum_mbps": np.mean([x["sum_rate"] for x in ns3]) / 1e6,
        # throughput đo được / lượng đã gửi vào; 1.0 nghĩa là mạng chuyển hết
        "delivered_ratio": np.mean([x["sum_rate"] for x in ns3]) / 1e6 / offered,
        "model_min_mbps": np.mean([x["min_rate"] for x in model]) / 1e6,
        "ns3_min_mbps": np.mean([x["min_rate"] for x in ns3]) / 1e6,
        "ns3_jain": np.mean([x["jain"] for x in ns3]),
        "ns3_coverage": np.mean([x["coverage"] for x in ns3]),
        "ns3_delay_ms": sum(delays) / rx if rx else float("nan"),
        "ns3_loss": 1 - rx / tx if tx else 0.0,
        "cell_match": np.mean([x["cell_match"] for x in ns3]),
        "energy_j_per_slot": np.mean([x["energy"] for x in model]),
        "_model": model, "_ns3": ns3,
    }


def replay(session: Path, scheduler: str, link: str, timeout: float) -> dict:
    """Phát lại trong NS-3 một phiên đã ghi bằng uavsim.live (session/config.json, plan/, model_slots.csv).

    Trả về số của mô hình và số đo NS-3 cạnh nhau: throughput tổng, min, delay, mất gói.
    """
    cfg = SimConfig.from_json(str(session / "config.json"))
    out = session / f"ns3-{link}-{scheduler}"
    t0 = time.time()
    run_ns3(ns3_command(cfg, session / "plan", out, scheduler, 1.0, link=link), out, timeout)
    ns3 = ns3_metrics(out, cfg)
    with open(session / "model_slots.csv") as f:
        model = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    queue = cfg.demand_mbps is not None
    k_thr, k_min = ("throughput", "min_throughput") if queue else ("sum_rate", "min_rate")
    tx, rx = sum(x["tx_pkts"] for x in ns3), sum(x["rx_pkts"] for x in ns3)
    thr = np.array([x[k_thr] for x in model])
    res = {
        "slots": cfg.slots, "dt": cfg.dt, "link": link, "scheduler": scheduler, "wall_s": time.time() - t0,
        "model_thr_mbps": float(thr.mean() / 1e6),
        "ns3_thr_mbps": float(np.mean([x["sum_rate"] for x in ns3]) / 1e6),
        "model_min_mbps": float(np.mean([x[k_min] for x in model]) / 1e6),
        "ns3_min_mbps": float(np.mean([x["min_rate"] for x in ns3]) / 1e6),
        "ns3_delay_ms": sum(x["delay_ms"] * x["rx_pkts"] for x in ns3 if x["rx_pkts"]) / rx if rx else float("nan"),
        "ns3_loss": 1 - rx / tx if tx else 0.0,
        "cell_match": float(np.mean([x["cell_match"] for x in ns3])),
    }
    if queue:
        res["model_delay_ms"] = (float(np.nansum(np.array([x["delay_ms"] for x in model]) * thr) / thr.sum())
                                 if thr.sum() else float("nan"))
        res["model_loss"] = episode_loss(model, cfg)
    (out / "replay_summary.json").write_text(json.dumps(res, indent=2))
    return res


def plot(root: Path, results: list[dict]):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = max(r["load"] for r in results)
    first = {}
    for r in results:  # seed đầu, load cao nhất
        if r["load"] == top:
            first.setdefault(r["algo"], r)
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for i, (name, r) in enumerate(first.items()):
        t = [x["t"] for x in r["_model"]]
        axes[0].plot(t, [x["sum_rate"] / 1e6 for x in r["_model"]], "--", color=f"C{i}", label=f"{name} (mô hình)")
        axes[0].plot(t, [x["sum_rate"] / 1e6 for x in r["_ns3"]], color=f"C{i}", label=f"{name} (NS-3)")
        axes[1].plot(t, [x["delay_ms"] for x in r["_ns3"]], color=f"C{i}", label=name)
        axes[2].plot(t, [100 * x["loss"] for x in r["_ns3"]], color=f"C{i}", label=name)
    axes[0].set(title=f"Sum rate: kế hoạch (đứt) vs NS-3 (liền), load {top:g}", xlabel="khe", ylabel="Mbps")
    axes[1].set(title="Delay trung bình NS-3", xlabel="khe", ylabel="ms", yscale="log")
    axes[2].set(title="Tỷ lệ mất gói NS-3", xlabel="khe", ylabel="%")
    for ax in axes:
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(root / "ns3_compare.png", dpi=130)


AGG_KEYS = ["model_sum_mbps", "ns3_sum_mbps", "delivered_ratio", "ns3_min_mbps", "ns3_jain",
            "ns3_coverage", "ns3_delay_ms", "ns3_loss", "cell_match", "energy_j_per_slot"]
QUEUE_KEYS = ["offered_per_user_mbps", "model_thr_mbps", "model_min_thr_mbps", "model_delay_ms", "model_loss"]
MODEL_OF = {"ns3_sum_mbps": "model_thr_mbps", "ns3_min_mbps": "model_min_thr_mbps",
            "ns3_delay_ms": "model_delay_ms", "ns3_loss": "model_loss"}  # đường mô hình vẽ cạnh số đo NS-3


def aggregate(results: list[dict]) -> list[dict]:
    """Trung bình và độ lệch chuẩn qua seed cho mỗi (thuật toán, load)."""
    out = []
    for algo in dict.fromkeys(r["algo"] for r in results):
        for load in sorted({r["load"] for r in results}):
            rs = [r for r in results if r["algo"] == algo and r["load"] == load]
            row = {"algo": algo, "load": load, "n_seeds": len(rs)}
            for k in AGG_KEYS + [k for k in TRACE_KEYS + QUEUE_KEYS if k in rs[0]]:
                v = np.array([r[k] for r in rs], float)
                row[k], row[k + "_std"] = float(np.nanmean(v)), float(np.nanstd(v))
            out.append(row)
    return out


def plot_matrix(root: Path, agg: list[dict]):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    panels = [
        ("ns3_sum_mbps", "Throughput tổng NS-3 (Mbps)", None),
        ("delivered_ratio", "Tỷ lệ chuyển được = NS-3 / lượng gửi", None),
        ("ns3_delay_ms", "Delay trung bình (ms)", "log"),
        ("ns3_loss", "Tỷ lệ mất gói", None),
        ("ns3_min_mbps", "Min throughput (Mbps)", None),
        ("ns3_jain", "Jain fairness", None),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5))
    for ax, (key, title, scale) in zip(axes.flat, panels):
        queue = "model_thr_mbps" in agg[0]
        for i, algo in enumerate(dict.fromkeys(r["algo"] for r in agg)):
            rs = [r for r in agg if r["algo"] == algo]
            x = [r["offered_per_user_mbps"] if queue else r["load"] for r in rs]
            ax.errorbar(x, [r[key] for r in rs], yerr=[r[key + "_std"] for r in rs], marker="o", capsize=3,
                        color=f"C{i}", label=f"{algo} (NS-3)")
            if queue and key in MODEL_OF:  # dự đoán của mô hình hàng đợi, nét đứt
                ax.plot(x, [r[MODEL_OF[key]] for r in rs], "--", marker="s", ms=3, color=f"C{i}",
                        label=f"{algo} (mô hình)")
            if key == "ns3_sum_mbps":  # lượng thực gửi vào mạng
                offered = [r["ns3_sum_mbps"] / r["delivered_ratio"] for r in rs]  # tổng lưu lượng gửi vào
                ax.plot(x, offered, ":", color="gray")
        ax.set(title=title, xlabel="lưu lượng mỗi user (Mbps)" if queue else "load (hệ số nhân rate kế hoạch)")
        if scale:
            ax.set_yscale(scale)
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=7, title="chấm xám = lượng gửi; nét đứt = mô hình", title_fontsize=7)
    n = agg[0]["n_seeds"]
    fig.suptitle(f"Ma trận NS-3 LTE: trung bình ± độ lệch chuẩn qua {n} seed", fontsize=11)
    fig.tight_layout()
    fig.savefig(root / "ns3_matrix.png", dpi=130)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--algos", nargs="+", default=["hover-equal", "kmeans-equal", "kmeans-maxmin"], choices=list(REGISTRY))
    p.add_argument("--config", help="file JSON ghi đè SimConfig")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VAL")
    p.add_argument("--seeds", type=int, default=1)
    p.add_argument("--scheduler", choices=["pf", "rr", "wpf"], default="pf",
                   help="MAC scheduler LTE; wpf = PF có trọng số b_k của thuật toán (áp cấp phát băng thông ở tầng MAC)")
    p.add_argument("--load", type=float, nargs="+", default=[1.0], help="một hoặc nhiều hệ số nhân rate kế hoạch")
    p.add_argument("--parallel", type=int, default=os.cpu_count() // 2 or 1)
    p.add_argument("--timeout", type=float, default=3600)
    p.add_argument("--traces", action="store_true", help="ghi trace PHY/MAC LTE và tính SINR, MCS, BLER, HARQ")
    p.add_argument("--link", choices=["lte", "ideal"], default="lte",
                   help="ideal: mỗi user một liên kết điểm-điểm, tốc độ từng khe = rate lý thuyết, bộ đệm buffer_bytes")
    p.add_argument("--replay", metavar="SESSION", help="phát lại phiên đã ghi bằng uavsim.live (bỏ qua --algos/--load)")
    p.add_argument("--out", default=None, help="mặc định experiments/results/ns3-<thời gian>")
    args = p.parse_args(argv)

    if args.replay:
        res = replay(Path(args.replay), args.scheduler, args.link, args.timeout)
        print("\n".join(f"{k:>24}: {v:.4g}" if isinstance(v, float) else f"{k:>24}: {v}" for k, v in res.items()))
        return

    user = parse_set(args.set)
    # Không có demand: NS-3 gửi đúng rate mô hình, nên phải dùng rate LTE (Shannon thuần chắc chắn quá tải).
    # Có demand: NS-3 gửi demand, rate mô hình chỉ là dự đoán lý thuyết, giữ mặc định Shannon như paper.
    # link=ideal: tốc độ liên kết = rate mô hình nên giữ Shannon của paper.
    lte_rate = args.link == "lte" and user.get("demand_mbps") is None
    overrides = ({"rate_model": "lte"} if lte_rate else {}) | user
    base = SimConfig.from_json(args.config, **overrides) if args.config else SimConfig(**overrides)
    root = Path(args.out or f"experiments/results/ns3-{time.strftime('%Y%m%d-%H%M%S')}")
    root.mkdir(parents=True, exist_ok=True)
    meta = {**base.to_dict(), "algos": args.algos, "seeds": args.seeds, "scheduler": args.scheduler, "load": args.load,
            "traces": args.traces, "link": args.link}
    (root / "config.json").write_text(json.dumps(meta, indent=2))

    jobs = [(SimConfig(**{**base.to_dict(), "seed": base.seed + s}), name, load)
            for name in args.algos for load in args.load for s in range(args.seeds)]
    print(f"{len(jobs)} run NS-3, song song {args.parallel} ...", flush=True)
    t0 = time.time()

    def job(j):
        r = run_one(j[0], j[1], root, args.scheduler, j[2], args.timeout, args.traces and args.link == "lte", args.link)
        print(f"  xong {j[1]} load={j[2]:g} seed={j[0].seed}  ({time.time() - t0:.0f}s)", flush=True)
        return r

    with ThreadPoolExecutor(args.parallel) as ex:
        results = list(ex.map(job, jobs))

    cols = [k for k in results[0] if not k.startswith("_")]
    with open(root / "summary_ns3.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    agg = aggregate(results)
    with open(root / "aggregate_ns3.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(agg[0]))
        w.writeheader()
        w.writerows(agg)
    show = ["model_sum_mbps", "ns3_sum_mbps", "delivered_ratio", "ns3_min_mbps", "ns3_delay_ms", "ns3_loss", "cell_match"]
    if base.demand_mbps is not None:
        show = ["offered_per_user_mbps", "model_thr_mbps", "ns3_sum_mbps", "model_min_thr_mbps", "ns3_min_mbps",
                "model_delay_ms", "ns3_delay_ms", "model_loss", "ns3_loss"]
    print(f"{'algo':16}{'load':>6}" + "".join(f"{k:>17}" for k in show))
    for r in agg:
        print(f"{r['algo']:16}{r['load']:>6g}" + "".join(f"{r[k]:>10.4g} ±{r[k + '_std']:<5.2g}" for k in show))
    if args.traces:
        tk = TRACE_KEYS
        print(f"\n{'algo':16}{'load':>6}" + "".join(f"{k:>17}" for k in tk))
        for r in agg:
            print(f"{r['algo']:16}{r['load']:>6g}" + "".join(f"{r[k]:>10.4g} ±{r[k + '_std']:<5.2g}" for k in tk))
    plot(root, results)
    if len(args.load) > 1:
        plot_matrix(root, agg)
    print(f"Kết quả: {root.resolve()}")


if __name__ == "__main__":
    main()
