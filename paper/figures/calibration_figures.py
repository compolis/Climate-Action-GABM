"""
Generate calibration (Section 5) figures for the seminar paper.

The calibration section uses two samples drawn from saved outputs under
data/output/calibration/: a six-policy sample at n=30 and a higher-power
follow-up sample at n=100 for Carbon tax and Climate compensation.

Both samples call ``SurveyedCitizen.administer_survey`` with the same
survey-path stack used in Probes 1 and 2 (Claude Sonnet, two-step debias,
no extended thinking, T=0.5), with no memory, no broadcasts, no peers,
and ``opinion_history`` cleared per call.

Writes PDF and PNG versions of three figures into paper/figures/:

    - calib_null_sixpolicy.pdf   6-panel grid, one panel per policy. Each
                                                             panel shows the permutation null
                                                             distribution of MAE under shuffled
                                                             agent->GT pairing (1000 shuffles per
                                                             panel) with the real MAE marked as a
                                                             vertical line.
    - calib_null_followup.pdf    2-panel grid for Carbon tax and Climate
                                                             compensation at n=100 with B=1000
                                                             shuffles, same null/real overlay.
    - calib_bias.pdf             Per-policy signed bias (LLM - GT) bar
                                                             chart, with the higher-power follow-up
                                                             estimates overlaid where available.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CALIB_DIR = REPO_ROOT / "data" / "output" / "calibration"
FIG_DIR = Path(__file__).resolve().parent

SIXPOLICY_RUN = "20260425_203841"
FOLLOWUP_RUN = "20260425_211242_persona"

POLICY_LABELS = {
    "ClimatePolicyID(1)": "Renewable energy",
    "ClimatePolicyID(2)": "Ban fossil fuels",
    "ClimatePolicyID(3)": "Ban petrol cars",
    "ClimatePolicyID(4)": "Green housing",
    "ClimatePolicyID(5)": "Carbon tax",
    "ClimatePolicyID(6)": "Climate compensation",
}
POLICY_ORDER = list(POLICY_LABELS.keys())
FOLLOWUP_POLICIES = ["ClimatePolicyID(5)", "ClimatePolicyID(6)"]

C_SAMPLE_30 = "#4C78A8"
C_SAMPLE_100 = "#F58518"
C_REAL = "#1F2937"
C_GRID = "#D1D5DB"

POLICY_COLORS = {
    "ClimatePolicyID(1)": "#009E73",
    "ClimatePolicyID(2)": "#56B4E9",
    "ClimatePolicyID(3)": "#0072B2",
    "ClimatePolicyID(4)": "#66A61E",
    "ClimatePolicyID(5)": "#D55E00",
    "ClimatePolicyID(6)": "#CC79A7",
}

N_PERMS_FIG = 1000
RNG_SEED = 7
PNG_DPI = 300


def _save(fig, name: str) -> Path:
    out = FIG_DIR / name
    fig.savefig(out, format="pdf", bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), format="png", dpi=PNG_DPI,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def _load_raw(run_dir: str) -> pd.DataFrame:
    path = CALIB_DIR / run_dir / "calibration_raw.csv"
    df = pd.read_csv(path)
    return df.dropna(subset=["llm"]).copy()


def _load_per_policy(run_dir: str) -> pd.DataFrame:
    return pd.read_csv(CALIB_DIR / run_dir / "per_policy.csv")


def _permutation_mae(llm: np.ndarray, gt: np.ndarray, n_perms: int,
                     rng: np.random.Generator) -> tuple[float, np.ndarray]:
    real_mae = float(np.mean(np.abs(llm - gt)))
    perms = np.empty(n_perms, dtype=float)
    for k in range(n_perms):
        perms[k] = float(np.mean(np.abs(llm - rng.permutation(gt))))
    return real_mae, perms


def _per_policy_bias_se(df: pd.DataFrame) -> pd.DataFrame:
    """Signed-bias mean and standard error per policy."""
    g = df.groupby("policy_id")["err"].agg(["mean", "std", "count"]).reset_index()
    g["se"] = g["std"] / g["count"] ** 0.5
    g.rename(columns={"mean": "bias"}, inplace=True)
    return g


def _style_axes(ax) -> None:
    ax.set_axisbelow(True)
    ax.grid(True, axis="y", linestyle=":", linewidth=0.8, alpha=0.55,
            color=C_GRID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _null_panel(ax, llm: np.ndarray, gt: np.ndarray, title: str,
                rng: np.random.Generator, show_xlabel: bool,
                show_ylabel: bool, panel_color: str) -> None:
    real_mae, perms = _permutation_mae(llm, gt, N_PERMS_FIG, rng)
    null_mean = float(np.mean(perms))
    p_mae = float(np.mean(perms <= real_mae))
    ax.hist(perms, bins=30, color=panel_color, alpha=0.55, edgecolor="white",
            linewidth=0.7)
    ax.axvline(null_mean, color=panel_color, linestyle="--", linewidth=1.5,
               label=f"Null mean = {null_mean:.2f}")
    ax.axvline(real_mae, color=C_REAL, linewidth=2.1,
               label=f"Real MAE = {real_mae:.2f}")
    ax.set_title(f"{title}\n$p_{{\\mathrm{{MAE}}}}={p_mae:.3f}$", fontsize=10,
                 color=panel_color, fontweight="bold")
    if show_xlabel:
        ax.set_xlabel("MAE under shuffled pairing")
    if show_ylabel:
        ax.set_ylabel("Permutation count")
    ax.tick_params(axis="both", labelsize=8)
    _style_axes(ax)
    ax.legend(fontsize=7, loc="upper right", framealpha=0.92)


def plot_null_sixpolicy() -> Path:
    df = _load_raw(SIXPOLICY_RUN)
    rng = np.random.default_rng(RNG_SEED)
    fig, axes = plt.subplots(2, 3, figsize=(11.0, 6.2))
    fig.patch.set_facecolor("white")
    for idx, pid in enumerate(POLICY_ORDER):
        sub = df[df["policy_id"] == pid]
        llm = sub["llm"].to_numpy(dtype=float)
        gt = sub["gt"].to_numpy(dtype=float)
        ax = axes[idx // 3, idx % 3]
        _null_panel(ax, llm, gt, POLICY_LABELS[pid], rng,
                    show_xlabel=(idx // 3 == 1),
                    show_ylabel=(idx % 3 == 0),
                    panel_color=POLICY_COLORS[pid])
    fig.suptitle(
        f"Six-policy calibration sample: permutation null on MAE  ($n=30$, $B={N_PERMS_FIG}$)",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return _save(fig, "calib_null_sixpolicy.pdf")


def plot_null_followup() -> Path:
    df = _load_raw(FOLLOWUP_RUN)
    rng = np.random.default_rng(RNG_SEED + 1)
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.6))
    fig.patch.set_facecolor("white")
    for ax, pid in zip(axes, FOLLOWUP_POLICIES):
        sub = df[df["policy_id"] == pid]
        llm = sub["llm"].to_numpy(dtype=float)
        gt = sub["gt"].to_numpy(dtype=float)
        _null_panel(ax, llm, gt, POLICY_LABELS[pid], rng,
                    show_xlabel=True, show_ylabel=True,
                    panel_color=POLICY_COLORS[pid])
    fig.suptitle(
        f"Higher-power follow-up sample: permutation null on MAE  ($n=100$, $B={N_PERMS_FIG}$)",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return _save(fig, "calib_null_followup.pdf")


def plot_bias() -> Path:
    sample_30 = _per_policy_bias_se(_load_raw(SIXPOLICY_RUN))
    sample_100 = _per_policy_bias_se(_load_raw(FOLLOWUP_RUN))

    sample_30 = sample_30.set_index("policy_id").loc[POLICY_ORDER].reset_index()
    sample_100 = sample_100.set_index("policy_id").loc[FOLLOWUP_POLICIES].reset_index()

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    fig.patch.set_facecolor("white")
    x = np.arange(len(POLICY_ORDER))
    width = 0.36

    ax.bar(x - width / 2, sample_30["bias"], width=width,
           yerr=sample_30["se"], color=C_SAMPLE_30, alpha=0.85, capsize=3,
           label="Six-policy sample ($n=30$)", edgecolor="white", linewidth=0.4)

    followup_x = [POLICY_ORDER.index(pid) + width / 2 for pid in sample_100["policy_id"]]
    ax.bar(followup_x, sample_100["bias"], width=width,
           yerr=sample_100["se"], color=C_SAMPLE_100, alpha=0.85, capsize=3,
           label="Higher-power follow-up ($n=100$)", edgecolor="white", linewidth=0.4)

    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([POLICY_LABELS[p] for p in POLICY_ORDER],
                       rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("Signed bias  $\\hat{y}-y$  (LLM minus ground truth)")
    ax.set_ylim(-0.3, 1.3)
    _style_axes(ax)
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9)
    fig.tight_layout()
    return _save(fig, "calib_bias.pdf")


def main() -> None:
    for fn in (plot_null_sixpolicy, plot_null_followup, plot_bias):
        out = fn()
        print(
            f"wrote {out.relative_to(REPO_ROOT)} and "
            f"{out.with_suffix('.png').relative_to(REPO_ROOT)}"
        )


if __name__ == "__main__":
    main()
