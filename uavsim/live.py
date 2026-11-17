"""Trạm điều khiển thời gian thực: dashboard web, lái tay từng UAV, đổi tham số, đo NS-3 theo lệnh, Gazebo 3D.

python -m uavsim.live                         # mở http://localhost:8000
python -m uavsim.live --gazebo                # thêm Gazebo: cùng kịch bản, vẽ trên bãi của ~/simulation/multi_uav
python -m uavsim.live --algo calib-ifair --set num_uavs=4 --set demand_mbps=2

Mỗi khe (mặc định dt = 0.25 s, chạy đúng thời gian thực): thuật toán ra quyết định, UAV đang lái tay thì vận tốc bị
thay bằng lệnh từ dashboard (phím, hoặc bay tới điểm nhấp trên bản đồ), Network.step tính rate/hàng đợi/năng lượng.
Dashboard nội suy chuyển động giữa hai khe; Gazebo nhận vị trí nội suy 20 lần mỗi giây.
Số trên dashboard là số *tính*: theo Shannon (như paper) và theo LTE đã hiệu chỉnh (dự đoán NS-3). Muốn số *đo*:
bấm "Ghi & đo" trên dashboard, server ghi một đoạn rồi chạy NS-3 (liên kết lý tưởng hoặc LTE) và trả kết quả về web.
"""
import argparse
import asyncio
import csv
import functools
import json
import os
import signal
import threading
import time
from dataclasses import replace
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

from .algorithms import LTE_CAL_ALPHA, LTE_CAL_SE_MAX, REGISTRY
from .config import ENVIRONMENTS, SimConfig
from .energy import rotary_power
from .network import Network, class_metrics, jain
from .ns3 import LTE_RB, PlanRecorder, replay
from .run import parse_set

WEB = Path(__file__).parent / "web"
ENDLESS = 10**9  # số khe: phiên chạy đến khi người dùng dừng
GZ_HZ = 20
# tham số đổi được từ dashboard: (min, max) cho số, danh sách cho lựa chọn, None cho bool
EDITABLE = {
    "num_uavs": (1, 8), "num_users": (1, 60), "altitude": (20.0, 300.0), "demand_mbps": (0.1, 20.0),
    "p_max": (0.05, 5.0), "user_speed": (0.0, 5.0), "v_max": (1.0, 40.0), "seed": (0, 9999),
    "environment": list(ENVIRONMENTS), "user_layout": ["clustered", "uniform"], "interference": None,
    "important_frac": (0.0, 1.0), "critical_frac": (0.0, 1.0),
}


