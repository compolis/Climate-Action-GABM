"""
Generate Probe 2 (reach asymmetry) figures for the seminar paper.

Three runs, identical except for the audience-reach probabilities of the two
political agents on the single climate policy ``ClimatePolicyID(3)`` (Ban
petrol cars), N=30 citizens, 4 simulated days, peer messaging off,
audience cap on:

  - S  symmetric           (p_R, p_G) = (1.00, 1.00)   20260425_125855
  - C1 reform-dominant     (p_R, p_G) = (1.00, 0.25)   20260425_132515
  - C3 green-dominant      (p_R, p_G) = (0.25, 1.00)   20260425_135538

Writes two PDFs into paper/figures/:

  - probe2_means.pdf                Mean opinion vs day, three conditions
                                    overlaid, with a +/- 1 SE band per
                                    condition computed from cross-agent
                                    dispersion, and a YouGov ground-truth
                                    reference line.
  - probe2_shares_by_condition.pdf  Population share line plot per condition
                                    (1x3 grid, support / neutral / against),
                                    same colour-marker convention as Probe 1.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = REPO_ROOT / "data" / "output" / "experiments"
FIG_DIR = Path(__file__).resolve().parent

POLICY_ID = "ClimatePolicyID(3)"
POLICY_NAME = "Ban petrol cars"

CONDITIONS = [
    # (key, display name, run dir, line colour)
    ("S", "Symmetric", "20260425_125855", "black"),
    ("C1", "Reform-dominant", "20260425_132515", "#1f77b4"),
    ("C3", "Green-dominant", "20260425_135538", "#2ca25f"),
]

C_SUPPORT = "#2ca25f"
C_NEUTRAL_LINE = "#7f7f7f"
C_AGAINST = "#de2d26"
C_GT = "#d62728"


def _save(fig, name: str) -> Path:
    out = FIG_DIR / name
    fig.savefig(out, format="pdf", bbox_inches="tight")
    plt.close(fig)
    return out


def _load_means(run_dir: str) -> pd.DataFrame:
    path = EXPERIMENTS / run_dir / "opinion_trajectories.csv"
    df = pd.read_csv(path)
    df = df[df["policy_id"] == POLICY_ID]
    g = df.groupby("day")["numeric"].agg(["mean", "std", "count"]).reset_index()
    g["se"] = g["std"] / g["count"] ** 0.5
    return g


def _load_shares(run_dir: str) -> pd.DataFrame:
    path = EXPERIMENTS / run_dir / "opinion_shares.csv"
    df = pd.read_csv(path)
    return df[df["policy_id"] == POLICY_ID].sort_values("day")


def _load_gt_mean(run_dir: str) -> float:
    path = EXPERIMENTS / run_dir / "ground_truth.csv"
    df = pd.read_csv(path)
    return float(df[df["policy_id"] == POLICY_ID]["ground_truth"].mean())


def plot_means() -> Path:
    fig, ax = plt.subplots(figsize=(7.0, 4.2))

    gt_mean = _load_gt_mean(CONDITIONS[0][2])
    ax.axhline(gt_mean, color=C_GT, linestyle="--", linewidth=1.0,
               label=f"YouGov ground truth ({gt_mean:+.2f})")

    for key, label, run_dir, colour in CONDITIONS:
        g = _load_means(run_dir)
        days = g["day"].to_numpy()
        mean = g["mean"].to_numpy()
        se = g["se"].to_numpy()
        ax.fill_between(days, mean - se, mean + se, color=colour, alpha=0.12,
                        linewidth=0)
        ax.plot(days, mean, color=colour, marker="o", linewidth=2, label=label)

    ax.set_xlabel("Simulation day")
    ax.set_ylabel(f"Mean opinion: {POLICY_NAME} ($-3$ to $+3$)")
    ax.set_xticks(range(0, 5))
    ax.set_ylim(-1.0, 2.0)
    ax.axhline(0, color="black", linewidth=0.5, alpha=0.3)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.legend(loc="lower right", framealpha=0.9, fontsize=9)
    fig.tight_layout()
    return _save(fig, "probe2_means.pdf")


def plot_shares_by_condition() -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.6), sharey=True)
    for ax, (key, label, run_dir, _colour) in zip(axes, CONDITIONS):
        sh = _load_shares(run_dir)
        days = sh["day"].to_numpy()
        ax.plot(days, sh["support_pct"].to_numpy(), color=C_SUPPORT,
                marker="o", linewidth=1.6, markersize=4, label="Support")
        ax.plot(days, sh["neutral_pct"].to_numpy(), color=C_NEUTRAL_LINE,
                marker="s", linewidth=1.6, markersize=4, label="Neutral")
        ax.plot(days, sh["against_pct"].to_numpy(), color=C_AGAINST,
                marker="^", linewidth=1.6, markersize=4, label="Against")
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Simulation day")
        ax.set_xticks(range(0, 5))
        ax.set_ylim(0, 100)
        ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    axes[0].set_ylabel(f"Share (%): {POLICY_NAME}")
    handles = [
        plt.Line2D([0], [0], color=C_SUPPORT, marker="o", linewidth=1.6,
                   label="Support (response $>0$)"),
        plt.Line2D([0], [0], color=C_NEUTRAL_LINE, marker="s", linewidth=1.6,
                   label="Neutral (response $=0$)"),
        plt.Line2D([0], [0], color=C_AGAINST, marker="^", linewidth=1.6,
                   label="Against (response $<0$)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3,
               bbox_to_anchor=(0.5, -0.04), frameon=False)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return _save(fig, "probe2_shares_by_condition.pdf")


def main() -> None:
    for fn in (plot_means, plot_shares_by_condition):
        out = fn()
        print(f"wrote {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
