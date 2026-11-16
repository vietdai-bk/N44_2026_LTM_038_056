"""Môi trường Gymnasium: agent điều khiển vận tốc UAV, cấp phát tài nguyên giao cho allocator heuristic.

Đây là cách tách phổ biến trong paper DRL (DRL cho quỹ đạo, cấp phát tài nguyên dùng thuật toán đóng).
Muốn DRL học luôn cấp phát thì viết env khác dựa trên Network.step(Action).
"""
import gymnasium as gym
import numpy as np

from .algorithms import Heuristic
from .config import SimConfig
from .network import Action, Network


def sum_rate_reward(m: dict, cfg: SimConfig) -> float:
    return m["sum_rate"] / (cfg.num_users * cfg.r_min)


class UavBsEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, cfg: SimConfig | None = None, allocator=None, reward_fn=sum_rate_reward):
        self.cfg = cfg or SimConfig()
        self.net = Network(self.cfg)
        self.allocator = allocator or Heuristic("hover", "equal")
        self.reward_fn = reward_fn
        M, K = self.cfg.num_uavs, self.cfg.num_users
        self.observation_space = gym.spaces.Box(0.0, 1.0, (2 * (M + K),), np.float32)
        self.action_space = gym.spaces.Box(-1.0, 1.0, (M, 2), np.float32)

    def _obs(self):
        return (np.concatenate([self.net.uav_xy.ravel(), self.net.user_xy.ravel()]) / self.cfg.area).astype(np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        # seed=None: mỗi episode một kịch bản mới (vị trí user/UAV khác nhau)
        self.net.reset(seed if seed is not None else int(self.np_random.integers(2**31)))
        self.allocator.reset(self.net)
        return self._obs(), {}

    def step(self, action):
        assoc, bw, power = self.allocator.allocate(self.net)
        vel = np.clip(np.asarray(action, float), -1, 1) * self.cfg.v_max
        m = self.net.step(Action(assoc, bw, power, vel))
        return self._obs(), float(self.reward_fn(m, self.cfg)), False, self.net.done, m
