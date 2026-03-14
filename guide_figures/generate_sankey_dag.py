#!/usr/bin/env python3
"""Generate a Sankey diagram of the SISEPUEDE DAG with emission magnitudes.

Flow widths = source node emission magnitude (shows upstream impact).
Layout left-to-right by DAG execution step.
"""

import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go

PROJECT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent

# Find latest WIDE output
runs = sorted((PROJECT / "ssp_modeling" / "ssp_run_output").glob("calibration_*/WIDE_INPUTS_OUTPUTS.csv"))
if not runs:
    print("ERROR: No WIDE_INPUTS_OUTPUTS.csv found"); sys.exit(1)
wide = pd.read_csv(runs[-1])
print(f"Using: {runs[-1].parent.name}")

TP = 7
tp7 = wide[wide['time_period'] == TP].iloc[0]

# Subsector metadata
NAMES = {
    'agrc': 'Agriculture', 'frst': 'Forest', 'lndu': 'Land Use', 'lsmm': 'Manure Mgmt',
    'lvst': 'Livestock', 'soil': 'Soil N₂O', 'waso': 'Solid Waste', 'trww': 'Wastewater',
    'ippu': 'IPPU', 'inen': 'Industry Energy', 'scoe': 'Buildings', 'trns': 'Transport',
    'entc': 'Electricity', 'fgtv': 'Fugitive', 'ccsq': 'CCS',
}

COLORS = {
    'agrc': '#8C6D31', 'frst': '#31A354', 'lndu': '#B5CF6B', 'lsmm': '#E7BA52',
    'lvst': '#BD9E39', 'soil': '#8C6D31', 'waso': '#843C39', 'trww': '#D6616B',
    'ccsq': '#C6DBEF', 'entc': '#6B6ECF', 'fgtv': '#393B79', 'inen': '#3182BD',
    'scoe': '#6BAED6', 'trns': '#756BB1', 'ippu': '#CE6DBD',
}

# DAG layers (x-position)
LAYERS = {
    'lvst': 0, 'lsmm': 0, 'agrc': 0, 'soil': 0, 'lndu': 0, 'frst': 0,
    'waso': 1, 'trww': 1,
    'ippu': 2,
    'inen': 3, 'scoe': 3, 'trns': 3,
    'entc': 4,
    'fgtv': 5, 'ccsq': 5,
}

LAYER_NAMES = {
    0: 'AFOLU', 1: 'Waste', 2: 'IPPU', 3: 'Energy Demand', 4: 'Energy Production', 5: 'Fugitive',
}

# DAG edges (verified against sisepuede source code)
DAG_EDGES = {
    'lvst': ['lsmm', 'soil', 'lndu', 'agrc', 'waso', 'inen'],
    'lsmm': ['soil', 'entc'],
    'agrc': ['soil', 'inen', 'entc', 'waso'],
    'lndu': ['frst', 'soil', 'agrc'],
    'frst': [], 'soil': [],
    'waso': ['entc', 'ippu'],
    'trww': ['entc'],
    'wali': [],
    'ippu': ['inen', 'entc'],
    'inen': ['entc', 'fgtv'],
    'scoe': ['entc', 'fgtv'],
    'trns': ['entc', 'fgtv'],
    'entc': ['fgtv'],
    'fgtv': [], 'ccsq': [],
}

# Get emissions
emissions = {}
for s in NAMES:
    col = f'emission_co2e_subsector_total_{s}'
    emissions[s] = abs(tp7.get(col, 0.01))

# Only show cross-layer edges in Sankey (within-layer edges clutter)
# Also filter to edges where source has meaningful emissions
nodes = [s for s in NAMES if s != 'wali']
node_idx = {s: i for i, s in enumerate(nodes)}

# Build Sankey links — all forward edges (cross-layer + selected within-layer)
sources, targets, values, link_colors = [], [], [], []
MIN_FLOW = 0.08

