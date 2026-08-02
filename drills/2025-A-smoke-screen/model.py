"""2025 CUMCM A: smoke-screen kinematics and visibility model.

This module deliberately depends only on the official problem statement.  A
cloud is effective when it intersects every sampled sight segment from a
missile to the visible boundary of the protected cylindrical target.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

import numpy as np


GRAVITY = 9.8
MISSILE_SPEED = 300.0
CLOUD_RADIUS = 10.0
CLOUD_LIFETIME = 20.0
CLOUD_SINK_SPEED = 3.0
TARGET_CENTER = np.array([0.0, 200.0, 5.0])
TARGET_RADIUS = 7.0
TARGET_HEIGHT = 10.0

MISSILES = {
    "M1": np.array([20000.0, 0.0, 2000.0]),
    "M2": np.array([19000.0, 600.0, 2100.0]),
    "M3": np.array([18000.0, -600.0, 1900.0]),
}

DRONES = {
    "FY1": np.array([17800.0, 0.0, 1800.0]),
    "FY2": np.array([12000.0, 1400.0, 1400.0]),
    "FY3": np.array([6000.0, -3000.0, 700.0]),
    "FY4": np.array([11000.0, 2000.0, 1800.0]),
    "FY5": np.array([13000.0, -2000.0, 1300.0]),
}


@dataclass(frozen=True)
class CloudPlan:
    drone: str
    missile: str
    direction_deg: float
    speed: float
    release_time: float
    fuse_delay: float
    bomb_no: int = 1

    @property
    def burst_time(self) -> float:
        return self.release_time + self.fuse_delay

    def to_dict(self) -> dict:
        data = asdict(self)
        data["burst_time"] = self.burst_time
        data["release_point"] = release_point(self).round(6).tolist()
        data["burst_point"] = burst_point(self).round(6).tolist()
        return data


def direction_vector(direction_deg: float) -> np.ndarray:
    angle = np.deg2rad(direction_deg)
    return np.array([np.cos(angle), np.sin(angle), 0.0])


def missile_hit_time(missile: str) -> float:
    return float(np.linalg.norm(MISSILES[missile]) / MISSILE_SPEED)


def missile_positions(missile: str, times: np.ndarray) -> np.ndarray:
    initial = MISSILES[missile]
    scale = 1.0 - MISSILE_SPEED * np.asarray(times) / np.linalg.norm(initial)
    return scale[:, None] * initial[None, :]


def drone_positions(drone: str, direction_deg: float, speed: float, times: np.ndarray) -> np.ndarray:
    initial = DRONES[drone]
    return initial[None, :] + np.asarray(times)[:, None] * speed * direction_vector(direction_deg)[None, :]


def release_point(plan: CloudPlan) -> np.ndarray:
    return drone_positions(
        plan.drone, plan.direction_deg, plan.speed, np.array([plan.release_time])
    )[0]


def burst_point(plan: CloudPlan) -> np.ndarray:
    point = drone_positions(
        plan.drone, plan.direction_deg, plan.speed, np.array([plan.burst_time])
    )[0]
    point[2] -= 0.5 * GRAVITY * plan.fuse_delay**2
    return point


def cloud_centers(plan: CloudPlan, times: np.ndarray) -> np.ndarray:
    center = np.repeat(burst_point(plan)[None, :], len(times), axis=0)
    center[:, 2] -= CLOUD_SINK_SPEED * (np.asarray(times) - plan.burst_time)
    return center


def plan_is_feasible(plan: CloudPlan) -> bool:
    if not (0.0 <= plan.direction_deg <= 360.0 and 70.0 <= plan.speed <= 140.0):
        return False
    if plan.release_time < 0.0 or plan.fuse_delay < 0.0:
        return False
    if plan.burst_time > missile_hit_time(plan.missile):
        return False
    return bool(burst_point(plan)[2] >= 0.0)


@lru_cache(maxsize=16)
def target_boundary_points(n_angles: int = 48) -> np.ndarray:
    """Sample the two extreme circular rims of the convex cylinder."""
    angle = np.linspace(0.0, 2.0 * np.pi, n_angles, endpoint=False)
    x = TARGET_RADIUS * np.cos(angle)
    y = TARGET_CENTER[1] + TARGET_RADIUS * np.sin(angle)
    bottom = np.column_stack((x, y, np.zeros_like(angle)))
    top = np.column_stack((x, y, np.full_like(angle, TARGET_HEIGHT)))
    return np.vstack((bottom, top, [[0.0, 200.0, 0.0], [0.0, 200.0, 10.0]]))


def _segments_intersect_sphere(
    missile_pos: np.ndarray,
    target_points: np.ndarray,
    cloud_center: np.ndarray,
) -> np.ndarray:
    """Return a (time, target-point) sight-segment intersection mask."""
    start = missile_pos[:, None, :]
    segment = target_points[None, :, :] - start
    offset = cloud_center[:, None, :] - start
    denom = np.sum(segment * segment, axis=2)
    projection = np.sum(segment * offset, axis=2) / denom
    projection = np.clip(projection, 0.0, 1.0)
    nearest = start + projection[:, :, None] * segment
    distance = np.linalg.norm(nearest - cloud_center[:, None, :], axis=2)
    return distance <= CLOUD_RADIUS


def coverage_mask(
    missile: str,
    plans: list[CloudPlan],
    times: np.ndarray,
    n_angles: int = 48,
    center_only: bool = False,
) -> np.ndarray:
    """Return times when the plans collectively obscure the target."""
    times = np.asarray(times, dtype=float)
    if not plans:
        return np.zeros(times.shape, dtype=bool)
    points = TARGET_CENTER[None, :] if center_only else target_boundary_points(n_angles)
    missile_pos = missile_positions(missile, times)
    blocked = np.zeros((len(times), len(points)), dtype=bool)

    for plan in plans:
        active = (
            (times >= plan.burst_time)
            & (times <= plan.burst_time + CLOUD_LIFETIME)
            & (times <= missile_hit_time(missile))
        )
        if not np.any(active) or not plan_is_feasible(plan):
            continue
        hit = _segments_intersect_sphere(
            missile_pos[active], points, cloud_centers(plan, times[active])
        )
        blocked[active] |= hit
    return np.all(blocked, axis=1)


def mask_duration(mask: np.ndarray, times: np.ndarray) -> float:
    if len(times) < 2:
        return 0.0
    return float(np.count_nonzero(mask) * np.median(np.diff(times)))


def coverage_intervals(mask: np.ndarray, times: np.ndarray) -> list[list[float]]:
    indices = np.flatnonzero(mask)
    if len(indices) == 0:
        return []
    dt = float(np.median(np.diff(times)))
    breaks = np.flatnonzero(np.diff(indices) > 1)
    starts = np.r_[indices[0], indices[breaks + 1]]
    ends = np.r_[indices[breaks], indices[-1]]
    return [[float(times[a] - dt / 2), float(times[b] + dt / 2)] for a, b in zip(starts, ends)]


def evaluate_plans(
    missile: str,
    plans: list[CloudPlan],
    dt: float = 0.01,
    n_angles: int = 96,
    center_only: bool = False,
) -> dict:
    times = np.arange(0.0, missile_hit_time(missile) + dt / 2, dt)
    mask = coverage_mask(missile, plans, times, n_angles=n_angles, center_only=center_only)
    return {
        "duration": mask_duration(mask, times),
        "intervals": coverage_intervals(mask, times),
        "dt": dt,
        "n_angles": n_angles,
    }

