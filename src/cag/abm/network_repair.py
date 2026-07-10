"""
Network parameter resolution, connectivity repair, and diagnostics.

Three layers of network hygiene that run during ``_resolve_runtime``:

1. ``_resolve_network_params`` — fold legacy flat keys (``p_intra`` /
   ``p_inter``) into the modern ``network_params`` dict for the factory.
2. ``_adjust_network_params_for_small_n`` — bump connectivity-relevant
   params up (never down) when ``n_citizens`` is below the empirical
   safe-zone thresholds for the chosen network type.
3. ``_auto_connect_components`` — if the realised graph is still disjoint
   after build, add the minimum number of deterministic bridging edges.

Plus two reporting helpers (``_log_network_summary``,
``_safe_network_diagnostics``) and a JSON serialiser
(``_safe_network_snapshot``) used by ``_collect_results``.

Extracted from ``cag.abm.sim`` in the 2026-06-22 refactor; all names are
re-exported from ``cag.abm.sim`` for backwards compatibility.
"""

__version__ = "0.9.0"

import logging
import math

import numpy as np


def _resolve_network_params(cfg):
    """Build the params dict for the network factory.

    Reads the new ``network_params`` dict if present; otherwise falls back
    to the legacy flat keys (``p_intra``, ``p_inter``) so existing
    configurations and notebooks keep working.
    """
    params = dict(cfg.get("network_params") or {})
    network_type = cfg.get("network_type", "stochastic_block")
    if network_type == "stochastic_block":
        for legacy_key in ("p_intra", "p_inter"):
            if legacy_key in cfg and legacy_key not in params:
                val = cfg.get(legacy_key)
                if val is not None:
                    params[legacy_key] = val
    return params


def _adjust_network_params_for_small_n(cfg, n_agents):
    """Layer 1: bump network params to reduce disjoint-graph risk on small n.

    Only raises values; never lowers. Logs every adjustment. Skips
    network types that are always connected by construction
    (watts_strogatz, barabasi_albert).

    SBM thresholds (empirical sweep, p_intra=0.15, 100 trials):
      - n<30:        ~0% connectivity even at p_inter=0.15 -> bump to 0.10 + warn
      - n in [30,100): p_inter=0.05 gives ~80%, 0.06 gives ~89%
      - n>=100:      p_inter=0.05 gives 100% connectivity

    ER thresholds (classical ln(n)/n):
      - n=30  -> 0.113
      - n=50  -> 0.078
      - n=100 -> 0.046
    """
    network_type = cfg.get("network_type", "stochastic_block")
    if network_type in ("watts_strogatz", "barabasi_albert"):
        return  # always connected by construction

    params = dict(cfg.get("network_params") or {})

    if network_type == "stochastic_block":
        current_p_inter = float(
            params.get("p_inter", cfg.get("p_inter", 0.05))
        )
        if n_agents < 30:
            target = 0.10
            if current_p_inter < target:
                logging.warning(
                    "Small population (n=%d): 2-block SBM is unreliable. "
                    "Bumping p_inter %.3f -> %.3f. Consider n>=50 or "
                    "network_type='barabasi_albert'.",
                    n_agents, current_p_inter, target,
                )
                cfg["p_inter"] = target
                params["p_inter"] = target
                cfg["network_params"] = params
        elif n_agents < 100:
            target = 0.06
            if current_p_inter < target:
                logging.info(
                    "Small population (n=%d): bumping p_inter %.3f -> %.3f "
                    "to keep SBM connected (~90%% probability).",
                    n_agents, current_p_inter, target,
                )
                cfg["p_inter"] = target
                params["p_inter"] = target
                cfg["network_params"] = params

    elif network_type == "erdos_renyi":
        current_p = float(params.get("p", 0.10))
        if n_agents < 30:
            target = 0.20
            if current_p < target:
                logging.warning(
                    "Small population (n=%d): Erdos-Renyi connectivity "
                    "threshold is %.3f. Bumping p %.3f -> %.3f.",
                    n_agents, math.log(max(n_agents, 2)) / max(n_agents, 2),
                    current_p, target,
                )
                params["p"] = target
                cfg["network_params"] = params
        elif n_agents < 100:
            target = 0.10
            if current_p < target:
                logging.info(
                    "Small population (n=%d): bumping ER p %.3f -> %.3f "
                    "to stay well above connectivity threshold.",
                    n_agents, current_p, target,
                )
                params["p"] = target
                cfg["network_params"] = params


