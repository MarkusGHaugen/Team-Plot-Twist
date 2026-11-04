"""Initialise the same module revision as the app before test imports."""
from pathlib import Path
from runtime_loader import load_backend
load_backend(Path(__file__).resolve().parents[1])
