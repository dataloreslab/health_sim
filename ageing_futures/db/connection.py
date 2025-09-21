"""Database connection utilities with Streamlit-friendly caching."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from sqlmodel import SQLModel, create_engine

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - used in non-Streamlit contexts
    st = None  # type: ignore


DEFAULT_SQLITE_URL = "sqlite:///ageing_futures.db"


def _create_engine(db_url: Optional[str] = None):
    url = db_url or os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, echo=False, connect_args=connect_args)


if st is not None:

    @st.cache_resource(show_spinner=False)
    def get_engine(db_url: Optional[str] = None):
        """Return a cached SQLModel engine for Streamlit sessions."""
        engine = _create_engine(db_url)
        SQLModel.metadata.create_all(engine)
        return engine

else:

    @lru_cache(maxsize=1)
    def get_engine(db_url: Optional[str] = None):
        engine = _create_engine(db_url)
        SQLModel.metadata.create_all(engine)
        return engine


__all__ = ["get_engine", "DEFAULT_SQLITE_URL"]
