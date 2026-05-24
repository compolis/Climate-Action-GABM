"""Pytest configuration for the cag test suite.

Global fixtures live here. The main job of this file is to keep the
test suite hermetic with respect to the local-LLM provider: since
``SIM_CONFIG['llm_provider']`` defaults to ``"local"`` (research canon
as of 2026-05), any test that calls :func:`cag.abm.sim.run_simulation`
without an explicit provider override would otherwise reach out to
``localhost:8080`` and block on connection timeout for hundreds of
seconds when no ``mlx_lm.server`` is running.

The ``_mock_local_llm_runtime`` fixture below auto-applies to every
test and short-circuits the two runtime helpers
(:func:`cag.io.llm.configure_local` and :func:`cag.io.llm.ping_local`)
so they become silent no-ops. Tests that genuinely need to exercise
local-LLM wiring should mock these explicitly inside the test body and
the autouse fixture will not interfere (``unittest.mock.patch`` stacks
cleanly).

Note: ``sim.py`` uses ``from cag.io.llm import configure_local,
ping_local``, which binds the symbols locally at import time. We
therefore patch BOTH the source module and the ``cag.abm.sim``
re-export so the runtime helpers are neutralised regardless of which
binding is reached first.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _mock_local_llm_runtime():
    """Neutralise local-LLM runtime helpers for every test.

    Stacks four patches:
      - ``cag.io.llm.configure_local`` → no-op
      - ``cag.io.llm.ping_local``       → returns a stub registry entry
      - ``cag.abm.sim.configure_local`` → no-op (sim.py local binding)
      - ``cag.abm.sim.ping_local``      → returns a stub registry entry
    """
    stub_info = {"model": "mock-local", "served_model_name": "mock-local"}
    with patch("cag.io.llm.configure_local", return_value=None), \
         patch("cag.io.llm.ping_local", return_value=stub_info), \
         patch("cag.abm.sim.configure_local", return_value=None), \
         patch("cag.abm.sim.ping_local", return_value=stub_info):
        yield
