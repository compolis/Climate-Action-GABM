"""
Simulation runner for Climate-Action-GABM.
"""
from dataclasses import dataclass
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from cag.abm.agent import PoliticalAgent
from cag.abm.attributes.opinion import (
    ALL_CLIMATE_POLICIES,
    ClimatePolicyID,
    PACKAGE_SCOPE,
    PRO_CLIMATE_INDEX_COLUMN,
    SURVEY_COLUMN_MAP,
    SURVEY_QUESTIONS,
    compute_package_index,
)
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
    "llm_model": "gpt-5-mini",
    "llm_provider": "openai",
    "llm_temperature": 0.5,
    "survey_model": None,       # override model for surveys (None → use llm_model)
    "survey_provider": None,    # override provider for surveys (None → use llm_provider)
    "thinking": False,
    "debias": False,
    "communication_mode": "single_policy",
    "package_policies": ALL_CLIMATE_POLICIES,
    "day0_anchor": "llm_survey",
    "random_seed": 42,
    "output_dir": "data/output/experiments",
}


VALID_DAY0_ANCHORS = ("llm_survey", "ground_truth", "ground_truth_with_rationale")


def _is_package_mode(config):
    return config.get("communication_mode") == "package"


def _get_package_policies(config):
    return config.get("package_policies") or ALL_CLIMATE_POLICIES


def _run_baseline_surveys(nation, policies, api_key, model, provider,
                          temperature, thinking, debias):
    for agent in nation.agents_active.values():
        for policy_id in policies:
            agent.administer_survey(
                policy_id,
                day=0,
                api_key=api_key,
                model=model,
                provider=provider,
                temperature=temperature,
                thinking=thinking,
                debias=debias,
            )


def _run_day0(nation, policies, anchor_mode, api_key, model, provider,
              temperature, thinking, debias):
    """Initialise Day 0 opinions according to the configured anchor mode.

    - ``llm_survey``: existing behaviour (administer the survey via LLM).
    - ``ground_truth``: seed opinion_history from the real survey response;
      no LLM call.
    - ``ground_truth_with_rationale``: seed from ground truth and ask the
      LLM to rationalise the position; rationale stored in survey_reasoning.
    """
    if anchor_mode == "llm_survey":
        _run_baseline_surveys(
            nation, policies, api_key, model, provider,
            temperature, thinking, debias,
        )
        return

    if debias:
        logging.info(
            "day0_anchor=%s: debias flag is ignored on Day 0 "
            "(still applies to end-of-day surveys).",
            anchor_mode,
        )

    for agent in nation.agents_active.values():
        for policy_id in policies:
            if anchor_mode == "ground_truth":
                agent.seed_opinion_from_ground_truth(policy_id, day=0)
            else:  # ground_truth_with_rationale
                agent.seed_opinion_with_rationale(
                    policy_id, day=0,
                    api_key=api_key, model=model, provider=provider,
                    temperature=temperature, thinking=thinking,
                )


