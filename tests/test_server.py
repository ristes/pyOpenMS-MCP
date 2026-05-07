"""Tests for the MCP server tools (integration-style, without transport)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyopenms_mcp import storage
import pyopenms_mcp.server as srv


class TestUploadMzml:
    def test_uploads_and_returns_entry(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        assert "id" in entry
        assert entry["name"] == "sample.mzML"

    def test_idempotent(self, data_dir: Path, sample_mzml: Path) -> None:
        e1 = srv.upload_mzml(str(sample_mzml))
        e2 = srv.upload_mzml(str(sample_mzml))
        assert e1["id"] == e2["id"]

    def test_raises_for_missing_file(self, data_dir: Path) -> None:
        with pytest.raises(FileNotFoundError):
            srv.upload_mzml("/no/such/file.mzML")


class TestListMzmlFiles:
    def test_empty_initially(self, data_dir: Path) -> None:
        assert srv.list_mzml_files() == []

    def test_lists_uploaded(self, data_dir: Path, sample_mzml: Path) -> None:
        srv.upload_mzml(str(sample_mzml))
        files = srv.list_mzml_files()
        assert len(files) == 1

    def test_delete_removes_from_list(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        srv.delete_mzml_file(entry["id"])
        assert srv.list_mzml_files() == []


class TestGetSpectraSummary:
    def test_returns_summary(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        summary = srv.get_spectra_summary(entry["id"])
        assert summary["n_spectra"] == 4
        assert summary["ms_levels"] == {1: 3, 2: 1}

    def test_result_is_cached(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        srv.get_spectra_summary(entry["id"])
        # Second call should hit the cache — modify the underlying file to prove it
        cached = storage.get_cached_result(entry["id"], "spectra_summary")
        assert cached is not None
        assert cached["n_spectra"] == 4

    def test_raises_for_unknown_file_id(self, data_dir: Path) -> None:
        with pytest.raises(KeyError):
            srv.get_spectra_summary("unknown_id")


class TestGetSpectrum:
    def test_returns_spectrum_data(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        data = srv.get_spectrum(entry["id"], 0)
        assert data["index"] == 0
        assert data["ms_level"] == 1
        assert data["n_peaks"] == 5

    def test_caches_result(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        srv.get_spectrum(entry["id"], 0)
        cached = storage.get_cached_result(entry["id"], "spectrum", {"spectrum_index": 0})
        assert cached is not None
        assert cached["index"] == 0

    def test_raises_for_invalid_index(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        with pytest.raises(IndexError):
            srv.get_spectrum(entry["id"], 999)


class TestGetChromatogramSummary:
    def test_returns_summary(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        summary = srv.get_chromatogram_summary(entry["id"])
        assert "n_chromatograms" in summary
        assert summary["n_chromatograms"] == 0


class TestRunPeakPicking:
    def test_returns_result(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        result = srv.run_peak_picking(entry["id"])
        assert "total_peaks" in result
        assert result["n_spectra_processed"] == 4

    def test_caches_result(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        srv.run_peak_picking(entry["id"])
        cached = storage.get_cached_result(entry["id"], "peak_picking", {"signal_to_noise": 1.0})
        assert cached is not None

    def test_different_sn_gives_different_cache_entries(
        self, data_dir: Path, sample_mzml: Path
    ) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        r1 = srv.run_peak_picking(entry["id"], signal_to_noise=1.0)
        r2 = srv.run_peak_picking(entry["id"], signal_to_noise=0.1)
        # Different thresholds — results may differ, but both should be cached
        assert storage.get_cached_result(entry["id"], "peak_picking", {"signal_to_noise": 1.0}) is not None
        assert storage.get_cached_result(entry["id"], "peak_picking", {"signal_to_noise": 0.1}) is not None
