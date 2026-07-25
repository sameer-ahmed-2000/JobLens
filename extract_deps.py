"""
extract_deps.py — CI helper. Prints backend/pyproject.toml's [project.dependencies]
list, one per line, so CI can `pip install -r` it without needing the package to
be a properly installable distribution (pyproject.toml here has no [build-system]
section, so `pip install -e .` isn't an option).
"""
import tomllib
import sys
from pathlib import Path

pyproject_path = Path(__file__).parent / "backend" / "pyproject.toml"
with open(pyproject_path, "rb") as f:
    deps = tomllib.load(f)["project"]["dependencies"]

sys.stdout.write("\n".join(deps) + "\n")