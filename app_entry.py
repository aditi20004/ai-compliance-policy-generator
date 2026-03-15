"""Streamlit Community Cloud entry point — delegates to streamlit_app/app.py."""
import importlib
import sys
from pathlib import Path

# Ensure repo root is on sys.path for app.* imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit_app.app  # noqa: F401, E402
