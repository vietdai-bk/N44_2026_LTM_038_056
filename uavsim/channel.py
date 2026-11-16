"""Mô hình kênh Air-to-Ground."""
import numpy as np

from .config import ENVIRONMENTS, SimConfig

C = 299_792_458.0


def los_probability(elevation_deg, environment: str):
    a, b, _, _ = ENVIRONMENTS[environment]
    return 1.0 / (1.0 + a * np.exp(-b * (elevation_deg - a)))


def path_loss_db(d3, horiz, cfg: SimConfig):
    """Suy hao trung bình (dB). d3: khoảng cách 3D, horiz: khoảng cách ngang (m)."""
    if cfg.channel == "los":  # Wu-Zeng-Zhang 2018: g = beta0 / d^2
        return -cfg.beta0_db + 20 * np.log10(d3)
    _, _, eta_los, eta_nlos = ENVIRONMENTS[cfg.environment]
    p_los = los_probability(np.degrees(np.arctan2(cfg.altitude, horiz)), cfg.environment)
    fspl = 20 * np.log10(4 * np.pi * cfg.fc * d3 / C)
    return fspl + p_los * eta_los + (1 - p_los) * eta_nlos


def rician_power(shape, k_db, rng):
    """|h|^2 của fading Rician, kỳ vọng bằng 1."""
    k = 10 ** (k_db / 10)
    nlos = (rng.standard_normal(shape) + 1j * rng.standard_normal(shape)) / np.sqrt(2)
    return np.abs(np.sqrt(k / (k + 1)) + np.sqrt(1 / (k + 1)) * nlos) ** 2


def channel_gain(uav_xy, user_xy, cfg: SimConfig, rng):
    """Độ lợi công suất tuyến tính, shape [M, K]."""
    horiz = np.linalg.norm(uav_xy[:, None, :] - user_xy[None, :, :], axis=-1)
    d3 = np.sqrt(horiz**2 + cfg.altitude**2)
    g = 10 ** (-path_loss_db(d3, horiz, cfg) / 10)
    if cfg.rician_k_db is not None:
        g = g * rician_power(g.shape, cfg.rician_k_db, rng)
    return g