def _log_package_index(nation, policies, day):
    package_indices = []
    for agent in nation.agents_active.values():
        numeric_values = []
        for policy_id in policies:
            history = agent.opinion_history.get(policy_id, [])
            if not history or history[-1][0] != day:
                numeric_values = []
                break
            numeric_values.append(history[-1][1])
        if numeric_values:
            package_indices.append(compute_package_index(numeric_values))
    if package_indices:
        mean_index = sum(package_indices) / len(package_indices)
        logging.info(f"Day {day} mean package index: {mean_index:+.2f}")


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
    thinking = cfg["thinking"]
    debias = cfg["debias"]
    k_peers = cfg["k_peers_per_day"]

    # Survey-specific model override (falls back to main model when None)
    survey_model = cfg.get("survey_model") or model
    survey_provider = cfg.get("survey_provider") or provider
    survey_api_key = (
        load_api_key(survey_provider) if survey_provider != provider else api_key
    )
    days = cfg["days"]
    n_days = len(days)
    package_mode = _is_package_mode(cfg)
    package_policies = _get_package_policies(cfg)
    anchor_mode = cfg.get("day0_anchor", "llm_survey")
    if anchor_mode not in VALID_DAY0_ANCHORS:
        raise ValueError(
            f"day0_anchor must be one of {VALID_DAY0_ANCHORS}, got {anchor_mode!r}"
        )

    nation.message_log = []

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

    if package_mode:
        logging.info(
            "Running package baseline survey (day 0), policies=%s, anchor=%s",
            [str(policy_id) for policy_id in package_policies],
            anchor_mode,
        )
        _run_day0(
            nation, package_policies, anchor_mode,
            survey_api_key, survey_model, survey_provider,
            temperature, thinking, debias,
        )
        _log_package_index(nation, package_policies, day=0)
    else:
        baseline_policy = days[0]["policy"]
        logging.info(
            f"Running baseline survey (day 0), policy={baseline_policy}, anchor={anchor_mode}"
        )
        _run_day0(
            nation, [baseline_policy], anchor_mode,
            survey_api_key, survey_model, survey_provider,
            temperature, thinking, debias,
        )

    # Daily loop
    for day_index, day_config in enumerate(days):
        day = day_index + 1
        phases = day_config["phases"]
        if package_mode:
            logging.info(
                "--- Day %s/%s (package=%s, phases=%s) ---",
                day,
                n_days,
                PACKAGE_SCOPE,
                phases,
            )
        else:
            policy = day_config["policy"]
            logging.info(f"--- Day {day}/{n_days} (policy={policy}, phases={phases}) ---")

        for phase in phases:
            if package_mode:
                if phase in ("P-A", "P-B"):
                    nation.run_package_broadcast(
                        phase, package_policies, day,
                        api_key=api_key, model=model,
                        provider=provider, temperature=temperature,
                    )
                elif phase == "C":
                    nation.run_package_peer_messaging(
                        package_policies, day, k_peers=k_peers,
                        api_key=api_key, model=model,
                        provider=provider, temperature=temperature,
                    )
                else:
                    logging.warning(f"Unknown phase '{phase}' on day {day}, skipping.")
            else:
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

        if package_mode:
            for policy_id in package_policies:
                nation.run_end_of_day_survey(
                    policy_id,
                    day,
                    api_key=survey_api_key,
                    model=survey_model,
                    provider=survey_provider,
                    temperature=temperature,
                    thinking=thinking,
                    debias=debias,
                )
        else:
            nation.run_end_of_day_survey(
                policy, day,
                api_key=survey_api_key, model=survey_model,
                provider=survey_provider,
                temperature=temperature, thinking=thinking, debias=debias,
            )

        # Memory management
        for agent in nation.agents_active.values():
            if package_mode:
                agent.manage_memory(
                    day,
                    PACKAGE_SCOPE,
                    api_key=api_key,
                    model=model,
                    provider=provider,
                    temperature=temperature,
                )
            else:
                agent.manage_memory(
                    day, policy,
                    api_key=api_key, model=model, provider=provider,
                    temperature=temperature,
                )

        # Log progress
        if package_mode:
            _log_package_index(nation, package_policies, day)
        else:
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
    package_rows = []
    ref_rows = []
    message_rows = []
    survey_reasoning_rows = []
    daily_summary_rows = []
    package_mode = _is_package_mode(config)
    package_policies = _get_package_policies(config) if package_mode else []
    agents = list(nation.agents_active.values())

    for event in getattr(nation, "message_log", []):
        policy_id = event.get("policy_id")
        policy_ids = event.get("policy_ids") or []
        message_rows.append({
            "day": event.get("day"),
            "phase": event.get("phase", ""),
            "message_type": event.get("message_type", ""),
            "sender_type": event.get("sender_type", ""),
            "sender_id": event.get("sender_id"),
            "sender_side": event.get("sender_side", ""),
            "recipient_id": event.get("recipient_id"),
            "recipient_scope": event.get("recipient_scope", ""),
            "policy_id": str(policy_id) if policy_id not in (None, "") else "",
            "package_scope": event.get("package_scope", ""),
            "policy_ids_json": json.dumps([str(pid) for pid in policy_ids]),
            "message_text": event.get("message_text", ""),
        })

    for agent in agents:
        for pid, history in agent.opinion_history.items():
            for day, numeric in history:
                traj_rows.append({
                    "agent_id": agent.id,
                    "day": day,
                    "policy_id": str(pid),
                    "numeric": numeric,
                })

        if package_mode:
            day_maps = {}
            for policy_id in package_policies:
                history = agent.opinion_history.get(policy_id, [])
                if not history:
                    day_maps = {}
                    break
                day_maps[policy_id] = {day: numeric for day, numeric in history}
            if day_maps:
                common_days = set.intersection(*(set(day_map.keys()) for day_map in day_maps.values()))
                for day in sorted(common_days):
                    numeric_values = [day_maps[policy_id][day] for policy_id in package_policies]
                    package_rows.append({
                        "agent_id": agent.id,
                        "day": day,
                        "index_name": PRO_CLIMATE_INDEX_COLUMN,
                        "package_scope": PACKAGE_SCOPE,
                        "package_index": compute_package_index(numeric_values),
                    })

        for policy_id, reasoning_entries in agent.survey_reasoning.items():
            for day, reasoning in reasoning_entries:
                survey_reasoning_rows.append({
                    "agent_id": agent.id,
                    "day": day,
                    "policy_id": str(policy_id),
                    "reasoning": reasoning,
                })

        for (day, policy_id), summary in agent.daily_summaries.items():
            daily_summary_rows.append({
                "agent_id": agent.id,
                "day": day,
                "policy_id": str(policy_id),
                "summary": summary,
            })

        for r in agent.reflections:
            policy_id = r.get("policy_id", "")
            policy_ids = r.get("policy_ids") or []
            messages_received = r.get("messages_received") or []
            ref_rows.append({
                "agent_id": agent.id,
                "day": r["day"],
                "phase": r["phase"],
                "policy_id": str(policy_id),
                "package_scope": PACKAGE_SCOPE if policy_id == PACKAGE_SCOPE else "",
                "policy_ids_json": json.dumps([str(pid) for pid in policy_ids]),
                "messages_received_json": json.dumps(messages_received),
                "messages_received_count": len(messages_received),
                "text": r["text"],
            })

    ground_truth_df = collect_ground_truth(agents)
    package_ground_truth_df = collect_package_ground_truth(agents)

    return {
        "opinion_trajectories": pd.DataFrame(
            traj_rows,
            columns=["agent_id", "day", "policy_id", "numeric"],
        ),
        "package_index_trajectories": pd.DataFrame(
            package_rows,
            columns=["agent_id", "day", "index_name", "package_scope", "package_index"],
        ),
        "reflections": pd.DataFrame(
            ref_rows,
            columns=[
                "agent_id",
                "day",
                "phase",
                "policy_id",
                "package_scope",
                "policy_ids_json",
                "messages_received_json",
                "messages_received_count",
                "text",
            ],
        ),
        "messages": pd.DataFrame(
            message_rows,
            columns=[
                "day",
                "phase",
                "message_type",
                "sender_type",
                "sender_id",
                "sender_side",
                "recipient_id",
                "recipient_scope",
                "policy_id",
                "package_scope",
                "policy_ids_json",
                "message_text",
            ],
        ),
        "survey_reasoning": pd.DataFrame(
            survey_reasoning_rows,
            columns=["agent_id", "day", "policy_id", "reasoning"],
        ),
        "daily_summaries": pd.DataFrame(
            daily_summary_rows,
            columns=["agent_id", "day", "policy_id", "summary"],
        ),
        "ground_truth": ground_truth_df,
        "package_ground_truth": package_ground_truth_df,
        "config": config,
    }


