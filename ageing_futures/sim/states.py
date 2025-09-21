"""Core state enumerations and dataclasses for the Ageing Futures simulation."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np


class LTCState(int, Enum):
    """Multimorbidity tiers for the population."""

    NONE = 0
    MILD = 1  # 1 long-term condition
    MODERATE = 2  # 2-4 LTCs
    SEVERE = 3  # 5+ LTCs


@dataclass
class Cohort:
    """Container for synthetic cohort data."""

    data: Dict[str, np.ndarray]
    months_elapsed: int = 0

    def copy(self) -> "Cohort":
        return Cohort({k: v.copy() for k, v in self.data.items()}, self.months_elapsed)

    @property
    def size(self) -> int:
        return len(next(iter(self.data.values()))) if self.data else 0


@dataclass
class SimulationTimestepResult:
    """Summary metrics returned each timestep."""

    month_index: int
    incidence: float
    hospital_admissions: float
    bed_days: float
    care_home_admissions: float
    deaths: float
    costs_gbp: float
    qalys: float
    disability_prevalence: float
    equity_gaps: Dict[str, float] = field(default_factory=dict)


@dataclass
class PolicyEffect:
    policy_id: str
    effects: Dict[str, float]
    ramp_fraction: float


@dataclass
class ShockEffect:
    name: str
    modifiers: Dict[str, float]
    months_remaining: int


@dataclass
class SimulationConfig:
    start_year: int
    horizon_years: int
    time_step_months: int
    cohort_size: int
    budget_per_round: float
    scoring_weights: Dict[str, float]
    random_seed: int = 1234


DEFAULT_ICON_CHOICES: List[str] = ["👩‍⚕️", "🧑‍🔬", "🧑‍⚕️", "🧓", "🏥", "🧠"]
