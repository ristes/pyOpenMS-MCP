"""MCP server exposing pyOpenMS functionality."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from pyopenms_mcp import analysis, storage, visualizations

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
# Visualization tools
# ---------------------------------------------------------------------------


def _make_plot_result(file_id: str, plot_type: str, out_path, params: dict | None = None) -> dict:
    """Build the standard return dict for a visualization tool."""
    image_b64 = storage.encode_image_base64(out_path)
    return {
        "file_id": file_id,
        "plot_type": plot_type,
        "plot_path": str(out_path),
        "format": "png",
        "image_base64": image_b64,
    }


@mcp.tool()
def plot_tic(file_id: str) -> dict:
    """Generate a Total Ion Chromatogram (TIC) plot for an mzML file.

    The plot is saved to disk and returned as a base64-encoded PNG image.

    Parameters
    ----------
    file_id:
        Identifier of a previously uploaded mzML file.

    Returns
    -------
    A dict with keys: file_id, plot_type, plot_path, format, image_base64.
    """
    entry = storage.get_mzml_file(file_id)
    out = storage.plot_path(file_id, "tic")
    if not out.exists():
        exp = analysis.load_experiment(entry["path"])
        visualizations.plot_tic(exp, out)
    return _make_plot_result(file_id, "tic", out)


@mcp.tool()
def plot_ms1_spectrum(file_id: str) -> dict:
    """Generate a representative MS1 spectrum plot for an mzML file.

    Plots the middle MS1 scan.  The plot is saved to disk and returned as a
    base64-encoded PNG image.

    Parameters
    ----------
    file_id:
        Identifier of a previously uploaded mzML file.

    Returns
    -------
    A dict with keys: file_id, plot_type, plot_path, format, image_base64.
    """
    entry = storage.get_mzml_file(file_id)
    out = storage.plot_path(file_id, "ms1_spectrum")
    if not out.exists():
        exp = analysis.load_experiment(entry["path"])
        visualizations.plot_ms1_spectrum(exp, out)
    return _make_plot_result(file_id, "ms1_spectrum", out)


@mcp.tool()
def plot_spectra_2d(
    file_id: str,
    ms_level: int = 1,
    rt_tol: float = 15.0,
    mz_tol: float = 0.5,
) -> dict:
    """Generate a 2D spectra map (RT vs m/z, colored by intensity) for an mzML file.

    Peaks are binned by RT and m/z tolerance to reduce rendering cost.  The
    plot is saved to disk and returned as a base64-encoded PNG image.

    Parameters
    ----------
    file_id:
        Identifier of a previously uploaded mzML file.
    ms_level:
        MS level to plot (default: 1).
    rt_tol:
        Retention-time binning width in seconds (default: 15).
    mz_tol:
        m/z binning width in Da (default: 0.5).

    Returns
    -------
    A dict with keys: file_id, plot_type, plot_path, format, image_base64.
    """
    params = {"ms_level": ms_level, "rt_tol": rt_tol, "mz_tol": mz_tol}
    entry = storage.get_mzml_file(file_id)
    out = storage.plot_path(file_id, "spectra_2d", params)
    if not out.exists():
        exp = analysis.load_experiment(entry["path"])
        visualizations.plot_spectra_2d(exp, out, ms_level=ms_level, rt_tol=rt_tol, mz_tol=mz_tol)
    return _make_plot_result(file_id, "spectra_2d", out, params)


@mcp.tool()
def plot_feature_map(file_id: str, signal_to_noise: float = 1.0) -> dict:
    """Detect features in an mzML file and plot them as a scatter feature map.

    Runs peak picking followed by feature detection, then visualises the
    resulting features as a scatter plot of RT vs m/z coloured by log10
    intensity.  The plot is saved to disk and returned as a base64-encoded PNG.

    Parameters
    ----------
    file_id:
        Identifier of a previously uploaded mzML file.
    signal_to_noise:
        Signal-to-noise threshold for peak picking (default: 1.0).

    Returns
    -------
    A dict with keys: file_id, plot_type, plot_path, format, image_base64,
    n_features.
    """
    params = {"signal_to_noise": signal_to_noise}
    entry = storage.get_mzml_file(file_id)
    out = storage.plot_path(file_id, "feature_map", params)
    if not out.exists():
        exp = analysis.load_experiment(entry["path"])
        _, df = analysis.run_feature_detection(exp, signal_to_noise=signal_to_noise)
        visualizations.plot_feature_map(df, out)
    result = _make_plot_result(file_id, "feature_map", out, params)
    return result


@mcp.tool()
def plot_2d_density_map(file_id: str, signal_to_noise: float = 1.0) -> dict:
    """Detect features in an mzML file and plot a 2D hexbin density map.

    Runs peak picking followed by feature detection, then produces a 2D hexbin
    map of RT vs m/z with summed log-intensity as colour.  The plot is saved
    to disk and returned as a base64-encoded PNG.

    Parameters
    ----------
    file_id:
        Identifier of a previously uploaded mzML file.
    signal_to_noise:
        Signal-to-noise threshold for peak picking (default: 1.0).

    Returns
    -------
    A dict with keys: file_id, plot_type, plot_path, format, image_base64.
    """
    params = {"signal_to_noise": signal_to_noise}
    entry = storage.get_mzml_file(file_id)
    out = storage.plot_path(file_id, "2d_density_map", params)
    if not out.exists():
        exp = analysis.load_experiment(entry["path"])
        _, df = analysis.run_feature_detection(exp, signal_to_noise=signal_to_noise)
        visualizations.plot_2d_density_map(df, out)
    return _make_plot_result(file_id, "2d_density_map", out, params)


@mcp.tool()
def plot_intensity_distribution(file_id: str, signal_to_noise: float = 1.0) -> dict:
    """Detect features in an mzML file and plot their intensity distribution.

    Runs peak picking followed by feature detection, then produces a histogram
    of feature intensities on a log10 scale.  The plot is saved to disk and
    returned as a base64-encoded PNG.

    Parameters
    ----------
    file_id:
        Identifier of a previously uploaded mzML file.
    signal_to_noise:
        Signal-to-noise threshold for peak picking (default: 1.0).

    Returns
    -------
    A dict with keys: file_id, plot_type, plot_path, format, image_base64.
    """
    params = {"signal_to_noise": signal_to_noise}
    entry = storage.get_mzml_file(file_id)
    out = storage.plot_path(file_id, "intensity_distribution", params)
    if not out.exists():
        exp = analysis.load_experiment(entry["path"])
        _, df = analysis.run_feature_detection(exp, signal_to_noise=signal_to_noise)
        visualizations.plot_intensity_distribution(df, out)
    return _make_plot_result(file_id, "intensity_distribution", out, params)


@mcp.tool()
def plot_3d_features(file_id: str, signal_to_noise: float = 1.0) -> dict:
    """Detect features in an mzML file and plot chromatographic traces in 3D.

    Runs peak picking followed by feature detection, then visualises each
    feature as a 3D line trace (RT × Intensity × m/z).  The plot is saved to
    disk and returned as a base64-encoded PNG.

    Parameters
    ----------
    file_id:
        Identifier of a previously uploaded mzML file.
    signal_to_noise:
        Signal-to-noise threshold for peak picking (default: 1.0).

    Returns
    -------
    A dict with keys: file_id, plot_type, plot_path, format, image_base64.
    """
    params = {"signal_to_noise": signal_to_noise}
    entry = storage.get_mzml_file(file_id)
    out = storage.plot_path(file_id, "3d_features", params)
    if not out.exists():
        exp = analysis.load_experiment(entry["path"])
        feature_map, _ = analysis.run_feature_detection(exp, signal_to_noise=signal_to_noise)
        visualizations.plot_3d_features(feature_map, out)
    return _make_plot_result(file_id, "3d_features", out, params)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server using stdio transport (default for MCP clients)."""
    mcp.run()


if __name__ == "__main__":
    main()