def collect_ground_truth(agents, policy_ids=None):
    """Extract real survey responses for agents into a DataFrame.

    Args:
        agents: iterable of SurveyedCitizen instances.
        policy_ids: optional list of ClimatePolicyID.  If *None*, all
            policies in SURVEY_COLUMN_MAP are included.

    Returns:
        DataFrame with columns ``agent_id``, ``policy_id``, ``ground_truth``.
    """
    if policy_ids is None:
        policy_ids = list(SURVEY_COLUMN_MAP.keys())
    rows = []
    for agent in agents:
        for pid in policy_ids:
            rows.append({
                "agent_id": agent.id,
                "policy_id": str(pid),
                "ground_truth": agent.get_real_survey_response(pid),
            })
    return pd.DataFrame(rows, columns=["agent_id", "policy_id", "ground_truth"])


def collect_package_ground_truth(agents):
    """Extract the real package-level climate support index for each agent.

    Returns:
        DataFrame with columns ``agent_id``, ``index_name``, ``ground_truth``.
    """
    rows = []
    for agent in agents:
        if hasattr(agent, "get_real_package_index"):
            ground_truth = agent.get_real_package_index()
        else:
            numeric_values = [
                agent.get_real_survey_response(policy_id)
                for policy_id in ALL_CLIMATE_POLICIES
            ]
            ground_truth = compute_package_index(numeric_values)
        rows.append({
            "agent_id": agent.id,
            "index_name": PRO_CLIMATE_INDEX_COLUMN,
            "ground_truth": ground_truth,
        })
    return pd.DataFrame(rows, columns=["agent_id", "index_name", "ground_truth"])


# ── Output ──────────────────────────────────────────────────────

