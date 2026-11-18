import csv
import numpy as np
import pytest

from uavsim.algorithms import REGISTRY, Heuristic
from uavsim.channel import channel_gain, los_probability, path_loss_db
from uavsim.config import SimConfig
from uavsim.energy import rotary_power
from uavsim.network import Action, Network
from uavsim.run import run_episode, summarize


def test_los_channel_matches_beta0_over_d2():
    cfg = SimConfig(channel="los", altitude=100.0)
    g = channel_gain(np.array([[0.0, 0.0]]), np.array([[0.0, 0.0]]), cfg, None)
    assert g[0, 0] == pytest.approx(1e-6 / 100**2)


def test_al_hourani_los_prob_grows_with_elevation_and_adds_excess_loss():
    assert los_probability(10, "urban") < los_probability(45, "urban") < los_probability(90, "urban")
    cfg = SimConfig()
    d = np.array([300.0])
    fspl = 20 * np.log10(4 * np.pi * cfg.fc * d / 299_792_458.0)
    assert np.all(path_loss_db(d, d, cfg) > fspl)


def test_rotary_power_known_points():
    assert rotary_power(0) == pytest.approx(79.86 + 88.63)
    v = np.linspace(0, 40, 401)
    assert 8 < v[np.argmin(rotary_power(v))] < 14  # tốc độ tiết kiệm công suất nhất ~10 m/s


def test_single_link_rate_is_shannon():
    cfg = SimConfig(num_uavs=1, num_users=1, interference=False, slots=1)
    net = Network(cfg)
    a = Action(np.array([0]), np.array([1.0]), np.array([cfg.p_max]), np.zeros((1, 2)))
    snr = cfg.p_max * net.gain[0, 0] / (cfg.noise_psd * cfg.bandwidth)
    assert net.rates(a)[0] == pytest.approx(cfg.bandwidth * np.log2(1 + snr))


def test_lte_rate_model_is_capped_shannon():
    cfg = SimConfig(num_uavs=1, num_users=1, interference=False, rate_model="lte")
    net = Network(cfg)
    a = Action(np.array([0]), np.array([1.0]), np.array([cfg.p_max]), np.zeros((1, 2)))
    snr = cfg.p_max * net.gain[0, 0] / (cfg.noise_psd * cfg.bandwidth)
    expected = cfg.bandwidth * min(0.6 * np.log2(1 + snr), 4.4)
    assert net.rates(a)[0] == pytest.approx(expected)
    assert net.rates(a)[0] <= 4.4 * cfg.bandwidth


def test_interference_lowers_rate():
    cfg = SimConfig(num_uavs=2, num_users=4)
    net = Network(cfg)
    half = np.full(4, 0.5)
    a = Action(np.array([0, 0, 1, 1]), half, half * cfg.p_max, np.zeros((2, 2)))
    r_int = net.rates(a)
    net.cfg = SimConfig(num_uavs=2, num_users=4, interference=False)
    assert np.all(net.rates(a) >= r_int) and net.rates(a).sum() > r_int.sum()


def test_infeasible_action_rejected():
    cfg = SimConfig(num_uavs=1, num_users=2)
    net = Network(cfg)
    z = np.zeros((1, 2))
    with pytest.raises(ValueError, match="băng thông"):
        net.step(Action(np.array([0, 0]), np.array([0.7, 0.7]), np.array([0.1, 0.1]), z))
    with pytest.raises(ValueError, match="công suất"):
        net.step(Action(np.array([0, 0]), np.array([0.5, 0.5]), np.array([1.0, 1.0]), z))


def test_velocity_clipped_and_uav_stays_in_area():
    cfg = SimConfig(num_uavs=1, num_users=1, slots=50)
    net = Network(cfg)
    before = net.uav_xy.copy()
    net.step(Action(np.array([0]), np.array([1.0]), np.array([1.0]), np.array([[1e3, 0.0]])))
    assert np.linalg.norm(net.uav_xy - before) <= cfg.v_max * cfg.dt + 1e-9
    for _ in range(49):
        net.step(Action(np.array([0]), np.array([1.0]), np.array([1.0]), np.array([[1e3, 1e3]])))
    assert np.all((net.uav_xy >= 0) & (net.uav_xy <= cfg.area))


