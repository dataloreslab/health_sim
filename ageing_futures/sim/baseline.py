"""Synthetic baseline cohort generation."""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from .states import Cohort, LTCState
from .utils import BaselinePopulationConfig, load_config_bundle, rng

AGE_BANDS = {
    "65-69": (65, 69),
    "70-74": (70, 74),
    "75-79": (75, 79),
    "80-84": (80, 84),
    "85+": (85, 95),
}


def _sample_from_distribution(gen: np.random.Generator, dist: Dict[str, float], size: int) -> np.ndarray:
    choices = list(dist.keys())
    probs = np.array([dist[k] for k in choices], dtype=float)
    probs = probs / probs.sum()
    return gen.choice(choices, size=size, p=probs)


def create_baseline_cohort(
    seed: int,
    baseline_config: BaselinePopulationConfig | None = None,
) -> Cohort:
    cfg = baseline_config or load_config_bundle().baseline
    gen = rng(seed)
    n = cfg.cohort_size

    age_band = _sample_from_distribution(gen, cfg.age_distribution, n)
    ages = np.empty(n)
    for band, bounds in AGE_BANDS.items():
        mask = age_band == band
        if band == "85+":
            ages[mask] = gen.integers(bounds[0], bounds[1] + 1, size=mask.sum())
        else:
            ages[mask] = gen.integers(bounds[0], bounds[1] + 1, size=mask.sum())

    sex = _sample_from_distribution(gen, cfg.sex_distribution, n)
    region = _sample_from_distribution(gen, cfg.regions, n)
    imd = gen.choice(np.arange(1, len(cfg.imd_distribution) + 1), size=n, p=np.array(cfg.imd_distribution))
    urban_rural = _sample_from_distribution(gen, cfg.urban_rural_split, n)

    service_gp = gen.normal(cfg.service_indices.get("gp_density_mean", 0.0), cfg.service_indices.get("gp_density_sd", 0.1), size=n)
    service_comm = gen.normal(cfg.service_indices.get("community_capacity_mean", 0.0), cfg.service_indices.get("community_capacity_sd", 0.1), size=n)
    heat = gen.normal(cfg.environment_indices.get("heat_exposure_mean", 0.0), cfg.environment_indices.get("heat_exposure_sd", 0.1), size=n)
    cold = gen.normal(cfg.environment_indices.get("cold_exposure_mean", 0.0), cfg.environment_indices.get("cold_exposure_sd", 0.1), size=n)

    # LTC baseline distribution: older + deprived more likely
    base_prob = 0.2 + 0.01 * (ages - 65) + 0.03 * (imd - 3)
    base_prob = np.clip(base_prob, 0.05, 0.9)
    ltc_state = np.where(gen.random(n) < base_prob, 1, 0)
    progression_prob = np.clip(0.15 + 0.008 * (ages - 70), 0.05, 0.8)
    ltc_state = np.where(gen.random(n) < progression_prob * (ltc_state > 0), 2, ltc_state)
    severe_prob = np.clip(0.06 + 0.01 * (ages - 80), 0.02, 0.6)
    ltc_state = np.where(gen.random(n) < severe_prob * (ltc_state >= 2), 3, ltc_state)

    disability = gen.random(n) < np.clip(0.1 + 0.02 * (ltc_state), 0, 0.7)
    hospitalised = np.zeros(n, dtype=bool)
    alive = np.ones(n, dtype=bool)
    care_home = np.zeros(n, dtype=bool)

    cohort = Cohort(
        data={
            "age": ages,
            "sex": sex,
            "region": region,
            "imd_quintile": imd.astype(int),
            "urban_rural": urban_rural,
            "ltc_state": ltc_state.astype(int),
            "disability": disability.astype(int),
            "hospitalised": hospitalised.astype(int),
            "alive": alive.astype(int),
            "care_home": care_home.astype(int),
            "gp_access": service_gp,
            "community_capacity": service_comm,
            "heat_exposure": heat,
            "cold_exposure": cold,
            "hospital_beds_per_1k": np.full(n, cfg.care_capacity.get("hospital_beds_per_1k", 3.0)),
            "care_home_beds_per_1k": np.full(n, cfg.care_capacity.get("care_home_beds_per_1k", 5.0)),
        }
    )
    return cohort


__all__ = ["create_baseline_cohort"]
