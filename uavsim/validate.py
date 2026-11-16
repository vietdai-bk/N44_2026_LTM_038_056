"""Kiểm chứng nguyên nhân chênh lệch giữa mô hình giải tích (công thức paper) và NS-3 LTE.

1. Đường cong một liên kết: 1 UAV, 1 user, không nhiễu, gửi bão hòa; quét công suất phát để quét SINR.
   So hiệu suất phổ NS-3 với Shannon, 3GPP 36.942 (alpha=0.6, trần 4.4) và khớp alpha/trần từ dữ liệu.
2. Hiệu chỉnh: tính lại mô hình cho các run NS-3 đã có (A/B/C) với alpha/trần đã khớp, xem tỷ lệ NS-3/mô hình.
3. SINR từng user: mô hình tính vs NS-3 đo (trace DlRsrpSinrStats) trên cùng (khe, user).
4. Phân rã: Shannon -> 36.942 -> trần LTE -> độ dốc LTE -> NS-3, cho thấy mỗi cơ chế chiếm bao nhiêu.
5. (--demand-run) Delay và mất gói: so các biến thể lý thuyết hàng đợi với NS-3 trên một run uavsim.ns3 có demand_mbps.

python -m uavsim.validate --runs experiments/results/ns3-interference/*/
"""
import argparse
import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from pathlib import Path

import numpy as np

from .algorithms import REGISTRY
from .channel import channel_gain
from .config import SimConfig
from .network import Network
from .ns3 import WARMUP, _load, ns3_command, run_ns3, trace_stats
from .run import episode_loss, run_episode, summarize


# ------------------------------------------------------------------ 1. đường cong một liên kết
def link_point(p_dbm: float, root: Path, slots: int = 6, horiz: float = 100.0) -> dict:
    """1 UAV ở (500, 500, H), 1 user cách ngang `horiz` m, gửi 200 Mbps (bão hòa)."""
    cfg = SimConfig(num_uavs=1, num_users=1, slots=slots, p_max=10 ** ((p_dbm - 30) / 10), rate_model="lte")
    d = root / f"p{p_dbm:+.0f}dBm"
    plan = d / "plan"
    plan.mkdir(parents=True, exist_ok=True)
    uav, user = (500.0, 500.0), (500.0 + horiz, 500.0)
    (plan / "uavs.csv").write_text("slot,uav,x,y\n" + "".join(f"{s},0,{uav[0]},{uav[1]}\n" for s in range(slots + 1)))
    (plan / "users.csv").write_text("slot,user,x,y,serving,rate_bps\n" + "".join(
        f"{s},0,{user[0]},{user[1]},{0 if s < slots else -1},{200e6 if s < slots else 0}\n" for s in range(slots + 1)))
    run_ns3(ns3_command(cfg, plan, d, "pf", 1.0, traces=True), d, timeout=600)

    with open(d / "ns3_slots.csv") as f:
        rows = [r for r in csv.DictReader(f) if int(r["slot"]) >= 1]  # bỏ khe 0 (hàng đợi đang lấp đầy)
    app = sum(int(r["rx_bytes"]) for r in rows) * 8 / (len(rows) * cfg.dt)
    ts = trace_stats(d, cfg)
    g = channel_gain(np.array([uav]), np.array([user]), cfg, None)[0, 0]
    snr_model = cfg.p_max * g / (cfg.noise_psd * cfg.bandwidth)
    return {
        "p_dbm": p_dbm,
        "snr_model_db": 10 * np.log10(snr_model),
        "sinr_ns3_db": ts["sinr_db_median"],
        "mcs": ts["mcs_mean"],
        "bler": ts["bler_first_tx"],
        "se_ns3_phy": ts["phy_goodput_mbps"] * 1e6 / cfg.bandwidth,
        "se_ns3_app": app / cfg.bandwidth,
    }


def se_formula(sinr_lin, alpha, se_max):
    se = np.minimum(alpha * np.log2(1 + sinr_lin), se_max)
    return np.where(sinr_lin < 0.1, 0.0, se)


