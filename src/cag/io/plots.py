"""
Result plots for Climate-Action-GABM.

Extracted from ``cag.abm.sim`` in the 2026-06-22 refactor. All names are
re-exported from ``cag.abm.sim`` for backwards compatibility — notebooks
and tests can keep importing from either location.
"""
import logging
from pathlib import Path

from cag.abm.attributes.opinion import ClimatePolicyID


def _policy_short_names():
    """Build a policy_id -> readable short name lookup."""
    return {
        str(ClimatePolicyID.RENEWABLE_ENERGY): "Renewable Energy",
        str(ClimatePolicyID.BAN_FOSSIL_FUEL): "Ban Fossil Fuels",
        str(ClimatePolicyID.BAN_PETROL_CARS): "Ban Petrol Cars",
        str(ClimatePolicyID.GREEN_HOUSING): "Green Housing",
        str(ClimatePolicyID.CARBON_TAX): "Carbon Tax",
        str(ClimatePolicyID.CLIMATE_COMPENSATION): "Climate Compensation",
    }


def plot_opinion_trajectories(results, output_path=None):
    """Plot opinion trajectories over time."""
    import matplotlib.pyplot as plt

    df = results["opinion_trajectories"]
    if df.empty:
        logging.warning("No opinion data to plot.")
        return

    policies = df["policy_id"].unique()
    n_policies = len(policies)
    ncols = min(n_policies, 3)
    nrows = (n_policies + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows), squeeze=False)

    policy_names = _policy_short_names()

    for i, pid in enumerate(policies):
        ax = axes[i // ncols, i % ncols]
        pdf = df[df["policy_id"] == pid]

        for agent_id in pdf["agent_id"].unique():
            agent_data = pdf[pdf["agent_id"] == agent_id].sort_values("day")
            ax.plot(agent_data["day"], agent_data["numeric"],
                    alpha=0.15, color="steelblue", linewidth=0.8)

        mean = pdf.groupby("day")["numeric"].mean()
        ax.plot(mean.index, mean.values, color="black", linewidth=2, label="Mean")

        ax.set_xlabel("Day")
        ax.set_ylabel("Opinion (-3 to +3)")
        ax.set_ylim(-3.5, 3.5)
        ax.set_title(policy_names.get(pid, str(pid))[:50])
        ax.legend()

    # Hide unused subplots
    for i in range(n_policies, nrows * ncols):
        axes[i // ncols, i % ncols].set_visible(False)

    fig.suptitle("Opinion Trajectories", fontsize=13)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()

    return fig


def plot_opinion_shares(results, output_path=None):
    """Plot support, neutral, and against shares over time."""
    import matplotlib.pyplot as plt

    # Late import: aggregator currently lives in cag.abm.sim; will move to
    # cag.io.aggregators in Phase B of the sim.py decomposition.
    from cag.io.aggregators import build_opinion_shares

    share_df = build_opinion_shares(results)
    if share_df.empty:
        logging.warning("No opinion share data to plot.")
        return

    policies = share_df["policy_id"].unique()
    n_policies = len(policies)
    ncols = min(n_policies, 3)
    nrows = (n_policies + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows), squeeze=False)
    policy_names = _policy_short_names()

    for i, pid in enumerate(policies):
        ax = axes[i // ncols, i % ncols]
        pdf = share_df[share_df["policy_id"] == pid].sort_values("day")

        ax.plot(pdf["day"], pdf["support_pct"], color="forestgreen", linewidth=2, marker="o", label="Support (+1 to +3)")
        ax.plot(pdf["day"], pdf["neutral_pct"], color="dimgray", linewidth=2, marker="o", label="Neutral (0)")
        ax.plot(pdf["day"], pdf["against_pct"], color="firebrick", linewidth=2, marker="o", label="Against (-3 to -1)")

        ax.set_xlabel("Day")
        ax.set_ylabel("Share of agents (%)")
        ax.set_ylim(0, 100)
        ax.set_title(policy_names.get(pid, str(pid))[:50])
        ax.legend()

    for i in range(n_policies, nrows * ncols):
        axes[i // ncols, i % ncols].set_visible(False)

    fig.suptitle("Opinion Shares", fontsize=13)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()

    return fig


def plot_package_index_trajectories(results, output_path=None):
    """Plot package-index trajectories over time when package data is present."""
    import matplotlib.pyplot as plt

    df = results.get("package_index_trajectories")
    if df is None or df.empty:
        logging.warning("No package index data to plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 5))

    for agent_id in df["agent_id"].unique():
        agent_data = df[df["agent_id"] == agent_id].sort_values("day")
        ax.plot(
            agent_data["day"],
            agent_data["package_index"],
            alpha=0.15,
            color="steelblue",
            linewidth=0.8,
        )

    mean = df.groupby("day")["package_index"].mean()
    ax.plot(mean.index, mean.values, color="black", linewidth=2, label="Mean")

    package_ground_truth_df = results.get("package_ground_truth")
    if package_ground_truth_df is not None and not package_ground_truth_df.empty:
        gt_mean = package_ground_truth_df["ground_truth"].mean()
        ax.axhline(
            gt_mean,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"Ground truth mean ({gt_mean:+.2f})",
        )

    ax.set_xlabel("Day")
    ax.set_ylabel("Package index (-3 to +3)")
    ax.set_ylim(-3.5, 3.5)
    ax.set_title("Package Index Trajectory")
    ax.legend()
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()

    return fig


def plot_package_index_shares(results, output_path=None):
    """Plot support, neutral, and against shares for the package index over time."""
    import matplotlib.pyplot as plt

    from cag.io.aggregators import build_package_index_shares

    share_df = build_package_index_shares(results)
    if share_df.empty:
        logging.warning("No package index share data to plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    pdf = share_df.sort_values("day")

    ax.plot(pdf["day"], pdf["support_pct"], color="forestgreen", linewidth=2, marker="o", label="Support (> 0)")
    ax.plot(pdf["day"], pdf["neutral_pct"], color="dimgray", linewidth=2, marker="o", label="Neutral (0)")
    ax.plot(pdf["day"], pdf["against_pct"], color="firebrick", linewidth=2, marker="o", label="Against (< 0)")

    ax.set_xlabel("Day")
    ax.set_ylabel("Share of agents (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Package Index Shares")
    ax.legend()
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()

    return fig


def plot_package_index_by_bucket(results, output_path=None):
    """2x2-style panel grid: package-index spaghetti+mean per bucket."""
    import matplotlib.pyplot as plt

    from cag.io.aggregators import (
        _attach_bucket,
        _sorted_buckets,
        build_package_index_by_bucket,
    )

    by_bucket = build_package_index_by_bucket(results)
    traj = results.get("package_index_trajectories")
    attrs = results.get("agent_attributes")
    if (
        by_bucket.empty or traj is None or traj.empty
        or attrs is None or attrs.empty
    ):
        logging.warning("No bucketed package data to plot.")
        return None

    joined = _attach_bucket(traj, attrs)
    present = _sorted_buckets(joined["political_exposure"].dropna().unique())
    if not present:
        logging.warning("No buckets present for package_index_by_bucket plot.")
        return None

    n = len(present)
    ncols = min(n, 2)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(7 * ncols, 4.5 * nrows), squeeze=False)

    gt_mean = None
    pkg_gt = results.get("package_ground_truth")
    if pkg_gt is not None and not pkg_gt.empty:
        gt_mean = float(pkg_gt["ground_truth"].mean())

    for i, bucket in enumerate(present):
        ax = axes[i // ncols, i % ncols]
        bdf = joined[joined["political_exposure"] == bucket]
        for aid in bdf["agent_id"].unique():
            adata = bdf[bdf["agent_id"] == aid].sort_values("day")
            ax.plot(adata["day"], adata["package_index"],
                    alpha=0.18, color="steelblue", linewidth=0.8)
        mean = bdf.groupby("day")["package_index"].mean()
        ax.plot(mean.index, mean.values, color="black", linewidth=2, label="Mean")
        if gt_mean is not None:
            ax.axhline(gt_mean, color="red", linestyle="--", linewidth=1.2,
                       label=f"GT mean ({gt_mean:+.2f})")
        ax.set_title(f"{bucket} (n={bdf['agent_id'].nunique()})")
        ax.set_xlabel("Day")
        ax.set_ylabel("Package index (-3..+3)")
        ax.set_ylim(-3.5, 3.5)
        ax.legend(loc="best", fontsize=8)

    for j in range(n, nrows * ncols):
        axes[j // ncols, j % ncols].set_visible(False)

    fig.suptitle("Package Index by Political-Exposure Bucket", fontsize=13)
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()
    return fig


def plot_opinion_shares_by_bucket(results, output_path=None):
    """Grid of (policy x bucket) panels: support/neutral/against lines."""
    import matplotlib.pyplot as plt

    from cag.io.aggregators import _sorted_buckets, build_opinion_shares_by_bucket

    share_df = build_opinion_shares_by_bucket(results)
    if share_df.empty:
        logging.warning("No bucketed opinion-share data to plot.")
        return None

    policies = list(share_df["policy_id"].unique())
    buckets = _sorted_buckets(share_df["political_exposure"].dropna().unique())
    if not policies or not buckets:
        logging.warning("Insufficient (policy x bucket) cells to plot.")
        return None

    policy_names = _policy_short_names()
    nrows, ncols = len(policies), len(buckets)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(4 * ncols, 3.2 * nrows), squeeze=False,
    )

    for i, pid in enumerate(policies):
        for j, bucket in enumerate(buckets):
            ax = axes[i, j]
            cell = share_df[
                (share_df["policy_id"] == pid)
                & (share_df["political_exposure"] == bucket)
            ].sort_values("day")
            if cell.empty:
                ax.set_visible(False)
                continue
            ax.plot(cell["day"], cell["support_pct"], color="forestgreen",
                    marker="o", label="Support")
            ax.plot(cell["day"], cell["neutral_pct"], color="dimgray",
                    marker="o", label="Neutral")
            ax.plot(cell["day"], cell["against_pct"], color="firebrick",
                    marker="o", label="Against")
            ax.set_ylim(0, 100)
            if i == 0:
                ax.set_title(bucket)
            if j == 0:
                ax.set_ylabel(policy_names.get(pid, str(pid))[:25], fontsize=9)
            if i == nrows - 1:
                ax.set_xlabel("Day")
            if i == 0 and j == ncols - 1:
                ax.legend(fontsize=7, loc="best")

    fig.suptitle("Opinion Shares by (Policy x Bucket)", fontsize=13)
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()
    return fig


def plot_gap_widening(results, output_path=None):
    """Bold package-index (A_mean - B_mean) line, thin per-policy traces."""
    import matplotlib.pyplot as plt

    from cag.io.aggregators import (
        _attach_bucket,
        build_opinion_shares_by_bucket,
        build_package_index_by_bucket,
    )

    by_bucket = build_package_index_by_bucket(results)
    opinion_by_bucket = build_opinion_shares_by_bucket(results)
    if by_bucket.empty:
        logging.warning("No bucketed package data for gap plot.")
        return None

    has_a = (by_bucket["political_exposure"] == "A-only").any()
    has_b = (by_bucket["political_exposure"] == "B-only").any()
    if not (has_a and has_b):
        logging.warning(
            "gap_widening needs both A-only and B-only buckets; skipping."
        )
        return None

    pivot = by_bucket.pivot_table(
        index="day", columns="political_exposure", values="mean",
    )
    gap_pkg = (pivot.get("A-only") - pivot.get("B-only")).sort_index()

    fig, ax = plt.subplots(figsize=(8, 5))

    # Per-policy gap traces (thin grey)
    if not opinion_by_bucket.empty:
        # Use the mean numeric per (policy, day, bucket) computed by
        # re-grouping the original opinion_trajectories; the share frame
        # already collapses to share counts so we recompute means here.
        traj = results.get("opinion_trajectories")
        attrs = results.get("agent_attributes")
        if traj is not None and not traj.empty and attrs is not None:
            joined = _attach_bucket(traj, attrs)
            per_pol = (
                joined.groupby(["policy_id", "day", "political_exposure"])
                ["numeric"].mean().reset_index()
            )
            for pid in per_pol["policy_id"].unique():
                sub = per_pol[per_pol["policy_id"] == pid].pivot_table(
                    index="day", columns="political_exposure", values="numeric",
                )
                if "A-only" in sub.columns and "B-only" in sub.columns:
                    g = (sub["A-only"] - sub["B-only"]).sort_index()
                    ax.plot(g.index, g.values, color="grey",
                            alpha=0.45, linewidth=1.0)

    ax.plot(gap_pkg.index, gap_pkg.values,
            color="black", linewidth=2.5, marker="o",
            label="Package index gap (A_mean - B_mean)")
    ax.axhline(0, color="darkgrey", linestyle=":", linewidth=0.8)
    ax.set_xlabel("Day")
    ax.set_ylabel("A-only mean minus B-only mean")
    ax.set_title("Persuasion-Signal Gap-Widening")
    ax.legend(loc="best", fontsize=9)
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()
    return fig


def plot_network_graph(results, output_path=None):
    """Render the peer graph from network_snapshot, coloured by bucket."""
    import matplotlib.pyplot as plt

    snap = results.get("network_snapshot")
    if not snap or not snap.get("nodes"):
        logging.warning("No network snapshot to plot.")
        return None

    try:
        import networkx as nx  # local import: optional for tests that skip plots
    except ImportError:  # pragma: no cover
        logging.warning("networkx not available for network plot.")
        return None

    G = nx.Graph()
    color_map = {
        "A-only": "forestgreen", "B-only": "firebrick",
        "both": "goldenrod", "neither": "lightgrey",
    }
    node_colors = []
    sizes = []
    for node in snap["nodes"]:
        G.add_node(node["id"])
        node_colors.append(color_map.get(node["bucket"], "lightblue"))
        sizes.append(40 + 18 * int(node["degree"]))
    for u, v in snap["edges"]:
        G.add_edge(u, v)

    pos = nx.spring_layout(G, seed=42)
    fig, ax = plt.subplots(figsize=(9, 7))
    nx.draw_networkx_edges(G, pos, alpha=0.25, width=0.6, ax=ax)
    nx.draw_networkx_nodes(
        G, pos, node_color=node_colors, node_size=sizes,
        edgecolors="black", linewidths=0.4, ax=ax,
    )
    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=c, markersize=8, label=b)
        for b, c in color_map.items()
    ]
    ax.legend(handles=legend_handles, loc="best", fontsize=8)
    ax.set_title("Peer Network (nodes coloured by political_exposure)")
    ax.set_axis_off()
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()
    return fig


def plot_calibration_by_policy(results, output_path=None):
    """Per-policy scatter of last-day LLM opinion vs ground truth + diagonal."""
    import matplotlib.pyplot as plt

    traj = results.get("opinion_trajectories")
    gt = results.get("ground_truth")
    if traj is None or traj.empty or gt is None or gt.empty:
        logging.warning("No data for calibration plot.")
        return None

    policies = list(traj["policy_id"].unique())
    if not policies:
        return None
    last_day = int(traj["day"].max())
    last = traj[traj["day"] == last_day]

    ncols = min(len(policies), 3)
    nrows = (len(policies) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows), squeeze=False)
    policy_names = _policy_short_names()

    for i, pid in enumerate(policies):
        ax = axes[i // ncols, i % ncols]
        merged = last[last["policy_id"] == pid].merge(
            gt[gt["policy_id"] == pid], on=["agent_id", "policy_id"], how="inner",
        )
        if merged.empty:
            ax.set_visible(False)
            continue
        try:
            rho = float(merged["numeric"].corr(merged["ground_truth"], method="spearman"))
        except Exception:  # noqa: BLE001
            rho = float("nan")
        ax.scatter(merged["ground_truth"], merged["numeric"], alpha=0.6)
        ax.plot([-3, 3], [-3, 3], color="grey", linestyle="--", linewidth=0.8)
        ax.set_xlim(-3.5, 3.5)
        ax.set_ylim(-3.5, 3.5)
        ax.set_xlabel("Ground truth")
        ax.set_ylabel(f"LLM opinion (day {last_day})")
        ax.set_title(f"{policy_names.get(pid, str(pid))[:30]} (rho={rho:+.2f})")

    for j in range(len(policies), nrows * ncols):
        axes[j // ncols, j % ncols].set_visible(False)

    fig.suptitle("Calibration: LLM Opinion vs Ground Truth (last day)", fontsize=13)
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()
    return fig


def save_result_plots(results, out_path):
    """Write the standard PNG outputs for a completed run."""
    out_path = Path(out_path)
    plot_paths = {}

    trajectory_plot_path = out_path / "opinion_trajectories.png"
    if plot_opinion_trajectories(results, output_path=trajectory_plot_path) is not None:
        plot_paths["opinion_trajectories"] = trajectory_plot_path

    shares_plot_path = out_path / "opinion_shares.png"
    if plot_opinion_shares(results, output_path=shares_plot_path) is not None:
        plot_paths["opinion_shares"] = shares_plot_path

    package_plot_path = out_path / "package_index_trajectories.png"
    if plot_package_index_trajectories(results, output_path=package_plot_path) is not None:
        plot_paths["package_index_trajectories"] = package_plot_path

    package_shares_plot_path = out_path / "package_index_shares.png"
    if plot_package_index_shares(results, output_path=package_shares_plot_path) is not None:
        plot_paths["package_index_shares"] = package_shares_plot_path

    bucket_path = out_path / "package_index_by_bucket.png"
    if plot_package_index_by_bucket(results, output_path=bucket_path) is not None:
        plot_paths["package_index_by_bucket"] = bucket_path

    osbucket_path = out_path / "opinion_shares_by_bucket.png"
    if plot_opinion_shares_by_bucket(results, output_path=osbucket_path) is not None:
        plot_paths["opinion_shares_by_bucket"] = osbucket_path

    gap_path = out_path / "gap_widening.png"
    if plot_gap_widening(results, output_path=gap_path) is not None:
        plot_paths["gap_widening"] = gap_path

    network_path = out_path / "network_graph.png"
    if plot_network_graph(results, output_path=network_path) is not None:
        plot_paths["network_graph"] = network_path

    calib_path = out_path / "calibration_by_policy.png"
    if plot_calibration_by_policy(results, output_path=calib_path) is not None:
        plot_paths["calibration_by_policy"] = calib_path

    return plot_paths
