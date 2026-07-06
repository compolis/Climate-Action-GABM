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


def _save_or_show(fig, output_path):
    import matplotlib.pyplot as plt
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()
    return fig


def _day0_is_anchor(results):
    """True when Day 0 is a ground-truth anchor (not a simulated opinion)."""
    cfg = results.get("config") or {}
    if not isinstance(cfg, dict):
        return False
    return cfg.get("day0_anchor") in ("ground_truth", "ground_truth_with_rationale")


def _mean_ci_by_day(df, value_col):
    """Return (mean, lo, hi) Series indexed by day; 95% normal-approx CI."""
    g = df.groupby("day")[value_col]
    m = g.mean()
    n = g.count()
    sem = (g.std(ddof=1) / n.pow(0.5)).fillna(0.0)
    return m, m - 1.96 * sem, m + 1.96 * sem


def _mean_line_with_anchor(ax, mean_series, *, anchor, color="black",
                           linewidth=2, label="Mean",
                           anchor_label="Day-0 GT anchor"):
    """Plot a mean trajectory. When ``anchor`` and Day 0 is present, render
    Day 0 as a distinct diamond marker and start the line at Day 1 (Day 0 is
    an injected ground-truth anchor, not a simulated opinion)."""
    s = mean_series.sort_index()
    if anchor and 0 in s.index and len(s.index) > 1:
        ax.scatter([0], [s.loc[0]], color=color, marker="D", s=45, zorder=5,
                   edgecolors="black", linewidths=0.5, label=anchor_label)
        rest = s[s.index >= 1]
        ax.plot(rest.index, rest.values, color=color, linewidth=linewidth,
                marker="o", markersize=4, label=label)
    else:
        ax.plot(s.index, s.values, color=color, linewidth=linewidth,
                marker="o", markersize=4, label=label)


def _ci_band(ax, m, lo, hi, *, anchor, color="black", alpha=0.12, label=None):
    idx = m.index
    mask = (idx >= 1) if anchor else (idx >= idx.min())
    ax.fill_between(idx[mask], lo.values[mask], hi.values[mask],
                    color=color, alpha=alpha, label=label)


