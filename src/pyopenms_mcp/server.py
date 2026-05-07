"""MCP server exposing pyOpenMS functionality."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from pyopenms_mcp import analysis, storage

mcp = FastMCP(
    "pyOpenMS MCP",
    instructions=(
        "This server exposes pyOpenMS mass-spectrometry data processing "
        "through the MCP protocol.  You can upload mzML files, list them, "
        "and run analyses such as spectra summarisation, spectrum retrieval, "
        "chromatogram summarisation, and peak picking.  Analysis results are "
        "automatically cached so repeated calls return instantly."
    ),
)


# ---------------------------------------------------------------------------
# File management tools
# ---------------------------------------------------------------------------


@mcp.tool()
def upload_mzml(file_path: str) -> dict:
    """Register an mzML file by its local path.

    The file is copied into the server's uploads directory and assigned a
    stable identifier derived from its content.  If the same file has already
    been uploaded the existing record is returned.

    Parameters
    ----------
    file_path:
        Absolute or relative path to the mzML file on the local file system.

    Returns
    -------
    A dict with keys: id, name, path, size_bytes, uploaded_at.
    """
    return storage.register_mzml(file_path)


@mcp.tool()
def list_mzml_files() -> list[dict]:
    """List all uploaded mzML files.

    Returns
    -------
    A list of file-info dicts (id, name, path, size_bytes, uploaded_at).
    """
    return storage.list_mzml_files()


@mcp.tool()
def delete_mzml_file(file_id: str) -> dict:
    """Remove a previously uploaded mzML file and all its cached results.

    Parameters
    ----------
    file_id:
        The identifier returned by *upload_mzml*.

    Returns
    -------
    The file-info dict of the deleted entry.
    """
    return storage.delete_mzml_file(file_id)


# ---------------------------------------------------------------------------
# Analysis tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_spectra_summary(file_id: str) -> dict:
    """Return a summary of all spectra contained in an mzML file.

    The result is cached; subsequent calls for the same file return instantly.

    Parameters
    ----------
    file_id:
        Identifier of a previously uploaded mzML file.

    Returns
    -------
    A dict with keys: n_spectra, ms_levels, rt_range_seconds, mz_range.
    """
    cached = storage.get_cached_result(file_id, "spectra_summary")
    if cached is not None:
        return cached

    entry = storage.get_mzml_file(file_id)
    exp = analysis.load_experiment(entry["path"])
    result = analysis.get_spectra_summary(exp)
    storage.store_cached_result(file_id, "spectra_summary", result)
    return result


@mcp.tool()
def get_spectrum(file_id: str, spectrum_index: int) -> dict:
    """Return the raw data for a single spectrum.

    The result is cached per (file_id, spectrum_index) pair.

    Parameters
    ----------
    file_id:
        Identifier of a previously uploaded mzML file.
    spectrum_index:
        Zero-based index of the spectrum within the file.

    Returns
    -------
    A dict with keys: index, native_id, ms_level, rt_seconds, n_peaks,
    mz, intensity, precursors.
    """
    params = {"spectrum_index": spectrum_index}
    cached = storage.get_cached_result(file_id, "spectrum", params)
    if cached is not None:
        return cached

    entry = storage.get_mzml_file(file_id)
    exp = analysis.load_experiment(entry["path"])
    result = analysis.get_spectrum_data(exp, spectrum_index)
    storage.store_cached_result(file_id, "spectrum", result, params)
    return result


@mcp.tool()
def get_chromatogram_summary(file_id: str) -> dict:
    """Return a summary of all chromatograms contained in an mzML file.

    The result is cached; subsequent calls for the same file return instantly.

    Parameters
    ----------
    file_id:
        Identifier of a previously uploaded mzML file.

    Returns
    -------
    A dict with keys: n_chromatograms, chromatograms (list of per-chromatogram
    dicts with native_id, n_points, rt_range_seconds, max_intensity).
    """
    cached = storage.get_cached_result(file_id, "chromatogram_summary")
    if cached is not None:
        return cached

    entry = storage.get_mzml_file(file_id)
    exp = analysis.load_experiment(entry["path"])
    result = analysis.get_chromatogram_summary(exp)
    storage.store_cached_result(file_id, "chromatogram_summary", result)
    return result


@mcp.tool()
def run_peak_picking(file_id: str, signal_to_noise: float = 1.0) -> dict:
    """Run peak picking on an mzML file using PeakPickerHiRes.

    The result is cached per (file_id, signal_to_noise) pair.

    Parameters
    ----------
    file_id:
        Identifier of a previously uploaded mzML file.
    signal_to_noise:
        Minimum signal-to-noise ratio for peak detection (default: 1.0).

    Returns
    -------
    A dict with keys: n_spectra_processed, signal_to_noise_threshold,
    peaks_per_ms_level, total_peaks.
    """
    params = {"signal_to_noise": signal_to_noise}
    cached = storage.get_cached_result(file_id, "peak_picking", params)
    if cached is not None:
        return cached

    entry = storage.get_mzml_file(file_id)
    exp = analysis.load_experiment(entry["path"])
    result = analysis.run_peak_picking(exp, signal_to_noise=signal_to_noise)
    storage.store_cached_result(file_id, "peak_picking", result, params)
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server using stdio transport (default for MCP clients)."""
    mcp.run()


if __name__ == "__main__":
    main()
