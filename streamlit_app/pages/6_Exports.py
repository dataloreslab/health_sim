"""Data export utilities."""
from __future__ import annotations

import io
import json
import pandas as pd
import streamlit as st
from sqlmodel import Session as DBSession, select

from ageing_futures.db import crud
from ageing_futures.db.connection import get_engine
from ageing_futures.db.models import Result, Team

st.set_page_config(page_title="Exports", layout="wide")

st.title("📦 Exports")
st.write("Download per-team results and session summaries.")

session_code = st.session_state.get("active_session_code")
if not session_code:
    st.warning("Join or create a session first.")
    st.stop()

engine = get_engine()
with DBSession(engine) as db:
    session = crud.get_session_by_code(db, session_code)
    if session is None:
        st.error("Session not found.")
        st.stop()
    teams = crud.list_teams(db, session.id)
    results = db.exec(
        select(Result)
        .where(Result.session_id == session.id)
        .order_by(Result.team_id, Result.round_id)
    ).all()

if not results:
    st.info("No results available yet. Run at least one round.")
    st.stop()

summary_rows = []
timeseries_rows = []
for result in results:
    team = next((team for team in teams if team.id == result.team_id), None)
    team_name = team.name if team else f"Team {result.team_id}"
    summary_row = {"team": team_name, "round": result.round_id}
    summary_row.update(result.metrics_json)
    summary_rows.append(summary_row)
    for record in result.timeseries_json.get("monthly", []):
        record_copy = dict(record)
        record_copy.update({"team": team_name, "round": result.round_id})
        timeseries_rows.append(record_copy)

summary_df = pd.DataFrame(summary_rows)
timeseries_df = pd.DataFrame(timeseries_rows)

summary_buffer = io.StringIO()
timeseries_buffer = io.StringIO()
summary_df.to_csv(summary_buffer, index=False)
timeseries_df.to_csv(timeseries_buffer, index=False)

st.download_button(
    label="Download round summaries",
    data=summary_buffer.getvalue().encode("utf-8"),
    file_name=f"ageing_futures_{session.code}_summary.csv",
    mime="text/csv",
)

st.download_button(
    label="Download monthly timeseries",
    data=timeseries_buffer.getvalue().encode("utf-8"),
    file_name=f"ageing_futures_{session.code}_timeseries.csv",
    mime="text/csv",
)

st.caption("CSV exports include per-team decisions, outcomes, and monthly traces for further analysis.")
