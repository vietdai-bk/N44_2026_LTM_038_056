"""Tham số mô phỏng. Giá trị mặc định lấy theo các paper multi-UAV BS hay dùng (xem docs/MODEL.md)."""
import json
from dataclasses import asdict, dataclass, fields

# Al-Hourani et al., IEEE WCL 2014: (a, b, eta_LoS dB, eta_NLoS dB)
ENVIRONMENTS = {
    "suburban": (4.88, 0.43, 0.1, 21.0),
    "urban": (9.61, 0.16, 1.0, 20.0),
    "dense_urban": (12.08, 0.11, 1.6, 23.0),
    "highrise": (27.23, 0.08, 2.3, 34.0),
}


@dataclass
class SimConfig:
    # Topology
    num_uavs: int = 3
    num_users: int = 20
    area: float = 1000.0          # m, vùng vuông area x area
    altitude: float = 100.0       # m, độ cao bay cố định của UAV
    user_layout: str = "clustered"  # "uniform" | "clustered"
    user_speed: float = 0.0       # m/s, random walk; 0 = user đứng yên
    # Thời gian
    slots: int = 200
    dt: float = 1.0               # s mỗi khe
    v_max: float = 20.0           # m/s
    # Kênh
    channel: str = "al_hourani"   # "al_hourani" | "los" (beta0/d^2)
    environment: str = "urban"
    fc: float = 2e9               # Hz
    beta0_db: float = -60.0       # độ lợi kênh tại 1 m, chỉ dùng cho channel="los"
    rician_k_db: float | None = None  # None = không fading nhỏ
    # Vô tuyến
    bandwidth: float = 10e6       # Hz, mỗi UAV dùng lại toàn bộ băng (reuse 1)
    noise_psd_dbm: float = -169.0  # dBm/Hz
    p_max: float = 1.0            # W, tổng công suất phát mỗi UAV
    interference: bool = True     # nhiễu đồng kênh giữa các UAV
    rate_model: str = "shannon"   # "shannon" | "lte" (Shannon cắt ngọn, 3GPP TR 36.942)
    lte_alpha: float = 0.6        # rate_model="lte": SE = min(lte_alpha*log2(1+SINR), lte_se_max)
    lte_se_max: float = 4.4       # bit/s/Hz
    r_min: float = 1e6            # bit/s, ngưỡng tính coverage
    # Lưu lượng và hàng đợi (tùy chọn). None = full buffer: chỉ tính năng lực (rate), không có delay/mất gói
    demand_mbps: float | None = None  # lưu lượng CBR đến mỗi user (Mbps)
    buffer_bytes: int = 1048576   # hàng đợi mỗi user; 1 MiB khớp LteRlcUm::MaxTxBufferSize trong uav-lte.cc
    pkt_bytes: int = 1200         # kích thước gói, khớp payload UDP của NS-3
    # False: băng thông mỗi user cố định = b_k của thuật toán (như paper). True: trong mỗi UAV, phần băng user
    # không cần (hàng đợi rỗng) được chia lại cho user còn chờ (water-filling), giống scheduler LTE.
    work_conserving: bool = False
    # False: mọi UAV luôn phát đủ công suất trên cả băng nên gây nhiễu tối đa (như paper). True: nhiễu từ UAV j nhân
    # với tỷ lệ băng UAV j thực sự dùng ở khe trước (load-coupled interference), giống eNB chỉ phát trên RB được cấp.
    load_coupled: bool = False
    # Ba nhóm user (normal, important, critical): tỷ lệ important/critical; còn lại là normal. Mặc định 0 = mọi user như
    # nhau (giữ nguyên các thí nghiệm cũ). Nhóm được bốc bằng rng riêng nên không làm đổi vị trí user.
    important_frac: float = 0.0
    critical_frac: float = 0.0
    class_weights: tuple = (1.0, 2.0, 4.0)     # trọng số w trong Σ w log r, theo (normal, important, critical)
    class_rmin_mbps: tuple = (0.5, 1.0, 2.0)   # tốc độ tối thiểu mong muốn theo nhóm (Mbps), dùng để chấm QoS từng nhóm
    seed: int = 0

    def __post_init__(self):
        if self.channel not in ("al_hourani", "los"):
            raise ValueError(f"channel không hợp lệ: {self.channel}")
        if self.environment not in ENVIRONMENTS:
            raise ValueError(f"environment phải thuộc {list(ENVIRONMENTS)}")
        if self.rate_model not in ("shannon", "lte"):
            raise ValueError(f"rate_model không hợp lệ: {self.rate_model}")
        if self.user_layout not in ("uniform", "clustered"):
            raise ValueError(f"user_layout không hợp lệ: {self.user_layout}")
        if min(self.num_uavs, self.num_users, self.slots) < 1:
            raise ValueError("num_uavs, num_users, slots phải >= 1")
        if not (0 <= self.important_frac and 0 <= self.critical_frac and self.important_frac + self.critical_frac <= 1):
            raise ValueError("important_frac, critical_frac phải >= 0 và tổng <= 1")
        self.class_weights, self.class_rmin_mbps = tuple(self.class_weights), tuple(self.class_rmin_mbps)
        if len(self.class_weights) != 3 or len(self.class_rmin_mbps) != 3 or min(self.class_weights) <= 0:
            raise ValueError("class_weights (dương) và class_rmin_mbps phải có 3 phần tử: normal, important, critical")

    @property
    def noise_psd(self) -> float:  # W/Hz
        return 10 ** ((self.noise_psd_dbm - 30) / 10)

    @classmethod
    def from_json(cls, path: str, **overrides) -> "SimConfig":
        with open(path) as f:
            data = json.load(f)
        unknown = set(data) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"khóa cấu hình lạ: {sorted(unknown)}")
        return cls(**{**data, **overrides})

    def to_dict(self) -> dict:
        return asdict(self)
