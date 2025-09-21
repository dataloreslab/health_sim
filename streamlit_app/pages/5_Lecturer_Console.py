"""Lecturer control centre."""
from __future__ import annotations

import json
from typing import Dict, List

import numpy as np
import streamlit as st
from sqlmodel import Session as DBSession, select

from ageing_futures.db import crud
from ageing_futures.db.connection import get_engine
from ageing_futures.db.models import Decision, Result, Round, Session as SessionModel, Team
from ageing_futures.sim.engine import create_baseline_cohort, simulate_round
from ageing_futures.sim.shocks import PREDEFINED_SHOCKS, get_shock
from ageing_futures.sim.states import Cohort
from ageing_futures.sim.utils import ConfigBundle, load_config_bundle

st.set_page_config(page_title="Lecturer Console", layout="wide")

st.title("🎓 Lecturer Console")
st.write("Manage sessions, rounds, shocks, and run the simulation engine.")

engine = get_engine()
base_bundle = load_config_bundle()

with DBSession(engine) as db:
    sessions = crud.list_sessions(db)

if not sessions:
    st.info("Create a session first from the Join/Create page.")
    st.stop()

session_lookup = {f"{session.code} (round {session.current_round})": session for session in sessions}
selected_label = st.selectbox("Select session", list(session_lookup.keys()))
selected_session = session_lookup[selected_label]
session_bundle = ConfigBundle(
    baseline=base_bundle.baseline.copy(
        update={"cohort_size": selected_session.settings_json.get("cohort_size", base_bundle.baseline.cohort_size)}
    ),
    transitions=base_bundle.transitions,
    policies=base_bundle.policies,
    costs=base_bundle.costs,
    scoring=base_bundle.scoring.copy(
        update={"weights": selected_session.settings_json.get("scoring_weights", base_bundle.scoring.weights)}
    ),
)

with DBSession(engine) as db:
    teams = crud.list_teams(db, selected_session.id)
    rounds = db.exec(select(Round).where(Round.session_id == selected_session.id).order_by(Round.index)).all()

st.subheader("Session overview")
cols = st.columns(4)
cols[0].metric("Teams", len(teams))
cols[1].metric("Rounds", len(rounds))
cols[2].metric("Status", selected_session.status)
cols[3].metric("Seed", selected_session.random_seed)

with st.expander("Start a new round"):
    with st.form("start-round"):
        round_index = len(rounds) + 1
        months = st.slider("Months to simulate", min_value=1, max_value=24, value=12)
        shock_choice = st.selectbox(
            "Shock card (optional)",
            ["None"] + list(PREDEFINED_SHOCKS.keys()),
        )
        payload = {}
        if shock_choice != "None":
            payload = {"name": shock_choice}
        submitted = st.form_submit_button("Create round", use_container_width=True)
        if submitted:
            with DBSession(engine) as db:
                crud.start_round(db, selected_session, round_index, months, shock=payload)
            st.success(f"Round {round_index} created.")
            st.experimental_rerun()

if not rounds:
    st.stop()

current_round = rounds[-1]
st.subheader(f"Round {current_round.index} controls")
st.caption(f"Months to advance: {current_round.months_advanced}. Shock: {current_round.shock_json or 'None'}")

with DBSession(engine) as db:
    decisions = db.exec(
        select(Decision).where(
            Decision.session_id == selected_session.id,
            Decision.round_id == current_round.id,
        )
    ).all()

decision_table = [
    {
        "Team": next((team.name for team in teams if team.id == decision.team_id), f"Team {decision.team_id}"),
        "Budget": decision.budget_spent,
        "Locked": bool(decision.locked_ts),
    }
    for decision in decisions
]

st.write("Team readiness")
if decision_table:
    st.dataframe(decision_table)
else:
    st.info("No decisions submitted yet.")

run_sim = st.button("Advance round", use_container_width=True, type="primary")
if run_sim:
    st.info("Running simulation... this may take a few seconds for large cohorts.")
    with DBSession(engine) as db:
        results_created = []
        for team in teams:
            decision = next((d for d in decisions if d.team_id == team.id), None)
            decisions_payload = decision.policies_json if decision else {}

            prev_result = db.exec(
                select(Result)
                .where(Result.session_id == selected_session.id, Result.team_id == team.id)
                .order_by(Result.round_id.desc())
                .limit(1)
            ).first()

            if prev_result and "cohort_state" in prev_result.timeseries_json:
                cohort_state = prev_result.timeseries_json["cohort_state"]
                cohort = Cohort(
                    {key: np.array(value) for key, value in cohort_state.items()},
                    months_elapsed=prev_result.timeseries_json.get("months_elapsed", 0),
                )
            else:
                baseline = session_bundle.baseline
                cohort = create_baseline_cohort(selected_session.random_seed + team.id, baseline)

            shocks: List = []
            if current_round.shock_json:
                shock_obj = get_shock(current_round.shock_json.get("name", ""))
                if shock_obj:
                    shocks.append(shock_obj)

            cohort, timesteps, summary, _ = simulate_round(
                cohort,
                months=current_round.months_advanced,
                decisions=decisions_payload,
                shocks=shocks,
                config_bundle=session_bundle,
                seed=selected_session.random_seed + current_round.index + team.id,
            )

            monthly_payload = [
                {
                    "month": result.month_index,
                    "incidence": result.incidence,
                    "hospital_admissions": result.hospital_admissions,
                    "bed_days": result.bed_days,
                    "care_home_admissions": result.care_home_admissions,
                    "deaths": result.deaths,
                    "costs_gbp": result.costs_gbp,
                    "qalys": result.qalys,
                    "disability_prevalence": result.disability_prevalence,
                    "equity_gap_disability": result.equity_gaps.get("disability", 0.0),
                }
                for result in timesteps
            ]
            state_payload = {key: value.tolist() for key, value in cohort.data.items()}
            timeseries_payload = {
                "monthly": monthly_payload,
                "cohort_state": state_payload,
                "months_elapsed": cohort.months_elapsed,
            }
            crud.record_result(
                db,
                session_id=selected_session.id,
                team_id=team.id,
                round_id=current_round.id,
                metrics=summary,
                timeseries=timeseries_payload,
            )
            results_created.append((team.name, summary))
        crud.lock_round(db, current_round)
    st.success(f"Simulated {len(results_created)} teams. Leaderboard updated.")
