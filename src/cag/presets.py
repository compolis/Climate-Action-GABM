"""
Run-bundle presets for the Climate-Action-GABM CLI.

A "run bundle" is just a named dict of ``SIM_CONFIG`` overrides that the
``--preset NAME`` flag merges in. Each entry uses ``SIM_CONFIG`` keys
directly (see :mod:`cag.abm.sim`); ``"days"`` accepts an integer
day-count that ``cag.__main__`` expands to the alternating P-A / P-B / C
schedule via :func:`cag.__main__.build_days`.

Adding a preset is **optional**. Every knob is independently composable as
a ``--flag`` at the sbatch command line, so new experiments never require
a preset definition — sweeps stay in sbatch text files (see
``scripts/aire/sweeps/``).

Application order (lowest → highest precedence)::

    SIM_CONFIG defaults (sim.py)
        → preset bundle (this module)
            → individual --flag overrides
"""

__version__ = "0.9.0"


RUN_BUNDLE_PRESETS = {
    "smoke": {
        "description": (
            "Fast smoke-test run shape: 10 agents, 2 days, no peer "
            "messaging. Does NOT pin a model — Mac picks up the SIM_CONFIG "
            "default (mlx-lm Qwen3-8B-4bit on http://localhost:8080/v1), "
            "AIRE picks up scripts/aire/run.sh's --model $HF_MODEL. "
            "Override with --provider / --model to retest against an API."
        ),
        "config": {
            "n_citizens": 10,
            "days": 2,
            "k_peers_per_day": 0,
            "thinking": False,
        },
    },
    "r14_canonical": {
        "description": (
            "Run-14 baseline run shape: 50 agents, 5 days, no peer "
            "messaging, Day-0 anchor = ground-truth + rationale. Does NOT "
            "pin a model: on AIRE scripts/aire/run.sh forces "
            "--model $HF_MODEL (default Qwen/Qwen3-14B via vLLM); on Mac "
            "the SIM_CONFIG default (mlx-community/Qwen3-8B-4bit via "
            "mlx-lm) applies. Exposure target must be set explicitly via "
            "--exposure-targets (e.g. split50)."
        ),
        "config": {
            "n_citizens": 50,
            "days": 5,
            "k_peers_per_day": 0,
            "thinking": False,
            "day0_anchor": "ground_truth_with_rationale",
        },
    },
    "tierP": {
        "description": (
            "Tier-P persona-null run shape: 100 agents, Day-0-only "
            "(single empty-phase day so no broadcasts or peer messaging), "
            "package mode, Day-0 anchor = llm_survey so each Day-0 opinion "
            "is a pure function of (persona + policy question), memory = "
            "persona_only to remove cross-policy leakage. Does NOT pin a "
            "model (AIRE run.sh forces --model $HF_MODEL, default "
            "Qwen/Qwen3-14B; Mac uses the SIM_CONFIG default). Set the "
            "arm with --persona-mode {real,shuffled,neutral} and vary "
            "--seed for the permutation."
        ),
        "config": {
            "n_citizens": 100,
            "days": [{"phases": []}],
            "k_peers_per_day": 0,
            "communication_mode": "package",
            "day0_anchor": "llm_survey",
            "memory": "persona_only",
            "thinking": False,
        },
    },
    "tier1": {
        "description": (
            "Tier-1 bias-invariance run shape: 100 agents, 5-day "
            "alternating P-A/P-B/C schedule, package mode, k_peers=2, "
            "Day-0 anchor = ground_truth_with_rationale (so any end-of-run "
            "gap above ground truth is pure pro-climate drift). Exposure, "
            "network, message set and temperature all fall through "
            "to the SIM_CONFIG research canon (committed_minority_symmetric "
            "targets, stochastic_block p_intra=0.15/p_inter=0.05, offline "
            "v1 messages, temp 0.5). Memory is pinned to the v0.9 canon "
            "(full default sections, but the Day-0 anchor expires after "
            "day 1 via ttl_days=1) to match the pilot config exactly. "
            "Does NOT pin a model "
            "(AIRE run.sh forces --model $HF_MODEL, default Qwen/Qwen3-14B; "
            "Mac uses the SIM_CONFIG default). Set the reach-asymmetry "
            "condition with --reach-a / --reach-b, the no-broadcast placebo "
            "with --exposure-targets neither, and vary --seed. This is the "
            "honest multi-seed successor to the seed-42/n=50 v0.8 pilot. "
            "Both use the same canon p_inter=0.05: at n=100 the SBM is 100% "
            "connected so 0.05 stands, whereas the pilot's n=50 was auto-"
            "bumped to 0.06 by the documented small-n connectivity repair "
            "(_adjust_network_params_for_small_n; n in [30,100) -> 0.06). "
            "So this is not a deliberate deviation — it is the same base "
            "canon under the n-dependent repair."
        ),
        "config": {
            "n_citizens": 100,
            "days": 5,
            "k_peers_per_day": 2,
            "communication_mode": "package",
            "day0_anchor": "ground_truth_with_rationale",
            "memory": {"day0_anchor": {"ttl_days": 1}},
            "thinking": False,
        },
    },
}


def list_presets():
    """Print all registered presets with their config to stdout."""
    if not RUN_BUNDLE_PRESETS:
        print("(no presets registered)")
        return
    for name, entry in RUN_BUNDLE_PRESETS.items():
        print(f"\n{name}")
        print(f"  {entry['description']}")
        print("  config:")
        for k, v in entry["config"].items():
            print(f"    {k} = {v!r}")
    print()
