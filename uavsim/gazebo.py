"""Hiển thị 3D trong Gazebo (Harmonic, gz sim 8): kịch bản của mô hình, vẽ trên bãi thảm họa của ~/simulation/multi_uav.

- Kịch bản là của mô hình (SimConfig: số UAV, số user, vị trí user theo seed, vùng, độ cao), giống mọi thí nghiệm.
- Bãi (worlds/multi_uav_world.sdf, models/disaster_site) chỉ làm nền. 54 người có sẵn của bãi được bỏ trong một bản
  sao của disaster_site (mesh, texture dùng symlink; dự án multi_uav không bị sửa). User vẽ bằng hình người đơn giản (_marker).
- Tỷ lệ: 1 m Gazebo = 1/SCALE m mô hình, tâm vùng mô hình đặt ở tâm bãi (gốc tọa độ).
- Gazebo chỉ hiển thị: vị trí UAV và user được đặt qua service set_pose_vector (do system Physics áp, nên model không
  static; trọng lực tắt, không có va chạm nên chúng đứng yên giữa hai lần đặt).
- World dựng sẵn MAX_UAVS UAV và MAX_USERS user; model chưa dùng nằm dưới mặt đất. Nhờ vậy đổi số UAV, số user từ
  dashboard không cần khởi động lại Gazebo.
"""
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("MULTI_UAV_DIR", Path.home() / "simulation/multi_uav"))
WORLD = "multi_uav_world"
SITE_SIZE = 140.0  # m, mặt đất của world
SCALE = 0.1  # m Gazebo trên m mô hình
MAX_UAVS, MAX_USERS = 8, 60  # bể model dựng sẵn
PARK_Z = -50.0  # model chưa dùng nằm dưới mặt đất
UAV_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
RESIDENT = "_resident_"
UNSERVED = "#d01010"
MARK_Z = 0.0  # hình người đứng trên mặt đất
CAMERA = "0 -62 48 0 0.72 1.5708"  # nhìn chéo từ phía nam, thấy trọn vùng 100 × 100 m


def to_gz(xy_model, area: float) -> np.ndarray:
    return (np.asarray(xy_model, float) - area / 2) * SCALE


def prepare_site(out: Path, root: Path = ROOT):
    """Ghi out/models/disaster_site không có người (user do world_sdf vẽ riêng)."""
    src = root / "models/disaster_site"
    dst = out / "models/disaster_site"
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("meshes", "materials", "model.config"):
        link = dst / name
        if not link.exists():
            link.symlink_to(src / name)
    tree = ET.parse(src / "model.sdf")
    site = tree.getroot().find("model")
    removed = 0
    for parent in list(site.iter()):
        for child in list(parent):
            if child.tag == "model" and RESIDENT in child.get("name", ""):
                parent.remove(child)
                removed += 1
    if not removed:
        raise ValueError("disaster_site không có model người (*_resident_*), cấu trúc khác dự kiến")
    tree.write(dst / "model.sdf", encoding="unicode")


def _rgb(hex_color: str) -> str:
    return " ".join(f"{int(hex_color[i:i + 2], 16) / 255:.3f}" for i in (1, 3, 5))


def _uav(j: int, x: float, y: float, z: float) -> str:
    """Quadrotor vẽ bằng khối cơ bản, sải ~7 m Gazebo: thân và tay mang màu UAV (trùng dashboard), cánh quạt xám mờ."""
    c = _rgb(UAV_COLORS[j % len(UAV_COLORS)])
    col = f"<material><ambient>{c} 1</ambient><diffuse>{c} 1</diffuse><emissive>{c} 0.05</emissive></material>"
    prop = "<material><ambient>0.15 0.15 0.17 1</ambient><diffuse>0.15 0.15 0.17 1</diffuse></material>"
    arms = "".join(f"""
        <visual name="arm{i}"><pose>0 0 0 0 0 {yaw}</pose><geometry><box><size>6.4 0.45 0.35</size></box></geometry>{col}</visual>"""
                   for i, yaw in enumerate((0.7854, -0.7854)))
    rotors = "".join(f"""
        <visual name="rotor{i}"><pose>{sx * 2.26:.2f} {sy * 2.26:.2f} 0.35 0 0 0</pose><transparency>0.35</transparency>
          <geometry><cylinder><radius>1.2</radius><length>0.08</length></cylinder></geometry>{prop}</visual>"""
                     for i, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))))
    return f"""
    <model name="uav{j}"><pose>{x:.3f} {y:.3f} {z:.3f} 0 0 0</pose>
      <link name="base_link"><gravity>false</gravity>
        <visual name="body"><geometry><box><size>1.9 1.9 0.9</size></box></geometry>{col}</visual>{arms}{rotors}
        <visual name="beam"><pose>0 0 -40 0 0 0</pose><cast_shadows>false</cast_shadows><transparency>0.6</transparency>
          <geometry><cylinder><radius>0.12</radius><length>80</length></cylinder></geometry>{col}</visual>
      </link></model>"""


