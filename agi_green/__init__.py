from importlib.metadata import version, PackageNotFoundError
import tomli
from pathlib import Path
import os

# Ensure __version__ is always defined, even during import failures
__version__ = 'unknown'

try:
    __version__ = version("agi.green")
except PackageNotFoundError:
    # Fallback to reading pyproject.toml directly when in editable mode
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if os.path.exists(pyproject_path):
            with open(pyproject_path, "rb") as f:
                __version__ = f"edit mode: {tomli.load(f)['project']['version']}"
        else:
            __version__ = f"edit mode: {Path(__file__).resolve().parent}"
    except Exception as e:
        __version__ = f"edit mode: {Path(__file__).resolve().parent}"