@pytest.mark.parametrize("name", list(REGISTRY))
def test_registry_algorithms_feasible_and_deterministic(name):
    cfg = SimConfig(slots=20, user_speed=2.0, rician_k_db=10.0)
    rows1, tr1 = run_episode(cfg, REGISTRY[name]())
    rows2, tr2 = run_episode(cfg, REGISTRY[name]())
    assert len(rows1) == 20 and rows1 == rows2 and np.array_equal(tr1, tr2)


def test_maxmin_equalizes_rates_within_uav_without_interference():
    cfg = SimConfig(num_uavs=1, num_users=5, interference=False, slots=1)
    net = Network(cfg)
    algo = Heuristic("hover", "maxmin")
    algo.reset(net)
    r = net.rates(algo.act(net))
    assert r.min() == pytest.approx(r.max(), rel=1e-9)


def test_kmeans_mobility_improves_rate_over_hover():
    cfg = SimConfig(slots=100)
    hover = np.mean([r["sum_rate"] for r in run_episode(cfg, Heuristic("hover"))[0][-10:]])
    km = np.mean([r["sum_rate"] for r in run_episode(cfg, Heuristic("kmeans"))[0][-10:]])
    assert km > hover


def test_gym_env_passes_checker():
    gym_utils = pytest.importorskip("gymnasium.utils.env_checker")
    from uavsim.env import UavBsEnv

    env = UavBsEnv(SimConfig(slots=10))
    gym_utils.check_env(env, skip_render_check=True)
    obs, _ = env.reset(seed=1)
    steps = 0
    done = False
    while not done:
        obs, rew, term, trunc, info = env.step(env.action_space.sample())
        done = term or trunc
        steps += 1
        assert env.observation_space.contains(obs) and rew >= 0
    assert steps == 10


def test_ns3_replay_low_load_matches_plan(tmp_path):
    """Tải 30% kế hoạch: NS-3 không tắc nghẽn nên throughput đo được ~ 0.3 * rate kế hoạch."""
    from uavsim import ns3

    if not ns3.BIN.exists():
        pytest.skip("chưa build kịch bản NS-3 (ns3/install.sh)")
    cfg = SimConfig(num_uavs=2, num_users=4, slots=4, rate_model="lte")
    r = ns3.run_one(cfg, "kmeans-equal", tmp_path, "pf", 0.3, timeout=300)
    assert r["cell_match"] == 1.0
    assert r["ns3_loss"] < 0.02
    assert r["ns3_sum_mbps"] == pytest.approx(0.3 * r["model_sum_mbps"], rel=0.1)
    assert (tmp_path / "kmeans-equal_load0.3_seed0" / "ns3.log").exists()
    assert r["delivered_ratio"] == pytest.approx(1.0, abs=0.1)


def test_ns3_rejects_non_lte_bandwidth(tmp_path):
    from uavsim import ns3

    with pytest.raises(ValueError, match="LTE"):
        ns3.ns3_command(SimConfig(bandwidth=7e6), tmp_path, tmp_path, "pf", 1.0)


def test_ns3_traces_and_separate_channels(tmp_path):
    """Mỗi eNB một kênh riêng (interference=False) thì SINR phải cao hơn hẳn khi dùng chung kênh."""
    from uavsim import ns3

    if not ns3.BIN.exists():
        pytest.skip("chưa build kịch bản NS-3 (ns3/install.sh)")
    res = {}
    for interf in (True, False):
        # seed 3: mỗi UAV phục vụ 3 user, nên cả hai eNB đều phát và có thể gây nhiễu cho nhau
        cfg = SimConfig(num_uavs=2, num_users=6, user_layout="uniform", seed=3, slots=3, rate_model="lte",
                        interference=interf)
        res[interf] = ns3.run_one(cfg, "hover-equal", tmp_path / str(interf), "pf", 1.0, timeout=300, traces=True)
    for r in res.values():
        assert r["cell_match"] == 1.0
        assert 0 <= r["mcs_mean"] <= 28 and 0 <= r["bler_first_tx"] <= 1
        assert r["phy_goodput_mbps"] >= r["ns3_sum_mbps"]  # PHY có thêm header so với payload UDP
        assert r["active_cells"] == 2
    assert res[False]["sinr_db_median"] > res[True]["sinr_db_median"] + 3