def fit_alpha_cap(sinr_db, se):
    """Khớp SE = min(alpha*log2(1+SINR), cap): cap = SE lớn nhất đo được, alpha bình phương tối thiểu trên vùng chưa bão hòa."""
    sinr_db, se = np.asarray(sinr_db), np.asarray(se)
    cap = float(se.max())
    x = np.log2(1 + 10 ** (sinr_db / 10))
    mask = (se < 0.9 * cap) & (sinr_db > -5)
    alpha = float(np.sum(x[mask] * se[mask]) / np.sum(x[mask] ** 2)) if mask.any() else 0.6
    return alpha, cap


# ------------------------------------------------------------------ 2 + 3. các run A/B/C đã có
def replay_model(cfg: SimConfig, algo_name: str):
    """Chạy lại mô hình (tất định) để lấy SINR và rate từng (khe, user)."""
    net = Network(cfg)
    algo = REGISTRY[algo_name]()
    algo.reset(net)
    sinr, rate = [], []
    while not net.done:
        a = algo.act(net)
        sinr.append(net.sinr(a))
        rate.append(net.rates(a))
        net.step(a)
    return np.array(sinr), np.array(rate)


def ns3_sinr_per_slot(d: Path, cfg: SimConfig) -> np.ndarray:
    """SINR trung vị (tuyến tính) mỗi (khe, user) từ DlRsrpSinrStats; IMSI = user + 1."""
    tr = _load(d / "DlRsrpSinrStats.txt", (0, 2, 5))  # time, IMSI, sinr
    out = np.full((cfg.slots, cfg.num_users), np.nan)
    slot = np.floor((tr[:, 0] - WARMUP) / cfg.dt).astype(int)
    for s in range(cfg.slots):
        for k in range(cfg.num_users):
            v = tr[(slot == s) & (tr[:, 1] == k + 1), 2]
            if v.size:
                out[s, k] = np.median(v)
    return out


def analyze_run(d: Path, base: dict, algo: str, seed: int, alpha: float, cap: float) -> dict:
    keys = {f.name for f in fields(SimConfig)}
    cfg = SimConfig(**{**{k: v for k, v in base.items() if k in keys}, "seed": seed})
    variant = lambda **kw: replay_model(SimConfig(**{**cfg.to_dict(), **kw}), algo)[1].sum(1).mean() / 1e6  # noqa: E731
    sinr_m, rate_std = replay_model(cfg, algo)
    _, rate_cal = replay_model(SimConfig(**{**cfg.to_dict(), "lte_alpha": alpha, "lte_se_max": cap}), algo)
    with open(d / "ns3_slots.csv") as f:
        ns3_sum = sum(int(r["rx_bytes"]) for r in csv.DictReader(f)) * 8 / (cfg.slots * cfg.dt)
    has_trace = any(d.glob("DlRsrpSinrStats.txt*"))
    sinr_n = ns3_sinr_per_slot(d, cfg) if has_trace else np.full_like(sinr_m, np.nan)
    ok = (sinr_m > 0) & np.isfinite(sinr_n) & (sinr_n > 0)
    err_db = 10 * np.log10(sinr_n[ok]) - 10 * np.log10(sinr_m[ok])
    phy = trace_stats(d, cfg)["phy_goodput_mbps"] * 1e6 if has_trace else np.nan
    return {
        "run": d.parent.name, "algo": algo, "seed": seed,
        # chuỗi phân rã: Shannon (paper) -> 36.942 -> chỉ hạ trần -> hạ cả độ dốc -> NS-3
        "shannon_mbps": variant(rate_model="shannon"),
        "lte36942_mbps": variant(rate_model="lte", lte_alpha=0.6, lte_se_max=4.4),
        "cap_only_mbps": variant(rate_model="lte", lte_alpha=0.6, lte_se_max=cap),
        "model_std_mbps": rate_std.sum(1).mean() / 1e6,
        "model_cal_mbps": rate_cal.sum(1).mean() / 1e6,
        "ns3_app_mbps": ns3_sum / 1e6,
        "ns3_phy_mbps": phy / 1e6,
        "ratio_std": ns3_sum / rate_std.sum(1).mean(),
        "ratio_cal": ns3_sum / rate_cal.sum(1).mean(),
        "ratio_cal_phy": phy / rate_cal.sum(1).mean(),
        "sinr_err_db_median": float(np.median(err_db)) if err_db.size else np.nan,
        "sinr_err_db_mae": float(np.mean(np.abs(err_db))) if err_db.size else np.nan,
        "_sinr_model_db": 10 * np.log10(sinr_m[ok]), "_sinr_ns3_db": 10 * np.log10(sinr_n[ok]),
    }


