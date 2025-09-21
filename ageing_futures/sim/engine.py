"""Simulation engine for Ageing Futures."""
from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Mapping, Tuple

import numpy as np
import pandas as pd

from .baseline import create_baseline_cohort
from .capacity import capacity_feedback
from .hazards import log_linear_predictor, log_hazard_to_probability
from .policies import aggregate_policy_effects, build_active_policies, calculate_policy_cost
from .scoring import score_round
from .shocks import Shock, active_shock_modifiers
from .states import Cohort, SimulationTimestepResult
from .utils import ConfigBundle, load_config_bundle, rng


def _build_features(cohort: Cohort) -> Dict[str, np.ndarray]:
    data = cohort.data
    return {
        "age": data["age"],
        "imd_quintile": data["imd_quintile"],
        "community_capacity": data["community_capacity"],
        "ltc_level": data["ltc_state"],
        "disability": data["disability"],
        "heat_exposure": data["heat_exposure"],
        "cold_exposure": data["cold_exposure"],
        "hospitalised": data["hospitalised"],
    }


def _probability_for_transition(
    name: str,
    features: Dict[str, np.ndarray],
    intercept: float,
    coefficients: Dict[str, float],
    dt_months: float,
    policy_modifiers: Dict[str, float],
    shock_modifiers: Dict[str, float],
) -> np.ndarray:
    alive_mask = features["age"] * 0 + 1.0  # placeholder to get shape
    intercept_shift = policy_modifiers.get(name, 0.0) + shock_modifiers.get(name, 0.0)
    combined_features = dict(features)
    for source in (policy_modifiers, shock_modifiers):
        for key, value in source.items():
            if key.startswith("capacity_"):
                continue
            if key in coefficients and key not in combined_features:
                combined_features[key] = np.full_like(alive_mask, value)
    lp = log_linear_predictor(intercept + intercept_shift, coefficients, combined_features)
    return log_hazard_to_probability(lp, dt_months)


