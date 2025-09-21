"""Leaderboard overview."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlmodel import Session as DBSession

from ageing_futures.db import crud
from ageing_futures.db.connection import get_engine
from ageing_futures.sim.scoring import score_round
from ageing_futures.sim.utils import load_config_bundle
from ageing_futures.viz.charts import leaderboard_bar

st.set_page_config(page_title="Leaderboard", layout="wide")

st.title("🏆 Leaderboard")
st.autorefresh(interval=5000, key="auto-leaderboard")

session_code = st.session_state.get("active_session_code")
if not session_code:
    st.warning("Join a session to view the leaderboard.")
    st.stop()

engine = get_engine()
config = load_config_bundle()

with DBSession(engine) as db:
    session = crud.get_session_by_code(db, session_code)
    if session is None:
        st.error("Session not found.")
        st.stop()
    leaderboard_data = crud.fetch_leaderboard_data(db, session.id)

if not leaderboard_data:
    st.info("No teams have submitted results yet.")
    st.stop()

rows = []
for team, result in leaderboard_data:
    metrics = result.metrics_json if result else {}
    rows.append(
        {
            "team": team.name,
            "health_value": metrics.get("health_value", 0.0),
            "cost_value": metrics.get("cost_value", 0.0),
            "capacity_value": metrics.get("capacity_value", 0.0),
            "equity_value": metrics.get("equity_value", 0.0),
        }
    )

metrics_df = pd.DataFrame(rows)
scored = score_round(metrics_df, config.scoring)

st.plotly_chart(leaderboard_bar(scored), use_container_width=True)
st.dataframe(scored, use_container_width=True)

st.caption("Scores are normalised each round. Ties break on equity then cost performance.")