def test_fit_alpha_cap_recovers_known_curve():
    from uavsim.validate import fit_alpha_cap, se_formula

    sinr_db = np.arange(-4, 46, 5.0)
    se = se_formula(10 ** (sinr_db / 10), 0.4, 3.5)
    alpha, cap = fit_alpha_cap(sinr_db, se)
    assert alpha == pytest.approx(0.4, rel=1e-6) and cap == pytest.approx(3.5)


def test_lte_alpha_and_cap_are_configurable():
    cfg = SimConfig(num_uavs=1, num_users=1, interference=False, rate_model="lte", lte_alpha=0.4, lte_se_max=3.5)
    net = Network(cfg)
    a = Action(np.array([0]), np.array([1.0]), np.array([cfg.p_max]), np.zeros((1, 2)))
    snr = net.sinr(a)[0]
    assert net.rates(a)[0] == pytest.approx(cfg.bandwidth * min(0.4 * np.log2(1 + snr), 3.5))


def test_queue_step_underload_and_overload():
    from uavsim.network import queue_step

    # thiếu tải: phục vụ hết, không tồn đọng, không mất
    q, served, dropped, q_avg = queue_step(np.zeros(1), np.array([5.0]), np.array([10.0]), np.array([100.0]))
    assert q[0] == 0 and served[0] == 5 and dropped[0] == 0 and q_avg[0] == 0
    # quá tải: hàng đợi tăng tới bộ đệm, phần dư bị bỏ
    q = np.zeros(1)
    total_drop = 0.0
    for _ in range(100):
        q, served, dropped, _ = queue_step(q, np.array([20.0]), np.array([10.0]), np.array([50.0]))
        total_drop += dropped[0]
    assert q[0] == 50 and served[0] == 10 and dropped[0] == 10
    assert total_drop == pytest.approx(100 * 10 - 50)  # tổng đến - tổng phục vụ - phần còn trong hàng đợi


def test_network_demand_gives_delay_and_loss():
    lo = run_episode(SimConfig(slots=20, demand_mbps=0.1), Heuristic("kmeans"))[0]
    hi = run_episode(SimConfig(slots=20, demand_mbps=50.0), Heuristic("kmeans"))[0]
    assert all(r["loss"] == 0 for r in lo) and np.nanmax([r["delay_ms"] for r in lo]) < 50
    assert hi[-1]["loss"] > 0.5 and hi[-1]["delay_ms"] > lo[-1]["delay_ms"]
    assert all(r["throughput"] <= r["sum_rate"] + 1e-6 for r in hi)  # không phục vụ quá năng lực


def test_export_plan_sends_demand(tmp_path):
    from uavsim.ns3 import export_plan

    cfg = SimConfig(num_uavs=2, num_users=3, slots=2, demand_mbps=2.5)
    export_plan(cfg, Heuristic("hover"), tmp_path)
    rows = [l.split(",") for l in (tmp_path / "users.csv").read_text().splitlines()[1:]]
    assert {float(r[5]) for r in rows if int(r[0]) < 2} == {2.5e6}


def test_waterfill_max_min():
    from uavsim.network import waterfill

    assert np.allclose(waterfill(np.array([0.1, 0.5, 0.5]), 1.0), [0.1, 0.45, 0.45])
    assert np.allclose(waterfill(np.array([0.1, 0.2]), 1.0), [0.1, 0.2])  # đủ cho tất cả, không cấp thừa
    assert np.allclose(waterfill(np.array([np.inf, np.inf]), 1.0), [0.5, 0.5])


