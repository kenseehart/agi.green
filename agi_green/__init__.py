from importlib.metadata import version, PackageNotFoundError
import tomli
from pathlib import Path

try:
    __version__ = version("agi.green")
except PackageNotFoundError:
    # Fallback to reading pyproject.toml directly when in editable mode
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            __version__ = tomli.load(f)["project"]["version"]
    except Exception:
        __version__ = "unknown"
