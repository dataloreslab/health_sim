from __future__ import annotations

import numpy as np

from ageing_futures.sim.engine import create_baseline_cohort, simulate_round
from ageing_futures.sim.shocks import get_shock
from ageing_futures.sim.utils import load_config_bundle


def test_simulate_round_generates_outputs():
    bundle = load_config_bundle()
    baseline_cfg = bundle.baseline.copy(update={"cohort_size": 500})
    cohort = create_baseline_cohort(seed=123, baseline_config=baseline_cfg)
    shock = get_shock("flu_season")
    decisions = {"falls_prevention": {"intensity": 0.8, "coverage": 0.6}}
    cohort, timesteps, summary, leaderboard = simulate_round(
        cohort,
        months=3,
        decisions=decisions,
        shocks=[shock] if shock else None,
        config_bundle=bundle,
        seed=456,
    )
    assert len(timesteps) == 3
    assert summary["incidence_total"] >= 0
    assert "total_score" in leaderboard
    assert cohort.months_elapsed == 3


