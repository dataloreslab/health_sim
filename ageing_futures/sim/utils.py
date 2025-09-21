"""Utility helpers for configuration loading and deterministic RNG."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


class BaselinePopulationConfig(BaseModel):
    cohort_size: int = Field(..., gt=0)
    age_distribution: Dict[str, float]
    sex_distribution: Dict[str, float]
    regions: Dict[str, float]
    imd_distribution: List[float]
    urban_rural_split: Dict[str, float]
    service_indices: Dict[str, float]
    environment_indices: Dict[str, float]
    care_capacity: Dict[str, float]


class TransitionDefinition(BaseModel):
    intercept: float
    coefficients: Dict[str, float]


class LengthOfStayConfig(BaseModel):
    mean: float
    overdispersion: float
    capacity_multiplier: float


class TransitionsConfig(BaseModel):
    time_step_months: int = 1
    transitions: Dict[str, TransitionDefinition]
    length_of_stay: Dict[str, LengthOfStayConfig]


class PolicyConfig(BaseModel):
    id: str
    name: str
    description: str
    cost_per_capita: float
    target: Dict[str, object]
    effects: Dict[str, float]
    lag_months: int = 0
    diminishing_return: float = 0.0


class PoliciesConfig(BaseModel):
    policies: List[PolicyConfig]
    round_budget_gbp: float


class CostsConfig(BaseModel):
    unit_costs: Dict[str, float]
    qaly_weights: Dict[str, float]


class ScoringConfig(BaseModel):
    weights: Dict[str, float]
    equity_outcomes: List[str]
    normalisation: str = Field("zscore", regex="^(zscore|minmax)$")


@dataclass
class ConfigBundle:
    baseline: BaselinePopulationConfig
    transitions: TransitionsConfig
    policies: PoliciesConfig
    costs: CostsConfig
    scoring: ScoringConfig

    def hash(self) -> str:
        hasher = hashlib.sha256()
        for payload in (
            self.baseline.json(sort_keys=True),
            self.transitions.json(sort_keys=True),
            self.policies.json(sort_keys=True),
            self.costs.json(sort_keys=True),
            self.scoring.json(sort_keys=True),
        ):
            hasher.update(payload.encode("utf-8"))
        return hasher.hexdigest()


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=4)
def load_config_bundle(config_dir: Optional[Path] = None) -> ConfigBundle:
    directory = config_dir or CONFIG_DIR
    baseline = BaselinePopulationConfig.parse_obj(
        _load_json(directory / "baseline_population_config.json")
    )
    transitions = TransitionsConfig.parse_obj(
        _load_json(directory / "transitions_config.json")
    )
    policies = PoliciesConfig.parse_obj(
        _load_json(directory / "policies_config.json")
    )
    costs = CostsConfig.parse_obj(_load_json(directory / "costs_config.json"))
    scoring = ScoringConfig.parse_obj(_load_json(directory / "scoring_config.json"))
    return ConfigBundle(
        baseline=baseline,
        transitions=transitions,
        policies=policies,
        costs=costs,
        scoring=scoring,
    )


def rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


__all__ = [
    "BaselinePopulationConfig",
    "TransitionsConfig",
    "PoliciesConfig",
    "PolicyConfig",
    "CostsConfig",
    "ScoringConfig",
    "ConfigBundle",
    "load_config_bundle",
    "rng",
]
