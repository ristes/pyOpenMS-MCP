"""Tests for the visualization tools (server tools and visualization functions)."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
import pyopenms as oms

from pyopenms_mcp import analysis, storage, visualizations
import pyopenms_mcp.server as srv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _loaded_exp(sample_mzml: Path) -> oms.MSExperiment:
    return analysis.load_experiment(str(sample_mzml))


# ---------------------------------------------------------------------------
# visualizations module — unit tests
# ---------------------------------------------------------------------------


class TestPlotTic:
    def test_creates_file(self, tmp_path: Path, sample_mzml: Path) -> None:
        exp = _loaded_exp(sample_mzml)
        out = tmp_path / "tic.png"
        result = visualizations.plot_tic(exp, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0


class TestPlotMs1Spectrum:
    def test_creates_file(self, tmp_path: Path, sample_mzml: Path) -> None:
        exp = _loaded_exp(sample_mzml)
        out = tmp_path / "ms1.png"
        result = visualizations.plot_ms1_spectrum(exp, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_empty_experiment_returns_path(self, tmp_path: Path) -> None:
        exp = oms.MSExperiment()
        out = tmp_path / "ms1_empty.png"
        result = visualizations.plot_ms1_spectrum(exp, out)
        assert result == out
        assert out.exists()  # placeholder image always created


class TestPlotSpectra2d:
    def test_creates_file(self, tmp_path: Path, sample_mzml: Path) -> None:
        exp = _loaded_exp(sample_mzml)
        out = tmp_path / "spectra2d.png"
        result = visualizations.plot_spectra_2d(exp, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_missing_ms_level_creates_placeholder(self, tmp_path: Path, sample_mzml: Path) -> None:
        exp = _loaded_exp(sample_mzml)
        out = tmp_path / "spectra2d_ms3.png"
        result = visualizations.plot_spectra_2d(exp, out, ms_level=3)
        assert result == out
        assert out.exists()


class TestPlotFeatureMap:
    def test_creates_file(self, tmp_path: Path) -> None:
        import pandas as pd

        df = pd.DataFrame(
            {
                "feature_id": [1, 2, 3],
                "rt_min": [1.0, 2.0, 3.0],
                "mz": [100.0, 200.0, 300.0],
                "intensity": [1000.0, 2000.0, 3000.0],
            }
        )
        out = tmp_path / "feature_map.png"
        result = visualizations.plot_feature_map(df, out)
        assert result == out
        assert out.exists()

    def test_empty_df_returns_path(self, tmp_path: Path) -> None:
        import pandas as pd

        df = pd.DataFrame(columns=["feature_id", "rt_min", "mz", "intensity"])
        out = tmp_path / "feature_map_empty.png"
        result = visualizations.plot_feature_map(df, out)
        assert result == out
        assert out.exists()  # placeholder image always created


class TestPlot2dDensityMap:
    def test_creates_file(self, tmp_path: Path) -> None:
        import pandas as pd

        df = pd.DataFrame(
            {
                "feature_id": list(range(20)),
                "rt_min": [float(i) for i in range(20)],
                "mz": [100.0 + i * 5 for i in range(20)],
                "intensity": [float((i + 1) * 1000) for i in range(20)],
            }
        )
        out = tmp_path / "density_map.png"
        result = visualizations.plot_2d_density_map(df, out, gridsize=10)
        assert result == out
        assert out.exists()


class TestPlotIntensityDistribution:
    def test_creates_file(self, tmp_path: Path) -> None:
        import pandas as pd

        df = pd.DataFrame(
            {
                "intensity": [float((i + 1) * 100) for i in range(50)],
            }
        )
        out = tmp_path / "intensity_dist.png"
        result = visualizations.plot_intensity_distribution(df, out)
        assert result == out
        assert out.exists()


class TestPlot3dFeatures:
    def test_empty_feature_map_creates_file(self, tmp_path: Path) -> None:
        fm = oms.FeatureMap()
        out = tmp_path / "3d_features.png"
        result = visualizations.plot_3d_features(fm, out)
        assert result == out
        assert out.exists()


# ---------------------------------------------------------------------------
# storage helpers
# ---------------------------------------------------------------------------


class TestPlotPath:
    def test_deterministic(self, data_dir: Path) -> None:
        p1 = storage.plot_path("abc123", "tic")
        p2 = storage.plot_path("abc123", "tic")
        assert p1 == p2

    def test_different_params_give_different_paths(self, data_dir: Path) -> None:
        p1 = storage.plot_path("abc123", "spectra_2d", {"ms_level": 1})
        p2 = storage.plot_path("abc123", "spectra_2d", {"ms_level": 2})
        assert p1 != p2

    def test_path_under_plots_dir(self, data_dir: Path) -> None:
        p = storage.plot_path("abc123", "tic")
        assert "plots" in p.parts


class TestEncodeImageBase64:
    def test_roundtrip(self, tmp_path: Path) -> None:
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
        encoded = storage.encode_image_base64(img)
        assert isinstance(encoded, str)
        assert base64.b64decode(encoded)[:8] == b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------------------
# Server visualization tools — integration tests
# ---------------------------------------------------------------------------


class TestServerPlotTic:
    def test_returns_expected_keys(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        result = srv.plot_tic(entry["id"])
        assert result["file_id"] == entry["id"]
        assert result["plot_type"] == "tic"
        assert result["format"] == "png"
        assert isinstance(result["image_base64"], str)
        assert len(result["image_base64"]) > 0
        assert Path(result["plot_path"]).exists()

    def test_cached_on_second_call(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        r1 = srv.plot_tic(entry["id"])
        r2 = srv.plot_tic(entry["id"])
        assert r1["plot_path"] == r2["plot_path"]

    def test_raises_for_unknown_id(self, data_dir: Path) -> None:
        with pytest.raises(KeyError):
            srv.plot_tic("unknown")


class TestServerPlotMs1Spectrum:
    def test_returns_expected_keys(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        result = srv.plot_ms1_spectrum(entry["id"])
        assert result["plot_type"] == "ms1_spectrum"
        assert isinstance(result["image_base64"], str)


class TestServerPlotSpectra2d:
    def test_returns_expected_keys(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        result = srv.plot_spectra_2d(entry["id"])
        assert result["plot_type"] == "spectra_2d"
        assert isinstance(result["image_base64"], str)

    def test_different_params_produce_different_files(
        self, data_dir: Path, sample_mzml: Path
    ) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        r1 = srv.plot_spectra_2d(entry["id"], ms_level=1)
        r2 = srv.plot_spectra_2d(entry["id"], ms_level=2)
        assert r1["plot_path"] != r2["plot_path"]


class TestServerFeatureVisualizations:
    def test_plot_feature_map(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        result = srv.plot_feature_map(entry["id"])
        assert result["plot_type"] == "feature_map"
        assert isinstance(result["image_base64"], str)
        assert Path(result["plot_path"]).exists()

    def test_plot_2d_density_map(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        result = srv.plot_2d_density_map(entry["id"])
        assert result["plot_type"] == "2d_density_map"
        assert Path(result["plot_path"]).exists()

    def test_plot_intensity_distribution(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        result = srv.plot_intensity_distribution(entry["id"])
        assert result["plot_type"] == "intensity_distribution"
        assert Path(result["plot_path"]).exists()

    def test_plot_3d_features(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        result = srv.plot_3d_features(entry["id"])
        assert result["plot_type"] == "3d_features"
        assert Path(result["plot_path"]).exists()

    def test_feature_plots_cached_on_second_call(
        self, data_dir: Path, sample_mzml: Path
    ) -> None:
        entry = srv.upload_mzml(str(sample_mzml))
        r1 = srv.plot_feature_map(entry["id"])
        r2 = srv.plot_feature_map(entry["id"])
        assert r1["plot_path"] == r2["plot_path"]
