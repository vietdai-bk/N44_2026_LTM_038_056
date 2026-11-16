"""Biểu đồ ba tầng: lý thuyết (paper) / NS-3 liên kết lý tưởng / NS-3 LTE, theo lưu lượng mỗi user.

python experiments/plot_three_tier.py experiments/results/ns3-demand-ideal experiments/results/ns3-demand-lte out.png
Đọc aggregate_ns3.csv của hai lần chạy `uavsim.ns3 --link ideal|lte` cùng cấu hình; ghi thêm <out>.csv sai số từng tầng.
"""
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
# màu theo tầng (đó là điều hình cần nói), thứ tự cố định của bảng màu
THEORY, IDEAL, LTE = "#2a78d6", "#eb6834", "#1baf7a"
# (cột NS-3, cột mô hình, tên hàng, thang log, hệ số hiển thị)
PANELS = [("ns3_sum_mbps", "model_thr_mbps", "Throughput tổng\n(Mbps)", False, 1),
          ("ns3_min_mbps", "model_min_thr_mbps", "Min throughput\n(Mbps)", False, 1),
          ("ns3_delay_ms", "model_delay_ms", "Delay trung bình\n(ms, thang log)", True, 1),
          ("ns3_loss", "model_loss", "Mất gói\n(%)", False, 100)]


def load(d):
    with open(Path(d) / "aggregate_ns3.csv") as f:
        return [{k: (v if k == "algo" else float(v)) for k, v in r.items()} for r in csv.DictReader(f)]


def series(rows, algo, key):
    rs = sorted((r for r in rows if r["algo"] == algo), key=lambda r: r["offered_per_user_mbps"])
    return [r["offered_per_user_mbps"] for r in rs], [r[key] for r in rs], [r.get(key + "_std", 0) for r in rs]


def main(ideal_dir, lte_dir, out):
    ideal, lte = load(ideal_dir), load(lte_dir)
    algos = list(dict.fromkeys(r["algo"] for r in ideal))
    assert algos == list(dict.fromkeys(r["algo"] for r in lte)), "hai lần chạy phải cùng danh sách thuật toán"
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": MUTED,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlecolor": INK})
    # lưới nhỏ: hàng = chỉ số, cột = thuật toán; mỗi ô đúng 3 đường, 3 tầng
    fig, axes = plt.subplots(len(PANELS), len(algos), figsize=(3.6 * len(algos) + 1.2, 10.5), sharex=True,
                             squeeze=False, facecolor=SURFACE)
    for r, (key, mkey, label, log, k) in enumerate(PANELS):
        for c, algo in enumerate(algos):
            ax = axes[r, c]
            x, m, _ = series(ideal, algo, mkey)
            _, yi, _ = series(ideal, algo, key)
            _, yl, el = series(lte, algo, key)
            m, yi, yl, el = ([v * k for v in a] for a in (m, yi, yl, el))
            lo = [max(v - e, v * 0.1 if log else 0) for v, e in zip(yl, el)]
            ax.fill_between(x, lo, [v + e for v, e in zip(yl, el)], color=LTE, alpha=0.15, lw=0)
            ax.plot(x, yl, color=LTE, lw=2, marker="^", ms=6, label="NS-3 LTE (± độ lệch chuẩn)")
            ax.plot(x, m, color=THEORY, lw=2.5, label="Lý thuyết")
            # NS-3 lý tưởng: chỉ chấm, đè lên đường lý thuyết để thấy hai tầng trùng nhau
            ax.plot(x, yi, ls="none", marker="o", ms=8, mfc="none", mec=IDEAL, mew=2, label="NS-3 liên kết lý tưởng")
            if log:
                ax.set_yscale("log")
            ax.grid(color=GRID, lw=0.8)
            ax.spines[["top", "right"]].set_visible(False)
            ax.set_facecolor(SURFACE)
            if r == 0:
                ax.set_title(algo, fontsize=10, fontweight="bold")
            if c == 0:
                ax.set_ylabel(label)
            if r == len(PANELS) - 1:
                ax.set_xlabel("lưu lượng mỗi user (Mbps)")
    h, l = axes[0, 0].get_legend_handles_labels()
    order = [1, 2, 0]  # lý thuyết, lý tưởng, LTE
    fig.legend([h[i] for i in order], [l[i] for i in order], loc="upper center", ncol=3, frameon=False,
               labelcolor=INK, bbox_to_anchor=(0.5, 0.955), fontsize=10)
    n = int(lte[0]["n_seeds"])
    fig.suptitle("Lý thuyết và NS-3 liên kết lý tưởng trùng nhau; NS-3 LTE tách ra: khoảng chênh là do giao thức LTE",
                 color=INK, fontsize=12, fontweight="bold", y=0.995)
    fig.text(0.5, 0.005, f"Trung bình {n} seed. Lý thuyết: Shannon, hàng đợi FIFO 1 MiB. "
             "NS-3 lý tưởng: gói UDP thật trên liên kết có tốc độ = rate lý thuyết. NS-3 LTE: eNB/UE/EPC đầy đủ.",
             ha="center", color=MUTED, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.02, 1, 0.93))
    fig.savefig(out, dpi=150, facecolor=fig.get_facecolor())

    # bảng sai số tương đối so với lý thuyết: tầng 1 (ideal) kiểm chứng mô hình, tầng 2 (lte) là ảnh hưởng của LTE
    with open(Path(out).with_suffix(".csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["algo", "offered_per_user_mbps", "metric", "model", "ideal", "lte", "ideal_err", "lte_err"])
        for algo in algos:
            for key, mkey, *_ in PANELS:
                x, m, _ = series(ideal, algo, mkey)
                _, yi, _ = series(ideal, algo, key)
                xl, yl, _ = series(lte, algo, key)
                assert x == xl, f"{algo}: hai lần chạy khác mức tải"
                for xv, mv, iv, lv in zip(x, m, yi, yl):
                    err = (lambda v: (v - mv) / mv if mv else v - mv)  # loss = 0 thì dùng sai số tuyệt đối
                    w.writerow([algo, xv, key.removeprefix("ns3_"), f"{mv:.6g}", f"{iv:.6g}", f"{lv:.6g}",
                                f"{err(iv):+.4f}", f"{err(lv):+.4f}"])
    print(f"Đã ghi {out} và {Path(out).with_suffix('.csv')}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
