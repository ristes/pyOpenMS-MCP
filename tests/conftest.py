"""Shared fixtures for the test suite."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pyopenms as oms
import pytest


@pytest.fixture(scope="session")
def sample_mzml(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a minimal synthetic mzML file once per test session."""
    tmp = tmp_path_factory.mktemp("mzml")
    out = tmp / "sample.mzML"

    exp = oms.MSExperiment()

    # Three MS1 spectra
    for i in range(3):
        spec = oms.MSSpectrum()
        spec.setMSLevel(1)
        spec.setRT(float(i * 10))
        for j in range(5):
            p = oms.Peak1D()
            p.setMZ(100.0 + j * 10.0)
            p.setIntensity(float((i + 1) * (j + 1) * 100))
            spec.push_back(p)
        exp.addSpectrum(spec)

    # One MS2 spectrum with a precursor
    spec2 = oms.MSSpectrum()
    spec2.setMSLevel(2)
    spec2.setRT(15.0)
    prec = oms.Precursor()
    prec.setMZ(300.0)
    prec.setCharge(2)
    prec.setIntensity(1000.0)
    spec2.setPrecursors([prec])
    p = oms.Peak1D()
    p.setMZ(150.0)
    p.setIntensity(5000.0)
    spec2.push_back(p)
    exp.addSpectrum(spec2)

    oms.MzMLFile().store(str(out), exp)
    return out


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect storage to a temporary directory for each test."""
    monkeypatch.setenv("PYOPENMS_MCP_DATA_DIR", str(tmp_path))
    yield tmp_path
    # tmp_path is cleaned up automatically by pytest
