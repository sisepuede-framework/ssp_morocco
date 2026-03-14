#!/usr/bin/env python3
"""Generate a Sankey diagram of the SISEPUEDE DAG with emission magnitudes.

Derives edges and layers from compare_to_inventory.DAG_AFFECTS and DAG_ORDER
(single source of truth). Flow widths = source node emission magnitude.
"""

import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go

PROJECT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent

# Import DAG structure from single source of truth
sys.path.insert(0, str(PROJECT / "ssp_modeling" / "output_postprocessing" / "scripts"))
from compare_to_inventory import DAG_AFFECTS, DAG_ORDER

# Find latest WIDE output
runs = sorted((PROJECT / "ssp_modeling" / "ssp_run_output").glob("calibration_*/WIDE_INPUTS_OUTPUTS.csv"))
if not runs:
    print("ERROR: No WIDE_INPUTS_OUTPUTS.csv found"); sys.exit(1)
wide = pd.read_csv(runs[-1])
print(f"Using: {runs[-1].parent.name}")

TP = 7
tp7 = wide[wide['time_period'] == TP].iloc[0]

NAMES = {
    'agrc': 'Agriculture', 'frst': 'Forest', 'lndu': 'Land Use', 'lsmm': 'Manure Mgmt',
    'lvst': 'Livestock', 'soil': 'Soil N\u2082O', 'waso': 'Solid Waste', 'trww': 'Wastewater',
    'ippu': 'IPPU', 'inen': 'Industry Energy', 'scoe': 'Buildings', 'trns': 'Transport',
    'entc': 'Electricity', 'fgtv': 'Fugitive', 'ccsq': 'CCS',
}

COLORS = {
    'agrc': '#8C6D31', 'frst': '#31A354', 'lndu': '#B5CF6B', 'lsmm': '#E7BA52',
    'lvst': '#BD9E39', 'soil': '#8C6D31', 'waso': '#843C39', 'trww': '#D6616B',
    'ccsq': '#C6DBEF', 'entc': '#6B6ECF', 'fgtv': '#393B79', 'inen': '#3182BD',
    'scoe': '#6BAED6', 'trns': '#756BB1', 'ippu': '#CE6DBD',
}

LAYER_LABELS = {0: 'AFOLU', 1: 'Waste', 2: 'IPPU', 3: 'Energy Demand', 4: 'Energy Production', 5: 'Fugitive', 6: 'CCS'}

# Normalize layers to 0-based
min_layer = min(DAG_ORDER.values())
layers = {s: v - min_layer for s, v in DAG_ORDER.items()}
max_layer = max(layers.values())

# Get emissions
emissions = {}
for s in NAMES:
    col = f'emission_co2e_subsector_total_{s}'
    emissions[s] = abs(tp7.get(col, 0.01))

# Derive forward edges from DAG_AFFECTS (cross-layer only)
sankey_edges = []
for src, tgts in DAG_AFFECTS.items():
    for tgt in tgts:
        if tgt in layers and src in layers and layers[tgt] > layers[src]:
            sankey_edges.append((src, tgt))

# Auto-compute Y positions: sort by emission within each layer
layer_groups = {}
for s, l in layers.items():
    layer_groups.setdefault(l, []).append(s)

y_pos = {}
for layer, group in layer_groups.items():
    sorted_nodes = sorted(group, key=lambda s: -emissions.get(s, 0))
    n = len(sorted_nodes)
    for i, s in enumerate(sorted_nodes):
        y_pos[s] = 0.05 + i * (0.90 / max(n - 1, 1)) if n > 1 else 0.5

# Build Sankey
nodes = [s for s in NAMES if s in layers]
node_idx = {s: i for i, s in enumerate(nodes)}
node_x = [0.01 + layers[s] * (0.95 / max(max_layer, 1)) for s in nodes]
node_y = [y_pos.get(s, 0.5) for s in nodes]

sources, targets, values, link_colors = [], [], [], []
for src, tgt in sankey_edges:
    if src not in node_idx or tgt not in node_idx:
        continue
    flow = max(emissions.get(src, 0.01) * 0.25, 0.08)
    sources.append(node_idx[src])
    targets.append(node_idx[tgt])
    values.append(flow)
    hex_c = COLORS.get(src, '#999')
    r, g, b = int(hex_c[1:3], 16), int(hex_c[3:5], 16), int(hex_c[5:7], 16)
    link_colors.append(f'rgba({r},{g},{b},0.35)')

fig = go.Figure(go.Sankey(
    arrangement='fixed',
    node=dict(
        pad=15, thickness=20,
        line=dict(color='white', width=1),
        label=[f'{NAMES[s]}<br>{emissions[s]:.1f} Mt' for s in nodes],
        color=[COLORS.get(s, '#999') for s in nodes],
        x=node_x, y=node_y,
    ),
    link=dict(source=sources, target=targets, value=values, color=link_colors),
))

for layer_num in sorted(set(layers.values())):
    label = LAYER_LABELS.get(layer_num, f'Step {layer_num+1}')
    fig.add_annotation(
        x=0.01 + layer_num * (0.95 / max(max_layer, 1)), y=-0.06,
        text=f'<b>Step {layer_num+1}</b>: {label}',
        showarrow=False, font=dict(size=9, color='gray'),
        xref='paper', yref='paper',
    )

fig.update_layout(
    title=dict(
        text='SISEPUEDE DAG: Emission Flow by Sector Dependency<br>'
             '<sub>Flow width proportional to upstream emission magnitude. '
             f'Derived from DAG_AFFECTS ({len(sankey_edges)} cross-layer edges).</sub>',
        font=dict(size=14),
    ),
    font=dict(size=10), width=1400, height=700,
    margin=dict(l=20, r=20, t=60, b=50),
)

fig.write_image(str(OUT_DIR / 'dag_sankey.png'), scale=2)
print(f"  dag_sankey.png ({len(sankey_edges)} edges, {len(nodes)} nodes)")

fig.write_html(str(OUT_DIR / 'dag_sankey.html'))
print("  dag_sankey.html (interactive)")