# Curated edges: show the most important DAG dependencies
# Skip noisy within-AFOLU edges (e.g., lvst→lndu, lndu→agrc) to avoid spaghetti
SANKEY_EDGES = [
    # AFOLU internals (key flows only)
    ('lvst', 'lsmm'),   # livestock → manure management
    ('agrc', 'soil'),    # crops → soil N2O (residue N)
    ('lndu', 'frst'),   # land use → forest
    # AFOLU → Waste
    ('lvst', 'waso'),    # animal mass → waste
    ('agrc', 'waso'),    # food loss → MSW
    # AFOLU → Energy
    ('agrc', 'inen'),    # crop yield → ag energy
    ('lvst', 'inen'),    # animal mass → ag energy
    # Waste → IPPU
    ('waso', 'ippu'),    # recycled waste
    # Waste/Manure → Electricity
    ('lsmm', 'entc'),    # manure biogas
    ('waso', 'entc'),    # waste biogas + incineration
    ('trww', 'entc'),    # WW biogas
    # IPPU → Energy
    ('ippu', 'inen'),    # production volumes → industrial energy
    # Energy Demand → Electricity
    ('inen', 'entc'),
    ('scoe', 'entc'),
    ('trns', 'entc'),
    # Energy → Fugitive
    ('inen', 'fgtv'),
    ('scoe', 'fgtv'),
    ('trns', 'fgtv'),
    ('entc', 'fgtv'),
]

for src, tgt in SANKEY_EDGES:
    if src not in node_idx or tgt not in node_idx:
        continue
    flow = max(emissions.get(src, 0.01) * 0.25, MIN_FLOW)
    sources.append(node_idx[src])
    targets.append(node_idx[tgt])
    values.append(flow)
    hex_c = COLORS.get(src, '#999')
    r, g, b = int(hex_c[1:3], 16), int(hex_c[3:5], 16), int(hex_c[5:7], 16)
    link_colors.append(f'rgba({r},{g},{b},0.35)')

# Node labels with emissions
node_labels = [f'{NAMES[s]}<br>{emissions[s]:.1f} Mt' for s in nodes]
node_colors = [COLORS.get(s, '#999') for s in nodes]

# Position nodes by layer (x) and spread vertically (y)
layer_groups = {}
for s in nodes:
    layer = LAYERS.get(s, 0)
    layer_groups.setdefault(layer, []).append(s)

node_x, node_y = [], []
# Manual y-positions for clean layout (0=top, 1=bottom)
Y_POS = {
    # AFOLU layer — spread vertically, big emitters prominent
    'soil': 0.02, 'lvst': 0.18, 'agrc': 0.35, 'lndu': 0.52, 'lsmm': 0.68, 'frst': 0.85,
    # Waste
    'waso': 0.35, 'trww': 0.60,
    # IPPU
    'ippu': 0.30,
    # Energy demand
    'inen': 0.15, 'scoe': 0.45, 'trns': 0.75,
    # Energy production — ENTC is the big convergence point
    'entc': 0.40,
    # Fugitive/CCS
    'fgtv': 0.40, 'ccsq': 0.75,
}
for s in nodes:
    layer = LAYERS.get(s, 0)
    node_x.append(0.01 + layer * 0.195)
    node_y.append(Y_POS.get(s, 0.5))

fig = go.Figure(go.Sankey(
    arrangement='snap',
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color='white', width=1),
        label=node_labels,
        color=node_colors,
        x=node_x,
        y=node_y,
    ),
    link=dict(
        source=sources,
        target=targets,
        value=values,
        color=link_colors,
    ),
))

# Add layer annotations
for layer, name in LAYER_NAMES.items():
    fig.add_annotation(
        x=0.02 + layer * 0.19,
        y=-0.06,
        text=f'<b>Step {layer+1}</b>: {name}',
        showarrow=False,
        font=dict(size=9, color='gray'),
        xref='paper', yref='paper',
    )

fig.update_layout(
    title=dict(
        text='SISEPUEDE DAG: Emission Flow by Sector Dependency<br>'
             '<sub>Flow width proportional to upstream emission magnitude. '
             'Layout follows model execution order (left → right).</sub>',
        font=dict(size=14),
    ),
    font=dict(size=10),
    width=1400,
    height=700,
    margin=dict(l=20, r=20, t=60, b=50),
)

fig.write_image(str(OUT_DIR / 'dag_sankey.png'), scale=2)
print("  dag_sankey.png")

# Also save an HTML version for interactive exploration
fig.write_html(str(OUT_DIR / 'dag_sankey.html'))
print("  dag_sankey.html (interactive)")
