"""Hiển thị 3D trong Gazebo (Harmonic, gz sim 8): kịch bản của mô hình, vẽ trên bãi thảm họa của ~/simulation/multi_uav.

- Kịch bản là của mô hình (SimConfig: số UAV, số user, vị trí user theo seed, vùng, độ cao), giống mọi thí nghiệm.
- Bãi (worlds/multi_uav_world.sdf, models/disaster_site) chỉ làm nền. 54 người có sẵn của bãi được bỏ trong một bản
  sao của disaster_site (mesh, texture dùng symlink; dự án multi_uav không bị sửa). User vẽ bằng hình người có tay/chân (_marker).
- Tỷ lệ: 1 m Gazebo = 1/SCALE m mô hình, tâm vùng mô hình đặt ở tâm bãi (gốc tọa độ).
- Gazebo chỉ hiển thị: vị trí UAV và user được đặt qua service set_pose_vector (do system Physics áp, nên model không
  static; trọng lực tắt, không có va chạm; thân đứng yên giữa hai lần đặt, rotor quay bằng joint).
- Bể user và màu áo chỉ dựng đủ cấu hình hiện tại, bổ sung qua create_multiple khi tăng số lượng.
  Model chưa dùng nằm dưới mặt đất; đổi cấu hình không cần khởi động lại Gazebo.
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
CAMERA = "0 -60 50 0 0.66 1.5708"  # góc gần; bản live đặt tâm tại cụm user
UAV_ASSET_DIR = Path(__file__).resolve().parent / "assets/gazebo/x500_fpv_cam"
UAV_DISPLAY_SCALE = 8.0  # phóng đại để đọc được trong bản đồ 1:10, không dùng cho vật lý
ROTOR_SPEED = 15.0  # rad/s hiển thị (quay chậm để thấy rõ), không phải RPM vật lý
ROTOR_CENTERS = ((.174, -.174, .06), (-.174, .174, .06), (.174, .174, .06), (-.174, -.174, .06))


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
    # The GUI can resolve resources from a different working directory than the server.
    # Absolute local URIs prevent missing terrain/roof meshes and repeated resource searches.
    for node in site.iter():
        if node.text and node.text.strip().startswith("model://disaster_site/"):
            relative = node.text.strip().removeprefix("model://disaster_site/")
            node.text = (src / relative).resolve().as_uri()
    tree.write(dst / "model.sdf", encoding="unicode")


def _rgb(hex_color: str) -> str:
    return " ".join(f"{int(hex_color[i:i + 2], 16) / 255:.3f}" for i in (1, 3, 5))


def _material(color: str, *, metal: float = 0.0, roughness: float = 0.65) -> str:
    rgb = _rgb(color)
    return (f"<material><ambient>{rgb} 1</ambient><diffuse>{rgb} 1</diffuse>"
            f"<specular>0.15 0.15 0.15 1</specular><pbr><metal><metalness>{metal}</metalness>"
            f"<roughness>{roughness}</roughness></metal></pbr></material>")


def _visual(name: str, geometry: str, color: str, pose: str = "0 0 0 0 0 0", *,
            transparency: float = 0.0, shadows: bool = True, metal: float = 0.0) -> str:
    return (f'<visual name="{name}"><pose>{pose}</pose><geometry>{geometry}</geometry>'
            f'<cast_shadows>{str(shadows).lower()}</cast_shadows><transparency>{transparency}</transparency>'
            f'{_material(color, metal=metal)}</visual>')


def _box(x, y, z) -> str:
    return f"<box><size>{x} {y} {z}</size></box>"


def _cylinder(radius, length) -> str:
    return f"<cylinder><radius>{radius}</radius><length>{length}</length></cylinder>"


def _ellipsoid(x, y, z) -> str:
    return f"<ellipsoid><radii>{x} {y} {z}</radii></ellipsoid>"


def _uav(j: int, x: float, y: float, z: float) -> str:
    """X500 FPV với mesh LOD và bốn rotor quay bằng joint, không sinh lực bay."""
    model = ET.parse(UAV_ASSET_DIR / "visual_model.sdf").getroot().find("model")
    model.set("name", f"uav{j}")
    ET.SubElement(model, "pose").text = f"{x:.3f} {y:.3f} {z:.3f} 0 0 0"
    for visual in model.findall("link/visual"):
        pose = visual.find("pose")
        values = np.fromstring(pose.text, sep=" ")
        pose.text = " ".join(map(str, [*(values[:3] * UAV_DISPLAY_SCALE), *values[3:]]))
        for node in visual.iter():
            if node.text and node.text.startswith("asset://"):
                asset = UAV_ASSET_DIR / node.text.removeprefix("asset://")
                lod = asset.parent / "lod" / (asset.stem + ".dae")
                node.text = (lod if asset.suffix in (".dae", ".stl") and lod.exists() else asset).as_uri()
        mesh = visual.find("geometry/mesh")
        if mesh is not None:
            scale = mesh.find("scale")
            if scale is None:
                scale = ET.SubElement(mesh, "scale")
                scale.text = "1 1 1"
            scale.text = " ".join(map(str, np.fromstring(scale.text, sep=" ") * UAV_DISPLAY_SCALE))
        for size in visual.findall("geometry/box/size") + visual.findall("geometry/plane/size"):
            size.text = " ".join(map(str, np.fromstring(size.text, sep=" ") * UAV_DISPLAY_SCALE))
        if visual.attrib.pop("fleet_color", None):
            visual.append(ET.fromstring(_material(UAV_COLORS[j % len(UAV_COLORS)])))
    base = model.find("link")
    _inertial(base, 10.0, 1.0)
    for i, center in enumerate(ROTOR_CENTERS):
        link = ET.SubElement(model, "link", name=f"rotor_{i}")
        origin = np.array(center) * UAV_DISPLAY_SCALE
        ET.SubElement(link, "pose").text = " ".join(map(str, [*origin, 0, 0, 0]))
        ET.SubElement(link, "gravity").text = "false"
        _inertial(link, .0001, .00001)
        for visual in list(base.findall("visual")):
            if visual.get("name").startswith(f"x500_rotor_{i}_"):
                values = np.fromstring(visual.find("pose").text, sep=" ")
                visual.find("pose").text = " ".join(map(str, [*(values[:3] - origin), *values[3:]]))
                shadow = visual.find("cast_shadows")
                if shadow is None:
                    shadow = ET.SubElement(visual, "cast_shadows")
                shadow.text = "false"
                base.remove(visual)
                link.append(visual)
        joint = ET.SubElement(model, "joint", name=f"rotor_{i}_joint", type="revolute")
        ET.SubElement(joint, "parent").text = "base_link"
        ET.SubElement(joint, "child").text = f"rotor_{i}"
        axis = ET.SubElement(joint, "axis")
        ET.SubElement(axis, "xyz").text = "0 0 1"
        plugin = ET.SubElement(model, "plugin", filename="gz-sim-joint-controller-system",
                               name="gz::sim::systems::JointController")
        ET.SubElement(plugin, "joint_name").text = f"rotor_{i}_joint"
        ET.SubElement(plugin, "initial_velocity").text = str(_rotor_speed(i) if z >= 0 else 0.0)
    return ET.tostring(model, encoding="unicode")


def _rotor_speed(i: int) -> float:
    return ROTOR_SPEED if i < 2 else -ROTOR_SPEED


def _inertial(link, mass: float, moment: float):
    inertial = ET.SubElement(link, "inertial")
    ET.SubElement(inertial, "mass").text = str(mass)
    inertia = ET.SubElement(inertial, "inertia")
    for name in ("ixx", "iyy", "izz"):
        ET.SubElement(inertia, name).text = str(moment)


def _camera_pose(user_xy, area: float) -> str:
    """Ưu tiên nhìn rõ cụm user; không tự zoom xa để chứa các UAV đang tiếp cận từ rìa."""
    if user_xy is None or len(user_xy) == 0:
        return CAMERA
    points = to_gz(user_xy, area)
    lower, upper = points.min(axis=0), points.max(axis=0)
    center = (lower + upper) / 2
    # Perspective leaves less ground in the foreground: bias the target toward the near users.
    center[1] -= 0.18 * (upper[1] - lower[1])
    return f"{center[0]:.3f} {center[1] - 60:.3f} 50 0 0.66 1.5708"


def _marker(c: int, k: int) -> str:
    """Người cao ~2.6 m Gazebo để đọc ở góc toàn cảnh: áo màu UAV, quần và giày trung tính."""
    shirt = UNSERVED if c == MAX_UAVS else UAV_COLORS[c % len(UAV_COLORS)]
    skin = ("#c68f6b", "#d9ac87", "#a97455")[k % 3]
    parts = [
        _visual("body", _ellipsoid(0.43, 0.26, 0.57), shirt, "0 0 1.55 0 0 0"),
        _visual("waist", _ellipsoid(0.32, 0.24, 0.19), "#38434e", "0 0 1.02 0 0 0"),
        _visual("head", _ellipsoid(0.26, 0.24, 0.30), skin, "0 0 2.27 0 0 0"),
        _visual("hair", _ellipsoid(0.265, 0.245, 0.14), "#3b302c", "0 0.02 2.46 0 0 0"),
    ]
    for i, sx in enumerate((-1, 1)):
        parts += [
            _visual(f"leg{i}", _cylinder(0.14, 0.75), "#38434e", f"{sx * 0.20} 0 0.56 0 0 0"),
            _visual(f"shoe{i}", _box(0.30, 0.48, 0.19), "#252b30", f"{sx * 0.20} -0.08 0.12 0 0 0"),
            _visual(f"arm{i}", _cylinder(0.13, 0.66), shirt,
                    f"{sx * 0.48} 0 1.49 0 {sx * -0.16} 0"),
            _visual(f"hand{i}", _ellipsoid(0.12, 0.12, 0.15), skin, f"{sx * 0.54} 0 1.08 0 0 0"),
        ]
    return (f'<model name="mk{c}_{k}"><pose>0 0 {PARK_Z} 0 0 0</pose>'
            f'<link name="l"><gravity>false</gravity>{"".join(parts)}</link></model>')


RING = {1: ("imp", "#eda100", 1.1), 2: ("crit", "#d01010", 1.4)}
RING_MESH = Path(__file__).resolve().parent / "assets/gazebo/priority_ring.dae"


def _ring(c: int, k: int) -> str:
    """Vành mảnh dưới chân user important/critical, không che mặt đường và chân người."""
    prefix, color, radius = RING[c]
    geometry = f"<mesh><uri>{RING_MESH.as_uri()}</uri><scale>{radius} {radius} 1</scale></mesh>"
    visual = _visual("v", geometry, color, "0 0 0.06 0 0 0", shadows=False)
    return (f'<model name="{prefix}{k}"><pose>0 0 {PARK_Z} 0 0 0</pose>'
            f'<link name="l"><gravity>false</gravity>{visual}</link></model>')


def _pool_models(users: int, uavs: int) -> dict[str, str]:
    """Tên -> SDF của bể vừa đủ: màu các UAV hiện có + màu không phục vụ."""
    if not 0 <= users <= MAX_USERS or not 0 <= uavs <= MAX_UAVS:
        raise ValueError("số UAV/user vượt giới hạn hiển thị Gazebo")
    models = {f"mk{c}_{k}": _marker(c, k) for c in (*range(uavs), MAX_UAVS) for k in range(users)}
    models.update({f"{RING[c][0]}{k}": _ring(c, k) for c in RING for k in range(users)})
    return models


def _all_markers(users: int = MAX_USERS, uavs: int = MAX_UAVS) -> list[str]:
    return ([f"mk{c}_{k}" for c in (*range(uavs), MAX_UAVS) for k in range(users)]
            + [f"{RING[c][0]}{k}" for c in RING for k in range(users)])


def _pad(xy_gz: np.ndarray, z: float, n: int) -> np.ndarray:
    """[n, 3]: các model đang dùng ở (x, y, z), phần còn lại của bể nằm ở PARK_Z."""
    if len(xy_gz) > n:
        raise ValueError(f"{len(xy_gz)} model vượt bể {n}")
    out = np.zeros((n, 3))
    out[:, 2] = PARK_Z
    out[:len(xy_gz), :2], out[:len(xy_gz), 2] = xy_gz, z
    return out


def world_sdf(uav_xy, altitude: float, area: float, root: Path = ROOT, *,
              num_users: int = MAX_USERS, num_uavs: int = MAX_UAVS, user_xy=None) -> str:
    """Nền + UAV + bể user theo cấu hình, trọng lực tắt. Mặc định tương thích caller cũ."""
    if area * SCALE > SITE_SIZE:
        raise ValueError(f"vùng {area:.0f} m × {SCALE} vượt mặt đất {SITE_SIZE:.0f} m của bãi")
    base = (root / f"worlds/{WORLD}.sdf").read_text()
    base = re.sub(r"<camera_pose>[^<]*</camera_pose>", f"<camera_pose>{_camera_pose(user_xy, area)}</camera_pose>", base)
    # Gazebo is a visual replay here: 100 Hz physics suffices for 20 Hz poses and rotor animation.
    base = re.sub(r"<max_step_size>[^<]*</max_step_size>", "<max_step_size>0.01</max_step_size>", base)
    if "</world>" not in base or "<gravity>" in base:
        raise ValueError(f"world {WORLD}.sdf có cấu trúc khác dự kiến")
    models = "".join(_uav(j, *p) for j, p in enumerate(_pad(to_gz(uav_xy, area), altitude * SCALE, MAX_UAVS)))
    models += "".join(_pool_models(num_users, num_uavs).values())
    return base.replace("</world>", f"    <gravity>0 0 0</gravity>{models}\n  </world>", 1)


def launch(world_file: Path, models_dir: Path, root: Path = ROOT) -> subprocess.Popen:
    """Mở gz sim (server + GUI). models_dir (bản disaster_site không người) đứng trước models của multi_uav."""
    env = dict(os.environ)
    gpu = env.get("UAVSIM_GZ_GPU", "auto")
    if gpu == "nvidia" or (gpu == "auto" and Path("/proc/driver/nvidia/gpus").is_dir()
                           and Path("/usr/share/glvnd/egl_vendor.d/10_nvidia.json").exists()
                           and env.get("LIBGL_ALWAYS_SOFTWARE", "").lower() not in ("1", "true")):
        env.setdefault("__NV_PRIME_RENDER_OFFLOAD", "1")
        env.setdefault("__GLX_VENDOR_LIBRARY_NAME", "nvidia")
    env["GZ_SIM_RESOURCE_PATH"] = os.pathsep.join(
        p for p in (str(models_dir.resolve()), str((root / "models").resolve()),
                    env.get("GZ_SIM_RESOURCE_PATH")) if p)
    # Keep diagnostics when the GUI fails instead of discarding driver/resource errors.
    with (world_file.parent / "gazebo.log").open("w") as log:
        return subprocess.Popen(["gz", "sim", "-r", str(world_file.resolve())], env=env,
                                stdout=log, stderr=log, start_new_session=True)


class GazeboView:
    """Đặt vị trí cả bể UAV và user bằng một lần gọi service /world/<WORLD>/set_pose_vector."""

    def __init__(self, area: float, timeout_ms: int = 100, *,
                 num_users: int = MAX_USERS, num_uavs: int = MAX_UAVS):
        from gz.msgs10.boolean_pb2 import Boolean
        from gz.msgs10.entity_factory_v_pb2 import EntityFactory_V
        from gz.msgs10.double_pb2 import Double
        from gz.msgs10.pose_v_pb2 import Pose_V
        from gz.transport13 import Node

        self.node, self.Pose_V, self.Boolean = Node(), Pose_V, Boolean
        self.area, self.timeout = area, timeout_ms
        self.service = f"/world/{WORLD}/set_pose_vector"
        self.EntityFactory_V = EntityFactory_V
        self.pool_users, self.pool_uavs = num_users, num_uavs
        self.Double, self._rotor_count, self._rotor_publishers = Double, num_uavs, {}
        self.marked: dict[str, tuple] = {}  # hình người đang đứng trên đất -> vị trí

    def _ensure_pool(self, users: int, uavs: int) -> bool:
        """Chỉ thêm model khi cấu hình tăng. Lỗi tạo bể sẽ được thử lại ở lần cập nhật sau."""
        if users <= self.pool_users and uavs <= self.pool_uavs:
            return True
        users, uavs = max(users, self.pool_users), max(uavs, self.pool_uavs)
        old = set(_all_markers(self.pool_users, self.pool_uavs))
        req = self.EntityFactory_V()
        for name, sdf in _pool_models(users, uavs).items():
            if name not in old:
                req.data.add().sdf = f'<sdf version="1.9">{sdf}</sdf>'
        ok, rep = self.node.request(f"/world/{WORLD}/create_multiple", req, self.EntityFactory_V,
                                    self.Boolean, max(self.timeout, 1000))
        if ok and rep.data:
            self.pool_users, self.pool_uavs = users, uavs
            return True
        return False

    def _markers(self, user_gz, assoc, cls=None) -> dict[str, tuple]:
        """Áo user = màu UAV phục vụ. Gazebo làm mất tin material_color khi đang nhận set_pose_vector, nên không đổi màu
        mà đổi chỗ: mỗi màu có sẵn một bể hình người, đặt hình đúng màu vào chỗ user, hình cũ về PARK_Z."""
        now = {f"mk{MAX_UAVS if a < 0 else a % MAX_UAVS}_{k}": (x, y, MARK_Z) for k, ((x, y), a) in enumerate(zip(user_gz, assoc))}
        if cls is not None:  # vòng nhóm dưới chân user important/critical
            now |= {f"{RING[c][0]}{k}": (x, y, 0.0) for k, ((x, y), c) in enumerate(zip(user_gz, cls)) if c in RING}
        self.calls = getattr(self, "calls", 0) + 1
        # lệnh cất đôi khi không được áp dù service trả lời: cứ 40 lần (2 s) cất lại cả bể hình người không dùng
        old = (_all_markers(getattr(self, "pool_users", MAX_USERS), getattr(self, "pool_uavs", MAX_UAVS))
               if self.calls % 40 == 0 else self.marked)
        out = {name: (0.0, 0.0, PARK_Z) for name in old if name not in now}
        changed = {name: pos for name, pos in now.items() if self.marked.get(name) != pos}
        return {**out, **changed}

    def update(self, uav_xy, user_xy, altitude: float, assoc=None, cls=None) -> bool:
        if not self._ensure_pool(len(user_xy), len(uav_xy)):
            return False
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
        if ok:
            self._sync_rotors(len(uav_xy))
        if ok and assoc is not None:  # chỉ nhớ khi Gazebo đã nhận, để hình cũ chắc chắn được cất
            self.marked = {n: p for n, p in (self.marked | marks).items() if p[2] != PARK_Z}
        return ok  # False khi Gazebo chưa sẵn sàng: bỏ qua, lần sau thử lại

    def _sync_rotors(self, active: int):
        """Start/stop reserved UAV rotors only when the active UAV count changes."""
        previous = getattr(self, "_rotor_count", active)
        if not hasattr(self, "_rotor_states"):
            self._rotor_states = {(j, i): _rotor_speed(i) if j < previous else 0.0
                                  for j in range(MAX_UAVS) for i in range(4)}
        for j in range(MAX_UAVS):
            for i in range(4):
                key = (j, i)
                value = _rotor_speed(i) if j < active else 0.0
                if self._rotor_states[key] == value:
                    continue
                if key not in self._rotor_publishers:
                    topic = f"/model/uav{j}/joint/rotor_{i}_joint/cmd_vel"
                    self._rotor_publishers[key] = self.node.advertise(topic, self.Double)
                publisher = self._rotor_publishers[key]
                # A publish can return True before discovery has connected the controller.
                # Keep the command pending until a subscriber exists, then retry if rejected.
                if publisher.has_connections() and publisher.publish(self.Double(data=value)):
                    self._rotor_states[key] = value
        if all(v == (_rotor_speed(i) if j < active else 0.0) for (j, i), v in self._rotor_states.items()):
            self._rotor_count = active