class LiveSession:
    """Trạng thái một phiên: mạng, thuật toán, UAV lái tay, bản ghi. Không phụ thuộc web hay Gazebo."""

    def __init__(self, cfg: SimConfig, algo: str):
        self.cfg = replace(cfg, slots=ENDLESS)
        self.algo_name = algo
        self.manual: dict[int, np.ndarray] = {}   # UAV lái tay -> vận tốc lệnh (m/s)
        self.target: dict[int, np.ndarray] = {}   # UAV lái tay -> điểm đến (m), ưu tiên hơn vận tốc lệnh
        self.rec: PlanRecorder | None = None
        self.reset()

    def reset(self):
        self.net = Network(self.cfg)
        self.set_algo(self.algo_name)
        self.target.clear()
        for j in self.manual:
            self.manual[j] = np.zeros(2)
        self.last: dict | None = None

    def set_algo(self, name: str):
        if name not in REGISTRY:
            raise ValueError(f"không có thuật toán {name}")
        self.algo_name, self.algo = name, REGISTRY[name]()
        self.algo.reset(self.net)

    def apply_config(self, changes: dict):
        """Đổi tham số rồi dựng lại kịch bản. Giá trị ngoài khoảng cho phép bị từ chối."""
        clean = {}
        for k, v in changes.items():
            if k not in EDITABLE:
                raise ValueError(f"không đổi được tham số {k}")
            rule = EDITABLE[k]
            if rule is None:
                clean[k] = bool(v)
            elif isinstance(rule, list):
                if v not in rule:
                    raise ValueError(f"{k} phải thuộc {rule}")
                clean[k] = v
            else:
                x = type(rule[0])(v)
                if not rule[0] <= x <= rule[1]:
                    raise ValueError(f"{k} phải trong [{rule[0]}, {rule[1]}]")
                clean[k] = x
        self.cfg = replace(self.cfg, **clean)
        self.rec = None
        self.manual = {j: v for j, v in self.manual.items() if j < self.cfg.num_uavs}
        self.reset()

    def set_manual(self, j: int, on: bool):
        if not 0 <= j < self.cfg.num_uavs:
            raise ValueError(f"không có UAV {j}")
        if on:
            self.manual.setdefault(j, np.zeros(2))
        else:
            self.manual.pop(j, None)
            self.target.pop(j, None)

    def command(self, j: int, vx: float, vy: float):
        """Vận tốc lệnh cho UAV lái tay; Network.step tự cắt về v_max và giữ UAV trong vùng."""
        if j in self.manual:
            self.manual[j] = np.nan_to_num(np.array([vx, vy], float))
            self.target.pop(j, None)  # lái bằng phím hủy điểm đến

    def goto(self, j: int, x: float, y: float):
        """Bay tới (x, y) với v_max rồi dừng. Tự bật lái tay cho UAV đó."""
        self.set_manual(j, True)
        self.target[j] = np.clip(np.nan_to_num(np.array([x, y], float)), 0, self.cfg.area)

    def stop_all(self):
        self.target.clear()
        for j in self.manual:
            self.manual[j] = np.zeros(2)

    def _manual_velocity(self, j: int) -> np.ndarray:
        if j not in self.target:
            return self.manual[j]
        d = self.target[j] - self.net.uav_xy[j]
        dist = np.linalg.norm(d)
        if dist < 0.5:
            del self.target[j]
            return np.zeros(2)
        return d / dist * min(self.cfg.v_max, dist / self.cfg.dt)  # khe cuối đi vừa đủ, không vọt qua

    def step(self) -> dict:
        net, c = self.net, self.cfg
        s, uav_xy, user_xy = net.t, net.uav_xy.copy(), net.user_xy.copy()
        a = self.algo.act(net)
        for j in list(self.manual):
            a.velocity[j] = self._manual_velocity(j)
        sinr = net.sinr(a)  # tại vị trí đầu khe, trước khi step dịch UAV
        m = net.step(a)
        if self.rec is not None:
            self.rec.add(s, uav_xy, user_xy, a, m)
        rates = m["rates"]
        # dự đoán LTE: cùng SINR, ánh xạ SINR -> tốc độ đo được trên NS-3 (thay cho Shannon)
        se = np.where(sinr < 0.1, 0.0, np.minimum(LTE_CAL_ALPHA * np.log2(1 + sinr), LTE_CAL_SE_MAX))
        lte = np.where(a.bw > 0, a.bw * c.bandwidth * se, 0.0)
        speed = np.minimum(np.linalg.norm(a.velocity, axis=1), c.v_max)
        self.last = {
            "t": s, "time": s * c.dt, "dt": c.dt, "area": c.area, "r_min": c.r_min, "v_max": c.v_max,
            "uav": uav_xy.round(2).tolist(), "users": user_xy.round(2).tolist(),
            "assoc": a.assoc.tolist(), "rate": (rates / 1e6).round(3).tolist(),
            "lte_rate": (lte / 1e6).round(3).tolist(),
            "sinr_db": (10 * np.log10(np.maximum(sinr, 1e-9))).round(1).tolist(),
            "sum_rate": m["sum_rate"] / 1e6, "min_rate": m["min_rate"] / 1e6,
            "lte_sum": float(lte.sum() / 1e6), "lte_min": float(lte.min() / 1e6),
            "lte_coverage": float(np.mean(lte >= c.r_min)), "lte_jain": jain(lte),
            "coverage": m["coverage"], "jain": m["jain"], "energy_w": float(rotary_power(speed).sum()),
            "uav_speed": speed.round(2).tolist(),
            "uav_load": np.bincount(a.assoc[a.assoc >= 0], minlength=c.num_uavs).tolist(),
            "targets": {str(j): t.round(1).tolist() for j, t in self.target.items()},
            "throughput": m.get("throughput", m["sum_rate"]) / 1e6,
            "delay_ms": _num(m.get("delay_ms")), "loss": _num(m.get("loss")),
            "queue_mbit": _num(m.get("queue_bits", 0.0) / 1e6),
            "user_class": net.user_class.tolist(),
            # min tốc độ LTE dự đoán (Mbps) và tỷ lệ đạt QoS của từng nhóm có mặt
            "classes": {k: (v / 1e6 if k.startswith("min_") else v) for k, v in
                        class_metrics(lte, net.user_class, c, None if c.demand_mbps is None else c.demand_mbps * 1e6).items()},
        }
        return self.last

    def start_recording(self):
        self.reset()  # NS-3 bắt đầu với hàng đợi rỗng ở khe 0, nên mô hình cũng phải vậy
        self.rec = PlanRecorder(self.cfg)

    def stop_recording(self, root: Path) -> Path | None:
        rec, self.rec = self.rec, None
        if rec is None or not rec.model:
            return None
        d = root / time.strftime("live-%Y%m%d-%H%M%S")
        rec.write(d / "plan", self.net.t, self.net.uav_xy, self.net.user_xy)
        cfg = replace(rec.cfg, slots=len(rec.model))
        (d / "config.json").write_text(json.dumps(cfg.to_dict(), indent=2))
        with open(d / "model_slots.csv", "w", newline="") as f:
            w = csv.DictWriter(f, list(rec.model[0]))
            w.writeheader()
            w.writerows(rec.model)
        return d

    def info(self) -> dict:
        c = self.cfg
        return {"algo": self.algo_name, "algos": list(REGISTRY), "num_uavs": c.num_uavs, "num_users": c.num_users,
                "manual": sorted(self.manual), "recording": self.rec is not None,
                "recorded": len(self.rec.model) if self.rec else 0,
                "config": {k: getattr(c, k) for k in EDITABLE},
                "fixed": {"area": c.area, "bandwidth_mhz": c.bandwidth / 1e6, "fc_ghz": c.fc / 1e9, "dt": c.dt,
                          "r_min_mbps": c.r_min / 1e6, "buffer_mib": c.buffer_bytes / 2**20},
                "limits": {k: v for k, v in EDITABLE.items() if v is not None}}


