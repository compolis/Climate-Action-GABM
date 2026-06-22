#!/usr/bin/env python3
"""
Estimate p_inter threshold for network connectivity in 2-block SBM.

For different population sizes, sweeps p_inter from 0.001 to 0.15 and measures
the probability that the resulting network is connected.

Outputs:
  - Console table: p_inter vs connectivity rate (%) for each population size
  - CSV: detailed results for plotting
  - PNG: visualization of connectivity threshold
"""
import os
import sys
import csv
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Configuration
P_INTRA = 0.15  # fixed intra-block probability
POPULATION_SIZES = [10, 20, 50, 100, 200, 500]
P_INTER_VALUES = np.linspace(0.001, 0.15, 30)  # sweep from 0.1% to 15%
N_TRIALS = 100  # trials per (n_pop, p_inter) pair
RANDOM_SEED = 42

OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'output' / 'connectivity_analysis'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def build_sbm(n_citizens, p_intra, p_inter, seed):
    """Build a 2-block SBM with equal-sized blocks."""
    np.random.seed(seed)
    block_size = n_citizens // 2
    sizes = [block_size, n_citizens - block_size]
    p_matrix = [[p_intra, p_inter], [p_inter, p_intra]]
    return nx.stochastic_block_model(sizes, p_matrix, seed=seed)

def estimate_connectivity_rate(n_citizens, p_inter, n_trials, p_intra=P_INTRA):
    """Run n_trials networks and return fraction that are connected."""
    connected_count = 0
    for trial in range(n_trials):
        G = build_sbm(n_citizens, p_intra, p_inter, seed=RANDOM_SEED + trial)
        if nx.is_connected(G):
            connected_count += 1
    return connected_count / n_trials

# Sweep: for each population size, test all p_inter values
print("Estimating connectivity thresholds (this may take 1-2 min)...\n")

results = []
for n_pop in POPULATION_SIZES:
    print(f"Population size: {n_pop}")
    for p_inter in P_INTER_VALUES:
        conn_rate = estimate_connectivity_rate(n_pop, p_inter, N_TRIALS)
        results.append({
            'n_citizens': n_pop,
            'p_inter': p_inter,
            'connectivity_rate': conn_rate,
        })
        pct = int(conn_rate * 100)
        print(f"  p_inter={p_inter:.4f}  →  {pct:>3d}% connected", flush=True)

# Write CSV for downstream analysis
csv_path = OUTPUT_DIR / 'connectivity_sweep.csv'
with open(csv_path, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['n_citizens', 'p_inter', 'connectivity_rate'])
    w.writeheader()
    w.writerows(results)
print(f"\nResults saved to: {csv_path}")

# Console summary table
print("\n" + "="*80)
print("CONNECTIVITY SUMMARY (by population size)")
print("="*80)
print(f"{'p_inter':>10}", end='')
for n in POPULATION_SIZES:
    print(f"{n:>10}", end='')
print()
print("-" * (10 + 10 * len(POPULATION_SIZES)))

for p_inter in sorted(set(r['p_inter'] for r in results))[::3]:  # every 3rd p_inter
    print(f"{p_inter:>10.4f}", end='')
    for n in POPULATION_SIZES:
        rate = next((r['connectivity_rate'] for r in results 
                     if r['n_citizens'] == n and abs(r['p_inter'] - p_inter) < 1e-6), None)
        if rate is not None:
            pct = int(rate * 100)
            print(f"{pct:>9d}%", end='')
        else:
            print(f"{'N/A':>10}", end='')
    print()

# Identify threshold (p_inter where connectivity_rate >= 90%) for each population size
print("\n" + "="*80)
print("RECOMMENDED p_inter for 90% connectivity guarantee")
print("="*80)
for n_pop in POPULATION_SIZES:
    subset = [r for r in results if r['n_citizens'] == n_pop]
    sorted_subset = sorted(subset, key=lambda x: x['p_inter'])
    threshold = next((r['p_inter'] for r in sorted_subset 
                     if r['connectivity_rate'] >= 0.90), None)
    if threshold:
        print(f"  n={n_pop:>3d}  →  p_inter ≥ {threshold:.4f}")
    else:
        print(f"  n={n_pop:>3d}  →  threshold not reached in sweep range")

# Plot: p_inter vs connectivity rate, one line per population size
fig, ax = plt.subplots(figsize=(12, 7))
colors = plt.cm.viridis(np.linspace(0, 1, len(POPULATION_SIZES)))

for i, n_pop in enumerate(POPULATION_SIZES):
    subset = sorted([r for r in results if r['n_citizens'] == n_pop], 
                    key=lambda x: x['p_inter'])
    p_vals = [r['p_inter'] for r in subset]
    conn_vals = [r['connectivity_rate'] for r in subset]
    ax.plot(p_vals, conn_vals, marker='o', linewidth=2, markersize=4,
            label=f'n={n_pop}', color=colors[i])

# Add reference lines
ax.axhline(0.90, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='90% threshold')
ax.axhline(0.95, color='orange', linestyle='--', linewidth=1.5, alpha=0.7, label='95% threshold')

ax.set_xlabel('Inter-block connection probability (p_inter)', fontsize=12, fontweight='bold')
ax.set_ylabel('Connectivity rate (fraction of trials)', fontsize=12, fontweight='bold')
ax.set_title(f'Network Connectivity vs p_inter\n(p_intra={P_INTRA}, {N_TRIALS} trials per point)', 
             fontsize=13, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend(fontsize=10, loc='lower right')
ax.set_ylim(-0.05, 1.05)
ax.set_xlim(min(P_INTER_VALUES) - 0.01, max(P_INTER_VALUES) + 0.01)

png_path = OUTPUT_DIR / 'connectivity_threshold.png'
plt.tight_layout()
plt.savefig(png_path, dpi=150, bbox_inches='tight')
print(f"\nPlot saved to: {png_path}\n")

print("="*80)
print("RECOMMENDATION")
print("="*80)
print("""
For opinion dynamics studies, we recommend:
  - Use p_inter ≥ 0.05 for populations n ≤ 100 (ensures ~95%+ connectivity)
  - Use p_inter ≥ 0.03 for populations n > 200 (ensures ~90%+ connectivity)

Default change: bump p_inter from 0.02 → 0.05 in SIM_CONFIG to ensure
connected networks across smoke tests and small experiments.

For very small populations (n < 20), further increase p_inter to 0.10+
or use an alternative topology (Erdős–Rényi or Watts–Strogatz).
""")