def _marker(c: int, k: int) -> str:
    """Hình người của user k, áo màu c (UAV c đang phục vụ, đỏ khi c == MAX_UAVS: không được phục vụ). Cao ~3,6 m
    Gazebo, phóng to chỉ để nhìn (ở tỷ lệ 1:10 người thật gần như không thấy); gốc model ở mặt đất."""
    rgb = _rgb(UNSERVED if c == MAX_UAVS else UAV_COLORS[c % len(UAV_COLORS)])
    return f"""
    <model name="mk{c}_{k}"><pose>0 0 {PARK_Z} 0 0 0</pose><link name="l"><gravity>false</gravity>
      <visual name="body"><pose>0 0 1.25 0 0 0</pose><geometry><cylinder><radius>0.6</radius><length>2.5</length></cylinder></geometry>
        <material><ambient>{rgb} 1</ambient><diffuse>{rgb} 1</diffuse><emissive>{rgb} 0.05</emissive></material></visual>
      <visual name="head"><pose>0 0 3.0 0 0 0</pose><geometry><sphere><radius>0.6</radius></sphere></geometry>
        <material><ambient>0.93 0.78 0.64 1</ambient><diffuse>0.93 0.78 0.64 1</diffuse></material></visual>
    </link></model>"""


RING = {1: ("imp", "#eda100", 1.5), 2: ("crit", "#d01010", 1.9)}  # nhóm -> (tiền tố model, màu, bán kính m Gazebo)


def _ring(c: int, k: int) -> str:
    """Vòng màu dưới chân user k thuộc nhóm c (vàng: important, đỏ: critical); user normal không có vòng."""
    prefix, color, radius = RING[c]
    rgb = _rgb(color)
    return f"""
    <model name="{prefix}{k}"><pose>0 0 {PARK_Z} 0 0 0</pose><link name="l"><gravity>false</gravity>
      <visual name="v"><pose>0 0 0.04 0 0 0</pose><cast_shadows>false</cast_shadows>
        <geometry><cylinder><radius>{radius}</radius><length>0.08</length></cylinder></geometry>
        <material><ambient>{rgb} 1</ambient><diffuse>{rgb} 1</diffuse></material></visual>
    </link></model>"""


def _all_markers() -> list[str]:
    return ([f"mk{c}_{k}" for c in range(MAX_UAVS + 1) for k in range(MAX_USERS)]
            + [f"{RING[c][0]}{k}" for c in RING for k in range(MAX_USERS)])


def _pad(xy_gz: np.ndarray, z: float, n: int) -> np.ndarray:
    """[n, 3]: các model đang dùng ở (x, y, z), phần còn lại của bể nằm ở PARK_Z."""
    if len(xy_gz) > n:
        raise ValueError(f"{len(xy_gz)} model vượt bể {n}")
    out = np.zeros((n, 3))
    out[:, 2] = PARK_Z
    out[:len(xy_gz), :2], out[:len(xy_gz), 2] = xy_gz, z
    return out


def world_sdf(uav_xy, altitude: float, area: float, root: Path = ROOT) -> str:
    """World có sẵn (nền) + bể MAX_UAVS UAV và MAX_USERS user, trọng lực tắt."""
    if area * SCALE > SITE_SIZE:
        raise ValueError(f"vùng {area:.0f} m × {SCALE} vượt mặt đất {SITE_SIZE:.0f} m của bãi")
    base = (root / f"worlds/{WORLD}.sdf").read_text()
    base = re.sub(r"<camera_pose>[^<]*</camera_pose>", f"<camera_pose>{CAMERA}</camera_pose>", base)
    if "</world>" not in base or "<gravity>" in base:
        raise ValueError(f"world {WORLD}.sdf có cấu trúc khác dự kiến")
    models = "".join(_uav(j, *p) for j, p in enumerate(_pad(to_gz(uav_xy, area), altitude * SCALE, MAX_UAVS)))
    models += "".join(_marker(c, k) for c in range(MAX_UAVS + 1) for k in range(MAX_USERS))
    models += "".join(_ring(c, k) for c in RING for k in range(MAX_USERS))
    return base.replace("</world>", f"    <gravity>0 0 0</gravity>{models}\n  </world>", 1)


