"""Trạng thái mạng multi-UAV BS -> user mặt đất, tiến theo khe thời gian.

Mỗi khe: thuật toán trả về Action (liên kết, băng thông, công suất, vận tốc UAV);
Network tính rate theo vị trí hiện tại, tính năng lượng bay, rồi di chuyển UAV/user.
"""
from dataclasses import dataclass

import numpy as np

from .channel import channel_gain
from .config import SimConfig
from .energy import rotary_power

TOL = 1e-6


@dataclass
class Action:
    assoc: np.ndarray     # [K] int, chỉ số UAV phục vụ user k, -1 = không phục vụ
    bw: np.ndarray        # [K] tỷ lệ băng thông của UAV phục vụ cấp cho user k, tổng mỗi UAV <= 1
    power: np.ndarray     # [K] W, tổng mỗi UAV <= p_max
    velocity: np.ndarray  # [M, 2] m/s, bị cắt về v_max


def queue_step(q, arrivals, capacity, buffer):
    """Một khe của hàng đợi dạng lỏng (Lyapunov): Q' = min(max(Q + A - C, 0), buffer).

    q, arrivals, capacity, buffer tính bằng bit. Trả về (Q', bit phục vụ, bit bị bỏ, Q trung bình trong khe).
    Lưu lượng đến và phục vụ coi như đều trong khe (CBR), nên Q trung bình = (Q đầu + Q cuối) / 2.
    """
    served = np.minimum(q + arrivals, capacity)
    q1 = q + arrivals - served
    dropped = np.maximum(q1 - buffer, 0.0)
    q1 = q1 - dropped
    return q1, served, dropped, (q + q1) / 2


def fifo_delay(hist, q, arrivals, capacity, buffer, t0, dt, n=200):
    """Tổng delay (bit*s) của các bit được phục vụ trong khe, hàng đợi FIFO dạng lỏng, tính chính xác theo đường tích lũy.

    hist: mỗi user một cặp list (thời điểm, bit đã nhận vào hàng đợi tích lũy) và tổng bit đã phục vụ; được cập nhật tại chỗ.
    Mỗi khe chia n bước con: bit phục vụ ở thời điểm t có delay = t - thời điểm nó đến (nghịch đảo đường đến tích lũy).
    Bit bị bỏ (đầy bộ đệm) không vào đường đến, giống DropTail bỏ gói đến khi đầy.
    """
    h = dt / n
    acc, srv = np.empty((n, len(q))), np.empty((n, len(q)))
    for i in range(n):
        srv[i] = np.minimum(q + arrivals / n, capacity / n)
        q = q + arrivals / n - srv[i]
        drop = np.maximum(q - buffer, 0.0)
        q = q - drop
        acc[i] = arrivals / n - drop
    t_end = t0 + h * np.arange(1, n + 1)
    total = np.zeros(len(q))
    for k, (ht, hc, served0) in enumerate(hist):
        ht = np.concatenate([ht, t_end])
        hc = np.concatenate([hc, hc[-1] + np.cumsum(acc[:, k])])
        cum = served0 + np.cumsum(srv[:, k])
        m = srv[:, k] > 0
        mid = (cum - srv[:, k] / 2)[m]               # bit giữa của phần phục vụ trong bước con
        j = np.searchsorted(hc, mid, "left")          # hc[j-1] < mid <= hc[j]: đoạn tăng chặt, không chia 0
        ta = ht[j - 1] + (mid - hc[j - 1]) / (hc[j] - hc[j - 1]) * (ht[j] - ht[j - 1])
        total[k] = np.sum((t_end[m] - h / 2 - ta) * srv[m, k])
        keep = max(np.searchsorted(hc, cum[-1], "left") - 1, 0)  # bỏ lịch sử đã phục vụ hết
        hist[k] = (ht[keep:], hc[keep:], cum[-1])
    return total


def waterfill(need, total=1.0):
    """Chia `total` cho các phần tử theo max-min: không ai nhận quá nhu cầu, phần dư chia đều cho người còn thiếu."""
    alloc = np.zeros(len(need))
    remaining = total
    order = np.argsort(need)
    for i, k in enumerate(order):
        alloc[k] = min(need[k], remaining / (len(order) - i))
        remaining -= alloc[k]
    return alloc


def jain(x) -> float:
    s = np.sum(x**2)
    return float(np.sum(x) ** 2 / (len(x) * s)) if s > 0 else 0.0


CLASS_NAMES = ("normal", "important", "critical")


def user_classes(cfg: SimConfig) -> np.ndarray:
    """Nhóm của từng user (0 normal, 1 important, 2 critical), cố định theo seed, rng riêng để không đổi vị trí user."""
    K = cfg.num_users
    n_crit = round(cfg.critical_frac * K)
    n_imp = min(round(cfg.important_frac * K), K - n_crit)
    cls = np.zeros(K, int)
    perm = np.random.default_rng([cfg.seed, 7]).permutation(K)
    cls[perm[:n_crit]], cls[perm[n_crit:n_crit + n_imp]] = 2, 1
    return cls