def test_work_conserving_never_worse_than_static():
    kw = dict(slots=30, demand_mbps=1.0, rate_model="lte", lte_alpha=0.401, lte_se_max=3.514)
    st = summarize(*[run_episode(SimConfig(**kw), Heuristic("hover"))[0]], SimConfig(**kw))
    wc = summarize(*[run_episode(SimConfig(**kw, work_conserving=True), Heuristic("hover"))[0]], SimConfig(**kw))
    assert wc["loss"] <= st["loss"] + 1e-9 and wc["throughput"] >= st["throughput"] - 1e-6


def test_load_coupled_interference_lowers_at_light_load():
    kw = dict(slots=10, demand_mbps=0.2, rate_model="lte")
    full = run_episode(SimConfig(**kw), Heuristic("kmeans"))[0]
    lc = run_episode(SimConfig(**kw, load_coupled=True), Heuristic("kmeans"))[0]
    # khe đầu chưa biết tải (util = 1) nên giống nhau; các khe sau nhiễu thấp hơn, năng lực cao hơn
    assert lc[0]["sum_rate"] == pytest.approx(full[0]["sum_rate"])
    assert lc[-1]["sum_rate"] > full[-1]["sum_rate"]


def _two_user_plan(plan, weights, slots=6):
    plan.mkdir(parents=True, exist_ok=True)
    (plan / "uavs.csv").write_text("slot,uav,x,y\n" + "".join(f"{s},0,500,500\n" for s in range(slots + 1)))
    (plan / "users.csv").write_text("slot,user,x,y,serving,rate_bps,bw\n" + "".join(
        f"{s},{k},550,500,{0 if s < slots else -1},{50e6 if s < slots else 0},{weights[k]}\n"
        for s in range(slots + 1) for k in range(2)))


def test_wpf_scheduler_shares_resources_by_weight(tmp_path):
    """Scheduler wpf: 2 UE cùng chỗ, trọng số 0.8/0.2, bão hòa -> throughput ~4:1; PF gốc -> 1:1, cùng tổng."""
    from uavsim import ns3

    if not ns3.BIN.exists():
        pytest.skip("chưa build kịch bản NS-3 (ns3/install.sh)")
    cfg = SimConfig(num_uavs=1, num_users=2, slots=6)
    thr = {}
    for sched in ("pf", "wpf"):
        d = tmp_path / sched
        _two_user_plan(d / "plan", (0.8, 0.2))
        ns3.run_ns3(ns3.ns3_command(cfg, d / "plan", d, sched, 1.0), d, 300)
        rows = [r for r in csv.DictReader(open(d / "ns3_slots.csv")) if int(r["slot"]) >= 1]
        thr[sched] = [sum(int(r["rx_bytes"]) for r in rows if int(r["user"]) == k) for k in range(2)]
    assert thr["pf"][0] / thr["pf"][1] == pytest.approx(1.0, rel=0.05)
    assert thr["wpf"][0] / thr["wpf"][1] == pytest.approx(4.0, rel=0.1)
    assert sum(thr["wpf"]) == pytest.approx(sum(thr["pf"]), rel=0.02)

    # dt = 0.1 s (< 0.15 s): trọng số WPF của khe trước không tràn sang khe sau khi đổi trọng số
    short_slots = 12
    short_cfg = SimConfig(num_uavs=1, num_users=2, slots=short_slots, dt=0.1)
    d_short = tmp_path / "wpf_short"
    (d_short / "plan").mkdir(parents=True)
    (d_short / "plan/uavs.csv").write_text("slot,uav,x,y\n" + "".join(f"{s},0,500,500\n" for s in range(short_slots + 1)))
    (d_short / "plan/users.csv").write_text("slot,user,x,y,serving,rate_bps,bw\n" + "".join(
        f"{s},{k},550,500,{0 if s < short_slots else -1},{50e6 if s < short_slots else 0},"
        f"{(0.05 if k == 0 else 0.95) if s < 2 else (0.9 if k == 0 else 0.1)}\n"
        for s in range(short_slots + 1) for k in range(2)))
    ns3.run_ns3(ns3.ns3_command(short_cfg, d_short / "plan", d_short, "wpf", 1.0), d_short, 300)
    short_rows = [r for r in csv.DictReader(open(d_short / "ns3_slots.csv")) if int(r["slot"]) >= 4]
    rx = [sum(int(r["rx_bytes"]) for r in short_rows if int(r["user"]) == k) for k in range(2)]
    assert rx[0] > 4.0 * rx[1]


