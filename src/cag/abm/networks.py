"""
Pluggable peer-network factory for Climate-Action-GABM.

Provides several alternative graph models keyed by ``network_type``:

- ``stochastic_block``     — current 2-block SBM driven by ``political_exposure``.
- ``erdos_renyi``          — ``G(n, p)`` null model.
- ``watts_strogatz``       — small-world (mean degree ``k``, rewire prob ``beta``).
- ``barabasi_albert``      — preferential attachment / scale-free (param ``m``).
- ``homophily_weighted``   — continuous similarity-weighted random graph over
                             a configurable subset of citizen attributes.

Plus a single :func:`compute_diagnostics` entry point that always reports
cheap structural metrics and conditionally reports clustering / path-length /
diameter under a wall-clock timeout so no algorithm runs unbounded.

All builders return an ``nx.Graph`` whose nodes are agent IDs (so
``SurveyedNation.assign_network_blocks`` works unchanged regardless of
topology).
"""
from __future__ import annotations

import logging
import math
import signal
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterable, List, Sequence

import networkx as nx
import numpy as np


# ── Public registry ────────────────────────────────────────────────

NETWORK_TYPES = (
    "stochastic_block",
    "erdos_renyi",
    "watts_strogatz",
    "barabasi_albert",
    "homophily_weighted",
)

# Default attribute set for the homophily-weighted builder.
# Must be names of attributes accessible on a SurveyedCitizen.
DEFAULT_HOMOPHILY_ATTRIBUTES = ("ukge2019_vote_id", "brexit_vote_id", "region_id")


# ── Builder dispatch ───────────────────────────────────────────────

def build_network(
    network_type: str,
    agents: Sequence[Any],
    params: Dict[str, Any] | None = None,
    seed: int = 42,
) -> nx.Graph:
    """Build a peer network of the requested type.

    Parameters
    ----------
    network_type
        One of :data:`NETWORK_TYPES`.
    agents
        Ordered iterable of agent objects. Each must have an ``id`` attribute;
        the returned graph's nodes are these IDs.
    params
        Type-specific parameter dict. See per-builder docstrings.
    seed
        Random seed (int).

    Returns
    -------
    nx.Graph
        Undirected graph whose nodes are agent IDs.
    """
    params = dict(params or {})
    if network_type not in NETWORK_TYPES:
        raise ValueError(
            f"Unknown network_type {network_type!r}; "
            f"valid options: {NETWORK_TYPES}"
        )

    agents = list(agents)
    n = len(agents)
    if n == 0:
        raise ValueError("Cannot build a network with zero agents.")

    builder = _BUILDERS[network_type]
    return builder(agents, params, int(seed))


# ── Individual builders ────────────────────────────────────────────

def _build_stochastic_block(
    agents: Sequence[Any], params: Dict[str, Any], seed: int
) -> nx.Graph:
    """Two-block SBM driven by ``political_exposure``.

    Parameters: ``p_intra`` (float, default 0.15),
    ``p_inter`` (float, default 0.02).

    A-only -> block 0, B-only -> block 1, both/neither swing
    (round-robin distributed). This preserves the v0.5 behaviour.
    """
    p_intra = float(params.get("p_intra", 0.15))
    p_inter = float(params.get("p_inter", 0.02))

    block_0, block_1, swing = [], [], []
    for citizen in agents:
        exposure = getattr(citizen, "political_exposure", None)
        if exposure == "A-only":
            block_0.append(citizen)
        elif exposure == "B-only":
            block_1.append(citizen)
        else:
            swing.append(citizen)

    for i, citizen in enumerate(swing):
        (block_0 if i % 2 == 0 else block_1).append(citizen)

    ordered = block_0 + block_1
    sizes = [len(block_0), len(block_1)]
    p_matrix = [[p_intra if i == j else p_inter for j in range(2)] for i in range(2)]

    G = nx.stochastic_block_model(sizes, p_matrix, seed=seed)
    return _relabel_to_agent_ids(G, ordered)


def _build_erdos_renyi(
    agents: Sequence[Any], params: Dict[str, Any], seed: int
) -> nx.Graph:
    """Erdős–Rényi ``G(n, p)`` null model.

    Parameters: ``p`` (float, default 0.05).
    """
    p = float(params.get("p", 0.05))
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"erdos_renyi: p must be in [0, 1], got {p!r}.")
    G = nx.erdos_renyi_graph(len(agents), p, seed=seed)
    return _relabel_to_agent_ids(G, agents)


