"""Thuật toán baseline. Thuật toán mới chỉ cần có reset(net) và act(net) -> Action, rồi thêm vào REGISTRY."""
from functools import partial

import numpy as np

from .channel import path_loss_db
from .network import Action, Network

# Hằng số ánh xạ SINR -> hiệu suất phổ đo được trên NS-3 LTE 10 MHz SISO (thí nghiệm một liên kết, validate.py)
LTE_CAL_ALPHA, LTE_CAL_SE_MAX = 0.401, 3.514


def associate_max_gain(net: Network) -> np.ndarray:
    return net.gain.argmax(0)


def split_by_weight(assoc, weights, M) -> np.ndarray:
    """Chia băng thông mỗi UAV cho user của nó theo tỷ lệ weights."""
    total = np.bincount(assoc, weights, M)
    return weights / total[assoc]


def power_by_bw(bw, p_max) -> np.ndarray:
    # PSD phẳng p_max/B trên phần băng được dùng
    return bw * p_max


def kmeans(points, centroids, iters=20):
    """Lloyd k-means khởi tạo từ centroids cho trước, giữ nguyên thứ tự cụm."""
    c = centroids.copy()
    for _ in range(iters):
        dist = np.linalg.norm(points[:, None] - c[None], axis=-1)
        label = dist.argmin(1)
        for j in range(len(c)):
            if np.any(label == j):
                c[j] = points[label == j].mean(0)
            else:  # cụm rỗng: lấy user xa tâm của nó nhất, để UAV không đứng không
                far = dist[np.arange(len(points)), label].argmax()
                c[j], label[far] = points[far], j
    return c


def calibrated_se(cfg, uav_xy, user_xy, model="lte"):
    """Hiệu suất phổ dự đoán (bit/s/Hz), có nhiễu từ mọi UAV đang phục vụ. Trả về (assoc, se).

    model="lte": ánh xạ LTE đã hiệu chỉnh trên NS-3 (đề xuất). model="shannon": log2(1+SINR) như các bài báo, dùng cho
    baseline cùng mục tiêu để tách phần lợi ích do mô hình LTE."""
    horiz = np.linalg.norm(uav_xy[:, None, :] - user_xy[None, :, :], axis=-1)
    g = 10 ** (-path_loss_db(np.sqrt(horiz**2 + cfg.altitude**2), horiz, cfg) / 10)
    assoc = g.argmax(0)
    k = np.arange(cfg.num_users)
    psd = cfg.p_max / cfg.bandwidth * (np.bincount(assoc, minlength=cfg.num_uavs) > 0)
    sig = psd[assoc] * g[assoc, k]
    interf = psd @ g - sig if cfg.interference else 0.0
    sinr = sig / (interf + cfg.noise_psd)
    if model == "shannon":
        return assoc, np.log2(1 + sinr)
    se = np.where(sinr < 0.1, 0.0, np.minimum(LTE_CAL_ALPHA * np.log2(1 + sinr), LTE_CAL_SE_MAX))
    return assoc, se


SE_FLOOR = 0.05  # sàn SE khi chia băng: user mất sóng không hút hết băng của UAV


def fair_utility(cfg, uav_xy, user_xy, w=None, model="lte") -> tuple[float, int]:
    """(Σ w_k log(r_k + r_0), số UAV có user) với đúng cách chia băng của ifair: b_k ∝ w_k/max(SE_k, SE_FLOOR),
    r_k = b_k·B·SE_k. w = None: mọi user trọng số 1."""
    assoc, se = calibrated_se(cfg, uav_xy, user_xy, model)
    w = np.ones(cfg.num_users) if w is None else w
    x = w / np.maximum(se, SE_FLOOR)
    load = np.bincount(assoc, x, cfg.num_uavs)
    r = x / load[assoc] * cfg.bandwidth * se
    return float((w * np.log(r + 1e3)).sum()), int(np.count_nonzero(load))


_DIRS = [(np.cos(t), np.sin(t)) for t in np.arange(8) * np.pi / 4]