def test_ns3_ideal_link_matches_queue_model(tmp_path):
    """link=ideal: tốc độ liên kết = rate lý thuyết, nên throughput NS-3 trùng mô hình hàng đợi."""
    from uavsim import ns3

    if not ns3.BIN.exists():
        pytest.skip("chưa build kịch bản NS-3 (ns3/install.sh)")
    cfg = SimConfig(num_uavs=2, num_users=4, slots=4, demand_mbps=3)
    r = ns3.run_one(cfg, "kmeans-equal", tmp_path, "pf", 2.0, timeout=120, link="ideal")
    assert r["ns3_sum_mbps"] == pytest.approx(r["model_thr_mbps"], rel=0.01)
    assert r["ns3_min_mbps"] == pytest.approx(r["model_min_thr_mbps"], rel=0.02)
    assert r["ns3_loss"] == pytest.approx(r["model_loss"], abs=0.005)
    assert r["ns3_delay_ms"] == pytest.approx(r["model_delay_ms"], rel=0.03)


def test_fifo_delay_exact():
    """Đến 2 bit/s, phục vụ 1 bit/s trong khe 1, rồi không đến nữa: bit phục vụ lúc t đến lúc t/2, delay t/2."""
    from uavsim.network import fifo_delay

    hist = [(np.zeros(1), np.zeros(1), 0.0)]
    w1 = fifo_delay(hist, np.zeros(1), np.array([2.0]), np.array([1.0]), np.inf, 0.0, 1.0)
    w2 = fifo_delay(hist, np.ones(1), np.zeros(1), np.array([1.0]), np.inf, 1.0, 1.0)
    assert w1[0] == pytest.approx(0.25, rel=1e-3)  # trung bình t/2 trên [0, 1]
    assert w2[0] == pytest.approx(0.75, rel=1e-3)  # trung bình t/2 trên [1, 2]


def test_live_manual_override_and_recording(tmp_path):
    """Lái tay: UAV đi đúng vận tốc lệnh (bị cắt về v_max), UAV khác theo thuật toán. Ghi phiên ra kế hoạch NS-3 hợp lệ."""
    from uavsim.live import LiveSession

    s = LiveSession(SimConfig(num_uavs=2, num_users=6, demand_mbps=1.0), "hover-equal")
    s.set_manual(0, True)
    s.command(0, 30.0, 0.0)  # vượt v_max = 20
    s.start_recording()
    s.set_manual(0, True)
    s.command(0, 30.0, 0.0)
    p0 = s.net.uav_xy.copy()
    for _ in range(3):
        st = s.step()
    moved = s.net.uav_xy - p0
    assert moved[0, 0] == pytest.approx(min(60.0, s.cfg.area - p0[0, 0]))  # 3 khe × 20 m/s, trừ khi chạm biên
    assert np.allclose(moved[1], 0)  # hover
    assert st["t"] == 2 and len(st["rate"]) == 6
    d = s.stop_recording(tmp_path)
    cfg = SimConfig.from_json(str(d / "config.json"))
    assert cfg.slots == 3 and cfg.demand_mbps == 1.0
    users = (d / "plan" / "users.csv").read_text().splitlines()
    assert users[0] == "slot,user,x,y,serving,rate_bps,bw,cap_bps" and len(users) == 1 + 4 * 6
    with pytest.raises(ValueError):
        s.set_manual(5, True)


