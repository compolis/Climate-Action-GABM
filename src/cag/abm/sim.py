"""
Simulation runner for Climate-Action-GABM.
"""
from dataclasses import dataclass
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from cag.abm.agent import PoliticalAgent
from cag.abm.attributes.opinion import ClimatePolicyID, SURVEY_QUESTIONS
from cag.io.llm import load_api_key


SIM_CONFIG = {
    "n_citizens": 200,
    "days": [
        {"policy": ClimatePolicyID.RENEWABLE_ENERGY, "phases": ["P-A", "P-B", "C"]},
        {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A", "P-B","C"]},
    ],
    "k_peers_per_day": 3,
    "network_type": "stochastic_block",
    "p_intra": 0.15,
    "p_inter": 0.02,
    "block_sizes": None,        # defaults to equal split
    "llm_model": "gpt-4o-mini",
    "llm_provider": "openai",
    "llm_temperature": 0.7,
    "random_seed": 42,
    "output_dir": "data/output/experiments",
}


# ── Main simulation loop ────────────────────────────────────────

def run_simulation(config, nation):
    """Run a full simulation and return results as a dict of DataFrames.

    Args:
        config: dict with simulation parameters (see SIM_CONFIG for keys).
            config["days"] is a list where each entry is:
                {"policy": ClimatePolicyID, "phases": ["P-A", "P-B", "C"]}
        nation: a SurveyedNation with agents already loaded.

    Returns:
        dict with keys "opinion_trajectories", "reflections", "config".
    """
    cfg = {**SIM_CONFIG, **config}

    api_key = load_api_key(cfg["llm_provider"])
    model = cfg["llm_model"]
    provider = cfg["llm_provider"]
    temperature = cfg["llm_temperature"]
    k_peers = cfg["k_peers_per_day"]
    days = cfg["days"]
    n_days = len(days)

    if not days:
        logging.warning("No days configured — nothing to simulate.")
        return _collect_results(nation, cfg)

    # Setup
    nation.political_agent_a = PoliticalAgent("agent_a", "pro_climate")
    nation.political_agent_b = PoliticalAgent("agent_b", "anti_climate")
    nation.assign_political_exposure()
    nation.create_network(
        p_intra=cfg["p_intra"],
        p_inter=cfg["p_inter"],
        seed=cfg["random_seed"],
    )
    nation.assign_network_blocks()

    n_agents = len(nation.agents_active)
    logging.info(f"Simulation: {n_agents} agents, {n_days} days")

    # Baseline (day 0) — survey on first day's policy
    baseline_policy = days[0]["policy"]
    logging.info(f"Running baseline survey (day 0), policy={baseline_policy}")
    for agent in nation.agents_active.values():
        agent.administer_survey(
            baseline_policy, day=0, api_key=api_key, model=model,
            provider=provider, temperature=temperature,
        )

    # Daily loop
    for day_index, day_config in enumerate(days):
        day = day_index + 1
        policy = day_config["policy"]
        phases = day_config["phases"]
        logging.info(f"--- Day {day}/{n_days} (policy={policy}, phases={phases}) ---")

        for phase in phases:
            if phase in ("P-A", "P-B"):
                nation.run_political_broadcast(
                    phase, policy, day,
                    api_key=api_key, model=model,
                    provider=provider, temperature=temperature,
                )
            elif phase == "C":
                nation.run_peer_messaging(
                    policy, day, k_peers=k_peers,
                    api_key=api_key, model=model,
                    provider=provider, temperature=temperature,
                )
            else:
                logging.warning(f"Unknown phase '{phase}' on day {day}, skipping.")

        # End-of-day survey
        nation.run_end_of_day_survey(
            policy, day,
            api_key=api_key, model=model, provider=provider,
        )

        # Memory management
        for agent in nation.agents_active.values():
            agent.manage_memory(
                day, policy,
                api_key=api_key, model=model, provider=provider,
            )

        # Log progress
        opinions = [
            agent.opinion_history[policy][-1][1]
            for agent in nation.agents_active.values()
            if policy in agent.opinion_history and agent.opinion_history[policy]
        ]
        if opinions:
            mean_op = sum(opinions) / len(opinions)
            logging.info(f"Day {day} mean opinion: {mean_op:+.2f}")

    return _collect_results(nation, cfg)


# ── Results collection ──────────────────────────────────────────

def _collect_results(nation, config):
    """Build DataFrames from agent state after simulation."""
    traj_rows = []
    for agent in nation.agents_active.values():
        for pid, history in agent.opinion_history.items():
            for day, numeric in history:
                traj_rows.append({
                    "agent_id": agent.id,
                    "day": day,
                    "policy_id": str(pid),
                    "numeric": numeric,
                })

    ref_rows = []
    for agent in nation.agents_active.values():
        for r in agent.reflections:
            ref_rows.append({
                "agent_id": agent.id,
                "day": r["day"],
                "phase": r["phase"],
                "policy_id": str(r.get("policy_id", "")),
                "text": r["text"],
            })

    return {
        "opinion_trajectories": pd.DataFrame(traj_rows),
        "reflections": pd.DataFrame(ref_rows),
        "config": config,
    }


# ── Output ──────────────────────────────────────────────────────

def save_results(results, output_dir="data/output/experiments"):
    """Save simulation results to a timestamped directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(output_dir) / timestamp
    out_path.mkdir(parents=True, exist_ok=True)

    results["opinion_trajectories"].to_csv(out_path / "opinion_trajectories.csv", index=False)
    results["reflections"].to_csv(out_path / "reflections.csv", index=False)

    # Serialise config (convert enums and lists of dicts to strings)
    config_serialisable = _serialise_config(results["config"])
    with open(out_path / "config.json", "w") as f:
        json.dump(config_serialisable, f, indent=2)

    logging.info(f"Results saved to {out_path}")
    return out_path


def _serialise_config(config):
    """Make config JSON-safe by converting enums to strings."""
    out = {}
    for k, v in config.items():
        if isinstance(v, ClimatePolicyID):
            out[k] = str(v)
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            # days list — convert policy enums inside each entry
            out[k] = [
                {dk: str(dv) if isinstance(dv, ClimatePolicyID) else dv
                 for dk, dv in entry.items()}
                for entry in v
            ]
        else:
            out[k] = v
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

    # Build a policy_id → short readable name lookup
    POLICY_SHORT_NAMES = {
        ClimatePolicyID.RENEWABLE_ENERGY: "Renewable Energy",
        ClimatePolicyID.BAN_FOSSIL_FUEL: "Ban Fossil Fuels",
        ClimatePolicyID.BAN_PETROL_CARS: "Ban Petrol Cars",
        ClimatePolicyID.GREEN_HOUSING: "Green Housing",
        ClimatePolicyID.CARBON_TAX: "Carbon Tax",
        ClimatePolicyID.CLIMATE_COMPENSATION: "Climate Compensation",
    }
    policy_names = {str(pid): name for pid, name in POLICY_SHORT_NAMES.items()}

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
