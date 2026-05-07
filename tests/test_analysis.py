"""Tests for the analysis module."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyopenms_mcp import analysis


@pytest.fixture()
def loaded_exp(sample_mzml: Path):
    return analysis.load_experiment(str(sample_mzml))


class TestLoadExperiment:
    def test_loads_mzml(self, sample_mzml: Path) -> None:
        exp = analysis.load_experiment(str(sample_mzml))
        assert exp.getNrSpectra() == 4

    def test_raises_for_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            analysis.load_experiment("/nonexistent/file.mzML")


class TestGetSpectraSummary:
    def test_structure(self, loaded_exp) -> None:
        summary = analysis.get_spectra_summary(loaded_exp)
        assert summary["n_spectra"] == 4
        assert summary["ms_levels"] == {1: 3, 2: 1}
        assert isinstance(summary["rt_range_seconds"], list)
        assert len(summary["rt_range_seconds"]) == 2
        assert isinstance(summary["mz_range"], list)
        assert len(summary["mz_range"]) == 2

    def test_rt_range_values(self, loaded_exp) -> None:
        summary = analysis.get_spectra_summary(loaded_exp)
        rt_min, rt_max = summary["rt_range_seconds"]
        assert rt_min == 0.0
        assert rt_max == 20.0

    def test_mz_range_values(self, loaded_exp) -> None:
        summary = analysis.get_spectra_summary(loaded_exp)
        mz_min, mz_max = summary["mz_range"]
        assert mz_min == 100.0
        assert mz_max == 150.0


class TestGetSpectrumData:
    def test_returns_correct_index(self, loaded_exp) -> None:
        data = analysis.get_spectrum_data(loaded_exp, 0)
        assert data["index"] == 0
        assert data["ms_level"] == 1
        assert data["rt_seconds"] == 0.0
        assert data["n_peaks"] == 5
        assert len(data["mz"]) == 5
        assert len(data["intensity"]) == 5

    def test_ms2_has_precursor(self, loaded_exp) -> None:
        data = analysis.get_spectrum_data(loaded_exp, 3)
        assert data["ms_level"] == 2
        assert len(data["precursors"]) == 1
        prec = data["precursors"][0]
        assert prec["mz"] == pytest.approx(300.0, abs=1e-4)
        assert prec["charge"] == 2

    def test_raises_for_out_of_range_index(self, loaded_exp) -> None:
        with pytest.raises(IndexError):
            analysis.get_spectrum_data(loaded_exp, 999)

    def test_raises_for_negative_index(self, loaded_exp) -> None:
        with pytest.raises(IndexError):
            analysis.get_spectrum_data(loaded_exp, -1)


class TestGetChromatogramSummary:
    def test_no_chromatograms(self, loaded_exp) -> None:
        summary = analysis.get_chromatogram_summary(loaded_exp)
        assert summary["n_chromatograms"] == 0
        assert summary["chromatograms"] == []


class TestRunPeakPicking:
    def test_returns_expected_keys(self, loaded_exp) -> None:
        result = analysis.run_peak_picking(loaded_exp)
        assert "n_spectra_processed" in result
        assert "signal_to_noise_threshold" in result
        assert "peaks_per_ms_level" in result
        assert "total_peaks" in result

    def test_processed_count_matches_spectra(self, loaded_exp) -> None:
        result = analysis.run_peak_picking(loaded_exp)
        assert result["n_spectra_processed"] == 4

    def test_custom_signal_to_noise(self, loaded_exp) -> None:
        result = analysis.run_peak_picking(loaded_exp, signal_to_noise=0.5)
        assert result["signal_to_noise_threshold"] == 0.5