def test_gazebo_world_follows_model(tmp_path):
    """World Gazebo: người có sẵn của bãi bị bỏ, thêm đúng M UAV và K user của mô hình theo tỷ lệ 1:10 quanh tâm bãi."""
    import xml.etree.ElementTree as ET

    from uavsim import gazebo

    if not (gazebo.ROOT / "worlds" / f"{gazebo.WORLD}.sdf").exists():
        pytest.skip("không có ~/simulation/multi_uav")
    gazebo.prepare_site(tmp_path)
    site = (tmp_path / "models/disaster_site/model.sdf").read_text()
    assert gazebo.RESIDENT not in site and "residential_01" in site  # chỉ bỏ người, giữ nhà
    users = np.array([[0.0, 0.0], [500.0, 500.0], [1000.0, 250.0]])
    root = ET.fromstring(gazebo.world_sdf(np.array([[500.0, 500.0]]), 100.0, 1000.0))
    w = root.find("world")
    names = [m.get("name") for m in w.findall("model")]
    assert [n for n in names if n.startswith("uav")] == [f"uav{j}" for j in range(gazebo.MAX_UAVS)]
    assert sum(n.startswith("mk") for n in names) == (gazebo.MAX_UAVS + 1) * gazebo.MAX_USERS
    pose = lambda n: [float(v) for v in w.find(f"model[@name='{n}']/pose").text.split()[:3]]
    assert np.allclose(pose("uav0"), [0, 0, 10]) and pose("uav1")[2] == gazebo.PARK_Z  # bể chưa dùng nằm dưới đất
    assert pose("mk0_0")[2] == gazebo.PARK_Z and w.find("model[@name='mk0_0']//collision") is None
    assert w.find("gravity").text == "0 0 0"
    assert np.allclose(gazebo.to_gz(users, 1000.0)[2], [50, -25])

    # người mặc áo màu UAV phục vụ: đổi UAV thì hình người màu cũ về PARK_Z, hình màu mới đứng vào chỗ
    view = object.__new__(gazebo.GazeboView)
    view.marked = {}
    m = view._markers(np.zeros((2, 2)), [1, -1])
    assert set(m) == {"mk1_0", f"mk{gazebo.MAX_UAVS}_1"}
    view.marked = m
    m = view._markers(np.zeros((2, 2)), [0, -1])
    assert m["mk1_0"][2] == gazebo.PARK_Z and m["mk0_0"][2] == gazebo.MARK_Z
    # vòng nhóm: user critical có vòng đỏ, important vòng vàng, normal không có
    assert sum(n.startswith(("crit", "imp")) for n in names) == 2 * gazebo.MAX_USERS
    view.marked = {}
    m = view._markers(np.zeros((3, 2)), [0, 0, 0], [0, 1, 2])
    assert "imp1" in m and "crit2" in m and not any(n.endswith("0") and n[:3] in ("imp", "cri") for n in m)


def test_live_goto_and_config():
    """Bay tới điểm nhấp rồi dừng đúng chỗ; đổi tham số dựng lại kịch bản; tham số ngoài khoảng bị từ chối."""
    from uavsim.live import LiveSession

    s = LiveSession(SimConfig(num_uavs=2, num_users=6, demand_mbps=1.0, dt=0.5), "hover-equal")
    start = s.net.uav_xy[0].copy()
    goal = np.clip(start + [30.0, -12.0], 0, 1000)
    s.goto(0, *goal)
    for _ in range(10):
        st = s.step()
    assert np.allclose(s.net.uav_xy[0], goal, atol=1e-6) and "0" not in st["targets"]
    assert len(st["lte_rate"]) == 6 and st["lte_sum"] <= st["sum_rate"] + 1e-9  # LTE hiệu chỉnh không vượt Shannon
    s.apply_config({"num_uavs": 4, "num_users": 12, "environment": "suburban"})
    assert s.net.uav_xy.shape == (4, 2) and s.net.user_xy.shape == (12, 2) and s.net.t == 0
    for bad in ({"num_uavs": 99}, {"bandwidth": 5e6}, {"environment": "mars"}):
        with pytest.raises(ValueError):
            s.apply_config(bad)

    # có demand_mbps: min throughput nhóm trên dashboard không vượt lưu lượng gửi vào ở khe đầu (hàng đợi rỗng)
    st_cls = LiveSession(SimConfig(demand_mbps=1.0, important_frac=0.25, critical_frac=0.15,
                                   rate_model="lte", lte_alpha=0.401, lte_se_max=3.514), "calib-ifair").step()
    assert st_cls["classes"]["min_critical"] <= 1.0 + 1e-6 and max(st_cls["user_thr"]) <= 1.0 + 1e-6