def _num(x):
    return None if x is None or not np.isfinite(x) else float(x)


class Server:
    def __init__(self, session: LiveSession, out: Path, gazebo=None):
        self.s, self.out, self.gz = session, out, gazebo
        self.clients, self.running, self.note, self.speed = set(), True, "", 1.0
        self.prev = self.cur = None  # (uav_xy, user_xy) của hai khe gần nhất, cho Gazebo nội suy
        self.assoc = None
        self.t_cur = 0.0
        self.measure = {"status": "idle"}  # idle | recording | running | done | error
        self.measure_task: asyncio.Task | None = None

    @property
    def period(self) -> float:
        return self.s.cfg.dt / self.speed

    def info(self) -> dict:
        return {"type": "info", **self.s.info(), "running": self.running, "note": self.note, "speed": self.speed,
                "gazebo": self.gz is not None, "measure": self.measure, "period": self.period}

    async def handle(self, ws):
        self.clients.add(ws)
        try:
            await ws.send(json.dumps(self.info()))
            async for raw in ws:
                try:
                    self.on_message(json.loads(raw))
                except (ValueError, KeyError, TypeError) as e:  # lệnh sai không làm sập server
                    self.note = f"Lệnh bị từ chối: {e}"
                await self.broadcast(self.info())
        finally:
            self.clients.discard(ws)
            if not self.clients:
                self.s.stop_all()  # mất kết nối thì UAV lái tay dừng lại, không bay tiếp theo lệnh cũ

    def on_message(self, msg: dict):
        cmd = msg["cmd"]
        self.note = ""
        if cmd == "vel":
            self.s.command(int(msg["uav"]), float(msg["vx"]), float(msg["vy"]))
        elif cmd == "goto":
            self.s.goto(int(msg["uav"]), float(msg["x"]), float(msg["y"]))
        elif cmd == "manual":
            self.s.set_manual(int(msg["uav"]), bool(msg["on"]))
        elif cmd == "algo":
            self.s.set_algo(str(msg["name"]))
        elif cmd == "pause":
            self.running = False
        elif cmd == "resume":
            self.running = True
        elif cmd == "speed":
            x = float(msg["x"])
            if x not in (0.5, 1.0, 2.0, 4.0):
                raise ValueError("tốc độ mô phỏng phải là 0.5, 1, 2 hoặc 4")
            self.speed = x
        elif cmd == "reset":
            self._abort_measure("đặt lại kịch bản")
            self.s.reset()
            self.prev = self.cur = None
        elif cmd == "config":
            self._abort_measure("đổi tham số")
            self.s.apply_config(dict(msg["set"]))
            self.prev = self.cur = None
            self.note = "Đã áp tham số mới, kịch bản dựng lại từ khe 0"
        elif cmd == "measure":
            self.start_measure(float(msg["seconds"]), str(msg["link"]), str(msg["scheduler"]))
        elif cmd == "measure_cancel":
            self._abort_measure("người dùng hủy")
        else:
            raise ValueError(f"lệnh lạ {cmd}")

    # ---- đo bằng NS-3 theo lệnh từ dashboard
    def start_measure(self, seconds: float, link: str, scheduler: str):
        if self.measure["status"] in ("recording", "running"):
            raise ValueError("đang có một phép đo chạy")
        if link not in ("ideal", "lte") or scheduler not in ("pf", "rr", "wpf"):
            raise ValueError("link hoặc scheduler không hợp lệ")
        if link == "lte" and self.s.cfg.bandwidth not in LTE_RB:
            raise ValueError("băng thông hiện tại không phải băng LTE")
        if not 2 <= seconds <= 120:
            raise ValueError("thời lượng ghi phải trong 2–120 s")
        slots = max(1, round(seconds / self.s.cfg.dt))
        self.s.start_recording()
        self.prev = self.cur = None
        self.running = True
        self.measure = {"status": "recording", "slots": slots, "link": link, "scheduler": scheduler,
                        "algo": self.s.algo_name}

    def _abort_measure(self, why: str):
        if self.measure["status"] == "recording":
            self.s.rec = None
            self.measure = {"status": "idle", "note": f"Đã hủy phép đo ({why})"}

    async def _run_ns3(self, session_dir: Path):
        m = self.measure
        try:
            res = await asyncio.to_thread(replay, session_dir, m["scheduler"], m["link"], 1800.0)
            self.measure = {**m, "status": "done", "result": res, "dir": str(session_dir)}
        except Exception as e:  # NS-3 lỗi hoặc chưa build: báo về web, server chạy tiếp
            self.measure = {**m, "status": "error", "error": str(e)}
        await self.broadcast(self.info())

    async def broadcast(self, payload: dict):
        msg = json.dumps(payload)
        for ws in list(self.clients):
            try:
                await ws.send(msg)
            except Exception:  # client vừa đóng: handle() sẽ gỡ nó
                pass

    async def loop(self):
        while True:
            t0 = time.monotonic()
            if self.running:
                st = self.s.step()
                self.prev, self.cur = self.cur, (np.array(st["uav"]), np.array(st["users"]))
                self.assoc = st["assoc"]
                self.t_cur = t0
                rec = len(self.s.rec.model) if self.s.rec else 0
                await self.broadcast({"type": "state", **st, "recorded": rec, "period": self.period})
                if self.measure["status"] == "recording" and rec >= self.measure["slots"]:
                    d = self.s.stop_recording(self.out)
                    self.measure = {**self.measure, "status": "running", "started": time.time()}
                    self.measure_task = asyncio.create_task(self._run_ns3(d))
                    await self.broadcast(self.info())
            await asyncio.sleep(max(0.0, self.period - (time.monotonic() - t0)))

    async def gazebo_loop(self):
        """Đặt vị trí trong Gazebo GZ_HZ lần mỗi giây, nội suy giữa hai khe để chuyển động liền mạch."""
        while True:
            started = time.monotonic()
            if self.cur is not None:
                (u1, w1), (u0, w0) = self.cur, self.prev or self.cur
                if u0.shape != u1.shape or w0.shape != w1.shape:
                    u0, w0 = u1, w1
                f = min(1.0, (time.monotonic() - self.t_cur) / self.period) if self.running else 1.0
                await asyncio.to_thread(self.gz.update, u0 + f * (u1 - u0), w0 + f * (w1 - w0), self.s.cfg.altitude,
                                        self.assoc, self.s.net.user_class)
            await asyncio.sleep(max(0.0, 1 / GZ_HZ - (time.monotonic() - started)))


