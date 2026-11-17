"""E12: hiệu năng server WebSocket của trạm điều khiển (uavsim.live).

python experiments/bench_websocket.py experiments/results/websocket
Khởi động server (không Gazebo), cho N client cùng kết nối, đo: kích thước bản tin, băng thông mỗi client, độ trễ lệnh
khứ hồi (gửi lệnh -> nhận info phản hồi), nhịp nhận state (độ lệch so với chu kỳ khe 0.25 s) và CPU của server.
Ghi <out>.csv.
"""
import asyncio
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import psutil
import websockets

PORT = 8100
CLIENTS = [1, 5, 10, 20, 50]
DURATION = 20.0  # giây đo cho mỗi N
PINGS = 40  # số lệnh đo khứ hồi (client 0 gửi)


async def client(i, stop, stats, rtt):
    async with websockets.connect(f"ws://127.0.0.1:{PORT + 1}", max_size=None) as ws:
        sizes, gaps, last = {"info": [], "state": []}, [], None
        pending = None

        async def pinger():
            nonlocal pending
            await asyncio.sleep(2.0)
            for _ in range(PINGS):
                pending = time.perf_counter()
                await ws.send(json.dumps({"cmd": "speed", "x": 1}))  # lệnh vô hại, server trả info cho mọi client
                await asyncio.sleep(0.3)

        task = asyncio.create_task(pinger()) if i == 0 else None
        while not stop.is_set():
            try:
                raw = await asyncio.wait_for(ws.recv(), 0.5)
            except asyncio.TimeoutError:
                continue
            t = time.perf_counter()
            kind = json.loads(raw)["type"]
            sizes[kind].append(len(raw.encode()))
            if kind == "state":
                if last is not None:
                    gaps.append(t - last)
                last = t
            elif pending is not None and i == 0:
                rtt.append(t - pending)
                pending = None
        if task:
            task.cancel()
        stats.append((sizes, gaps))


async def run(n):
    stop, stats, rtt = asyncio.Event(), [], []
    tasks = [asyncio.create_task(client(i, stop, stats, rtt)) for i in range(n)]
    await asyncio.sleep(DURATION)
    stop.set()
    await asyncio.gather(*tasks)
    return stats, rtt


def main(out):
    srv = subprocess.Popen([sys.executable, "-m", "uavsim.live", "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rows = []
    try:
        time.sleep(4)
        proc = psutil.Process(srv.pid)
        for n in CLIENTS:
            proc.cpu_percent(None)
            stats, rtt = asyncio.run(run(n))
            cpu = proc.cpu_percent(None)
            state = [s for st, _ in stats for s in st["state"]]
            info = [s for st, _ in stats for s in st["info"]]
            gaps = np.array([g for _, gs in stats for g in gs])
            per_client_bytes = (sum(state) + sum(info)) / n / DURATION
            rtt_ms = 1e3 * np.array(rtt)
            row = {"clients": n, "state_bytes": np.mean(state), "info_bytes": np.mean(info),
                   "kB_s_per_client": per_client_bytes / 1e3, "kB_s_total": per_client_bytes * n / 1e3,
                   "state_per_s": len(state) / n / DURATION,
                   "gap_ms_mean": 1e3 * gaps.mean(), "gap_ms_p95": 1e3 * np.percentile(gaps, 95),
                   "rtt_ms_median": np.median(rtt_ms), "rtt_ms_p95": np.percentile(rtt_ms, 95),
                   "rtt_n": len(rtt_ms), "server_cpu_pct": cpu}
            rows.append(row)
            print({k: round(v, 2) if isinstance(v, float) else v for k, v in row.items()}, flush=True)
    finally:
        srv.terminate()
        srv.wait(10)
    path = Path(out).with_suffix(".csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows({k: f"{v:.4g}" if isinstance(v, float) else v for k, v in r.items()} for r in rows)
    print(f"Đã ghi {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
