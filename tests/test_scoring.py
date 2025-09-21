from __future__ import annotations

import pandas as pd

from ageing_futures.sim.scoring import score_round
from ageing_futures.sim.utils import load_config_bundle


def test_score_round_ranks_teams():
    bundle = load_config_bundle()
    df = pd.DataFrame(
        [
            {"team": "A", "health_value": 10, "cost_value": 100, "capacity_value": -50, "equity_value": -0.1},
            {"team": "B", "health_value": 8, "cost_value": 80, "capacity_value": -40, "equity_value": -0.05},
        ]
    )
    scored = score_round(df, bundle.scoring)
    assert set(scored.columns).issuperset({"total_score", "rank"})
    assert scored.iloc[0]["rank"] == 1