class Heuristic:
    """mobility: hover | kmeans | random | calib;  alloc: equal | maxmin | wmaxmin | ifair.

    calib (đề xuất): k-means rồi tinh chỉnh trên mô hình LTE đã hiệu chỉnh. UAV còn xa tâm cụm thì bay theo k-means;
    tới nơi thì mỗi khe thử đứng yên và 8 hướng × 2 cỡ bước, giữ nước đi làm tổng log rate dự đoán lớn nhất (có
    nhiễu, có trần LTE). Không nhận nước đi làm một UAV mất hết user: tắt một UAV giảm nhiễu tức thời nhưng dẫn
    tới nghiệm kém.
    ifair (đề xuất): b_k ∝ w_k/SE_k với SE_k tính bằng SINR thật (có nhiễu) và ánh xạ LTE đã hiệu chỉnh, w_k là trọng
    số nhóm của user (normal/important/critical). calib dùng cùng Σ w_k log r_k.
    weighted=False: bỏ qua nhóm (w = 1). rate="shannon": quyết định bằng Shannon thay cho LTE hiệu chỉnh.
    """

    def __init__(self, mobility="hover", alloc="equal", weighted=True, rate="lte"):
        self.mobility, self.alloc, self.weighted, self.rate = mobility, alloc, weighted, rate
        self.name = f"{mobility}-{alloc}" + ("" if weighted else "-noclass") + ("" if rate == "lte" else f"-{rate}")

    def _w(self, net: Network):
        return net.weight if self.weighted else None

    def reset(self, net: Network):
        self.rng = np.random.default_rng(net.cfg.seed + 1)

    def allocate(self, net: Network):
        c = net.cfg
        assoc = associate_max_gain(net)
        if self.alloc == "equal":
            w = np.ones(c.num_users)
        elif self.alloc == "ifair":
            se = calibrated_se(c, net.uav_xy, net.user_xy, self.rate)[1]
            w = (net.weight if self.weighted else 1.0) / np.maximum(se, SE_FLOOR)
        else:  # maxmin: b_k ∝ 1/SE_k cho rate bằng nhau trong mỗi UAV (bỏ qua nhiễu); wmaxmin: nhân trọng số nhóm
            snr = c.p_max / c.bandwidth * net.gain[assoc, np.arange(c.num_users)] / c.noise_psd
            w = (net.weight if self.alloc == "wmaxmin" else 1.0) / np.log2(1 + snr)
        bw = split_by_weight(assoc, w, c.num_uavs)
        return assoc, bw, power_by_bw(bw, c.p_max)

    def velocity(self, net: Network):
        c = net.cfg
        if self.mobility == "hover":
            return np.zeros((c.num_uavs, 2))
        if self.mobility == "random":
            ang = self.rng.uniform(0, 2 * np.pi, c.num_uavs)
            return c.v_max * np.stack([np.cos(ang), np.sin(ang)], 1)
        # kmeans: khởi tạo từ vị trí UAV nên UAV j luôn bay về cụm j gần nó
        delta = kmeans(net.user_xy, net.uav_xy) - net.uav_xy
        if self.mobility == "kmeans":
            return delta / c.dt  # Network cắt về v_max
        step = c.v_max * c.dt
        q = net.uav_xy.copy()
        for j in range(c.num_uavs):
            if np.linalg.norm(delta[j]) > step:  # còn đang bay tới tâm cụm
                q[j] = q[j] + delta[j] * step / np.linalg.norm(delta[j])
                continue
            best, (best_u, active) = np.zeros(2), fair_utility(c, q, net.user_xy, self._w(net), self.rate)
            for mv in (np.array(d) * step * f for f in (1.0, 0.25) for d in _DIRS):
                cand = q.copy()
                cand[j] = np.clip(q[j] + mv, 0, c.area)
                u, n = fair_utility(c, cand, net.user_xy, self._w(net), self.rate)
                if n >= active and u > best_u + 1e-9:
                    best, best_u = mv, u
            q[j] = np.clip(q[j] + best, 0, c.area)
        return (q - net.uav_xy) / c.dt

    def act(self, net: Network) -> Action:
        assoc, bw, power = self.allocate(net)
        return Action(assoc, bw, power, self.velocity(net))


# tên -> hàm tạo thuật toán
REGISTRY = {
    f"{m}-{a}": partial(Heuristic, m, a)
    for m in ("hover", "kmeans", "random")
    for a in ("equal", "maxmin")
}
# thuật toán đề xuất và hai bản tách thành phần (ablation)
REGISTRY |= {n: partial(Heuristic, *n.split("-")) for n in ("calib-ifair", "calib-equal", "kmeans-ifair")}
# baseline biết nhóm user: max-min có trọng số (rate trong mỗi UAV tỷ lệ với w), Shannon, bỏ qua nhiễu, như kmeans-maxmin
REGISTRY["kmeans-wmaxmin"] = partial(Heuristic, "kmeans", "wmaxmin")
# cùng mục tiêu Σ w log r với calib-ifair: bỏ qua nhóm user, hoặc quyết định bằng Shannon như các bài báo
REGISTRY |= {"calib-ifair-noclass": partial(Heuristic, "calib", "ifair", weighted=False),
             "calib-ifair-shannon": partial(Heuristic, "calib", "ifair", rate="shannon")}
