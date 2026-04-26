"""
Generate Probe 1 (full simulation under symmetric broadcasts) figures for the
seminar paper.

Reads the saved CSVs under data/output/experiments/20260425_010615/ and writes
PDF and PNG versions of four figures into paper/figures/:

  - probe1_package_shares.pdf        Population shares (against / neutral /
                                     support) on the climate-policy package.
  - probe1_package_index.pdf         Mean pro-climate package index trajectory.
  - probe1_policy_shares.pdf         Population shares per policy (2x3 grid).
  - probe1_policy_index.pdf          Mean opinion per policy (2x3 grid).

Day 0 is ground-truth anchored, so the Day-0 share / mean equals the YouGov
panel mean by construction. The horizontal red dashed line on the index plots
makes that explicit; on the share plots the Day-0 column is itself the GT
reference and is annotated accordingly in the caption.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = REPO_ROOT / "data" / "output" / "experiments" / "20260425_010615"
FIG_DIR = Path(__file__).resolve().parent

POLICY_SHORT_NAMES = {
    "ClimatePolicyID(1)": "Renewable energy",
    "ClimatePolicyID(2)": "Ban fossil fuels",
    "ClimatePolicyID(3)": "Ban petrol cars",
    "ClimatePolicyID(4)": "Green housing",
    "ClimatePolicyID(5)": "Carbon tax",
    "ClimatePolicyID(6)": "Climate compensation",
}
POLICY_ORDER = list(POLICY_SHORT_NAMES.keys())

C_SUPPORT = "#2ca25f"
C_NEUTRAL = "#bdbdbd"
C_NEUTRAL_LINE = "#7f7f7f"
C_AGAINST = "#de2d26"
C_LINE = "black"
C_AGENT = "steelblue"
C_GT = "#d62728"
PNG_DPI = 300


def _save(fig, name: str) -> Path:
    out = FIG_DIR / name
    fig.savefig(out, format="pdf", bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), format="png", dpi=PNG_DPI,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def plot_package_shares() -> Path:
    df = pd.read_csv(RUN_DIR / "package_index_shares.csv").sort_values("day")
    days = df["day"].to_numpy()
    against = df["against_pct"].to_numpy()
    neutral = df["neutral_pct"].to_numpy()
    support = df["support_pct"].to_numpy()

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.plot(days, support, color=C_SUPPORT, marker="o", linewidth=2,
            label="Support (index $>0$)")
    ax.plot(days, neutral, color=C_NEUTRAL_LINE, marker="s", linewidth=2,
            label="Neutral (index $=0$)")
    ax.plot(days, against, color=C_AGAINST, marker="^", linewidth=2,
            label="Against (index $<0$)")
    ax.set_xlim(days.min(), days.max())
    ax.set_ylim(0, 100)
    ax.set_xlabel("Simulation day")
    ax.set_ylabel("Share of population (\\%)")
    ax.set_xticks(days)
    ax.legend(loc="lower left", frameon=True, fontsize=9)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    return _save(fig, "probe1_package_shares.pdf")


def plot_package_index() -> Path:
    df = pd.read_csv(RUN_DIR / "package_index_trajectories.csv")
    gt = pd.read_csv(RUN_DIR / "package_ground_truth.csv")
    gt_mean = gt["ground_truth"].mean()

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for _, sub in df.groupby("agent_id"):
        sub = sub.sort_values("day")
        ax.plot(sub["day"], sub["package_index"], color=C_AGENT, alpha=0.25,
                linewidth=0.8, marker="o", markersize=2.5)
    mean = df.groupby("day")["package_index"].mean()
    ax.plot(mean.index, mean.values, color=C_LINE, linewidth=2.2,
            marker="o", markersize=5, label="Population mean")
    ax.axhline(gt_mean, color=C_GT, linestyle="--", linewidth=1.4,
               label=f"YouGov ground-truth mean ({gt_mean:+.2f})")
    ax.axhline(0, color="grey", linewidth=0.6, alpha=0.5)
    ax.set_xlabel("Simulation day")
    ax.set_ylabel("Pro-climate package index ($-3$ to $+3$)")
    ax.set_ylim(-3.2, 3.2)
    ax.set_xticks(sorted(df["day"].unique()))
    ax.legend(loc="lower right", frameon=True, fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.4)
    return _save(fig, "probe1_package_index.pdf")


def plot_policy_shares() -> Path:
    df = pd.read_csv(RUN_DIR / "opinion_shares.csv")

    fig, axes = plt.subplots(2, 3, figsize=(11.5, 6.4), sharex=True, sharey=True)
    for ax, pid in zip(axes.flat, POLICY_ORDER):
        sub = df[df["policy_id"] == pid].sort_values("day")
        days = sub["day"].to_numpy()
        ax.plot(days, sub["support_pct"].to_numpy(), color=C_SUPPORT,
                marker="o", linewidth=1.6, markersize=4, label="Support")
        ax.plot(days, sub["neutral_pct"].to_numpy(), color=C_NEUTRAL_LINE,
                marker="s", linewidth=1.6, markersize=4, label="Neutral")
        ax.plot(days, sub["against_pct"].to_numpy(), color=C_AGAINST,
                marker="^", linewidth=1.6, markersize=4, label="Against")
        ax.set_title(POLICY_SHORT_NAMES[pid], fontsize=10)
        ax.set_xlim(days.min(), days.max())
        ax.set_ylim(0, 100)
        ax.set_xticks(days)
        ax.grid(True, axis="y", linestyle=":", alpha=0.4)

    for ax in axes[-1]:
        ax.set_xlabel("Simulation day")
    for ax in axes[:, 0]:
        ax.set_ylabel("Share of population (\\%)")

    handles = [
        plt.Line2D([0], [0], color=C_SUPPORT, marker="o", linewidth=1.6,
                   label="Support (response $>0$)"),
        plt.Line2D([0], [0], color=C_NEUTRAL_LINE, marker="s", linewidth=1.6,
                   label="Neutral (response $=0$)"),
        plt.Line2D([0], [0], color=C_AGAINST, marker="^", linewidth=1.6,
                   label="Against (response $<0$)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, -0.02), fontsize=10)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    return _save(fig, "probe1_policy_shares.pdf")


def plot_policy_index() -> Path:
    df = pd.read_csv(RUN_DIR / "opinion_trajectories.csv")
    gt = pd.read_csv(RUN_DIR / "ground_truth.csv")

    fig, axes = plt.subplots(2, 3, figsize=(11.5, 6.4), sharex=True, sharey=True)
    for ax, pid in zip(axes.flat, POLICY_ORDER):
        pdf = df[df["policy_id"] == pid]
        for _, sub in pdf.groupby("agent_id"):
            sub = sub.sort_values("day")
            ax.plot(sub["day"], sub["numeric"], color=C_AGENT, alpha=0.2,
                    linewidth=0.7, marker="o", markersize=2)
        mean = pdf.groupby("day")["numeric"].mean()
        ax.plot(mean.index, mean.values, color=C_LINE, linewidth=1.8,
                marker="o", markersize=4, label="Population mean")
        gt_mean = gt[gt["policy_id"] == pid]["ground_truth"].mean()
        ax.axhline(gt_mean, color=C_GT, linestyle="--", linewidth=1.2,
                   label=f"GT mean ({gt_mean:+.2f})")
        ax.axhline(0, color="grey", linewidth=0.5, alpha=0.5)
        ax.set_title(POLICY_SHORT_NAMES[pid], fontsize=10)
        ax.set_ylim(-3.2, 3.2)
        ax.set_xticks(sorted(pdf["day"].unique()))
        ax.grid(True, linestyle=":", alpha=0.4)
        ax.legend(loc="lower right", fontsize=7)

    for ax in axes[-1]:
        ax.set_xlabel("Simulation day")
    for ax in axes[:, 0]:
        ax.set_ylabel("Opinion ($-3$ to $+3$)")

    fig.tight_layout()
    return _save(fig, "probe1_policy_index.pdf")


def main() -> None:
    paths = [
        plot_package_shares(),
        plot_package_index(),
        plot_policy_shares(),
        plot_policy_index(),
    ]
    for p in paths:
        print(f"wrote {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