def serve_static(port: int, ws_port: int):
    class Handler(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_GET(self):
            if self.path in ("/config.js",):  # cho trang biết cổng WebSocket
                body = f"window.WS_PORT={ws_port};".encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

        def log_message(self, *a):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=str(WEB)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()


async def amain(args):
    import websockets

    # mặc định có lưu lượng để dashboard có delay, mất gói; khe ngắn để lái mượt
    overrides = {"demand_mbps": 1.0, "dt": args.dt, "important_frac": 0.25, "critical_frac": 0.15} | parse_set(args.set)
    cfg = SimConfig.from_json(args.config, **overrides) if args.config else SimConfig(**overrides)
    session = LiveSession(cfg, args.algo)
    out = Path(args.out)
    gz, proc = None, None
    if args.gazebo:
        from . import gazebo

        gz_dir = out / "gazebo"
        gazebo.prepare_site(gz_dir)
        world = gz_dir / "uavsim_world.sdf"
        world.write_text(gazebo.world_sdf(
            session.net.uav_xy, cfg.altitude, cfg.area,
            num_users=cfg.num_users, num_uavs=cfg.num_uavs, user_xy=session.net.user_xy))
        proc = gazebo.launch(world, gz_dir / "models")
        print(f"Gazebo: {world.resolve()}  (tỷ lệ 1 m Gazebo = {1 / gazebo.SCALE:g} m mô hình)")
        gz = gazebo.GazeboView(cfg.area, num_users=cfg.num_users, num_uavs=cfg.num_uavs)
    server = Server(session, out, gz)
    serve_static(args.port, args.port + 1)
    try:
        async with websockets.serve(server.handle, "127.0.0.1", args.port + 1):
            print(f"Dashboard: http://localhost:{args.port}   (Ctrl+C để thoát)")
            tasks = [server.loop()] + ([server.gazebo_loop()] if gz is not None else [])
            await asyncio.gather(*tasks)
    finally:
        if proc is not None:  # đóng Gazebo cùng server
            os.killpg(proc.pid, signal.SIGINT)  # gz sim bỏ qua SIGTERM, thoát gọn với SIGINT


def _interrupt(*_):
    raise KeyboardInterrupt


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--algo", default="calib-ifair", choices=list(REGISTRY))
    p.add_argument("--dt", type=float, default=0.25, help="độ dài khe mô hình (s); chạy đúng thời gian thực ở tốc độ 1×")
    p.add_argument("--port", type=int, default=8000, help="HTTP; WebSocket dùng port + 1")
    p.add_argument("--gazebo", action="store_true",
                   help="hiển thị 3D trong Gazebo, nền là bãi của ~/simulation/multi_uav (đổi bằng biến MULTI_UAV_DIR)")
    p.add_argument("--config", help="file JSON ghi đè SimConfig")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VAL")
    p.add_argument("--out", default="experiments/results", help="nơi lưu phiên đã ghi")
    args = p.parse_args(argv)
    signal.signal(signal.SIGTERM, _interrupt)  # kill cũng đi qua nhánh dọn dẹp, đóng Gazebo
    try:
        asyncio.run(amain(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