def _auto_connect_components(nation, seed):
    """Layer 2: if the network is disjoint, add the minimum bridging edges.

    Adds one deterministic edge per smaller component, connecting it to
    the largest component. Sets ``nation._auto_connected_edges`` to the
    number of edges added (0 if the graph was already connected).
    Logs a WARNING when repair is needed so the run is transparent.
    """
    import networkx as nx

    G = getattr(nation, "network", None)
    if not isinstance(G, nx.Graph) or G.number_of_nodes() == 0:
        nation._auto_connected_edges = 0
        return

    if nx.is_connected(G):
        nation._auto_connected_edges = 0
        return

    components = sorted(
        (sorted(c) for c in nx.connected_components(G)),
        key=lambda c: (-len(c), c[0]),  # largest first; tie-break for determinism
    )
    largest = components[0]
    rng = np.random.default_rng(seed)

    n_added = 0
    for comp in components[1:]:
        u_idx = int(rng.integers(0, len(largest)))
        v_idx = int(rng.integers(0, len(comp)))
        u = largest[u_idx]
        v = comp[v_idx]
        G.add_edge(u, v)
        n_added += 1

    # Refresh each agent's network_neighbors so peer messaging picks up
    # the new edges. assign_network_blocks() populates from G's adjacency.
    if hasattr(nation, "assign_network_blocks"):
        nation.assign_network_blocks()

    nation._auto_connected_edges = n_added
    logging.warning(
        "Network was disjoint (%d components, largest=%d/%d nodes). "
        "Auto-connected by adding %d bridging edge(s) (seed=%d).",
        len(components), len(largest), G.number_of_nodes(), n_added, seed,
    )


def _log_network_summary(nation):
    """Layer 3: one-line stdout summary after network setup is final."""
    import networkx as nx

    G = getattr(nation, "network", None)
    if not isinstance(G, nx.Graph) or G.number_of_nodes() == 0:
        return
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    n_comp = nx.number_connected_components(G)
    mean_deg = (2 * n_edges) / n_nodes if n_nodes else 0.0
    auto_added = getattr(nation, "_auto_connected_edges", 0)
    logging.info(
        "Network: n_nodes=%d, n_edges=%d, n_components=%d, "
        "mean_degree=%.2f, auto_connected_edges=%d",
        n_nodes, n_edges, n_comp, mean_deg, auto_added,
    )


def _safe_network_diagnostics(nation, config):
    """Compute network diagnostics, swallowing any error so a long
    simulation never aborts at the reporting stage.

    Returns ``None`` only when there is no graph on the nation. Otherwise
    always returns a dict with the always-on cheap-metric keys present;
    on failure those keys are filled with ``None`` and an ``error`` field
    is attached so downstream consumers can rely on a stable shape.
    """
    G = getattr(nation, "network", None)
    if G is None:
        return None
    try:
        from cag.abm.networks import compute_diagnostics
        timeout = config.get("diagnostics_timeout_s", 30.0)
        diag = compute_diagnostics(
            G, agents=list(nation.agents_active.values()),
            timeout_s=timeout,
        )
        diag["network_type"] = getattr(nation, "network_type", config.get("network_type"))
        diag["network_params"] = getattr(nation, "network_params", None) \
            or _resolve_network_params(config)
        diag["auto_connected_edges"] = int(
            getattr(nation, "_auto_connected_edges", 0)
        )
        return diag
    except Exception as e:  # noqa: BLE001
        logging.warning("Network diagnostics failed: %s", e)
        return {
            "n_nodes": None,
            "n_edges": None,
            "density": None,
            "mean_degree": None,
            "median_degree": None,
            "max_degree": None,
            "degree_histogram": None,
            "n_connected_components": None,
            "largest_component_size": None,
            "assortativity_political_exposure": None,
            "timed_out": False,
            "network_type": getattr(nation, "network_type", config.get("network_type")),
            "network_params": getattr(nation, "network_params", None)
                or _resolve_network_params(config),
            "auto_connected_edges": int(
                getattr(nation, "_auto_connected_edges", 0)
            ),
            "error": str(e),
        }


def _safe_network_snapshot(nation):
    """Serialise the peer graph to a JSON-friendly node/edge list.

    Returns None when there is no graph (e.g. tests that skip network
    creation). Each node carries its bucket and degree so a downstream
    plotter can colour/scale without re-reading agent state.
    """
    G = getattr(nation, "network", None)
    if G is None:
        return None
    try:
        bucket = {a.id: getattr(a, "political_exposure", None)
                  for a in nation.agents_active.values()}
        nodes = [
            {
                "id": str(n),
                "bucket": bucket.get(n),
                "degree": int(G.degree(n)),
            }
            for n in G.nodes()
        ]
        edges = [[str(u), str(v)] for u, v in G.edges()]
        return {"nodes": nodes, "edges": edges}
    except Exception as e:  # noqa: BLE001
        logging.warning("Network snapshot failed: %s", e)
        return None
