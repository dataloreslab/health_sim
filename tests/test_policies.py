from __future__ import annotations

from ageing_futures.sim.policies import aggregate_policy_effects, build_active_policies, calculate_policy_cost
from ageing_futures.sim.utils import load_config_bundle


def test_calculate_policy_cost_and_effects():
    bundle = load_config_bundle()
    decisions = {
        "smoking_cessation": {"intensity": 1.0, "coverage": 0.5},
        "community_rehab": {"intensity": 0.6, "coverage": 0.4},
    }
    cost = calculate_policy_cost(bundle.policies, decisions, cohort_size=1000)
    assert cost > 0
    active = build_active_policies(bundle.policies, decisions, {k: 5 for k in decisions})
    effects = aggregate_policy_effects(active.values())
    assert "ltc_onset" in effects or "disability_recovery" in effects
