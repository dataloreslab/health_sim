"""Scoring utilities for Ageing Futures."""
from __future__ import annotations

import math
from typing import Dict

import numpy as np
import pandas as pd

from .utils import ScoringConfig


DIMENSION_DIRECTIONS = {
    "health": 1,
    "cost": -1,
    "capacity": 1,
    "equity": 1,
}


def _normalise(series: pd.Series, method: str, direction: int) -> pd.Series:
    values = series * direction
    if method == "zscore":
        mean = values.mean()
        std = values.std(ddof=0)
        if math.isclose(std, 0.0):
            return pd.Series(np.zeros(len(values)), index=series.index)
        return (values - mean) / std
    min_val = values.min()
    max_val = values.max()
    if math.isclose(max_val, min_val):
        return pd.Series(np.zeros(len(values)), index=series.index)
    return (values - min_val) / (max_val - min_val)


def score_round(metrics: pd.DataFrame, scoring_cfg: ScoringConfig) -> pd.DataFrame:
    df = metrics.copy()
    for dimension in scoring_cfg.weights:
        column = f"{dimension}_value"
        if column not in df:
            df[column] = 0.0
        direction = DIMENSION_DIRECTIONS.get(dimension, 1)
        df[f"{dimension}_score"] = _normalise(
            df[column], scoring_cfg.normalisation, direction
        )
    df["total_score"] = 0.0
    for dimension, weight in scoring_cfg.weights.items():
        df["total_score"] += df[f"{dimension}_score"] * weight
    df = df.sort_values("total_score", ascending=False)
    df["rank"] = np.arange(1, len(df) + 1)
    return df


__all__ = ["score_round"]
