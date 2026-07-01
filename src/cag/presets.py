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
