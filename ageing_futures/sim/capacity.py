"""Capacity feedback effects for Ageing Futures."""
from __future__ import annotations

from typing import Dict

import numpy as np

from .states import Cohort


def capacity_feedback(
    cohort: Cohort,
    base_length_of_stay: float,
    modifiers: Dict[str, float] | None = None,
) -> Dict[str, float]:
    modifiers = modifiers or {}
    hospitalised = cohort.data["hospitalised"].astype(bool)
    care_home = cohort.data["care_home"].astype(bool)
    hospital_beds = cohort.data["hospital_beds_per_1k"].mean()
    care_beds = cohort.data["care_home_beds_per_1k"].mean()

    hospital_occupancy = hospitalised.mean() * 1000 / max(hospital_beds, 0.1)
    care_occupancy = care_home.mean() * 1000 / max(care_beds, 0.1)

    hospital_pressure = max(0.0, hospital_occupancy - 1.0)
    care_pressure = max(0.0, care_occupancy - 1.0)

    los_multiplier = 1.0 + hospital_pressure * 0.3
    mortality_multiplier = 1.0 + hospital_pressure * 0.2
    disability_persistence = 1.0 + care_pressure * 0.15

    los_multiplier *= 1.0 + modifiers.get("capacity_hospital", 0.0)
    disability_persistence *= 1.0 + modifiers.get("capacity_community", 0.0)

    return {
        "length_of_stay": base_length_of_stay * los_multiplier,
        "mortality_multiplier": mortality_multiplier,
        "disability_persistence": disability_persistence,
    }


__all__ = ["capacity_feedback"]
