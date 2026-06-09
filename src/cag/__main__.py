#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Headless entry point for running the Climate-Action-GABM simulation.

This mirrors the canonical reference run in
``notebooks/29_canonical_full_smoke.ipynb`` (package mode + offline political
messages + local Qwen3, with Day-0 anchoring from YouGov ground truth) but is
fully parameterised for the command line so it can run unattended as a Slurm
batch job on an HPC (see ``scripts/aire/smoke.sh``).

Usage (local Mac, mlx-lm server on :8080):
    PYTHONPATH=src python3 -m cag --outdir data/output/experiments

Usage (AIRE HPC, vLLM server on :8000):
    PYTHONPATH=src python3 -m cag \\
        --provider local --model Qwen/Qwen3-8B \\
        --base-url http://localhost:8000/v1 \\
        --outdir "$SCRATCH/cag/runs/run_$SLURM_JOB_ID" \\
        --seed 42 --no-thinking

All run artefacts (CSVs, PNGs, the config snapshot, and the run log) are
written under ``--outdir``. Nothing is written into the repository tree, so
the output directory can point at $SCRATCH on a cluster.
"""
__author__ = [
    "Andy Turner <agdturner@gmail.com>",
    "Ajaykumar Manivannan <ashwamanivannan@gmail.com>",
    "Charlie Pilgrim <pilgrimcharlie2@gmail.com>",
]
__version__ = "0.5.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

import argparse
import logging
import random
import sys
import time
from pathlib import Path

# Force a non-interactive backend before anything imports pyplot, so figure
# saving works on a headless compute node with no display.
import matplotlib
matplotlib.use("Agg")

# ── Agent / attribute imports (kept in lock-step with NB29) ───────
from gabm.abm.attributes.gender import GenderMap, GenderID
from gabm.abm.attributes.politics import PoliticsID
from gabm.abm.democracy.election import ElectionID

from cag.io.survey import load
from cag.abm.agent import SurveyedCitizen
from cag.abm.environment import SurveyedNation
from cag.abm.attributes.opinion import ALL_CLIMATE_POLICIES
from cag.abm.attributes.region import UKRegionMap, RegionID
from cag.abm.attributes.education import SurveyEducationMap, EducationID
from cag.abm.attributes.ethnicity import SurveyEthnicityMap, EthnicityID
from cag.abm.attributes.income import SurveyIncomeMap, IncomeID
from cag.abm.attributes.politics import SurveyPoliticsMap
from cag.abm.attributes.family import SurveyFamilyMap, FamilyID
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteMap, UKGE2019VoteID
from cag.abm.democracy.elections.brexit import BrexitVoteMap, BrexitVoteID
from cag.abm.attributes.narratives import (
    SelftranscMap, SelfenhMap, OpennessMap, ConformTradMap,
    SDOMap, EDOMap, RWAMap, rescale_1_6, rescale_1_7,
)
from cag.abm.sim import run_simulation, save_results, save_result_plots


# ── Defaults (the NB29 canonical smoke profile) ──────────────────
DEFAULT_SURVEY_CSV = "data/yougov_survey_data/YouGovProcessedData.csv"
DEFAULT_N_CITIZENS = 10           # NB29 smoke (full run = 100)
DEFAULT_DAYS = 2                  # NB29 smoke (alternating package days)
DEFAULT_K_PEERS = 2               # NB29 smoke (full run = 3)
DEFAULT_SEED = 42
DEFAULT_MODEL = "mlx-community/Qwen3-8B-4bit"   # Mac/mlx default; override on HPC
DEFAULT_PROVIDER = "local"
DEFAULT_TEMPERATURE = 0.5


def build_days(n_days):
    """Build an alternating package-mode day plan (mirrors NB29).

    Day 0 broadcasts P-A first, day 1 P-B first, and so on, always closing
    with a peer-messaging ("C") phase. No per-day ``policy`` key: package
    mode broadcasts every ``package_policies`` entry each phase.
    """
    plan = []
    for i in range(n_days):
        if i % 2 == 0:
            plan.append({"phases": ["P-A", "P-B", "C"]})
        else:
            plan.append({"phases": ["P-B", "P-A", "C"]})
    return plan


def build_config(args):
    """Assemble the SIM_CONFIG overrides for this run.

    Only keys that differ from ``cag.abm.sim.SIM_CONFIG`` defaults (or that we
    pin for reproducibility / CLI control) are set here; ``run_simulation``
    merges these on top of the canonical defaults (package mode, offline v1
    messages, Day-0 ground-truth-with-rationale anchoring, debias on).
    """
    return {
        "n_citizens": args.n_citizens,
        "days": build_days(args.days),
        "k_peers_per_day": DEFAULT_K_PEERS,
        "package_policies": list(ALL_CLIMATE_POLICIES),
        "llm_model": args.model,
        "llm_provider": args.provider,
        "llm_temperature": args.temperature,
        "thinking": args.thinking,
        "debias": args.debias,
        "random_seed": args.seed,
        "local_base_url": args.base_url,   # None → mlx default; set on HPC
    }


def build_nation(data, year=2026):
    """Create a SurveyedNation and populate it with citizens (mirrors NB29)."""
    UKGE2019_ELECTION_ID = ElectionID(0)
    BREXIT_REFERENDUM_ID = ElectionID(1)

    sn = SurveyedNation(
        year=year, place="UK",
        gender_map=GenderMap(),
        region_map=UKRegionMap(),
        education_map=SurveyEducationMap(),
        ethnicity_map=SurveyEthnicityMap(),
        income_map=SurveyIncomeMap(),
        politics_map=SurveyPoliticsMap(),
        family_map=SurveyFamilyMap(),
        ukge2019_vote_map=UKGE2019VoteMap(UKGE2019_ELECTION_ID),
        brexit_vote_map=BrexitVoteMap(BREXIT_REFERENDUM_ID),
        selftransc_map=SelftranscMap,
        selfenh_map=SelfenhMap,
        openness_map=OpennessMap,
        conformtrad_map=ConformTradMap,
        sdo_map=SDOMap,
        edo_map=EDOMap,
        rwa_map=RWAMap,
    )

    for i in range(len(data)):
        row = data.iloc[i]
        sc = SurveyedCitizen(
            agent_id=row.get("ID", None),
            environment=sn,
            year_of_birth=year - int(row.get("age", 0)),
            gender_id=GenderID.MALE if int(row.get("male_dummy", 0)) == 1 else GenderID.FEMALE,
            region_id=RegionID(int(row.get("tprofile_GOR", 0))),
            education_id=EducationID(int(row.get("profile_education_level", 0))),
            income_id=IncomeID(int(row.get("tprofile_gross_household", 0))),
            ethnicity_id=EthnicityID(int(row.get("ethnicity_R", 0))),
            family_id=FamilyID.PARENT if int(row.get("parent_dummy", 0)) == 1 else FamilyID.NOT_PARENT,
            ukge2019_vote_id=UKGE2019VoteID(int(row.get("Vote2019R", 0))),
            brexit_vote_id=BrexitVoteID(int(row.get("pastvote_EURef", 0))),
            politics_id=PoliticsID(int(row.get("Political_Left_Right", 0))),
            selftransc_id=rescale_1_6(int(row.get("Selftransc_Val", 0))),
            selfenh_id=rescale_1_6(int(row.get("Selfenh_Values", 0))),
            openness_id=rescale_1_6(int(row.get("Openness", 0))),
            conformtrad_id=rescale_1_6(int(row.get("ConformTrad", 0))),
            sdo_id=rescale_1_7(int(row.get("SDO", 0))),
            edo_id=rescale_1_7(int(row.get("EDO", 0))),
            rwa_id=rescale_1_6(int(row.get("RWA", 0))),
            original_survey_data=data.iloc[i],
        )
        sn.agents_active[sc.id] = sc

    return sn


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m cag",
        description="Run the Climate-Action-GABM simulation headless "
                    "(mirrors NB29: package mode, offline messages, local LLM).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--outdir", required=True,
        help="Directory for all run artefacts (CSVs, PNGs, log, config). "
             "On a cluster point this at $SCRATCH, never the repo tree.",
    )
    p.add_argument("--seed", type=int, default=DEFAULT_SEED,
                   help="Random seed (seeds Python + simulation RNGs).")
    p.add_argument("--n-citizens", type=int, default=DEFAULT_N_CITIZENS,
                   dest="n_citizens", help="Number of citizen agents to sample.")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS,
                   help="Number of alternating package-mode days to simulate.")
    p.add_argument("--data", default=DEFAULT_SURVEY_CSV,
                   help="Path to the YouGov processed survey CSV.")
    p.add_argument("--provider", default=DEFAULT_PROVIDER,
                   help="LLM provider: local / openai / anthropic / genai.")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help="Model name the server expects "
                        "(HPC/vLLM example: Qwen/Qwen3-8B).")
    p.add_argument("--base-url", default=None, dest="base_url",
                   help="OpenAI-compatible endpoint for provider=local "
                        "(HPC/vLLM example: http://localhost:8000/v1). "
                        "Default None -> mlx-lm http://localhost:8080/v1.")
    p.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE,
                   help="Sampling temperature.")

    thinking = p.add_mutually_exclusive_group()
    thinking.add_argument("--thinking", dest="thinking", action="store_true",
                          help="Enable model thinking/reasoning (slower).")
    thinking.add_argument("--no-thinking", dest="thinking", action="store_false",
                          help="Disable thinking (faster; recommended first HPC smoke).")
    p.set_defaults(thinking=True)   # NB29 executed config used thinking=True

    debias = p.add_mutually_exclusive_group()
    debias.add_argument("--debias", dest="debias", action="store_true",
                        help="Use the Condition B 2-step debias survey (research canon).")
    debias.add_argument("--no-debias", dest="debias", action="store_false",
                        help="Disable debias.")
    p.set_defaults(debias=True)

    return p.parse_args(argv)


def main(argv=None):
    overall_t0 = time.perf_counter()
    args = parse_args(argv)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Log to BOTH stdout (Slurm captures this into the .out file) and a file
    # inside the output directory (so the log travels with the results).
    log_file = outdir / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.info("--- Climate-Action-GABM v%s ---", __version__)
    logging.info(
        "Run profile: n_citizens=%d, days=%d, k_peers=%d, provider=%s, "
        "model=%s, base_url=%s, thinking=%s, debias=%s, seed=%d",
        args.n_citizens, args.days, DEFAULT_K_PEERS, args.provider, args.model,
        args.base_url or "(provider default)", args.thinking, args.debias, args.seed,
    )
    logging.info("Output directory: %s", outdir.resolve())

    random.seed(args.seed)

    # ── Stage 1: load + subsample survey data ────────────────────
    t0 = time.perf_counter()
    logging.info("Loading survey data from %s ...", args.data)
    data = load(args.data)
    data = data.sample(n=args.n_citizens, random_state=args.seed).reset_index(drop=True)
    t_load = time.perf_counter() - t0
    logging.info("Sampled %d citizens [%.2fs]", len(data), t_load)

    # ── Stage 2: build the nation ────────────────────────────────
    t0 = time.perf_counter()
    logging.info("Building SurveyedNation ...")
    nation = build_nation(data)
    t_build = time.perf_counter() - t0
    logging.info("Nation ready: %d agents [%.2fs]", len(nation.agents_active), t_build)

    # ── Stage 3: run the simulation (the LLM-bound phase) ────────
    config = build_config(args)
    t0 = time.perf_counter()
    logging.info("Starting simulation ...")
    results = run_simulation(config, nation)
    t_sim = time.perf_counter() - t0
    logging.info("Simulation complete [%.1fs / %.1f min]", t_sim, t_sim / 60.0)

    # ── Stage 4: save artefacts ──────────────────────────────────
    t0 = time.perf_counter()
    out_path = save_results(results, output_dir=str(outdir))
    plot_paths = save_result_plots(results, out_path)
    t_save = time.perf_counter() - t0
    logging.info("Artefacts saved to %s [%.2fs]", out_path, t_save)
    for plot_name, plot_path in plot_paths.items():
        logging.info("  plot %-28s -> %s", plot_name, plot_path)

    # ── Summary ──────────────────────────────────────────────────
    df = results["opinion_trajectories"]
    n_agents = df["agent_id"].nunique() if not df.empty else 0
    n_days = df["day"].nunique() if not df.empty else 0
    logging.info(
        "Trajectories: %d rows, %d agents, %d days, %d policies",
        len(df), n_agents, n_days,
        df["policy_id"].nunique() if not df.empty else 0,
    )

    overall = time.perf_counter() - overall_t0
    # A simple scaling unit to help estimate larger runs: simulation seconds
    # per (agent x day). Multiply by your target agents x days to extrapolate.
    agent_days = max(n_agents * n_days, 1)
    logging.info("==================== TIMING ====================")
    logging.info("  data load        : %8.2fs", t_load)
    logging.info("  nation build     : %8.2fs", t_build)
    logging.info("  simulation       : %8.2fs  (%.1f min)", t_sim, t_sim / 60.0)
    logging.info("  save artefacts   : %8.2fs", t_save)
    logging.info("  ------------------------------------")
    logging.info("  TOTAL wall-clock : %8.2fs  (%.1f min)", overall, overall / 60.0)
    logging.info("  sim per agent-day: %8.2fs  (n_agents=%d x n_days=%d)",
                 t_sim / agent_days, n_agents, n_days)
    logging.info(
        "  estimate: a run of N agents x D days ~= %.2fs x N x D "
        "(plus ~%.0fs fixed setup)",
        t_sim / agent_days, t_load + t_build,
    )
    logging.info("================================================")


if __name__ == "__main__":
    main()
