"""Shock definitions for random or lecturer-triggered events."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional


@dataclass
class Shock:
    name: str
    description: str
    duration_months: int
    modifiers: Dict[str, float]


PREDEFINED_SHOCKS: Dict[str, Shock] = {
    "heatwave": Shock(
        name="heatwave",
        description="Sustained heat raises frailty and hospitalisation risk.",
        duration_months=2,
        modifiers={"shock_hospital": 0.25, "shock_mortality": 0.15},
    ),
    "cold_snap": Shock(
        name="cold_snap",
        description="Winter cold strains capacity and drives mortality.",
        duration_months=3,
        modifiers={"shock_mortality": 0.2, "shock_hospital": 0.1},
    ),
    "flu_season": Shock(
        name="flu_season",
        description="Influenza season raises admissions but short-lived.",
        duration_months=3,
        modifiers={"shock_hospital": 0.18},
    ),
    "industrial_action": Shock(
        name="industrial_action",
        description="Workforce strike reduces capacity.",
        duration_months=1,
        modifiers={"capacity_hospital": -0.2, "capacity_community": -0.15},
    ),
}


def get_shock(name: str) -> Optional[Shock]:
    return PREDEFINED_SHOCKS.get(name)


def active_shock_modifiers(active: Iterable[Shock]) -> Dict[str, float]:
    modifiers: Dict[str, float] = {}
    for shock in active:
        for key, value in shock.modifiers.items():
            modifiers[key] = modifiers.get(key, 0.0) + value
    return modifiers


__all__ = ["Shock", "PREDEFINED_SHOCKS", "get_shock", "active_shock_modifiers"]
