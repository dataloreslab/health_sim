"""Policy selection interface for teams."""
from __future__ import annotations

import json
from typing import Dict

import streamlit as st
from sqlmodel import Session as DBSession, select

from ageing_futures.db import crud
from ageing_futures.db.connection import get_engine
from ageing_futures.db.models import Decision, Round
from ageing_futures.sim.policies import calculate_policy_cost
from ageing_futures.sim.utils import load_config_bundle

st.set_page_config(page_title="Team Policies", layout="wide")

st.title("🛠️ Policy Workshop")

session_code = st.session_state.get("active_session_code")
team_id = st.session_state.get("active_team_id")
if not session_code or not team_id:
    st.warning("Join a session first.")
    st.stop()

engine = get_engine()
config = load_config_bundle()

with DBSession(engine) as db:
    session = crud.get_session_by_code(db, session_code)
    if session is None:
        st.error("Session not found.")
        st.stop()
    current_round = db.exec(
        select(Round).where(Round.session_id == session.id).order_by(Round.index.desc())
    ).first()
    if current_round is None:
        st.info("The lecturer needs to start a round before policies can be submitted.")
        st.stop()
    existing_decision = db.exec(
        select(Decision)
        .where(Decision.session_id == session.id, Decision.team_id == team_id, Decision.round_id == current_round.id)
        .limit(1)
    ).first()

st.caption(f"Round {current_round.index} • Budget £{session.settings_json.get('budget_per_round', config.policies.round_budget_gbp):,.0f}")

with st.form("policy-form"):
    selected: Dict[str, Dict[str, float]] = {}
    total_cost = 0.0
    for policy in config.policies.policies:
        st.markdown(f"### {policy.name}")
        st.caption(policy.description)
        cols = st.columns([1, 1, 1])
        default_intensity = existing_decision.policies_json.get(policy.id, {}).get("intensity", 0.0) if existing_decision else 0.0
        default_coverage = existing_decision.policies_json.get(policy.id, {}).get("coverage", 0.0) if existing_decision else 0.0
        intensity = cols[0].slider("Intensity", 0.0, 1.0, float(default_intensity), key=f"{policy.id}-intensity")
        coverage = cols[1].slider("Coverage", 0.0, 1.0, float(default_coverage), key=f"{policy.id}-coverage")
        cols[2].markdown(f"Cost per capita: £{policy.cost_per_capita:,.0f}")
        if intensity > 0 and coverage > 0:
            selected[policy.id] = {"intensity": intensity, "coverage": coverage}

total_cost = calculate_policy_cost(
    config.policies,
    selected,
    session.settings_json.get("cohort_size", config.baseline.cohort_size),
)
    st.metric("Estimated round spend", f"£{total_cost:,.0f}")
    submit = st.form_submit_button("Save decision", use_container_width=True)
    ready = st.form_submit_button("Save & Ready", use_container_width=True)

if submit or ready:
    if total_cost > session.settings_json.get("budget_per_round", config.policies.round_budget_gbp):
        st.error("Decision exceeds the available budget. Adjust policy intensities or coverage.")
    else:
        with DBSession(engine) as db:
            crud.upsert_decision(
                db,
                session_id=session.id,
                team_id=team_id,
                round_id=current_round.id,
                policies=selected,
                budget_spent=total_cost,
                locked=ready,
            )
        st.success("Decision saved." if submit else "Decision locked for this round.")

st.info("Remember: decisions lock when the round closes. You can update them until the lecturer advances the round.")
