"""Join or create a session."""
from __future__ import annotations

import random
from typing import Dict

import streamlit as st
from sqlmodel import Session as DBSession

from ageing_futures.db import crud
from ageing_futures.db.connection import get_engine
from ageing_futures.sim.states import DEFAULT_ICON_CHOICES
from ageing_futures.sim.utils import load_config_bundle

st.set_page_config(page_title="Join or Create Session", layout="wide")

engine = get_engine()
config = load_config_bundle()

st.title("🧭 Join or Create a Session")
st.write(
    "Lecturers can create a new session with tailored parameters. Teams can then join using the six-character room code."
)

col_create, col_join = st.columns(2)

with col_create:
    st.subheader("Create a new session")
    with st.form("create-session"):
        start_year = st.number_input("Start year", value=2025, min_value=2020)
        horizon_years = st.slider("Horizon (years)", min_value=5, max_value=40, value=20)
        time_step = st.selectbox("Timestep (months)", [1, 3, 6, 12], index=0)
        cohort_size = st.number_input("Cohort size", value=config.baseline.cohort_size, min_value=1000, step=1000)
        budget = st.number_input("Budget per round (£)", value=config.policies.round_budget_gbp, step=100000.0)
        seed = st.number_input("Random seed", value=random.randint(1, 99999))
        weights: Dict[str, float] = {}
        st.markdown("**Scoring Weights**")
        weight_cols = st.columns(len(config.scoring.weights))
        for idx, (dim, default) in enumerate(config.scoring.weights.items()):
            weights[dim] = weight_cols[idx].slider(dim.capitalize(), 0.0, 1.0, float(default))
        submitted = st.form_submit_button("Create session", use_container_width=True)
        if submitted:
            settings = {
                "start_year": int(start_year),
                "horizon_years": int(horizon_years),
                "time_step_months": int(time_step),
                "cohort_size": int(cohort_size),
                "budget_per_round": float(budget),
                "scoring_weights": weights,
            }
            with DBSession(engine) as db:
                session = crud.create_session(db, settings=settings, random_seed=int(seed))
            st.success(f"Session created! Share the room code **{session.code}** with teams.")

with col_join:
    st.subheader("Join an existing session")
    with st.form("join-session"):
        code = st.text_input("Session code", max_chars=6).upper()
        team_name = st.text_input("Team name")
        colour = st.color_picker("Team colour", value="#2563eb")
        icon = st.selectbox("Icon", DEFAULT_ICON_CHOICES)
        submitted = st.form_submit_button("Join session", use_container_width=True)
        if submitted:
            with DBSession(engine) as db:
                session = crud.get_session_by_code(db, code)
                if session is None:
                    st.error("Session not found. Check the code and try again.")
                else:
                    team = crud.create_team(db, session, team_name, colour, icon)
                    st.success(
                        f"Welcome to {team.name}! Use the navigation to set policies and view the dashboard."
                    )
                    st.session_state["active_session_code"] = code
                    st.session_state["active_team_id"] = team.id
                    st.session_state["active_team_name"] = team.name

with st.expander("Need help?"):
    st.markdown(
        """
        1. The lecturer sets up the session and shares the room code.
        2. Teams join via this page and pick a distinctive name and colour.
        3. Head to the **Team Policies** page to allocate your budget before the round locks.
        """
    )
