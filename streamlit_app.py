"""Convenience entry point for Streamlit Cloud deployments.

This wrapper simply executes the multipage application defined in
``streamlit_app/Home.py`` so that Streamlit Community Cloud users can
select ``streamlit_app.py`` as the main file while preserving the
project's directory structure.
"""
from __future__ import annotations

from pathlib import Path
import runpy

HOME_PATH = Path(__file__).parent / "streamlit_app" / "Home.py"

if not HOME_PATH.exists():
    raise FileNotFoundError(
        "Expected multipage entry point at streamlit_app/Home.py; "
        "please ensure the repository structure is intact."
    )

runpy.run_path(HOME_PATH, run_name="__main__")