def launch(world_file: Path, models_dir: Path, root: Path = ROOT) -> subprocess.Popen:
    """Mở gz sim (server + GUI). models_dir (bản disaster_site không người) đứng trước models của multi_uav."""
    env = dict(os.environ)
    env["GZ_SIM_RESOURCE_PATH"] = os.pathsep.join(
        p for p in (str(models_dir), str(root / "models"), env.get("GZ_SIM_RESOURCE_PATH")) if p)
    return subprocess.Popen(["gz", "sim", "-r", str(world_file)], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


class GazeboView:
    """Đặt vị trí cả bể UAV và user bằng một lần gọi service /world/<WORLD>/set_pose_vector."""

    def __init__(self, area: float, timeout_ms: int = 100):
        from gz.msgs10.boolean_pb2 import Boolean
        from gz.msgs10.pose_v_pb2 import Pose_V
        from gz.transport13 import Node

        self.node, self.Pose_V, self.Boolean = Node(), Pose_V, Boolean
        self.area, self.timeout = area, timeout_ms
        self.service = f"/world/{WORLD}/set_pose_vector"
        self.marked: dict[str, tuple] = {}  # hình người đang đứng trên đất -> vị trí

    def _markers(self, user_gz, assoc, cls=None) -> dict[str, tuple]:
        """Áo user = màu UAV phục vụ. Gazebo làm mất tin material_color khi đang nhận set_pose_vector, nên không đổi màu
        mà đổi chỗ: mỗi màu có sẵn một bể hình người, đặt hình đúng màu vào chỗ user, hình cũ về PARK_Z."""
        now = {f"mk{MAX_UAVS if a < 0 else a % MAX_UAVS}_{k}": (x, y, MARK_Z) for k, ((x, y), a) in enumerate(zip(user_gz, assoc))}
        if cls is not None:  # vòng nhóm dưới chân user important/critical
            now |= {f"{RING[c][0]}{k}": (x, y, 0.0) for k, ((x, y), c) in enumerate(zip(user_gz, cls)) if c in RING}
        self.calls = getattr(self, "calls", 0) + 1
        # lệnh cất đôi khi không được áp dù service trả lời: cứ 40 lần (2 s) cất lại cả bể hình người không dùng
        old = _all_markers() if self.calls % 40 == 0 else self.marked
        out = {name: (0.0, 0.0, PARK_Z) for name in old if name not in now}
        return {**out, **now}

    def update(self, uav_xy, user_xy, altitude: float, assoc=None, cls=None) -> bool:
        msg = self.Pose_V()
        marks = self._markers(to_gz(user_xy, self.area), assoc, cls) if assoc is not None else {}
        for prefix, pts, z, n in [("uav", uav_xy, altitude * SCALE, MAX_UAVS)]:
            for i, (x, y, zz) in enumerate(_pad(to_gz(pts, self.area), z, n)):
                p = msg.pose.add()
                p.name = f"{prefix}{i}"
                p.position.x, p.position.y, p.position.z = float(x), float(y), float(zz)
                p.orientation.w = 1.0
        for name, (x, y, z) in marks.items():
            p = msg.pose.add()
            p.name = name
            p.position.x, p.position.y, p.position.z = float(x), float(y), float(z)
            p.orientation.w = 1.0
        ok, rep = self.node.request(self.service, msg, self.Pose_V, self.Boolean, self.timeout)
        ok = ok and rep.data
        if ok and assoc is not None:  # chỉ nhớ khi Gazebo đã nhận, để hình cũ chắc chắn được cất
            self.marked = {n: p for n, p in marks.items() if p[2] != PARK_Z}
        return ok  # False khi Gazebo chưa sẵn sàng: bỏ qua, lần sau thử lại