def _per_bucket_gt_means(results):
    """dict bucket -> mean package ground truth, plus 'TOTAL'."""
    gt = results.get("package_ground_truth")
    attrs = results.get("agent_attributes")
    out = {}
    if gt is None or gt.empty or attrs is None or attrs.empty:
        return out
    bmap = dict(zip(attrs["agent_id"], attrs["political_exposure"]))
    g = gt.copy()
    g["political_exposure"] = g["agent_id"].map(bmap)
    for bucket, sub in g.groupby("political_exposure"):
        out[bucket] = float(sub["ground_truth"].mean())
    out["TOTAL"] = float(gt["ground_truth"].mean())
    return out


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
    anchor = _day0_is_anchor(results)

    for i, pid in enumerate(policies):
        ax = axes[i // ncols, i % ncols]
        pdf = df[df["policy_id"] == pid]

        for agent_id in pdf["agent_id"].unique():
            agent_data = pdf[pdf["agent_id"] == agent_id].sort_values("day")
            ax.plot(agent_data["day"], agent_data["numeric"],
                    alpha=0.15, color="steelblue", linewidth=0.8)

        m, lo, hi = _mean_ci_by_day(pdf, "numeric")
        _ci_band(ax, m, lo, hi, anchor=anchor)
        _mean_line_with_anchor(ax, m, anchor=anchor)

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

    anchor = _day0_is_anchor(results)
    m, lo, hi = _mean_ci_by_day(df, "package_index")
    _ci_band(ax, m, lo, hi, anchor=anchor, label="95% CI")
    _mean_line_with_anchor(ax, m, anchor=anchor)

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

    gt_bucket = _per_bucket_gt_means(results)
    gt_total = gt_bucket.get("TOTAL")

    for i, bucket in enumerate(present):
        ax = axes[i // ncols, i % ncols]
        bdf = joined[joined["political_exposure"] == bucket]
        for aid in bdf["agent_id"].unique():
            adata = bdf[bdf["agent_id"] == aid].sort_values("day")
            ax.plot(adata["day"], adata["package_index"],
                    alpha=0.18, color="steelblue", linewidth=0.8)
        mean = bdf.groupby("day")["package_index"].mean()
        # Plain markered mean line (Day 0 included). The Day-0 anchor diamond
        # is dropped in bucket panels because the Bucket GT line already marks
        # that value; the diamond is kept in plot_package_index_trajectories.
        ax.plot(mean.index, mean.values, color="black", marker="o",
                markersize=5, linewidth=2, label="Mean")
        gmt = gt_bucket.get(bucket)
        if gmt is not None:
            ax.axhline(gmt, color="red", linestyle="--", linewidth=1.4,
                       label=f"Bucket GT ({gmt:+.2f})")
        if gt_total is not None:
            ax.axhline(gt_total, color="dimgray", linestyle="-.", linewidth=1.2,
                       alpha=0.9, label=f"Pop GT ({gt_total:+.2f})")
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


def plot_opinion_trajectories_by_bucket(results, output_path=None):
    """Per-policy figure: bucket MEAN opinion lines + per-bucket GT refs."""
    import matplotlib.pyplot as plt

    from cag.io.aggregators import _attach_bucket, _sorted_buckets

    traj = results.get("opinion_trajectories")
    attrs = results.get("agent_attributes")
    gt = results.get("ground_truth")
    if traj is None or traj.empty or attrs is None or attrs.empty:
        logging.warning("No data for opinion_trajectories_by_bucket.")
        return None
    joined = _attach_bucket(traj, attrs)
    buckets = _sorted_buckets(joined["political_exposure"].dropna().unique())
    policies = list(joined["policy_id"].unique())
    if not buckets or not policies:
        return None
    anchor = _day0_is_anchor(results)

    gt_means = {}
    if gt is not None and not gt.empty:
        bmap = dict(zip(attrs["agent_id"], attrs["political_exposure"]))
        gj = gt.copy()
        gj["political_exposure"] = gj["agent_id"].map(bmap)
        for (pid, b), sub in gj.groupby(["policy_id", "political_exposure"]):
            gt_means[(str(pid), b)] = float(sub["ground_truth"].mean())

    colors = plt.cm.tab10.colors
    n = len(policies)
    ncols = min(n, 3)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 4.5 * nrows), squeeze=False)
    names = _policy_short_names()

    for i, pid in enumerate(policies):
        ax = axes[i // ncols, i % ncols]
        pdf = joined[joined["policy_id"] == pid]
        for bi, b in enumerate(buckets):
            bsub = pdf[pdf["political_exposure"] == b]
            if bsub.empty:
                continue
            c = colors[bi % len(colors)]
            m = bsub.groupby("day")["numeric"].mean()
            _mean_line_with_anchor(ax, m, anchor=anchor, color=c, label=b,
                                   anchor_label=None)
            gmt = gt_means.get((str(pid), b))
            if gmt is not None:
                ax.axhline(gmt, color=c, linestyle=":", linewidth=0.8, alpha=0.6)
        ax.set_ylim(-3.5, 3.5)
        ax.set_title(names.get(str(pid), str(pid))[:30])
        ax.set_xlabel("Day")
        ax.set_ylabel("Opinion (-3..+3)")
        ax.legend(fontsize=7, loc="best")

    for j in range(n, nrows * ncols):
        axes[j // ncols, j % ncols].set_visible(False)
    fig.suptitle("Opinion Trajectories by Bucket (mean per bucket)", fontsize=13)
    plt.tight_layout()
    return _save_or_show(fig, output_path)


def plot_polarization(results, output_path=None):
    """Std of the package index over time (dispersion / polarization)."""
    import matplotlib.pyplot as plt

    df = results.get("package_index_trajectories")
    if df is None or df.empty:
        return None
    std = df.groupby("day")["package_index"].std(ddof=1)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(std.index, std.values, color="purple", marker="o", linewidth=2,
            label="Std dev")
    ax.set_xlabel("Day")
    ax.set_ylabel("Package-index std (spread)")
    ax.set_ylim(bottom=0)
    ax.set_title("Opinion Dispersion / Polarization over Time")
    ax.legend()
    plt.tight_layout()
    return _save_or_show(fig, output_path)


def plot_drift_from_gt(results, output_path=None):
    """Mean(index - ground truth) over time, overall + per bucket."""
    import matplotlib.pyplot as plt

    from cag.io.aggregators import _attach_bucket, _sorted_buckets

    traj = results.get("package_index_trajectories")
    gt = results.get("package_ground_truth")
    attrs = results.get("agent_attributes")
    if traj is None or traj.empty or gt is None or gt.empty:
        return None
    gmap = dict(zip(gt["agent_id"], gt["ground_truth"].astype(float)))
    d = traj.copy()
    d["gt"] = d["agent_id"].map(gmap)
    d = d.dropna(subset=["gt"])
    if d.empty:
        return None
    d["drift"] = d["package_index"] - d["gt"]

    fig, ax = plt.subplots(figsize=(8, 5))
    overall = d.groupby("day")["drift"].mean()
    ax.plot(overall.index, overall.values, color="black", linewidth=2.5,
            marker="o", label="All")
    if attrs is not None and not attrs.empty:
        dj = _attach_bucket(d, attrs)
        colors = plt.cm.tab10.colors
        for bi, b in enumerate(_sorted_buckets(dj["political_exposure"].dropna().unique())):
            sub = dj[dj["political_exposure"] == b].groupby("day")["drift"].mean()
            ax.plot(sub.index, sub.values, color=colors[bi % len(colors)],
                    alpha=0.8, marker=".", label=b)
    ax.axhline(0, color="grey", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Day")
    ax.set_ylabel("Mean(index - ground truth)")
    ax.set_title("Drift from Ground Truth over Time")
    ax.legend(fontsize=8)
    plt.tight_layout()
    return _save_or_show(fig, output_path)


def plot_opinion_ridgeline(results, output_path=None):
    """Joyplot: the package-index distribution for each day (Day 0 -> Day N)."""
    import numpy as np
    import matplotlib.pyplot as plt

    df = results.get("package_index_trajectories")
    if df is None or df.empty:
        return None
    days = sorted(int(d) for d in df["day"].unique())
    xs = np.linspace(-3.2, 3.2, 200)

    def _kde(vals):
        vals = np.asarray(vals, dtype=float)
        if len(vals) < 2 or float(np.std(vals)) == 0.0:
            y = np.zeros_like(xs)
            if len(vals):
                y[int(np.argmin(np.abs(xs - float(np.mean(vals)))))] = 1.0
            return y
        h = max(1.06 * float(np.std(vals)) * len(vals) ** (-1 / 5), 0.15)
        d = (xs[None, :] - vals[:, None]) / h
        return np.exp(-0.5 * d ** 2).sum(axis=0) / (len(vals) * h * np.sqrt(2 * np.pi))

    fig, ax = plt.subplots(figsize=(8, 1.1 * len(days) + 2))
    for i, day in enumerate(days):
        vals = df[df["day"] == day]["package_index"].values
        y = _kde(vals)
        y = y / (y.max() or 1.0) * 0.9
        color = plt.cm.viridis(i / max(1, len(days) - 1))
        ax.fill_between(xs, i, i + y, color=color, alpha=0.8, linewidth=0.8,
                        edgecolor="white")
        ax.text(-3.35, i + 0.05, f"Day {day}", va="bottom", ha="right", fontsize=8)
    ax.axvline(0, color="grey", linestyle=":", linewidth=0.8)
    ax.set_yticks([])
    ax.set_xlim(-3.6, 3.5)
    ax.set_xlabel("Package index (-3..+3)")
    ax.set_title("Opinion Distribution Evolution (ridgeline)")
    plt.tight_layout()
    return _save_or_show(fig, output_path)


def plot_network_before_after(results, output_path=None):
    """Two-panel peer graph coloured by opinion at Day 0 vs Day N.

    Node colour = package index, size = degree, black ring = reached by a
    political agent. The money shot for centrality-targeting runs.
    """
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    snap = results.get("network_snapshot")
    traj = results.get("package_index_trajectories")
    attrs = results.get("agent_attributes")
    if not snap or not snap.get("nodes") or traj is None or traj.empty:
        return None
    try:
        import networkx as nx
    except ImportError:  # pragma: no cover
        return None

    G = nx.Graph()
    for node in snap["nodes"]:
        G.add_node(node["id"])
    for u, v in snap.get("edges", []):
        G.add_edge(u, v)
    deg = dict(G.degree())
    days = sorted(int(d) for d in traj["day"].unique())
    d0, dn = days[0], days[-1]

    def _op(day):
        sub = traj[traj["day"] == day]
        return {str(k): v for k, v in zip(sub["agent_id"], sub["package_index"])}

    o0, on = _op(d0), _op(dn)
    reached = set()
    if attrs is not None and not attrs.empty and "reached_by_a" in attrs.columns:
        for _, r in attrs.iterrows():
            if bool(r.get("reached_by_a")) or bool(r.get("reached_by_b")):
                reached.add(str(r["agent_id"]))

    pos = nx.spring_layout(G, seed=42)
    norm = mpl.colors.Normalize(vmin=-3, vmax=3)
    cmap = plt.cm.RdYlGn
    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    for ax, omap, title, day in ((axes[0], o0, "Day", d0), (axes[1], on, "Day", dn)):
        node_colors = [cmap(norm(float(omap.get(str(n), 0.0)))) for n in G.nodes()]
        sizes = [60 + 25 * deg.get(n, 0) for n in G.nodes()]
        edgecols = ["black" if str(n) in reached else "none" for n in G.nodes()]
        lws = [1.6 if str(n) in reached else 0.3 for n in G.nodes()]
        nx.draw_networkx_edges(G, pos, alpha=0.2, width=0.5, ax=ax)
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=sizes,
                               edgecolors=edgecols, linewidths=lws, ax=ax)
        ax.set_title(f"{title} {day} (colour=opinion, size=degree, ring=reached)")
        ax.set_axis_off()
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    fig.colorbar(sm, ax=list(axes), fraction=0.025, label="Opinion (-3..+3)")
    fig.suptitle("Peer Network: Opinion Before vs After", fontsize=13)
    return _save_or_show(fig, output_path)


def plot_targeting_mechanism(results, output_path=None):
    """Two-step flow: end drift from GT for reached vs unreached agents."""
    import matplotlib.pyplot as plt

    traj = results.get("package_index_trajectories")
    gt = results.get("package_ground_truth")
    attrs = results.get("agent_attributes")
    if (traj is None or traj.empty or gt is None or gt.empty
            or attrs is None or attrs.empty or "reached_by_a" not in attrs.columns):
        return None
    end_day = int(traj["day"].max())
    end = traj[traj["day"] == end_day][["agent_id", "package_index"]].copy()
    gmap = dict(zip(gt["agent_id"], gt["ground_truth"].astype(float)))
    reached = {
        r["agent_id"]: (bool(r.get("reached_by_a")) or bool(r.get("reached_by_b")))
        for _, r in attrs.iterrows()
    }
    end["gt"] = end["agent_id"].map(gmap)
    end = end.dropna(subset=["gt"])
    if end.empty:
        return None
    end["drift"] = end["package_index"] - end["gt"]
    end["group"] = end["agent_id"].map(
        lambda a: "reached" if reached.get(a) else "unreached")
    means = end.groupby("group")["drift"].mean()
    order = [g for g in ("reached", "unreached") if g in means.index]
    if not order:
        return None
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.bar(order, [means[g] for g in order],
           color=["steelblue", "lightgrey"][:len(order)])
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.set_ylabel("Mean end drift from GT")
    ax.set_title("Two-Step Flow: Reached vs Unreached")
    plt.tight_layout()
    return _save_or_show(fig, output_path)


def plot_reach_qc(results, output_path=None):
    """QC bar: actually-reached counts (per side) against bucket sizes."""
    import numpy as np
    import matplotlib.pyplot as plt

    from cag.io.aggregators import _sorted_buckets

    attrs = results.get("agent_attributes")
    if attrs is None or attrs.empty or "reached_by_a" not in attrs.columns:
        return None
    buckets = _sorted_buckets(attrs["political_exposure"].dropna().unique())
    if not buckets:
        return None
    sizes = [int((attrs["political_exposure"] == b).sum()) for b in buckets]
    ra = [int(attrs[attrs["political_exposure"] == b]["reached_by_a"].astype(bool).sum())
          for b in buckets]
    rb = [int(attrs[attrs["political_exposure"] == b]["reached_by_b"].astype(bool).sum())
          for b in buckets]
    x = np.arange(len(buckets))
    w = 0.25
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - w, sizes, w, label="bucket size", color="lightgrey")
    ax.bar(x, ra, w, label="reached by A", color="forestgreen")
    ax.bar(x + w, rb, w, label="reached by B", color="firebrick")
    ax.set_xticks(x)
    ax.set_xticklabels(buckets)
    ax.set_ylabel("Agents")
    ax.set_title("Reach / Targeting QC (actually reached)")
    ax.legend(fontsize=8)
    plt.tight_layout()
    return _save_or_show(fig, output_path)


def plot_calibration_before_after(results, output_path=None):
    """Package index vs GT at Day 0 (anchored) and Day N (drifted)."""
    import matplotlib.pyplot as plt

    traj = results.get("package_index_trajectories")
    gt = results.get("package_ground_truth")
    if traj is None or traj.empty or gt is None or gt.empty:
        return None
    gmap = dict(zip(gt["agent_id"], gt["ground_truth"].astype(float)))
    days = sorted(int(d) for d in traj["day"].unique())
    d0, dn = days[0], days[-1]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), squeeze=False)
    for ax, day, title in ((axes[0, 0], d0, f"Day {d0}"), (axes[0, 1], dn, f"Day {dn}")):
        sub = traj[traj["day"] == day].copy()
        sub["gt"] = sub["agent_id"].map(gmap)
        sub = sub.dropna(subset=["gt"])
        if sub.empty:
            ax.set_visible(False)
            continue
        try:
            rho = float(sub["package_index"].corr(sub["gt"], method="spearman"))
        except Exception:  # noqa: BLE001
            rho = float("nan")
        ax.scatter(sub["gt"], sub["package_index"], alpha=0.6)
        ax.plot([-3, 3], [-3, 3], color="grey", linestyle="--", linewidth=0.8)
        ax.set_xlim(-3.5, 3.5)
        ax.set_ylim(-3.5, 3.5)
        ax.set_xlabel("Ground truth")
        ax.set_ylabel("Package index")
        ax.set_title(f"{title} (rho={rho:+.2f})")
    fig.suptitle("Calibration Before vs After (package index)", fontsize=13)
    plt.tight_layout()
    return _save_or_show(fig, output_path)


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

    # O2 additions: bucket trajectories, dispersion/drift, hero figures,
    # targeting diagnostics. Each returns None on insufficient data and is
    # then skipped.
    for name, fn in (
        ("opinion_trajectories_by_bucket", plot_opinion_trajectories_by_bucket),
        ("polarization", plot_polarization),
        ("drift_from_gt", plot_drift_from_gt),
        ("opinion_ridgeline", plot_opinion_ridgeline),
        ("network_before_after", plot_network_before_after),
        ("targeting_mechanism", plot_targeting_mechanism),
        ("reach_qc", plot_reach_qc),
        ("calibration_before_after", plot_calibration_before_after),
    ):
        p = out_path / f"{name}.png"
        if fn(results, output_path=p) is not None:
            plot_paths[name] = p

    return plot_paths