def plot(out: Path, pts: list[dict], alpha: float, cap: float, runs: list[dict]):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    ax = axes[0]
    x = np.linspace(-12, 52, 300)
    lin = 10 ** (x / 10)
    ax.plot(x, np.log2(1 + lin), ":", color="gray", label="Shannon thuần")
    ax.plot(x, se_formula(lin, 0.6, 4.4), "--", color="C0", label="3GPP 36.942 (α=0.6, trần 4.4)")
    ax.plot(x, se_formula(lin, alpha, cap), "-", color="C2", label=f"khớp từ NS-3 (α={alpha:.2f}, trần {cap:.2f})")
    s = [p["sinr_ns3_db"] for p in pts]
    ax.scatter(s, [p["se_ns3_phy"] for p in pts], color="C3", zorder=3, label="NS-3 goodput PHY")
    ax.scatter(s, [p["se_ns3_app"] for p in pts], color="C1", marker="x", zorder=3, label="NS-3 payload UDP")
    ax.set(xlabel="SINR (dB)", ylabel="hiệu suất phổ (bit/s/Hz)", ylim=(0, 6),
           title="Kiểm chứng 1: một liên kết, không nhiễu")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    ax = axes[1]
    for i, name in enumerate(dict.fromkeys(r["run"] for r in runs)):
        sm = np.concatenate([r["_sinr_model_db"] for r in runs if r["run"] == name])
        sn = np.concatenate([r["_sinr_ns3_db"] for r in runs if r["run"] == name])
        ax.scatter(sm, sn, s=4, alpha=0.4, color=f"C{i}", label=name)
    lim = (-10, 55)
    ax.plot(lim, lim, "k--", lw=1)
    ax.set(xlim=lim, ylim=lim, xlabel="SINR mô hình (dB)", ylabel="SINR NS-3 đo được (dB)",
           title="Kiểm chứng 3: SINR từng (khe, user)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, markerscale=4)
    fig.tight_layout()
    fig.savefig(out / "validation.png", dpi=130)


def plot_decomposition(out: Path, runs: list[dict]):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    steps = [("shannon_mbps", "Shannon\n(paper)"), ("lte36942_mbps", "3GPP 36.942\nα 0.6, trần 4.4"),
             ("cap_only_mbps", "hạ trần\n→ 3.51"), ("model_cal_mbps", "hạ độ dốc\nα → 0.40"),
             ("ns3_phy_mbps", "NS-3\ngoodput PHY"), ("ns3_app_mbps", "NS-3\npayload UDP")]
    names = list(dict.fromkeys(r["run"] + " / " + r["algo"] for r in runs))
    fig, ax = plt.subplots(figsize=(13, 5))
    w = 0.8 / len(names)
    for i, n in enumerate(names):
        rs = [r for r in runs if r["run"] + " / " + r["algo"] == n]
        vals = [np.nanmean([r[k] for r in rs]) for k, _ in steps]
        ax.bar(np.arange(len(steps)) + i * w, vals, w, label=n)
    ax.set_xticks(np.arange(len(steps)) + 0.4 - w / 2, [lbl for _, lbl in steps], fontsize=9)
    ax.set(ylabel="throughput tổng (Mbps)", title="Từ lý thuyết paper tới NS-3: phân rã theo từng cơ chế")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out / "decomposition.png", dpi=130)


