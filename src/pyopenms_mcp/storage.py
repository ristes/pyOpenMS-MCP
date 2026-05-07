"""Storage module: file registry and analysis result cache."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any


# Default data directory — override via PYOPENMS_MCP_DATA_DIR env variable.
DEFAULT_DATA_DIR = Path.home() / ".pyopenms_mcp"


def _data_dir() -> Path:
    return Path(os.environ.get("PYOPENMS_MCP_DATA_DIR", DEFAULT_DATA_DIR))


def _uploads_dir() -> Path:
    d = _data_dir() / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_dir() -> Path:
    d = _data_dir() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _plots_dir() -> Path:
    d = _data_dir() / "plots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _registry_path() -> Path:
    return _data_dir() / "registry.json"


# ---------------------------------------------------------------------------
# File registry
# ---------------------------------------------------------------------------


def _load_registry() -> dict[str, dict]:
    path = _registry_path()
    if path.exists():
        with path.open() as fh:
            return json.load(fh)
    return {}


def _save_registry(registry: dict[str, dict]) -> None:
    _registry_path().parent.mkdir(parents=True, exist_ok=True)
    with _registry_path().open("w") as fh:
        json.dump(registry, fh, indent=2)


def _file_id(file_path: Path) -> str:
    """Stable ID based on the SHA-256 of the file contents."""
    h = hashlib.sha256()
    with file_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def register_mzml(source_path: str) -> dict:
    """Copy *source_path* into the uploads directory and register it.

    Returns the file-info dict for the registered file.  If the same file
    content has been registered before the existing entry is returned and no
    copy is made.
    """
    src = Path(source_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"File not found: {source_path}")
    if src.suffix.lower() != ".mzml":
        raise ValueError(f"Expected an mzML file, got: {src.suffix}")

    file_id = _file_id(src)
    registry = _load_registry()

    if file_id in registry:
        return registry[file_id]

    dest = _uploads_dir() / f"{file_id}.mzML"
    shutil.copy2(src, dest)

    entry: dict = {
        "id": file_id,
        "name": src.name,
        "path": str(dest),
        "size_bytes": dest.stat().st_size,
        "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    registry[file_id] = entry
    _save_registry(registry)
    return entry


def list_mzml_files() -> list[dict]:
    """Return a list of all registered file-info dicts."""
    return list(_load_registry().values())


def get_mzml_file(file_id: str) -> dict:
    """Return the file-info dict for *file_id*, or raise KeyError."""
    registry = _load_registry()
    if file_id not in registry:
        raise KeyError(f"No file with id '{file_id}' found.")
    return registry[file_id]


def delete_mzml_file(file_id: str) -> dict:
    """Remove a file from the registry and delete the stored copy.

    Returns the file-info dict of the deleted entry.
    """
    registry = _load_registry()
    if file_id not in registry:
        raise KeyError(f"No file with id '{file_id}' found.")

    entry = registry.pop(file_id)
    stored = Path(entry["path"])
    if stored.exists():
        stored.unlink()

    # Invalidate all cached results for this file.
    for cache_file in _cache_dir().glob(f"{file_id}_*.json"):
        cache_file.unlink()

    _save_registry(registry)
    return entry


# ---------------------------------------------------------------------------
# Analysis result cache
# ---------------------------------------------------------------------------


def _cache_key(file_id: str, analysis_type: str, params: dict | None) -> str:
    params_str = json.dumps(params or {}, sort_keys=True)
    h = hashlib.sha256(params_str.encode()).hexdigest()[:8]
    return f"{file_id}_{analysis_type}_{h}"


def _cache_file(key: str) -> Path:
    return _cache_dir() / f"{key}.json"


def get_cached_result(file_id: str, analysis_type: str, params: dict | None = None) -> Any | None:
    """Return a cached result or *None* if not found."""
    key = _cache_key(file_id, analysis_type, params)
    cf = _cache_file(key)
    if cf.exists():
        with cf.open() as fh:
            return json.load(fh)
    return None


def store_cached_result(
    file_id: str, analysis_type: str, result: Any, params: dict | None = None
) -> None:
    """Persist *result* to the cache."""
    key = _cache_key(file_id, analysis_type, params)
    with _cache_file(key).open("w") as fh:
        json.dump(result, fh, indent=2)


# ---------------------------------------------------------------------------
# Plot storage
# ---------------------------------------------------------------------------


def plot_path(file_id: str, plot_type: str, params: dict | None = None) -> Path:
    """Return the path where a plot should be stored.

    The path is deterministic based on *file_id*, *plot_type*, and *params*
    so the same request always maps to the same file.
    """
    params_str = json.dumps(params or {}, sort_keys=True)
    h = hashlib.sha256(params_str.encode()).hexdigest()[:8]
    return _plots_dir() / f"{file_id}_{plot_type}_{h}.png"


def encode_image_base64(path: Path) -> str:
    """Return the base64-encoded contents of an image file."""
    with path.open("rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")
