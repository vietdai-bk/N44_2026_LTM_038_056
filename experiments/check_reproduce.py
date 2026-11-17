"""In các con số chính của E1–E12 từ thư mục kết quả, để so với docs/TAI_LAP_KET_QUA.md.

python experiments/check_reproduce.py [thư mục kết quả]     (mặc định experiments/results)
Chỉ đọc file đã có, không chạy thí nghiệm. Mỗi dòng có dạng "khóa = giá trị"; so từng dòng với bảng trong tài liệu.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

R = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "results"


def rows(path):
    with open(R / path) as f:
        return list(csv.DictReader(f))


def pick(rs, **kw):
    out = [r for r in rs if all(float(r[k]) == v if isinstance(v, float) else r[k] == v for k, v in kw.items())]
    assert len(out) == 1, (kw, len(out))
    return out[0]


def show(key, value, fmt="{:.3f}"):
    print(f"{key:<44} = {fmt.format(value)}")


def section(name, fn):
    print(f"\n# {name}")
    try:
        fn()
    except (FileNotFoundError, KeyError, AssertionError) as e:  # thiếu thí nghiệm nào thì bỏ qua mục đó
        print(f"(bỏ qua: {type(e).__name__} {e})")


def e1():
    g = defaultdict(list)
    for r in rows("demo/summary.csv"):
        g[r["algo"]].append(r)
    for a in sorted(g):
        show(f"E1 {a} sum_rate_mbps", np.mean([float(r["sum_rate"]) for r in g[a]]) / 1e6, "{:.1f}")
        show(f"E1 {a} min_rate_mbps", np.mean([float(r["min_rate"]) for r in g[a]]) / 1e6, "{:.2f}")


def e2():
    rs = rows("ns3-matrix/aggregate_ns3.csv")
    for a in ("hover-equal", "kmeans-equal", "kmeans-maxmin"):
        for load in (0.5, 1.0):
            r = pick(rs, algo=a, load=load)
            show(f"E2 {a} load{load} ns3_sum_mbps", float(r["ns3_sum_mbps"]), "{:.1f}")
            show(f"E2 {a} load{load} delivered", float(r["delivered_ratio"]))
            show(f"E2 {a} load{load} ns3_min_mbps", float(r["ns3_min_mbps"]))


def e4():
    fit = json.loads((R / "validation/fit.json").read_text())
    show("E4 lte_alpha", fit["lte_alpha"], "{:.4f}")
    show("E4 lte_se_max", fit["lte_se_max"], "{:.4f}")
    g = defaultdict(list)
    for r in rows("validation/calibration.csv"):
        g[r["run"]].append(r)
    for run in sorted(g):
        for c in ("shannon_mbps", "lte36942_mbps", "model_cal_mbps", "ns3_app_mbps", "ratio_cal"):
            show(f"E4 {run} {c}", np.mean([float(r[c]) for r in g[run]]), "{:.2f}")


def e5():
    rs = rows("ns3-demand-lte/aggregate_ns3.csv")
    for d in (1.0, 2.0, 4.0):
        r = pick(rs, algo="kmeans-equal", load=d)
        for c in ("model_thr_mbps", "ns3_sum_mbps", "model_delay_ms", "ns3_delay_ms", "ns3_loss"):
            show(f"E5 kmeans-equal {d}Mbps {c}", float(r[c]), "{:.3f}")


def e6():
    def load(d, a):
        return {(float(r["offered_per_user_mbps"]), r["seed"]): float(r["ns3_min_mbps"])
                for r in rows(f"{d}/summary_ns3.csv") if r["algo"] == a}
    for base, alt in (("hover-equal", "hover-maxmin"), ("kmeans-equal", "kmeans-maxmin")):
        b, m = load("ns3-demand-lte", base), load("ns3-demand-wpf-lte", alt)
        for d in (1.0, 2.0, 4.0):
            ks = [k for k in b if k[0] == d]
            show(f"E6 {alt}/{base} {d}Mbps min_gain", np.mean([m[k] for k in ks]) / np.mean([b[k] for k in ks]) - 1)


def e7():
    worst = 0.0
    for d in ("ns3-demand-ideal", "ns3-demand-wpf-ideal", "ns3-proposed-ideal"):
        for r in rows(f"{d}/summary_ns3.csv"):
            worst = max(worst, abs(float(r["ns3_sum_mbps"]) / float(r["model_thr_mbps"]) - 1))
    show("E7 max |ns3_ideal/model - 1| throughput", worst, "{:.5f}")


def e10():
    rs = rows("proposed.csv")
    for a in ("kmeans-equal", "kmeans-maxmin", "kmeans-ifair", "calib-equal", "calib-ifair"):
        for d in (1.0, 2.0, 4.0):
            r = pick(rs, algo=a, demand_mbps=d)
            show(f"E10 {a} {d}Mbps min_mbps", float(r["ns3_min_mbps"]))
            show(f"E10 {a} {d}Mbps sum_mbps", float(r["ns3_sum_mbps"]), "{:.2f}")
            show(f"E10 {a} {d}Mbps min_ratio_vs_equal", float(r["min_ratio_vs_base"]))


def e11():
    rs = rows("classes.csv")
    for a in ("kmeans-equal", "kmeans-maxmin", "kmeans-wmaxmin", "calib-ifair-noclass", "calib-ifair-shannon", "calib-ifair"):
        for d in (2.0, 4.0):
            r = pick(rs, algo=a, demand_mbps=d)
            show(f"E11 {a} {d}Mbps sat_critical", float(r["sat_critical"]))
            show(f"E11 {a} {d}Mbps min_critical", float(r["min_critical"]))
            show(f"E11 {a} {d}Mbps min_normal", float(r["min_normal"]))
            show(f"E11 {a} {d}Mbps thr_mbps", float(r["thr_mbps"]), "{:.2f}")


def e12():
    for r in rows("websocket.csv"):
        n = r["clients"]
        show(f"E12 {n} client state_bytes", float(r["state_bytes"]), "{:.0f}")
        show(f"E12 {n} client state_per_s", float(r["state_per_s"]), "{:.2f}")
        show(f"E12 {n} client rtt_ms_p95 (phụ thuộc máy)", float(r["rtt_ms_p95"]), "{:.2f}")


print(f"Thư mục kết quả: {R}")
for name, fn in (("E1 mô hình", e1), ("E2 NS-3 theo tải", e2), ("E3–E4 hiệu chỉnh", e4), ("E5 lưu lượng", e5),
                 ("E6 WPF", e6), ("E7 ba tầng", e7), ("E10 thuật toán đề xuất", e10), ("E11 ba nhóm user", e11),
                 ("E12 WebSocket", e12)):
    section(name, fn)
