"""Hazard and probability helpers for transition modelling."""
from __future__ import annotations

import numpy as np


def log_linear_predictor(
    intercept: float,
    coefficients: dict[str, float],
    features: dict[str, np.ndarray],
) -> np.ndarray:
    lp = np.full_like(next(iter(features.values())), fill_value=intercept, dtype=float)
    for key, coef in coefficients.items():
        values = features.get(key)
        if values is None:
            continue
        lp = lp + coef * values
    return lp


def hazard_to_probability(hazard: np.ndarray, dt_months: float) -> np.ndarray:
    dt_years = dt_months / 12.0
    probability = 1.0 - np.exp(-np.clip(hazard, 0, None) * dt_years)
    return np.clip(probability, 0.0, 1.0)


def log_hazard_to_probability(lp: np.ndarray, dt_months: float) -> np.ndarray:
    hazard = np.exp(lp)
    return hazard_to_probability(hazard, dt_months)


def ensure_competing_risk(probabilities: list[np.ndarray]) -> list[np.ndarray]:
    total = np.zeros_like(probabilities[0])
    for arr in probabilities:
        total += arr
    excess = np.maximum(total - 1.0, 0.0)
    if float(np.max(excess)) <= 1e-8:
        return probabilities
    # Rescale to keep sum <= 1
    adjusted = []
    for arr in probabilities:
        adjusted.append(np.clip(arr - excess * (arr / (total + 1e-12)), 0.0, 1.0))
    return adjusted


__all__ = [
    "log_linear_predictor",
    "hazard_to_probability",
    "log_hazard_to_probability",
    "ensure_competing_risk",
]
