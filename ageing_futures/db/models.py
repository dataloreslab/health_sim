"""SQLModel database models for Ageing Futures."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, JSON
from sqlmodel import Field, SQLModel


class Session(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, nullable=False)
    created_at: dt.datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=dt.datetime.utcnow)
    )
    settings_json: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    status: str = Field(default="lobby")
    current_round: int = Field(default=0)
    random_seed: int = Field(default=1234)


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True, foreign_key="session.id")
    name: str
    colour: str = Field(default="#2563eb")
    icon: str = Field(default="👩‍⚕️")
    joined_at: dt.datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=dt.datetime.utcnow)
    )


class Round(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True, foreign_key="session.id")
    index: int = Field(index=True)
    start_ts: dt.datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=dt.datetime.utcnow)
    )
    lock_ts: Optional[dt.datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    months_advanced: int = Field(default=12)
    shock_json: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )


class Decision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True, foreign_key="session.id")
    team_id: int = Field(index=True, foreign_key="team.id")
    round_id: int = Field(index=True, foreign_key="round.id")
    policies_json: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    budget_spent: float = Field(default=0.0)
    locked_ts: Optional[dt.datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )


class Result(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True, foreign_key="session.id")
    team_id: int = Field(index=True, foreign_key="team.id")
    round_id: int = Field(index=True, foreign_key="round.id")
    metrics_json: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    timeseries_json: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )


class Audit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True, foreign_key="session.id")
    team_id: Optional[int] = Field(default=None, foreign_key="team.id")
    action: str
    payload_json: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    ts: dt.datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=dt.datetime.utcnow)
    )


__all__ = [
    "Session",
    "Team",
    "Round",
    "Decision",
    "Result",
    "Audit",
]