def demand_variants(root: Path, fit: dict) -> list[dict]:
    """Tính lại lý thuyết hàng đợi (5 biến thể) cho từng run NS-3 có demand_mbps, đặt cạnh số đo NS-3."""
    meta = json.loads((root / "config.json").read_text())
    keys = {f.name for f in fields(SimConfig)}
    cal = {"rate_model": "lte", **fit}
    variants = {
        "paper": {},                                                      # Shannon, chia tĩnh, nhiễu tối đa
        "cal": cal,                                                       # + ánh xạ SINR->rate của LTE
        "cal_wc": {**cal, "work_conserving": True},                       # + chia băng linh hoạt
        "cal_lc": {**cal, "load_coupled": True},                          # + nhiễu theo tải
        "cal_wc_lc": {**cal, "work_conserving": True, "load_coupled": True},
    }
    out = []
    with open(root / "summary_ns3.csv") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        base = {**{k: v for k, v in meta.items() if k in keys}, "seed": int(r["seed"]),
                "demand_mbps": float(r["offered_per_user_mbps"])}
        row = {"algo": r["algo"], "demand_mbps": base["demand_mbps"], "seed": base["seed"],
               "ns3_thr": float(r["ns3_sum_mbps"]), "ns3_loss": float(r["ns3_loss"]),
               "ns3_delay": float(r["ns3_delay_ms"]), "ns3_min": float(r["ns3_min_mbps"])}
        for v, kw in variants.items():
            cfg = SimConfig(**{**base, **kw})
            rows_m = run_episode(cfg, REGISTRY[r["algo"]]())[0]
            sm = summarize(rows_m, cfg)
            row |= {f"{v}_thr": sm["throughput"] / 1e6, f"{v}_loss": episode_loss(rows_m, cfg), f"{v}_delay": sm["delay_ms"],
                    f"{v}_min": sm["min_throughput"] / 1e6}
        out.append(row)
    return out


