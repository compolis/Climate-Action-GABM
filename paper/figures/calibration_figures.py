"""
Generate calibration (Section 5) figures for the seminar paper.

Two notebooks feed this section:

  - NB 22: 30 personas (same as the simulation probes) x 6 policies
           = 180 LLM calls. Source dir: 20260425_203841/
  - NB 23: 100 fresh personas (random_state=23, disjoint from the
           probe sample) x 2 policies (Carbon tax, Climate compensation)
           = 200 LLM calls. Source dir: 20260425_211242_persona/

Both notebooks call ``SurveyedCitizen.administer_survey`` with the same
survey-path stack used in Probes 1 and 2 (Claude Sonnet, two-step debias,
no extended thinking, T=0.5), with no memory, no broadcasts, no peers,
and ``opinion_history`` cleared per call.

Writes three PDFs into paper/figures/:

  - calib_null_nb22.pdf     6-panel grid, one panel per policy. Each
                            panel shows the permutation null distribution
                            of MAE under shuffled agent->GT pairing
                            (1000 shuffles per panel, regenerated here
                            for visual consistency with NB 23) with the
                            real MAE marked as a vertical line.
  - calib_null_nb23.pdf     2-panel grid for Carbon tax and Climate
                            compensation at n=100 with B=1000 shuffles,
                            same null/real overlay.
  - calib_bias.pdf          Per-policy signed bias (LLM - GT) bar chart.
                            Six bars from NB 22 with +/- 1 SE. The two
                            NB 23 estimates overlaid as a second colour.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CALIB_DIR = REPO_ROOT / "data" / "output" / "calibration"
FIG_DIR = Path(__file__).resolve().parent

NB22_RUN = "20260425_203841"
NB23_RUN = "20260425_211242_persona"

POLICY_LABELS = {
    "ClimatePolicyID(1)": "Renewable energy",
    "ClimatePolicyID(2)": "Ban fossil fuels",
    "ClimatePolicyID(3)": "Ban petrol cars",
    "ClimatePolicyID(4)": "Green housing",
    "ClimatePolicyID(5)": "Carbon tax",
    "ClimatePolicyID(6)": "Climate compensation",
}
POLICY_ORDER = list(POLICY_LABELS.keys())
NB23_POLICIES = ["ClimatePolicyID(5)", "ClimatePolicyID(6)"]

C_NB22 = "#1f77b4"
C_NB23 = "#d95f02"
C_NULL = "#999999"
C_REAL = "#000000"

N_PERMS_FIG = 1000
RNG_SEED = 7


def _save(fig, name: str) -> Path:
    out = FIG_DIR / name
    fig.savefig(out, format="pdf", bbox_inches="tight")
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


def _null_panel(ax, llm: np.ndarray, gt: np.ndarray, title: str,
                rng: np.random.Generator, show_xlabel: bool,
                show_ylabel: bool) -> None:
    real_mae, perms = _permutation_mae(llm, gt, N_PERMS_FIG, rng)
    p_mae = float(np.mean(perms <= real_mae))
    ax.hist(perms, bins=30, color=C_NULL, alpha=0.7, edgecolor="white",
            linewidth=0.4)
    ax.axvline(real_mae, color=C_REAL, linewidth=1.6,
               label=f"Real MAE = {real_mae:.2f}")
    ax.set_title(f"{title}\n$p_{{\\mathrm{{MAE}}}}={p_mae:.3f}$", fontsize=9)
    if show_xlabel:
        ax.set_xlabel("MAE under shuffled pairing")
    if show_ylabel:
        ax.set_ylabel("Permutation count")
    ax.tick_params(axis="both", labelsize=8)
    ax.legend(fontsize=7, loc="upper right", framealpha=0.85)


def plot_null_nb22() -> Path:
    df = _load_raw(NB22_RUN)
    rng = np.random.default_rng(RNG_SEED)
    fig, axes = plt.subplots(2, 3, figsize=(11.0, 6.2))
    for idx, pid in enumerate(POLICY_ORDER):
        sub = df[df["policy_id"] == pid]
        llm = sub["llm"].to_numpy(dtype=float)
        gt = sub["gt"].to_numpy(dtype=float)
        ax = axes[idx // 3, idx % 3]
        _null_panel(ax, llm, gt, POLICY_LABELS[pid], rng,
                    show_xlabel=(idx // 3 == 1),
                    show_ylabel=(idx % 3 == 0))
    fig.suptitle(f"NB 22 permutation null on MAE  ($n=30$, $B={N_PERMS_FIG}$)",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return _save(fig, "calib_null_nb22.pdf")


def plot_null_nb23() -> Path:
    df = _load_raw(NB23_RUN)
    rng = np.random.default_rng(RNG_SEED + 1)
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.6))
    for ax, pid in zip(axes, NB23_POLICIES):
        sub = df[df["policy_id"] == pid]
        llm = sub["llm"].to_numpy(dtype=float)
        gt = sub["gt"].to_numpy(dtype=float)
        _null_panel(ax, llm, gt, POLICY_LABELS[pid], rng,
                    show_xlabel=True, show_ylabel=True)
    fig.suptitle(f"NB 23 permutation null on MAE  ($n=100$, $B={N_PERMS_FIG}$)",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return _save(fig, "calib_null_nb23.pdf")


def plot_bias() -> Path:
    nb22 = _per_policy_bias_se(_load_raw(NB22_RUN))
    nb23 = _per_policy_bias_se(_load_raw(NB23_RUN))

    nb22 = nb22.set_index("policy_id").loc[POLICY_ORDER].reset_index()
    nb23 = nb23.set_index("policy_id").loc[NB23_POLICIES].reset_index()

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    x = np.arange(len(POLICY_ORDER))
    width = 0.36

    ax.bar(x - width / 2, nb22["bias"], width=width,
           yerr=nb22["se"], color=C_NB22, alpha=0.85, capsize=3,
           label=f"NB 22 ($n=30$)", edgecolor="white", linewidth=0.4)

    nb23_x = [POLICY_ORDER.index(pid) + width / 2 for pid in nb23["policy_id"]]
    ax.bar(nb23_x, nb23["bias"], width=width,
           yerr=nb23["se"], color=C_NB23, alpha=0.85, capsize=3,
           label=f"NB 23 ($n=100$)", edgecolor="white", linewidth=0.4)

    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([POLICY_LABELS[p] for p in POLICY_ORDER],
                       rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("Signed bias  $\\hat{y}-y$  (LLM minus ground truth)")
    ax.set_ylim(-0.3, 1.3)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9)
    fig.tight_layout()
    return _save(fig, "calib_bias.pdf")


def main() -> None:
    for fn in (plot_null_nb22, plot_null_nb23, plot_bias):
        out = fn()
        print(f"wrote {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