def _build_watts_strogatz(
    agents: Sequence[Any], params: Dict[str, Any], seed: int
) -> nx.Graph:
    """Watts–Strogatz small-world graph.

    Parameters: ``k`` (int, mean degree, default 6, must be even and < n),
    ``beta`` (float, rewire probability, default 0.1).
    """
    n = len(agents)
    k = int(params.get("k", 6))
    beta = float(params.get("beta", 0.1))
    if k < 2 or k % 2 != 0:
        raise ValueError(f"watts_strogatz: k must be an even integer >= 2, got {k!r}.")
    if k >= n:
        raise ValueError(f"watts_strogatz: k ({k}) must be < n ({n}).")
    if not 0.0 <= beta <= 1.0:
        raise ValueError(f"watts_strogatz: beta must be in [0, 1], got {beta!r}.")
    G = nx.watts_strogatz_graph(n, k, beta, seed=seed)
    return _relabel_to_agent_ids(G, agents)


def _build_barabasi_albert(
    agents: Sequence[Any], params: Dict[str, Any], seed: int
) -> nx.Graph:
    """Barabási–Albert preferential attachment / scale-free graph.

    Parameters: ``m`` (int, edges per new node, default 3, must be 1 <= m < n).
    """
    n = len(agents)
    m = int(params.get("m", 3))
    if m < 1 or m >= n:
        raise ValueError(f"barabasi_albert: m must satisfy 1 <= m < n, got m={m}, n={n}.")
    G = nx.barabasi_albert_graph(n, m, seed=seed)
    return _relabel_to_agent_ids(G, agents)


def _build_homophily_weighted(
    agents: Sequence[Any], params: Dict[str, Any], seed: int
) -> nx.Graph:
    """Continuous similarity-weighted random graph.

    Edge probability between i and j is::

        p_ij = sigmoid(scale * sim(i, j) - threshold)

    where ``sim(i, j) ∈ [0, 1]`` is a weighted mean of per-attribute
    similarities (1.0 if categorical attrs match; 1 - normalised distance
    for numeric attrs).

    Parameters
    ----------
    attributes : list[str]
        Citizen attribute names to use. Defaults to
        :data:`DEFAULT_HOMOPHILY_ATTRIBUTES`.
    weights : list[float] | None
        Per-attribute weights (same length as ``attributes``).
        ``None`` → uniform.
    scale : float
        Steepness of the sigmoid. Default 6.0.
    threshold : float
        Raw threshold (no auto-tuning). Default 3.0. Larger ⇒ sparser graph.
    """
    n = len(agents)
    attributes = list(params.get("attributes") or DEFAULT_HOMOPHILY_ATTRIBUTES)
    weights = params.get("weights")
    scale = float(params.get("scale", 6.0))
    threshold = float(params.get("threshold", 3.0))

    if not attributes:
        raise ValueError("homophily_weighted: attributes list must be non-empty.")
    if weights is None:
        weights = [1.0] * len(attributes)
    weights = [float(w) for w in weights]
    if len(weights) != len(attributes):
        raise ValueError(
            "homophily_weighted: len(weights) must equal len(attributes)."
        )
    w_sum = sum(weights)
    if w_sum <= 0:
        raise ValueError("homophily_weighted: weights must sum to a positive value.")
    weights = [w / w_sum for w in weights]

    # Pre-extract attribute vectors and per-attribute numeric ranges.
    columns: List[List[Any]] = []
    is_numeric: List[bool] = []
    ranges: List[float] = []
    for attr in attributes:
        col = [getattr(a, attr, None) for a in agents]
        numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool)
                      for v in col if v is not None)
        is_numeric.append(numeric)
        if numeric:
            vals = [v for v in col if v is not None]
            rng = (max(vals) - min(vals)) if vals else 0.0
            ranges.append(float(rng) if rng > 0 else 1.0)
        else:
            ranges.append(1.0)
        columns.append(col)

    rng = np.random.default_rng(seed)
    G = nx.Graph()
    G.add_nodes_from(a.id for a in agents)

    for i in range(n):
        for j in range(i + 1, n):
            sim = 0.0
            for k, attr in enumerate(attributes):
                vi, vj = columns[k][i], columns[k][j]
                if vi is None or vj is None:
                    s = 0.0
                elif is_numeric[k]:
                    s = 1.0 - abs(float(vi) - float(vj)) / ranges[k]
                else:
                    s = 1.0 if vi == vj else 0.0
                sim += weights[k] * s
            p_ij = 1.0 / (1.0 + math.exp(-(scale * sim - threshold)))
            if rng.random() < p_ij:
                G.add_edge(agents[i].id, agents[j].id)

    return G


