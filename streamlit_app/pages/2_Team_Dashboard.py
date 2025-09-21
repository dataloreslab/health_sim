"""Team dashboard visualisations."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlmodel import Session as DBSession

from ageing_futures.db import crud
from ageing_futures.db.connection import get_engine
from ageing_futures.viz.charts import leaderboard_bar, multi_metric_chart, time_series_chart

st.set_page_config(page_title="Team Dashboard", layout="wide")

st.title("📊 Team Dashboard")
st.autorefresh(interval=5000, key="auto-dashboard")

session_code = st.session_state.get("active_session_code")
team_id = st.session_state.get("active_team_id")

if not session_code or not team_id:
    st.warning("Join a session first from the Join/Create page.")
    st.stop()

engine = get_engine()
with DBSession(engine) as db:
    session = crud.get_session_by_code(db, session_code)
    if session is None:
        st.error("Session not found.")
        st.stop()
    results = crud.list_results_for_team(db, session.id, team_id)

if not results:
    st.info("No simulation results yet. Once the lecturer advances a round your dashboard will populate.")
    st.stop()

latest = results[-1]
summary = latest.metrics_json
monthly = latest.timeseries_json.get("monthly", [])
monthly_df = pd.DataFrame(monthly)

if monthly_df.empty:
    st.info("Awaiting monthly detail from the simulation engine.")
    st.stop()

st.subheader(f"Session {session.code} – Team #{team_id}")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Incidence", f"{summary.get('incidence_total', 0):,.0f}")
col2.metric("Bed days", f"{summary.get('bed_days_total', 0):,.0f}")
col3.metric("Costs (£)", f"{summary.get('costs_total', 0):,.0f}")
col4.metric("QALYs", f"{summary.get('qalys_total', 0):,.1f}")

health_tab, capacity_tab, equity_tab, cost_tab = st.tabs(["Health", "Capacity", "Equity", "Costs"])
with health_tab:
    st.plotly_chart(
        time_series_chart(monthly_df, "incidence", "Incidence per month", "Incidents"),
        use_container_width=True,
    )
    st.plotly_chart(
        time_series_chart(monthly_df, "qalys", "QALYs generated", "QALYs"),
        use_container_width=True,
    )
with capacity_tab:
    st.plotly_chart(
        multi_metric_chart(
            monthly_df,
            {"hospital_admissions": "Admissions", "bed_days": "Bed-days"},
            "Capacity pressure",
        ),
        use_container_width=True,
    )
with equity_tab:
    st.plotly_chart(
        time_series_chart(
            monthly_df,
            "equity_gap_disability",
            "IMD equity gap (disability)",
            "Gap",
        ),
        use_container_width=True,
    )
with cost_tab:
    st.plotly_chart(
        time_series_chart(monthly_df, "costs_gbp", "Monthly costs", "£"),
        use_container_width=True,
    )

st.subheader("Round summary")
st.write(summary)