def simulate_round(
    cohort: Cohort,
    months: int,
    decisions: Mapping[str, Dict[str, float]] | None,
    shocks: List[Shock] | None,
    config_bundle: ConfigBundle | None = None,
    seed: int = 1234,
    policy_months_active: Mapping[str, int] | None = None,
) -> Tuple[Cohort, List[SimulationTimestepResult], Dict[str, float], pd.DataFrame]:
    cfg = config_bundle or load_config_bundle()
    transitions_cfg = cfg.transitions
    policies_cfg = cfg.policies
    costs_cfg = cfg.costs
    scoring_cfg = cfg.scoring

    gen = rng(seed)
    dt_months = transitions_cfg.time_step_months
    dt_years = dt_months / 12.0

    cohort = cohort.copy()
    features = _build_features(cohort)
    alive = cohort.data["alive"].astype(bool)
    ltc_state = cohort.data["ltc_state"].astype(int)
    disability = cohort.data["disability"].astype(bool)
    hospitalised = cohort.data["hospitalised"].astype(bool)
    care_home = cohort.data["care_home"].astype(bool)

    hospital_los_remaining = np.zeros(cohort.size, dtype=float)

    policy_counters = {policy_id: policy_months_active.get(policy_id, 0) if policy_months_active else 0 for policy_id in (decisions or {})}

    active_shocks = shocks or []
    shock_mods = active_shock_modifiers(active_shocks)

    timestep_results: List[SimulationTimestepResult] = []
    monthly_records = []

    base_los = transitions_cfg.length_of_stay.get("hospital").mean if "hospital" in transitions_cfg.length_of_stay else 7.0

    for month in range(months):
        alive_mask = alive.astype(float)
        features.update({
            "ltc_level": ltc_state.astype(float),
            "disability": disability.astype(float),
            "hospitalised": hospitalised.astype(float),
        })

        active = build_active_policies(policies_cfg, decisions, policy_counters)
        policy_modifiers = aggregate_policy_effects(active.values())
        capacity_modifiers = capacity_feedback(cohort, base_los, policy_modifiers | shock_mods)

        metrics = {"month": month + 1}
        new_incidence = 0
        new_hospital = 0
        new_care = 0
        new_deaths = 0
        bed_days = 0.0

        # LTC transitions
        onset_probs = _probability_for_transition(
            "ltc_onset",
            features,
            transitions_cfg.transitions["ltc_onset"].intercept,
            transitions_cfg.transitions["ltc_onset"].coefficients,
            dt_months,
            policy_modifiers,
            shock_mods,
        ) * alive_mask
        progression_probs = _probability_for_transition(
            "ltc_progression",
            features,
            transitions_cfg.transitions["ltc_progression"].intercept,
            transitions_cfg.transitions["ltc_progression"].coefficients,
            dt_months,
            policy_modifiers,
            shock_mods,
        ) * alive_mask

        severe_probs = np.clip(progression_probs * 0.5, 0.0, 1.0)

        draw = gen.random(cohort.size)
        onset_mask = (ltc_state == 0) & (draw < onset_probs)
        ltc_state[onset_mask] = 1
        new_incidence += onset_mask.sum()

        draw = gen.random(cohort.size)
        progress_mask = (ltc_state == 1) & (draw < progression_probs)
        ltc_state[progress_mask] = 2

        draw = gen.random(cohort.size)
        severe_mask = (ltc_state >= 2) & (draw < severe_probs)
        ltc_state[severe_mask] = 3

        # Disability transitions
        disability_probs = _probability_for_transition(
            "disability_onset",
            features,
            transitions_cfg.transitions["disability_onset"].intercept,
            transitions_cfg.transitions["disability_onset"].coefficients,
            dt_months,
            policy_modifiers,
            shock_mods,
        ) * alive_mask

        recovery_probs = _probability_for_transition(
            "disability_recovery",
            features,
            transitions_cfg.transitions["disability_recovery"].intercept,
            transitions_cfg.transitions["disability_recovery"].coefficients,
            dt_months,
            policy_modifiers,
            shock_mods,
        ) * alive_mask
        recovery_probs = recovery_probs / max(capacity_modifiers.get("disability_persistence", 1.0), 1e-6)

        draw = gen.random(cohort.size)
        disability_onset = (~disability) & (draw < disability_probs)
        disability[disability_onset] = True

        draw = gen.random(cohort.size)
        disability_recover = disability & (draw < recovery_probs)
        disability[disability_recover] = False

        # Hospitalisation transitions
        hospital_probs = _probability_for_transition(
            "hospitalisation",
            features,
            transitions_cfg.transitions["hospitalisation"].intercept,
            transitions_cfg.transitions["hospitalisation"].coefficients,
            dt_months,
            policy_modifiers,
            shock_mods,
        ) * alive_mask

        new_admissions_mask = (~hospitalised) & (gen.random(cohort.size) < hospital_probs)
        new_hospital += new_admissions_mask.sum()
        hospitalised[new_admissions_mask] = True
        los_mean = capacity_modifiers["length_of_stay"]
        los = np.maximum(1.0, gen.gamma(shape=los_mean / 2.0, scale=2.0, size=new_admissions_mask.sum()))
        hospital_los_remaining[new_admissions_mask] = los
        bed_days += float(los.sum())

        hospital_los_remaining[hospitalised] = np.maximum(0.0, hospital_los_remaining[hospitalised] - dt_months * 30)
        discharged = hospitalised & (hospital_los_remaining <= 0.0)
        hospitalised[discharged] = False

        # Care home admissions (only for disabled severe)
        care_probs = _probability_for_transition(
            "care_home",
            features,
            transitions_cfg.transitions["care_home"].intercept,
            transitions_cfg.transitions["care_home"].coefficients,
            dt_months,
            policy_modifiers,
            shock_mods,
        ) * alive_mask
        care_mask = (~care_home) & disability & (ltc_state >= 2) & (gen.random(cohort.size) < care_probs)
        care_home[care_mask] = True
        new_care += care_mask.sum()

        # Mortality
        mortality_probs = _probability_for_transition(
            "mortality",
            features,
            transitions_cfg.transitions["mortality"].intercept,
            transitions_cfg.transitions["mortality"].coefficients,
            dt_months,
            policy_modifiers,
            shock_mods,
        ) * alive_mask
        mortality_probs = np.clip(
            mortality_probs * capacity_modifiers.get("mortality_multiplier", 1.0), 0.0, 1.0
        )
        death_mask = alive & (gen.random(cohort.size) < mortality_probs)
        new_deaths += death_mask.sum()
        alive[death_mask] = False
        hospitalised[death_mask] = False
        care_home[death_mask] = False
        disability[death_mask] = False

        # Update cohort arrays
        cohort.data["age"] = cohort.data["age"] + dt_months / 12.0
        cohort.data["ltc_state"] = ltc_state.astype(int)
        cohort.data["disability"] = disability.astype(int)
        cohort.data["hospitalised"] = hospitalised.astype(int)
        cohort.data["care_home"] = care_home.astype(int)
        cohort.data["alive"] = alive.astype(int)
        features = _build_features(cohort)

        disability_prev = (disability & alive).sum() / max(alive.sum(), 1)
        qalys = _calculate_qalys(ltc_state, disability, alive, costs_cfg.qaly_weights, dt_years)
        policy_cost = calculate_policy_cost(policies_cfg, decisions, cohort.size) / max(months, 1)
        hospital_cost = bed_days * costs_cfg.unit_costs.get("hospital_bed_day", 0.0)
        care_cost = care_home.sum() * 30 * costs_cfg.unit_costs.get("care_home_day", 0.0)
        total_cost = policy_cost + hospital_cost + care_cost

        equity_gap = _imd_gap(disability.astype(int), cohort.data["imd_quintile"], alive)
        metrics.update(
            {
                "incidence": new_incidence,
                "hospital_admissions": new_hospital,
                "bed_days": bed_days,
                "care_home_admissions": new_care,
                "deaths": new_deaths,
                "costs_gbp": total_cost,
                "qalys": qalys,
                "disability_prevalence": disability_prev,
                "equity_gap_disability": equity_gap,
            }
        )

        monthly_records.append(metrics)
        timestep_results.append(
            SimulationTimestepResult(
                month_index=month + 1,
                incidence=new_incidence,
                hospital_admissions=new_hospital,
                bed_days=bed_days,
                care_home_admissions=new_care,
                deaths=new_deaths,
                costs_gbp=total_cost,
                qalys=qalys,
                disability_prevalence=disability_prev,
                equity_gaps={"disability": equity_gap},
            )
        )

        for policy_id in policy_counters:
            if decisions and policy_id in decisions:
                if decisions[policy_id].get("intensity", 0) > 0:
                    policy_counters[policy_id] += 1

    cohort.months_elapsed += months

    summary = _summarise_round(monthly_records)
    leaderboard = _build_leaderboard(summary, scoring_cfg)

    return cohort, timestep_results, summary, leaderboard