_BUILDERS: Dict[str, Callable[[Sequence[Any], Dict[str, Any], int], nx.Graph]] = {
    "stochastic_block":   _build_stochastic_block,
    "erdos_renyi":        _build_erdos_renyi,
    "watts_strogatz":     _build_watts_strogatz,
    "barabasi_albert":    _build_barabasi_albert,
    "homophily_weighted": _build_homophily_weighted,
}


# ── Helpers ────────────────────────────────────────────────────────

def _relabel_to_agent_ids(G: nx.Graph, ordered_agents: Sequence[Any]) -> nx.Graph:
    """Relabel integer-indexed graph nodes to agent IDs."""
    mapping = {i: ordered_agents[i].id for i in range(len(ordered_agents))}
    return nx.relabel_nodes(G, mapping)


# ── Diagnostics ────────────────────────────────────────────────────

# Hard caps to prevent the conditional metrics from running on huge graphs.
_CLUSTERING_NODE_CAP = 5000
_PATHLEN_NODE_CAP = 2000
_DIAMETER_NODE_CAP = 2000
# When average shortest path length is requested we sample at most this
# many source nodes from the largest connected component.
_PATHLEN_SAMPLE_CAP = 500


class _DiagnosticsTimeout(Exception):
    pass


@contextmanager
def _wallclock_timeout(seconds: float):
    """SIGALRM-based wall-clock timeout. POSIX-only; falls back to no-op
    elsewhere (Windows). Used as a hard ceiling on the conditional metric
    block, separate from the per-metric size caps."""
    if seconds is None or seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handler(signum, frame):
        raise _DiagnosticsTimeout()

    old = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, float(seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def compute_diagnostics(
    G: nx.Graph,
    agents: Iterable[Any] | None = None,
    timeout_s: float | None = 30.0,
) -> Dict[str, Any]:
    """Compute structural diagnostics for a peer network.

    Returns a dict with always-on cheap metrics plus conditional metrics
    (clustering, average shortest path length, diameter) that are skipped
    or timed out gracefully on large/expensive graphs. Each conditional
    metric has its own ``<name>_skipped_reason`` key when omitted.

    Parameters
    ----------
    G
        The graph.
    agents
        Optional iterable of agent objects (used for assortativity by
        ``political_exposure``). If ``None`` or any agent lacks the attribute,
        assortativity is reported as ``None``.
    timeout_s
        Wall-clock cap on the conditional-metrics block. ``None`` or
        non-positive disables the cap. POSIX-only; ignored on Windows.
    """
    n = G.number_of_nodes()
    m = G.number_of_edges()
    degrees = [d for _, d in G.degree()]
    max_possible_edges = n * (n - 1) / 2 if n > 1 else 0

    # Always-on cheap metrics
    out: Dict[str, Any] = {
        "n_nodes": n,
        "n_edges": m,
        "density": (m / max_possible_edges) if max_possible_edges else 0.0,
        "mean_degree": float(np.mean(degrees)) if degrees else 0.0,
        "median_degree": float(np.median(degrees)) if degrees else 0.0,
        "max_degree": int(max(degrees)) if degrees else 0,
        "degree_histogram": _degree_histogram(degrees, bins=20),
        "n_connected_components": nx.number_connected_components(G),
        "largest_component_size": (
            max(len(c) for c in nx.connected_components(G)) if n > 0 else 0
        ),
    }

    # Assortativity by political_exposure (categorical, cheap)
    if agents is not None:
        exp_map: Dict[Any, str] = {}
        for a in agents:
            exp = getattr(a, "political_exposure", None)
            if exp is not None and a.id in G:
                exp_map[a.id] = exp
        if exp_map and len(exp_map) == n:
            try:
                nx.set_node_attributes(G, exp_map, "_exposure")
                out["assortativity_political_exposure"] = float(
                    nx.attribute_assortativity_coefficient(G, "_exposure")
                )
            except Exception as e:  # noqa: BLE001 — diagnostics must not crash a run
                out["assortativity_political_exposure"] = None
                out["assortativity_political_exposure_error"] = str(e)
            finally:
                for nid in list(G.nodes):
                    G.nodes[nid].pop("_exposure", None)
        else:
            out["assortativity_political_exposure"] = None
    else:
        out["assortativity_political_exposure"] = None

    # Conditional / capped metrics (under a single wall-clock timeout)
    out["timed_out"] = False
    started = time.monotonic()
    try:
        with _wallclock_timeout(timeout_s):
            # Clustering
            if n > _CLUSTERING_NODE_CAP:
                out["average_clustering_skipped_reason"] = (
                    f"n={n} exceeds cap {_CLUSTERING_NODE_CAP}"
                )
            else:
                out["average_clustering"] = float(nx.average_clustering(G))

            # Avg shortest path length & diameter (need connectivity)
            if n > _PATHLEN_NODE_CAP:
                out["average_shortest_path_length_skipped_reason"] = (
                    f"n={n} exceeds cap {_PATHLEN_NODE_CAP}"
                )
                out["diameter_skipped_reason"] = (
                    f"n={n} exceeds cap {_DIAMETER_NODE_CAP}"
                )
            else:
                if nx.is_connected(G):
                    target = G
                    sub_note = None
                else:
                    largest_cc = max(nx.connected_components(G), key=len)
                    target = G.subgraph(largest_cc).copy()
                    sub_note = (
                        f"graph disconnected; computed on largest component "
                        f"({target.number_of_nodes()}/{n} nodes)"
                    )

                # Diameter on the (possibly sub) graph, only if small enough
                if target.number_of_nodes() <= _DIAMETER_NODE_CAP:
                    out["diameter"] = int(nx.diameter(target))
                    if sub_note:
                        out["diameter_note"] = sub_note
                else:
                    out["diameter_skipped_reason"] = (
                        f"largest-component n={target.number_of_nodes()} "
                        f"exceeds cap {_DIAMETER_NODE_CAP}"
                    )

                # Avg shortest path: sample sources if component is large
                if target.number_of_nodes() <= _PATHLEN_SAMPLE_CAP:
                    out["average_shortest_path_length"] = float(
                        nx.average_shortest_path_length(target)
                    )
                else:
                    out["average_shortest_path_length"] = (
                        _sampled_average_path_length(
                            target, sample=_PATHLEN_SAMPLE_CAP, seed=0
                        )
                    )
                    out["average_shortest_path_length_note"] = (
                        f"estimated from {_PATHLEN_SAMPLE_CAP} sampled sources"
                    )
                if sub_note and "average_shortest_path_length" in out:
                    out["average_shortest_path_length_note"] = (
                        sub_note + "; " + out.get(
                            "average_shortest_path_length_note", ""
                        )
                    ).rstrip("; ")
    except _DiagnosticsTimeout:
        out["timed_out"] = True
        out["timeout_s"] = float(timeout_s) if timeout_s else None
        logging.warning(
            "Network diagnostics timed out after %.1fs; partial results saved.",
            timeout_s,
        )

    out["elapsed_s"] = round(time.monotonic() - started, 4)
    return out


def _degree_histogram(degrees: Sequence[int], bins: int = 20) -> Dict[str, List[float]]:
    if not degrees:
        return {"bin_edges": [], "counts": []}
    counts, edges = np.histogram(degrees, bins=bins)
    return {
        "bin_edges": [float(e) for e in edges],
        "counts": [int(c) for c in counts],
    }


def _sampled_average_path_length(G: nx.Graph, sample: int, seed: int) -> float:
    rng = np.random.default_rng(seed)
    nodes = list(G.nodes)
    chosen = rng.choice(len(nodes), size=min(sample, len(nodes)), replace=False)
    total = 0.0
    pairs = 0
    for idx in chosen:
        src = nodes[int(idx)]
        lengths = nx.single_source_shortest_path_length(G, src)
        for tgt, d in lengths.items():
            if tgt == src:
                continue
            total += d
            pairs += 1
    return total / pairs if pairs else 0.0
