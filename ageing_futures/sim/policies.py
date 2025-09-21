"""Policy application utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping

import numpy as np

from .utils import PoliciesConfig, PolicyConfig


@dataclass
class ActivePolicy:
    policy: PolicyConfig
    intensity: float
    months_active: int

    def ramp(self) -> float:
        lag = max(self.policy.lag_months, 0)
        if self.months_active <= lag:
            return 0.0
        effective_months = self.months_active - lag
        ramp = 1.0 - np.exp(-effective_months / 6.0)
        return float(np.clip(ramp, 0.0, 1.0))

    def diminishing_multiplier(self) -> float:
        dim = max(0.0, min(1.0, self.policy.diminishing_return))
        return float(1.0 - dim * (1.0 - np.clip(self.intensity, 0.0, 1.0)))

    def effect_strength(self) -> float:
        return float(np.clip(self.intensity, 0.0, 1.0) * self.ramp() * self.diminishing_multiplier())


def build_active_policies(
    policies_cfg: PoliciesConfig,
    decisions: Mapping[str, Dict[str, float]] | None,
    months_elapsed: Mapping[str, int] | None = None,
) -> Dict[str, ActivePolicy]:
    active: Dict[str, ActivePolicy] = {}
    if not decisions:
        return active
    policy_by_id = {policy.id: policy for policy in policies_cfg.policies}
    for policy_id, detail in decisions.items():
        policy = policy_by_id.get(policy_id)
        if policy is None:
            continue
        intensity = float(detail.get("intensity", 1.0))
        months_active = int(months_elapsed.get(policy_id, 0) if months_elapsed else 0)
        active[policy_id] = ActivePolicy(policy=policy, intensity=intensity, months_active=months_active)
    return active


def aggregate_policy_effects(active: Iterable[ActivePolicy]) -> Dict[str, float]:
    modifiers: Dict[str, float] = {}
    for active_policy in active:
        strength = active_policy.effect_strength()
        if strength <= 0:
            continue
        for key, value in active_policy.policy.effects.items():
            modifiers[key] = modifiers.get(key, 0.0) + value * strength
    return modifiers


def calculate_policy_cost(
    policies_cfg: PoliciesConfig,
    decisions: Mapping[str, Dict[str, float]] | None,
    cohort_size: int,
) -> float:
    if not decisions:
        return 0.0
    total = 0.0
    policy_lookup = {policy.id: policy for policy in policies_cfg.policies}
    for policy_id, detail in decisions.items():
        policy = policy_lookup.get(policy_id)
        if policy is None:
            continue
        intensity = float(detail.get("intensity", 1.0))
        coverage = float(detail.get("coverage", 1.0))
        total += policy.cost_per_capita * cohort_size * intensity * coverage
    return float(total)


__all__ = [
    "ActivePolicy",
    "build_active_policies",
    "aggregate_policy_effects",
    "calculate_policy_cost",
]