def class_metrics(thr, cls, cfg: SimConfig, demand_bps=None) -> dict:
    """Chỉ số từng nhóm có mặt: min tốc độ và tỷ lệ đạt QoS. Đạt QoS khi r ≥ r_min của nhóm; khi có lưu lượng đến,
    ngưỡng là min(r_min, 0.9·lưu lượng) vì user không thể nhận nhiều hơn phần được gửi tới."""
    out = {}
    for c, name in enumerate(CLASS_NAMES):
        k = cls == c
        if not k.any():
            continue
        need = cfg.class_rmin_mbps[c] * 1e6
        if demand_bps is not None:
            need = min(need, 0.9 * demand_bps)
        out[f"min_{name}"] = float(thr[k].min())
        out[f"sat_{name}"] = float(np.mean(thr[k] >= need))
    return out


class Network:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.reset(cfg.seed)

    def reset(self, seed: int | None = None):
        c = self.cfg
        self.rng = np.random.default_rng(c.seed if seed is None else seed)
        self.uav_xy = self.rng.uniform(0, c.area, (c.num_uavs, 2))
        self.user_xy = self._place_users()
        self.user_class = user_classes(c)
        self.weight = np.asarray(c.class_weights)[self.user_class]
        self.t = 0
        self.queue = np.zeros(c.num_users)  # bit đang chờ của mỗi user
        self.hist = [(np.zeros(1), np.zeros(1), 0.0) for _ in range(c.num_users)]  # cho fifo_delay
        self.util = np.ones(c.num_uavs)     # tỷ lệ băng mỗi UAV dùng ở khe trước (load_coupled)
        self.gain = channel_gain(self.uav_xy, self.user_xy, c, self.rng)

    def _place_users(self):
        c, rng = self.cfg, self.rng
        if c.user_layout == "uniform":
            return rng.uniform(0, c.area, (c.num_users, 2))
        centers = rng.uniform(0.15 * c.area, 0.85 * c.area, (c.num_uavs, 2))
        pts = centers[rng.integers(0, c.num_uavs, c.num_users)] + rng.normal(0, 0.08 * c.area, (c.num_users, 2))
        return np.clip(pts, 0, c.area)

    @property
    def done(self) -> bool:
        return self.t >= self.cfg.slots

    def check(self, a: Action):
        """Từ chối action vi phạm ràng buộc thay vì sửa lặng lẽ, để lỗi thuật toán lộ ra."""
        M, K, c = self.cfg.num_uavs, self.cfg.num_users, self.cfg
        if a.assoc.shape != (K,) or a.bw.shape != (K,) or a.power.shape != (K,) or a.velocity.shape != (M, 2):
            raise ValueError("sai shape của Action")
        if np.any((a.assoc < -1) | (a.assoc >= M)):
            raise ValueError("assoc ngoài [-1, M)")
        if np.any(a.bw < -TOL) or np.any(a.power < -TOL):
            raise ValueError("bw/power âm")
        served = a.assoc >= 0
        bw_sum = np.bincount(a.assoc[served], a.bw[served], M)
        p_sum = np.bincount(a.assoc[served], a.power[served], M)
        if np.any(bw_sum > 1 + TOL):
            raise ValueError(f"tổng băng thông vượt 1: {bw_sum}")
        if np.any(p_sum > c.p_max * (1 + TOL)):
            raise ValueError(f"tổng công suất vượt p_max: {p_sum}")

    def sinr(self, a: Action) -> np.ndarray:
        """SINR tuyến tính từng user (0 nếu không được phục vụ). Nhiễu: UAV j trải công suất đều trên cả băng (xấp xỉ PSD)."""
        c = self.cfg
        served = a.assoc >= 0
        k = np.flatnonzero(served & (a.bw > 0))
        out = np.zeros(c.num_users)
        if k.size == 0:
            return out
        m = a.assoc[k]
        signal = a.power[k] / (a.bw[k] * c.bandwidth) * self.gain[m, k]  # W/Hz
        interf = np.zeros(k.size)
        if c.interference:
            psd = np.bincount(a.assoc[served], a.power[served], c.num_uavs) / c.bandwidth
            if c.load_coupled and c.demand_mbps is not None:
                psd = psd * self.util
            interf = psd @ self.gain[:, k] - psd[m] * self.gain[m, k]
        out[k] = signal / (interf + c.noise_psd)
        return out

    def rates(self, a: Action) -> np.ndarray:
        """Rate (bit/s) từng user."""
        c = self.cfg
        sinr = self.sinr(a)
        se = np.log2(1 + sinr)
        if c.rate_model == "lte":  # 3GPP TR 36.942 A.1: SE = min(alpha*log2(1+SINR), SE_max), SINR < -10 dB thì 0
            se = np.where(sinr < 0.1, 0.0, np.minimum(c.lte_alpha * se, c.lte_se_max))
        return np.where(a.bw > 0, a.bw * c.bandwidth * se, 0.0)

    def _queue(self, r, a: Action) -> dict:
        """Hàng đợi mỗi user với lưu lượng CBR demand_mbps và tốc độ phục vụ r (bit/s)."""
        c = self.cfg
        arrivals = np.full(c.num_users, c.demand_mbps * 1e6 * c.dt)
        with np.errstate(divide="ignore", invalid="ignore"):
            se_hz = np.where(a.bw > 0, r / (a.bw * c.bandwidth), 0.0)  # bit/s/Hz của user trên băng của nó
            need = np.where(se_hz > 0, (self.queue + arrivals) / (se_hz * c.bandwidth * c.dt), np.inf)  # phần băng cần
        if c.work_conserving:  # chia lại băng của mỗi UAV theo nhu cầu thực (hàng đợi + lưu lượng đến)
            bw = np.zeros(c.num_users)
            for m in range(c.num_uavs):
                k = np.flatnonzero(a.assoc == m)
                if k.size:
                    bw[k] = waterfill(need[k], a.bw[k].sum())
            r = bw * c.bandwidth * se_hz
            used = bw
        else:
            used = np.minimum(need, a.bw)
        served_mask = a.assoc >= 0
        total = np.bincount(a.assoc[served_mask], a.bw[served_mask], c.num_uavs)
        self.util = np.bincount(a.assoc[served_mask], used[served_mask], c.num_uavs) / np.maximum(total, 1e-12)
        wait = fifo_delay(self.hist, self.queue, arrivals, r * c.dt, c.buffer_bytes * 8.0, self.t * c.dt, c.dt)
        self.queue, served, dropped, q_avg = queue_step(self.queue, arrivals, r * c.dt, c.buffer_bytes * 8.0)
        thr = served / c.dt
        # delay chờ FIFO chính xác của từng bit, cộng thời gian phát một gói ở tốc độ r
        with np.errstate(divide="ignore", invalid="ignore"):
            delay = np.where(served > 0, wait / np.maximum(served, 1e-9) + c.pkt_bytes * 8.0 / np.maximum(r, 1e-9), np.nan)
        return {
            "throughput": float(thr.sum()),
            "min_throughput": float(thr.min()),
            "delay_ms": float(np.nansum(delay * served) / served.sum() * 1e3) if served.sum() > 0 else float("nan"),
            "loss": float(dropped.sum() / arrivals.sum()),
            "queue_bits": float(self.queue.sum()),
            "thr_per_user": thr,
            "capacity": r,  # tốc độ phục vụ thực của từng user sau khi chia lại băng (link=ideal của NS-3 dùng)
        }

    def step(self, a: Action) -> dict:
        if self.done:
            raise RuntimeError("episode đã kết thúc, gọi reset()")
        c = self.cfg
        self.check(a)
        r = self.rates(a)
        speed = np.linalg.norm(a.velocity, axis=1)
        v = a.velocity * np.minimum(1.0, c.v_max / np.maximum(speed, 1e-12))[:, None]
        energy = rotary_power(np.linalg.norm(v, axis=1)) * c.dt
        metrics = {
            "t": self.t,
            "sum_rate": float(r.sum()),
            "min_rate": float(r.min()),
            "jain": jain(r),
            "coverage": float(np.mean(r >= c.r_min)),
            "energy": float(energy.sum()),
            "rates": r,
            "uav_energy": energy,
        }
        if c.demand_mbps is not None:
            metrics.update(self._queue(r, a))
        if c.important_frac or c.critical_frac:  # chỉ số từng nhóm: theo throughput nếu có lưu lượng, không thì theo rate
            if c.demand_mbps is not None:
                metrics.update(class_metrics(metrics["thr_per_user"], self.user_class, c, c.demand_mbps * 1e6))
            else:
                metrics.update(class_metrics(r, self.user_class, c))
        self.uav_xy = np.clip(self.uav_xy + v * c.dt, 0, c.area)
        if c.user_speed > 0:
            ang = self.rng.uniform(0, 2 * np.pi, c.num_users)
            step = c.user_speed * c.dt * np.stack([np.cos(ang), np.sin(ang)], 1)
            self.user_xy = np.clip(self.user_xy + step, 0, c.area)
        self.t += 1
        self.gain = channel_gain(self.uav_xy, self.user_xy, c, self.rng)
        return metrics
