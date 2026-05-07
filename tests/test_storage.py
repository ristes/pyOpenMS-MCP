"""Tests for the storage module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyopenms_mcp import storage


class TestRegisterMzml:
    def test_registers_new_file(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = storage.register_mzml(str(sample_mzml))
        assert "id" in entry
        assert entry["name"] == "sample.mzML"
        assert Path(entry["path"]).exists()
        assert entry["size_bytes"] > 0
        assert "uploaded_at" in entry

    def test_idempotent_for_same_content(self, data_dir: Path, sample_mzml: Path) -> None:
        entry1 = storage.register_mzml(str(sample_mzml))
        entry2 = storage.register_mzml(str(sample_mzml))
        assert entry1["id"] == entry2["id"]
        # Only one file should be present in the registry
        assert len(storage.list_mzml_files()) == 1

    def test_raises_for_missing_file(self, data_dir: Path) -> None:
        with pytest.raises(FileNotFoundError):
            storage.register_mzml("/nonexistent/path/file.mzML")

    def test_raises_for_non_mzml_extension(self, data_dir: Path, tmp_path: Path) -> None:
        fake = tmp_path / "data.txt"
        fake.write_text("not mzml")
        with pytest.raises(ValueError, match="mzML"):
            storage.register_mzml(str(fake))


class TestListMzmlFiles:
    def test_empty_initially(self, data_dir: Path) -> None:
        assert storage.list_mzml_files() == []

    def test_returns_registered_files(self, data_dir: Path, sample_mzml: Path) -> None:
        storage.register_mzml(str(sample_mzml))
        files = storage.list_mzml_files()
        assert len(files) == 1
        assert files[0]["name"] == "sample.mzML"


class TestGetMzmlFile:
    def test_returns_existing_entry(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = storage.register_mzml(str(sample_mzml))
        fetched = storage.get_mzml_file(entry["id"])
        assert fetched == entry

    def test_raises_for_unknown_id(self, data_dir: Path) -> None:
        with pytest.raises(KeyError, match="deadbeef"):
            storage.get_mzml_file("deadbeef")


class TestDeleteMzmlFile:
    def test_removes_entry_and_file(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = storage.register_mzml(str(sample_mzml))
        stored_path = Path(entry["path"])
        assert stored_path.exists()

        deleted = storage.delete_mzml_file(entry["id"])
        assert deleted["id"] == entry["id"]
        assert not stored_path.exists()
        assert storage.list_mzml_files() == []

    def test_also_removes_cache_entries(self, data_dir: Path, sample_mzml: Path) -> None:
        entry = storage.register_mzml(str(sample_mzml))
        fid = entry["id"]
        storage.store_cached_result(fid, "spectra_summary", {"n": 1})
        storage.delete_mzml_file(fid)
        assert storage.get_cached_result(fid, "spectra_summary") is None

    def test_raises_for_unknown_id(self, data_dir: Path) -> None:
        with pytest.raises(KeyError):
            storage.delete_mzml_file("unknown_id")


class TestCache:
    def test_miss_returns_none(self, data_dir: Path) -> None:
        assert storage.get_cached_result("fid", "analysis") is None

    def test_round_trip(self, data_dir: Path) -> None:
        result = {"value": 42, "nested": [1, 2, 3]}
        storage.store_cached_result("fid", "analysis", result)
        cached = storage.get_cached_result("fid", "analysis")
        assert cached == result

    def test_params_affect_cache_key(self, data_dir: Path) -> None:
        storage.store_cached_result("fid", "pp", {"peaks": 10}, {"sn": 1.0})
        storage.store_cached_result("fid", "pp", {"peaks": 20}, {"sn": 2.0})
        assert storage.get_cached_result("fid", "pp", {"sn": 1.0}) == {"peaks": 10}
        assert storage.get_cached_result("fid", "pp", {"sn": 2.0}) == {"peaks": 20}