def _calculate_qalys(
    ltc_state: np.ndarray,
    disability: np.ndarray,
    alive: np.ndarray,
    weights: Dict[str, float],
    dt_years: float,
) -> float:
    base = np.select(
        [ltc_state == 0, ltc_state == 1, ltc_state == 2, ltc_state >= 3],
        [
            weights.get("healthy", 0.9),
            weights.get("ltc_mild", 0.8),
            weights.get("ltc_moderate", 0.65),
            weights.get("ltc_severe", 0.45),
        ],
        default=0.5,
    )
    disability_factor = weights.get("disability", 0.5) / max(weights.get("healthy", 0.9), 1e-6)
    adjusted = base * np.where(disability, disability_factor, 1.0)
    adjusted = adjusted * alive.astype(float)
    return float(adjusted.sum() * dt_years)


def _imd_gap(disability: np.ndarray, imd: np.ndarray, alive: np.ndarray) -> float:
    mask_alive = alive.astype(bool)
    if mask_alive.sum() == 0:
        return 0.0
    data = pd.DataFrame({"imd": imd[mask_alive], "disability": disability[mask_alive]})
    q1 = data[data["imd"] == data["imd"].min()]["disability"].mean()
    q5 = data[data["imd"] == data["imd"].max()]["disability"].mean()
    return float(q5 - q1)


def _summarise_round(monthly_records: List[Dict[str, float]]) -> Dict[str, float]:
    df = pd.DataFrame(monthly_records)
    summary = {
        "incidence_total": float(df["incidence"].sum()),
        "hospital_admissions_total": float(df["hospital_admissions"].sum()),
        "bed_days_total": float(df["bed_days"].sum()),
        "care_home_admissions_total": float(df["care_home_admissions"].sum()),
        "deaths_total": float(df["deaths"].sum()),
        "costs_total": float(df["costs_gbp"].sum()),
        "qalys_total": float(df["qalys"].sum()),
        "disability_prev_end": float(df["disability_prevalence"].iloc[-1]),
        "equity_gap_disability": float(df["equity_gap_disability"].iloc[-1]),
        "health_value": float(df["qalys"].sum()),
        "cost_value": float(df["costs_gbp"].sum()),
        "capacity_value": float(-df["bed_days"].sum()),
        "equity_value": -abs(float(df["equity_gap_disability"].iloc[-1])),
    }
    return summary


def _build_leaderboard(summary: Dict[str, float], scoring_cfg) -> pd.DataFrame:
    metrics_df = pd.DataFrame([
        {
            "team": "current",
            "health_value": summary["health_value"],
            "cost_value": summary["cost_value"],
            "capacity_value": summary["capacity_value"],
            "equity_value": summary["equity_value"],
        }
    ])
    scored = score_round(metrics_df, scoring_cfg)
    return scored


__all__ = ["simulate_round", "create_baseline_cohort"]