def test_proposed_algorithm_feasible_and_fairer():
    """calib-ifair hợp lệ, tái lập được, và trên mô hình LTE hiệu chỉnh cho min rate cao hơn kmeans-equal."""
    from uavsim.run import run_episode, summarize

    cal = dict(rate_model="lte", lte_alpha=0.401, lte_se_max=3.514, slots=30)
    mins = {}
    for name in ("kmeans-equal", "calib-ifair"):
        r = [summarize(run_episode(SimConfig(seed=s, **cal), REGISTRY[name]())[0], SimConfig(seed=s, **cal))["min_rate"]
             for s in range(3)]
        mins[name] = np.mean(r)
    a = run_episode(SimConfig(seed=1, **cal), REGISTRY["calib-ifair"]())[1]
    b = run_episode(SimConfig(seed=1, **cal), REGISTRY["calib-ifair"]())[1]
    assert np.array_equal(a, b)
    assert mins["calib-ifair"] > 1.3 * mins["kmeans-equal"]


def test_user_classes_and_weighted_allocation(tmp_path):
    """Ba nhóm user: tỷ lệ đúng, không đổi vị trí user; calib-ifair có trọng số ưu tiên critical hơn bản bỏ qua nhóm."""
    from uavsim.algorithms import associate_max_gain, calibrated_se
    from uavsim.animate import animate
    from uavsim.network import user_classes

    base = dict(num_users=20, slots=20, demand_mbps=2.0, rate_model="lte", lte_alpha=0.401, lte_se_max=3.514)
    cfg = SimConfig(important_frac=0.25, critical_frac=0.15, **base)
    cls = user_classes(cfg)
    assert np.bincount(cls, minlength=3).tolist() == [12, 5, 3]
    assert np.array_equal(Network(cfg).user_xy, Network(SimConfig(**base)).user_xy)  # nhóm không đổi kịch bản
    assert np.all(user_classes(SimConfig(**base)) == 0)
    with pytest.raises(ValueError):
        SimConfig(important_frac=0.7, critical_frac=0.5)

    crit = {}
    for name in ("calib-ifair-noclass", "calib-ifair"):
        net, algo, rows = Network(cfg), REGISTRY[name](), []
        algo.reset(net)
        while not net.done:
            a = algo.act(net)
            net.check(a)
            rows.append(net.step(a))
        crit[name] = np.mean([r["min_critical"] for r in rows])
        assert {"sat_normal", "sat_important", "sat_critical"} <= set(rows[0])
    assert crit["calib-ifair"] > 1.1 * crit["calib-ifair-noclass"]

    # baseline biết nhóm: max-min có trọng số cho user critical băng nhiều hơn maxmin thường
    net = Network(cfg)
    bw = {n: REGISTRY[n]().allocate(net)[1] for n in ("kmeans-maxmin", "kmeans-wmaxmin")}
    crit_k = net.user_class == 2
    assert bw["kmeans-wmaxmin"][crit_k].sum() > bw["kmeans-maxmin"][crit_k].sum()

    # fading nhỏ: ifair dùng đúng net.gain thực tế để liên kết và SE khớp nhau
    net_fad = Network(SimConfig(rician_k_db=3.0, slots=2))
    assoc_fad, _ = calibrated_se(net_fad.cfg, net_fad.uav_xy, net_fad.user_xy, gain=net_fad.gain)
    assert np.array_equal(assoc_fad, associate_max_gain(net_fad))

    # animate không lỗi khi chỉ có nhóm important (không có critical)
    out_gif = tmp_path / "partial.gif"
    animate(SimConfig(slots=4, demand_mbps=1.0, important_frac=0.25, critical_frac=0.0), ["calib-ifair"], out_gif, every=2)
    assert out_gif.exists() and out_gif.stat().st_size > 0
