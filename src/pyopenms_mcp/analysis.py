"""Analysis module: wraps pyOpenMS to provide structured analysis results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyopenms as oms


# ---------------------------------------------------------------------------
# Experiment loading
# ---------------------------------------------------------------------------


def load_experiment(file_path: str) -> oms.MSExperiment:
    """Load an mzML file into an MSExperiment object."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"mzML file not found: {file_path}")
    exp = oms.MSExperiment()
    oms.MzMLFile().load(str(path), exp)
    return exp


# ---------------------------------------------------------------------------
# Spectra
# ---------------------------------------------------------------------------


def get_spectra_summary(exp: oms.MSExperiment) -> dict[str, Any]:
    """Return a high-level summary of the spectra in *exp*."""
    n_spectra = exp.getNrSpectra()
    ms_levels: dict[int, int] = {}
    rt_min = float("inf")
    rt_max = float("-inf")
    mz_min = float("inf")
    mz_max = float("-inf")

    for i in range(n_spectra):
        spec = exp.getSpectrum(i)
        level = spec.getMSLevel()
        ms_levels[level] = ms_levels.get(level, 0) + 1
        rt = spec.getRT()
        rt_min = min(rt_min, rt)
        rt_max = max(rt_max, rt)
        if spec.size() > 0:
            mz_min = min(mz_min, spec.getMinMZ())
            mz_max = max(mz_max, spec.getMaxMZ())

    return {
        "n_spectra": n_spectra,
        "ms_levels": ms_levels,
        "rt_range_seconds": [
            round(rt_min, 4) if rt_min != float("inf") else None,
            round(rt_max, 4) if rt_max != float("-inf") else None,
        ],
        "mz_range": [
            round(mz_min, 6) if mz_min != float("inf") else None,
            round(mz_max, 6) if mz_max != float("-inf") else None,
        ],
    }


def get_spectrum_data(exp: oms.MSExperiment, index: int) -> dict[str, Any]:
    """Return the data for spectrum at *index* as a serialisable dict."""
    n = exp.getNrSpectra()
    if index < 0 or index >= n:
        raise IndexError(f"Spectrum index {index} out of range [0, {n - 1}].")

    spec = exp.getSpectrum(index)
    mz_arr, intensity_arr = spec.get_peaks()

    precursors = []
    for prec in spec.getPrecursors():
        precursors.append(
            {
                "mz": round(prec.getMZ(), 6),
                "charge": prec.getCharge(),
                "intensity": round(prec.getIntensity(), 4),
            }
        )

    return {
        "index": index,
        "native_id": spec.getNativeID(),
        "ms_level": spec.getMSLevel(),
        "rt_seconds": round(spec.getRT(), 4),
        "n_peaks": len(mz_arr),
        "mz": [round(float(v), 6) for v in mz_arr],
        "intensity": [round(float(v), 4) for v in intensity_arr],
        "precursors": precursors,
    }


# ---------------------------------------------------------------------------
# Chromatograms
# ---------------------------------------------------------------------------


def get_chromatogram_summary(exp: oms.MSExperiment) -> dict[str, Any]:
    """Return a summary of chromatograms in *exp*."""
    n_chrom = exp.getNrChromatograms()
    chromatograms = []
    for i in range(n_chrom):
        chrom = exp.getChromatogram(i)
        rt_arr, intensity_arr = chrom.get_peaks()
        chromatograms.append(
            {
                "index": i,
                "native_id": chrom.getNativeID(),
                "n_points": len(rt_arr),
                "rt_range_seconds": [
                    round(float(rt_arr.min()), 4) if len(rt_arr) > 0 else None,
                    round(float(rt_arr.max()), 4) if len(rt_arr) > 0 else None,
                ],
                "max_intensity": round(float(intensity_arr.max()), 4) if len(intensity_arr) > 0 else None,
            }
        )
    return {
        "n_chromatograms": n_chrom,
        "chromatograms": chromatograms,
    }


# ---------------------------------------------------------------------------
# Peak picking
# ---------------------------------------------------------------------------


def run_peak_picking(
    exp: oms.MSExperiment,
    signal_to_noise: float = 1.0,
) -> dict[str, Any]:
    """Run PeakPickerHiRes on *exp* and return a summary of the results.

    Parameters
    ----------
    exp:
        Loaded MSExperiment (profile-mode data).
    signal_to_noise:
        Minimum signal-to-noise ratio for peak detection.

    Returns
    -------
    A dict summarising the picked peaks per MS level.
    """
    picked = oms.MSExperiment()
    picker = oms.PeakPickerHiRes()

    params = picker.getParameters()
    params.setValue("signal_to_noise", signal_to_noise)
    picker.setParameters(params)

    picker.pickExperiment(exp, picked, True)

    ms_level_peaks: dict[int, int] = {}
    for i in range(picked.getNrSpectra()):
        spec = picked.getSpectrum(i)
        level = spec.getMSLevel()
        ms_level_peaks[level] = ms_level_peaks.get(level, 0) + spec.size()

    return {
        "n_spectra_processed": picked.getNrSpectra(),
        "signal_to_noise_threshold": signal_to_noise,
        "peaks_per_ms_level": ms_level_peaks,
        "total_peaks": sum(ms_level_peaks.values()),
    }
