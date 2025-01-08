from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("agi.green")
except PackageNotFoundError:
    # Package is not installed
    __version__ = "unknown"
