"""Save and load compiled DSPy modules to/from disk.

Optimized modules are stored as JSON files (DSPy native format) in
the data directory under `dspy_modules/`.
"""

import logging
from pathlib import Path

from backend.data_dir import get_data_dir

logger = logging.getLogger(__name__)

_MODULES_DIR = "dspy_modules"


def _get_module_path(module_name: str) -> Path:
    """Return the file path for a named module's saved state."""
    modules_dir = get_data_dir() / _MODULES_DIR
    modules_dir.mkdir(parents=True, exist_ok=True)
    return modules_dir / f"{module_name}.json"


def save_module(module_name: str, dspy_module) -> None:
    """Save a compiled DSPy module to disk."""
    path = _get_module_path(module_name)
    dspy_module.save(str(path))
    logger.info("Saved optimized module '%s' to %s", module_name, path)


def load_module_state(module_name: str, dspy_module) -> bool:
    """Load a previously compiled module state from disk, if available.

    Returns True if state was loaded, False otherwise.
    """
    path = _get_module_path(module_name)
    if not path.exists():
        return False

    try:
        dspy_module.load(str(path))
        logger.info("Loaded optimized module '%s' from %s", module_name, path)
        return True
    except Exception as e:
        logger.warning("Failed to load module '%s' from %s: %s", module_name, path, e)
        return False


def has_optimized_module(module_name: str) -> bool:
    """Check if an optimized module exists on disk."""
    return _get_module_path(module_name).exists()


def get_last_modified(module_name: str):
    """Return the last modified time of the module file, or None."""
    path = _get_module_path(module_name)
    if path.exists():
        return path.stat().st_mtime
    return None