def save_results(results, output_dir="data/output/experiments"):
    """Save simulation results to a timestamped directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(output_dir) / timestamp
    out_path.mkdir(parents=True, exist_ok=True)

    def _result_df(key, columns):
        value = results.get(key)
        if value is None:
            return pd.DataFrame(columns=columns)
        return value

    opinion_trajectories_df = _result_df(
        "opinion_trajectories",
        ["agent_id", "day", "policy_id", "numeric"],
    )
    opinion_trajectories_df.to_csv(out_path / "opinion_trajectories.csv", index=False)
    build_opinion_shares({"opinion_trajectories": opinion_trajectories_df}).to_csv(
        out_path / "opinion_shares.csv",
        index=False,
    )
    package_index_df = _result_df(
        "package_index_trajectories",
        ["agent_id", "day", "index_name", "package_scope", "package_index"],
    )
    if package_index_df is not None and not package_index_df.empty:
        package_index_df.to_csv(out_path / "package_index_trajectories.csv", index=False)
        build_package_index_shares(
            {"package_index_trajectories": package_index_df}
        ).to_csv(out_path / "package_index_shares.csv", index=False)
    _result_df(
        "reflections",
        [
            "agent_id",
            "day",
            "phase",
            "policy_id",
            "package_scope",
            "policy_ids_json",
            "messages_received_json",
            "messages_received_count",
            "text",
        ],
    ).to_csv(out_path / "reflections.csv", index=False)
    _result_df(
        "messages",
        [
            "day",
            "phase",
            "message_type",
            "sender_type",
            "sender_id",
            "sender_side",
            "recipient_id",
            "recipient_scope",
            "policy_id",
            "package_scope",
            "policy_ids_json",
            "message_text",
        ],
    ).to_csv(out_path / "messages.csv", index=False)
    _result_df(
        "survey_reasoning",
        ["agent_id", "day", "policy_id", "reasoning"],
    ).to_csv(out_path / "survey_reasoning.csv", index=False)
    _result_df(
        "daily_summaries",
        ["agent_id", "day", "policy_id", "summary"],
    ).to_csv(out_path / "daily_summaries.csv", index=False)
    ground_truth_df = results.get("ground_truth")
    if ground_truth_df is not None:
        ground_truth_df.to_csv(out_path / "ground_truth.csv", index=False)
    package_ground_truth_df = results.get("package_ground_truth")
    if package_ground_truth_df is not None and not package_ground_truth_df.empty:
        package_ground_truth_df.to_csv(out_path / "package_ground_truth.csv", index=False)

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
        elif isinstance(v, list) and v and all(isinstance(item, ClimatePolicyID) for item in v):
            out[k] = [str(item) for item in v]
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


def build_opinion_shares(results):
    """Aggregate support, neutral, and against shares by policy and day."""
    columns = [
        "policy_id",
        "day",
        "n_agents",
        "n_support",
        "support_pct",
        "n_neutral",
        "neutral_pct",
        "n_against",
        "against_pct",
    ]
    df = results.get("opinion_trajectories")
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)

    share_df = (
        df.groupby(["policy_id", "day"])
        .agg(
            n_agents=("agent_id", "count"),
            n_support=("numeric", lambda values: int((values > 0).sum())),
            n_neutral=("numeric", lambda values: int((values == 0).sum())),
            n_against=("numeric", lambda values: int((values < 0).sum())),
        )
        .reset_index()
        .sort_values(["policy_id", "day"])
    )

    share_df["support_pct"] = share_df["n_support"] / share_df["n_agents"] * 100.0
    share_df["neutral_pct"] = share_df["n_neutral"] / share_df["n_agents"] * 100.0
    share_df["against_pct"] = share_df["n_against"] / share_df["n_agents"] * 100.0
    return share_df[columns]


def build_package_index_shares(results):
    """Aggregate support, neutral, and against shares for the package index by day."""
    columns = [
        "day",
        "index_name",
        "package_scope",
        "n_agents",
        "n_support",
        "support_pct",
        "n_neutral",
        "neutral_pct",
        "n_against",
        "against_pct",
    ]
    df = results.get("package_index_trajectories")
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)

    share_df = (
        df.groupby(["day", "index_name", "package_scope"])
        .agg(
            n_agents=("agent_id", "count"),
            n_support=("package_index", lambda values: int((values > 0).sum())),
            n_neutral=("package_index", lambda values: int(np.isclose(values, 0.0).sum())),
            n_against=("package_index", lambda values: int((values < 0).sum())),
        )
        .reset_index()
        .sort_values(["day", "index_name", "package_scope"])
    )

    share_df["support_pct"] = share_df["n_support"] / share_df["n_agents"] * 100.0
    share_df["neutral_pct"] = share_df["n_neutral"] / share_df["n_agents"] * 100.0
    share_df["against_pct"] = share_df["n_against"] / share_df["n_agents"] * 100.0
    return share_df[columns]


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

    return plot_paths
