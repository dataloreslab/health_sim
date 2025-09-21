"""CRUD helpers for Ageing Futures database interactions."""
from __future__ import annotations

import datetime as dt
import secrets
import string
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlmodel import Session as DBSession, select

from .models import Audit, Decision, Result, Round, Session, Team

ROOM_CODE_ALPHABET = string.ascii_uppercase + string.digits
ROOM_CODE_LENGTH = 6


def generate_room_code() -> str:
    return "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))


def create_session(db: DBSession, settings: Dict[str, Any], random_seed: int) -> Session:
    code = generate_room_code()
    session = Session(code=code, settings_json=settings, random_seed=random_seed)
    db.add(session)
    db.commit()
    db.refresh(session)
    db.add(Audit(session_id=session.id, action="session_created", payload_json=settings))
    db.commit()
    return session


def get_session_by_code(db: DBSession, code: str) -> Optional[Session]:
    return db.exec(select(Session).where(Session.code == code)).first()


def list_sessions(db: DBSession) -> List[Session]:
    return list(db.exec(select(Session).order_by(Session.created_at.desc())))


def create_team(db: DBSession, session: Session, name: str, colour: str, icon: str) -> Team:
    team = Team(session_id=session.id, name=name, colour=colour, icon=icon)
    db.add(team)
    db.commit()
    db.refresh(team)
    db.add(
        Audit(
            session_id=session.id,
            team_id=team.id,
            action="team_joined",
            payload_json={"name": name},
        )
    )
    db.commit()
    return team


def list_teams(db: DBSession, session_id: int) -> List[Team]:
    return list(db.exec(select(Team).where(Team.session_id == session_id).order_by(Team.joined_at)))


def start_round(
    db: DBSession,
    session: Session,
    index: int,
    months: int,
    shock: Optional[Dict[str, Any]] = None,
) -> Round:
    round_obj = Round(
        session_id=session.id,
        index=index,
        months_advanced=months,
        shock_json=shock or {},
        start_ts=dt.datetime.utcnow(),
    )
    db.add(round_obj)
    db.commit()
    db.refresh(round_obj)
    session.current_round = index
    session.status = "active"
    db.add(session)
    db.add(
        Audit(
            session_id=session.id,
            action="round_started",
            payload_json={"round": index, "months": months},
        )
    )
    db.commit()
    return round_obj


def lock_round(db: DBSession, round_obj: Round) -> None:
    round_obj.lock_ts = dt.datetime.utcnow()
    db.add(round_obj)
    db.add(
        Audit(
            session_id=round_obj.session_id,
            action="round_locked",
            payload_json={"round": round_obj.index},
        )
    )
    db.commit()


def upsert_decision(
    db: DBSession,
    session_id: int,
    team_id: int,
    round_id: int,
    policies: Dict[str, Any],
    budget_spent: float,
    locked: bool = False,
) -> Decision:
    decision = db.exec(
        select(Decision).where(
            Decision.session_id == session_id,
            Decision.team_id == team_id,
            Decision.round_id == round_id,
        )
    ).first()
    now = dt.datetime.utcnow()
    if decision is None:
        decision = Decision(
            session_id=session_id,
            team_id=team_id,
            round_id=round_id,
            policies_json=policies,
            budget_spent=budget_spent,
            locked_ts=now if locked else None,
        )
    else:
        decision.policies_json = policies
        decision.budget_spent = budget_spent
        if locked:
            decision.locked_ts = now
    db.add(decision)
    db.add(
        Audit(
            session_id=session_id,
            team_id=team_id,
            action="decision_saved",
            payload_json={"round": round_id, "locked": locked},
        )
    )
    db.commit()
    db.refresh(decision)
    return decision


def record_result(
    db: DBSession,
    session_id: int,
    team_id: int,
    round_id: int,
    metrics: Dict[str, Any],
    timeseries: Dict[str, Any],
) -> Result:
    result = Result(
        session_id=session_id,
        team_id=team_id,
        round_id=round_id,
        metrics_json=metrics,
        timeseries_json=timeseries,
    )
    db.add(result)
    db.add(
        Audit(
            session_id=session_id,
            team_id=team_id,
            action="result_recorded",
            payload_json={"round": round_id},
        )
    )
    db.commit()
    db.refresh(result)
    return result


def list_results_for_round(db: DBSession, session_id: int, round_id: int) -> List[Result]:
    return list(
        db.exec(
            select(Result).where(
                Result.session_id == session_id, Result.round_id == round_id
            )
        )
    )


def list_results_for_team(db: DBSession, session_id: int, team_id: int) -> List[Result]:
    return list(
        db.exec(
            select(Result)
            .where(Result.session_id == session_id, Result.team_id == team_id)
            .order_by(Result.round_id)
        )
    )


def fetch_leaderboard_data(
    db: DBSession, session_id: int
) -> List[Tuple[Team, Optional[Result]]]:
    teams = list_teams(db, session_id)
    results = list(
        db.exec(
            select(Result)
            .where(Result.session_id == session_id)
            .order_by(Result.round_id.desc())
        )
    )
    latest_by_team: Dict[int, Result] = {}
    for result in results:
        latest_by_team.setdefault(result.team_id, result)
    return [(team, latest_by_team.get(team.id)) for team in teams]


def log_audit(db: DBSession, session_id: int, action: str, payload: Dict[str, Any]) -> None:
    db.add(Audit(session_id=session_id, action=action, payload_json=payload))
    db.commit()


__all__ = [
    "create_session",
    "get_session_by_code",
    "list_sessions",
    "create_team",
    "list_teams",
    "start_round",
    "lock_round",
    "upsert_decision",
    "record_result",
    "list_results_for_round",
    "list_results_for_team",
    "fetch_leaderboard_data",
    "log_audit",
]