def plot_demand(out_dir: Path, rows: list[dict]):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    algos = list(dict.fromkeys(r["algo"] for r in rows))
    shown = [("paper", "lý thuyết paper (Shannon)", ":"), ("cal", "+ ánh xạ LTE", "--"),
             ("cal_wc_lc", "+ chia linh hoạt + nhiễu theo tải", "-."), ("ns3", "NS-3 (đo)", "-")]
    fig, axes = plt.subplots(len(algos), 3, figsize=(16, 4 * len(algos)), squeeze=False)
    for i, a in enumerate(algos):
        rs = [r for r in rows if r["algo"] == a]
        x = sorted({r["demand_mbps"] for r in rs})
        for j, (metric, ylabel, scale, log) in enumerate([("thr", "throughput tổng (Mbps)", 1, False),
                                                          ("delay", "delay (ms)", 1, True), ("loss", "mất gói (%)", 100, False)]):
            ax = axes[i, j]
            for v, label, ls in shown:
                y = [scale * np.mean([r[f"{v}_{metric}"] for r in rs if r["demand_mbps"] == d]) for d in x]
                ax.plot(x, y, ls, marker="o" if v == "ns3" else None, lw=2 if v == "ns3" else 1.4,
                        color="k" if v == "ns3" else None, label=label)
            ax.set(title=f"{a}: {ylabel}", xlabel="lưu lượng mỗi user (Mbps)", ylabel=ylabel)
            if log:
                ax.set_yscale("log")
            ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "theory_vs_ns3.png", dpi=120)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--runs", nargs="+", default=[], help="thư mục kết quả uavsim.ns3 chạy với --traces")
    p.add_argument("--demand-run", help="thư mục kết quả uavsim.ns3 chạy với demand_mbps (so delay, mất gói)")
    p.add_argument("--fit", help="fit.json có sẵn; bỏ qua bước đo đường cong liên kết")
    p.add_argument("--powers", type=float, nargs="+", default=list(range(-40, 35, 5)), help="dBm, quét SINR")
    p.add_argument("--out", default="experiments/results/validation")
    p.add_argument("--parallel", type=int, default=os.cpu_count() // 2 or 1)
    p.add_argument("--glob", default="*_seed*", help="chọn thư mục run trong mỗi --runs, vd. '*_load1_seed*'")
    args = p.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.fit:
        fit = json.loads(Path(args.fit).read_text())
    if args.demand_run and args.fit:
        return _demand_only(Path(args.demand_run), fit)
    print(f"1) Đường cong một liên kết: {len(args.powers)} điểm công suất ...", flush=True)
    with ThreadPoolExecutor(args.parallel) as ex:
        pts = list(ex.map(lambda pw: link_point(pw, out / "link"), args.powers))
    pts.sort(key=lambda p: p["sinr_ns3_db"])
    alpha, cap = fit_alpha_cap([p["sinr_ns3_db"] for p in pts], [p["se_ns3_phy"] for p in pts])
    with open(out / "link_curve.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(pts[0]) + ["se_3gpp", "se_fit"])
        w.writeheader()
        for q in pts:
            lin = 10 ** (q["sinr_ns3_db"] / 10)
            w.writerow({**q, "se_3gpp": float(se_formula(lin, 0.6, 4.4)), "se_fit": float(se_formula(lin, alpha, cap))})
    print(f"{'P (dBm)':>8}{'SNR mô hình':>13}{'SINR NS-3':>11}{'MCS':>6}{'BLER':>8}{'SE NS-3':>9}{'SE 36.942':>10}")
    for q in pts:
        lin = 10 ** (q["sinr_ns3_db"] / 10)
        print(f"{q['p_dbm']:>8.0f}{q['snr_model_db']:>13.1f}{q['sinr_ns3_db']:>11.1f}{q['mcs']:>6.1f}"
              f"{q['bler']:>8.3f}{q['se_ns3_phy']:>9.2f}{float(se_formula(lin, 0.6, 4.4)):>10.2f}")
    print(f"Khớp: alpha = {alpha:.3f}, trần = {cap:.3f} bit/s/Hz (3GPP 36.942: 0.6, 4.4)\n")

    print("2+3) Hiệu chỉnh mô hình và so SINR trên các run có sẵn ...", flush=True)
    runs = []
    if not args.runs:
        raise SystemExit("cần --runs (hoặc --demand-run kèm --fit)")
    for rd in map(Path, args.runs):
        meta = json.loads((rd / "config.json").read_text())
        for d in sorted(rd.glob(args.glob)):
            algo = d.name.split("_load")[0]
            seed = int(d.name.rsplit("seed", 1)[1])
            runs.append(analyze_run(d, meta, algo, seed, alpha, cap))
    cols = [k for k in runs[0] if not k.startswith("_")]
    with open(out / "calibration.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(runs)
    show = ["shannon_mbps", "lte36942_mbps", "cap_only_mbps", "model_cal_mbps", "ns3_phy_mbps", "ns3_app_mbps",
            "ratio_cal", "sinr_err_db_median", "sinr_err_db_mae"]
    print(f"{'run / algo':38}" + "".join(f"{k:>15}" for k in show))
    for name in dict.fromkeys((r["run"], r["algo"]) for r in runs):
        rs = [r for r in runs if (r["run"], r["algo"]) == name]
        print(f"{' / '.join(name):38}" + "".join(f"{np.nanmean([r[k] for r in rs]):>15.3f}" for k in show))
    fit = {"lte_alpha": alpha, "lte_se_max": cap}
    (out / "fit.json").write_text(json.dumps(fit, indent=2))
    plot(out, pts, alpha, cap, [r for r in runs if r["_sinr_model_db"].size])
    plot_decomposition(out, runs)
    if args.demand_run:
        _demand_only(Path(args.demand_run), fit)
    print(f"Kết quả: {out.resolve()}")



def _demand_only(root: Path, fit: dict):
    print(f"5) Delay và mất gói: lý thuyết vs NS-3 trên {root} ...", flush=True)
    rows = demand_variants(root, fit)
    with open(root / "theory_variants.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    variants = ["paper", "cal", "cal_wc", "cal_lc", "cal_wc_lc"]
    print(f"{'biến thể':12}{'|sai số thr|':>14}{'|sai số mất gói|':>18}{'delay: trung vị |log10 tỷ lệ|':>32}")
    for v in variants:
        e_t = np.mean([abs(r[f"{v}_thr"] - r["ns3_thr"]) / r["ns3_thr"] for r in rows]) * 100
        e_l = np.mean([abs(r[f"{v}_loss"] - r["ns3_loss"]) for r in rows]) * 100
        e_d = np.median([abs(np.log10(max(r[f"{v}_delay"], 1e-3) / r["ns3_delay"])) for r in rows])
        print(f"{v:12}{e_t:>13.1f}%{e_l:>14.1f} điểm{e_d:>32.2f}")
    plot_demand(root, rows)
    print(f"Kết quả: {(root / 'theory_variants.csv').resolve()}, {(root / 'theory_vs_ns3.png').resolve()}")


if __name__ == "__main__":
    main()
