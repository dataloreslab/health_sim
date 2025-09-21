"""Landing page for the Ageing Futures Streamlit app."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from sqlmodel import Session as DBSession

from ageing_futures.db.connection import get_engine
from ageing_futures.db import crud
from ageing_futures.sim.utils import load_config_bundle

st.set_page_config(page_title="Ageing Futures", layout="wide")

st.title("🏥 Ageing Futures")
st.markdown(
    """
    Ageing Futures is a competitive policy simulation for Masters of Public Health cohorts.
    Teams design policy mixes to improve healthy ageing, control costs, and deliver equitable outcomes
    for an ageing UK population. Use the sidebar to navigate through the experience: join or create a session,
    pick your policies, monitor the dashboard, and track the leaderboard.
    """
)

with st.sidebar:
    st.header("Quick Links")
    st.page_link("pages/1_Join_or_Create_Session.py", label="Join or Create Session", icon="🧭")
    st.page_link("pages/3_Team_Policies.py", label="Team Policies", icon="🛠️")
    st.page_link("pages/2_Team_Dashboard.py", label="Team Dashboard", icon="📊")
    st.page_link("pages/4_Leaderboard.py", label="Leaderboard", icon="🏆")
    st.page_link("pages/5_Lecturer_Console.py", label="Lecturer Console", icon="🎓")
    st.page_link("pages/6_Exports.py", label="Exports", icon="📦")
    st.page_link("pages/7_Printables.py", label="Printables", icon="🖨️")

st.subheader("Default configuration snapshot")
config = load_config_bundle()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Cohort size", f"{config.baseline.cohort_size:,}")
    st.json(config.policies.dict())
with col2:
    st.metric("Budget per round", f"£{config.policies.round_budget_gbp:,.0f}")
    st.json(config.transitions.dict())
with col3:
    st.metric("Scoring weights", config.scoring.weights)
    st.json(config.costs.dict())

st.caption(
    "All configurations are stored locally in /ageing_futures/config."
)

engine = get_engine()
with DBSession(engine) as db:
    sessions = crud.list_sessions(db)

st.subheader("Recent sessions")
if not sessions:
    st.info("No sessions yet. Head to the Join/Create page to get started.")
else:
    st.dataframe(
        [
            {
                "Code": session.code,
                "Created": session.created_at.strftime("%Y-%m-%d %H:%M"),
                "Status": session.status,
                "Current Round": session.current_round,
            }
            for session in sessions
        ]
    )
