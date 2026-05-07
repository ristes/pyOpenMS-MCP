"""Visualization functions for LC-MS data pipelines.

Includes:
  - TIC plot
  - MS1 spectrum plot
  - Feature map (scatter)
  - 2D density map (hexbin)
  - Intensity distribution
  - Lipid class distribution
  - Annotated vs unannotated features
  - 3D feature plot (chromatographic traces per feature)
  - 2D spectra plot (RT vs m/z colored by intensity)
"""

from __future__ import annotations

import itertools
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

import pyopenms as oms


def _empty_plot(out: Path, message: str) -> Path:
    """Create a minimal placeholder plot with a message and save it to *out*."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes, fontsize=14)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_tic(exp: oms.MSExperiment, out: Path) -> Path:
    """Plot Total Ion Chromatogram (TIC) for MS1 spectra."""
    rt, tic = [], []
    for s in exp:
        if s.getMSLevel() == 1:
            _, ints = s.get_peaks()
            rt.append(s.getRT() / 60)
            tic.append(float(np.sum(ints)))
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(rt, tic, lw=0.8)
    ax.set_xlabel("Retention time [min]")
    ax.set_ylabel("Total Ion Current")
    ax.set_title("Total Ion Chromatogram (MS1)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_ms1_spectrum(exp: oms.MSExperiment, out: Path) -> Path:
    """Plot a representative MS1 spectrum (middle scan)."""
    ms1 = [s for s in exp if s.getMSLevel() == 1 and s.size() > 0]
    if not ms1:
        return _empty_plot(out, "No MS1 spectra found")
    spec = ms1[len(ms1) // 2]
    mzs, ints = spec.get_peaks()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.vlines(mzs, 0, ints, lw=0.4)
    ax.set_xlabel("m/z")
    ax.set_ylabel("Intensity")
    ax.set_title(f"MS1 spectrum at RT = {spec.getRT() / 60:.2f} min")
    if len(mzs) > 2:
        ax.set_xlim(np.percentile(mzs, 1), np.percentile(mzs, 99))
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_feature_map(df, out: Path) -> Path:
    """Plot feature map (RT vs m/z) colored by log10 intensity (scatter)."""
    if df.empty:
        return _empty_plot(out, "No features detected")
    fig, ax = plt.subplots(figsize=(10, 5))
    sc = ax.scatter(
        df["rt_min"],
        df["mz"],
        c=np.log10(df["intensity"].clip(lower=1)),
        s=5,
        alpha=0.6,
        cmap="plasma",
    )
    plt.colorbar(sc, ax=ax, label="log10 intensity")
    ax.set_xlabel("Retention time [min]")
    ax.set_ylabel("m/z")
    ax.set_title(f"LC-MS Feature Map  (n = {len(df):,})")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_2d_density_map(
    df, out: Path, gridsize: int = 200, cmap: str = "plasma"
) -> Path:
    """Create a 2D hexbin density map (RT vs m/z) colored by summed log-intensity.

    Parameters
    ----------
    df : pd.DataFrame
        Feature DataFrame with columns 'rt_min', 'mz', 'intensity'.
    out : Path
        Path to save the PNG image.
    gridsize : int
        Resolution of the hexbin grid.
    cmap : str
        Matplotlib colormap name.
    """
    if df is None or df.empty:
        return _empty_plot(out, "No features detected")

    x = df["rt_min"].values
    y = df["mz"].values
    weights = np.log10(df["intensity"].clip(lower=1)).values

    fig, ax = plt.subplots(figsize=(10, 6))
    hb = ax.hexbin(
        x, y, C=weights, reduce_C_function=np.sum, gridsize=gridsize, cmap=cmap, mincnt=1
    )
    ax.set_xlabel("Retention time [min]")
    ax.set_ylabel("m/z")
    ax.set_title("2D Feature Density Map (hexbin)")

    cbar = fig.colorbar(hb, ax=ax, pad=0.02)
    cbar.set_label("sum(log10 intensity)")

    if "feature_id" in df.columns:
        top_ann = df.nlargest(100, "intensity")
        ax.scatter(
            top_ann["rt_min"],
            top_ann["mz"],
            s=18,
            c="none",
            edgecolors="white",
            linewidths=0.8,
        )
        ax.scatter(top_ann["rt_min"], top_ann["mz"], s=12, c="red", alpha=0.9)

    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_intensity_distribution(df, out: Path) -> Path:
    """Plot histogram of feature intensities (log10 scale)."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(
        np.log10(df["intensity"].clip(lower=1)), bins=60, color="steelblue", edgecolor="none"
    )
    ax.set_xlabel("log10 intensity")
    ax.set_ylabel("# features")
    ax.set_title("Feature Intensity Distribution")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_lipid_classes(matches, out: Path) -> Path:
    """Plot bar chart of lipid class distribution."""
    if matches.empty:
        return _empty_plot(out, "No lipid annotations found")
    counts = matches["class"].value_counts()
    fig, ax = plt.subplots(figsize=(8, 4))
    counts.plot(kind="bar", ax=ax, color="darkorange", edgecolor="none")
    ax.set_xlabel("Lipid class")
    ax.set_ylabel("# putative matches")
    ax.set_title("Putative Lipid Class Distribution")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_annotated_map(df, matches, out: Path) -> Path:
    """Plot feature map highlighting annotated vs unannotated features."""
    if df.empty or matches.empty:
        return _empty_plot(out, "No data to plot")
    anno_ids = set(matches["feature_id"].unique())
    is_anno = df["feature_id"].isin(anno_ids)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(
        df.loc[~is_anno, "rt_min"],
        df.loc[~is_anno, "mz"],
        c="lightgray",
        s=4,
        alpha=0.5,
        label="Unannotated",
    )
    ax.scatter(
        df.loc[is_anno, "rt_min"],
        df.loc[is_anno, "mz"],
        c="crimson",
        s=18,
        alpha=0.85,
        label=f"Annotated ({is_anno.sum()})",
    )
    ax.set_xlabel("Retention time [min]")
    ax.set_ylabel("m/z")
    ax.set_title("Feature Map — Annotated vs Unannotated")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_3d_features(feature_map: oms.FeatureMap, out: Path) -> Path:
    """Plot 3D visualization of detected features with chromatographic traces.

    Each feature is plotted as a 3D line showing RT vs intensity for its m/z.
    Colors cycle through a set palette for each feature.

    Parameters
    ----------
    feature_map : oms.FeatureMap
        A loaded FeatureMap object.
    out : Path
        Path to save the PNG image.
    """
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection="3d")

    cycled_colors = itertools.cycle(
        ["red", "green", "blue", "orange", "purple", "brown", "cyan", "magenta", "black", "gray"]
    )

    for feature, color in zip(feature_map, cycled_colors):
        for i, sub in enumerate(feature.getSubordinates()):
            convex_hulls = sub.getConvexHulls()
            if not convex_hulls:
                continue
            hull = convex_hulls[0]
            hull_points = hull.getHullPoints()
            if not hull_points:
                continue

            retention_times = [x[0] / 60 for x in hull_points]
            intensities = [y[1] for y in hull_points]
            mz = sub.getMZ()

            ax.plot(retention_times, intensities, zs=mz, zdir="z", color=color, linewidth=1.5)

            if i == 0 and intensities:
                label = str(feature.getMetaValue("label"))
                ax.text(
                    retention_times[0], max(intensities) * 1.02, mz, label, color=color, fontsize=8
                )

    ax.set_xlabel("Retention Time [min]")
    ax.set_ylabel("Intensity [cps]")
    ax.set_zlabel("m/z")
    ax.set_title("3D Feature Traces (RT x Intensity x m/z)")

    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_spectra_2d(
    exp: oms.MSExperiment,
    out: Path,
    ms_level: int = 1,
    rt_tol: float = 15.0,
    mz_tol: float = 0.5,
) -> Path:
    """Plot 2D spectra (RT vs m/z) with intensity as color.

    Peaks are grouped/binned by RT and m/z tolerance to reduce resolution
    and speed up rendering for large datasets.

    Parameters
    ----------
    exp : oms.MSExperiment
        The MS experiment.
    out : Path
        Path to save the PNG image.
    ms_level : int
        Which MS level to plot (default 1).
    rt_tol : float
        Retention time binning tolerance in seconds (default 15).
    mz_tol : float
        m/z binning tolerance in Da (default 0.5).
    """
    import pandas as pd

    data = []
    for spec in exp.getSpectra():
        if spec.getMSLevel() == ms_level:
            mz, intensity = spec.get_peaks()
            if len(mz) == 0:
                continue
            rt_sec = spec.getRT()
            for m, i in zip(mz, intensity):
                data.append({"rt_sec": rt_sec, "mz": m, "intensity": float(i)})

    if not data:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(
            0.5,
            0.5,
            f"No spectra found for MS level {ms_level}",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        fig.savefig(out, dpi=150)
        plt.close(fig)
        return out

    df = pd.DataFrame(data)

    df["rt_bin"] = (df["rt_sec"] / rt_tol).round() * rt_tol
    df["mz_bin"] = (df["mz"] / mz_tol).round() * mz_tol

    df_grouped = df.groupby(["rt_bin", "mz_bin"])["intensity"].sum().reset_index()
    df_grouped["rt_min"] = df_grouped["rt_bin"] / 60.0

    fig, ax = plt.subplots(figsize=(12, 6))

    scatter = ax.scatter(
        df_grouped["rt_min"],
        df_grouped["mz_bin"],
        c=df_grouped["intensity"],
        cmap="afmhot_r",
        s=8,
        alpha=0.7,
        norm=mcolors.LogNorm(
            vmin=df_grouped["intensity"].min() + 1, vmax=df_grouped["intensity"].max()
        ),
    )

    ax.set_xlabel("Retention Time [min]")
    ax.set_ylabel("m/z")
    ax.set_title(
        f"2D Spectra Map (MS level {ms_level}, binned RT={rt_tol}s m/z={mz_tol}Da)"
    )
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Sum Intensity [cps]")

    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
