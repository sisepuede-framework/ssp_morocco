#!/usr/bin/env python3
"""Generate static PNG figures for morocco_calibration_guide.md.

Reads the latest WIDE_INPUTS_OUTPUTS.csv and df_input_0.csv to produce
9 plots (Tier 1 + Tier 2) as publication-quality PNGs.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

PROJECT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent
INPUT_CSV = PROJECT / "ssp_modeling" / "input_data" / "df_input_0.csv"
TARGETS_CSV = PROJECT / "ssp_modeling" / "output_postprocessing" / "data" / "invent" / "emission_targets_mar_2022.csv"

# Find latest WIDE output
runs = sorted((PROJECT / "ssp_modeling" / "ssp_run_output").glob("calibration_*/WIDE_INPUTS_OUTPUTS.csv"))
if not runs:
    print("ERROR: No WIDE_INPUTS_OUTPUTS.csv found"); sys.exit(1)
WIDE_CSV = runs[-1]
print(f"Using: {WIDE_CSV.parent.name}")

# Load data
wide = pd.read_csv(WIDE_CSV)
df_input = pd.read_csv(INPUT_CSV)
targets = pd.read_csv(TARGETS_CSV)
TP = 7  # calibration year

# Auto-detect country value column in targets
standard = {'subsector_ssp', 'sector', 'subsector', 'category', 'aggregation_category',
            'gas', 'ID', 'vars', 'ids', 'target_source', 'description', 'fixability', 'notes'}
val_col = [c for c in targets.columns if c not in standard][-1]
targets = targets.rename(columns={val_col: 'inventory'})

tp7 = wide[wide['time_period'] == TP].iloc[0]

SUBSECTOR_NAMES = {
    'agrc': 'Agriculture', 'frst': 'Forest', 'lndu': 'Land Use', 'lsmm': 'Manure Mgmt',
    'lvst': 'Livestock', 'soil': 'Soil N₂O', 'waso': 'Solid Waste', 'trww': 'Wastewater',
    'ippu': 'IPPU Process', 'inen': 'Industry Energy', 'scoe': 'Buildings', 'trns': 'Transport',
    'entc': 'Electricity', 'fgtv': 'Fugitive', 'ccsq': 'CCS',
}

SECTOR_COLORS = {
    'agrc': '#8C6D31', 'frst': '#31A354', 'lndu': '#B5CF6B', 'lsmm': '#E7BA52',
    'lvst': '#BD9E39', 'soil': '#8C6D31', 'waso': '#843C39', 'trww': '#D6616B',
    'ccsq': '#C6DBEF', 'entc': '#6B6ECF', 'fgtv': '#393B79', 'inen': '#3182BD',
    'scoe': '#6BAED6', 'trns': '#756BB1', 'ippu': '#CE6DBD',
}

DAG_AFFECTS = {
    'lvst': ['lsmm', 'soil', 'lndu', 'agrc', 'waso', 'inen'],
    'lsmm': ['soil', 'entc'], 'agrc': ['soil', 'inen', 'entc', 'waso'],
    'soil': [], 'lndu': ['frst', 'soil', 'agrc'], 'frst': [],
    'waso': ['entc', 'ippu'], 'trww': ['entc'], 'wali': [],
    'ippu': ['inen', 'entc'],
    'inen': ['entc', 'fgtv'], 'scoe': ['entc', 'fgtv'], 'trns': ['entc', 'fgtv'],
    'entc': ['fgtv'], 'fgtv': [], 'ccsq': [],
}

def parse_vars(row):
    v = row.get('vars', '')
    return [x.strip() for x in str(v).split(':') if x.strip()] if not pd.isna(v) and v else []


# ═══════════════════════════════════════════════════════════════════════════
# TIER 1: VIZ #1 — Sector Totals: Inventory vs Model
# ═══════════════════════════════════════════════════════════════════════════
def plot_sector_totals():
    sector_data = {}
    for _, row in targets.iterrows():
        sec = row.get('sector', '')
        if not sec:
            continue
        vl = parse_vars(row)
        model_val = sum(tp7.get(v, 0) for v in vl if v in tp7.index)
        inv_val = row['inventory']
        if sec not in sector_data:
            sector_data[sec] = {'inventory': 0, 'model': 0}
        sector_data[sec]['inventory'] += inv_val
        sector_data[sec]['model'] += model_val

    sectors = sorted(sector_data.keys())
    inv_vals = [sector_data[s]['inventory'] for s in sectors]
    mod_vals = [sector_data[s]['model'] for s in sectors]
    short_names = [s.split(' - ')[-1][:20] if ' - ' in s else s[:20] for s in sectors]

    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(sectors))
    w = 0.35
    bars_inv = ax.bar(x - w/2, inv_vals, w, label='NIR Inventory', color='#2196F3', alpha=0.85)
    bars_mod = ax.bar(x + w/2, mod_vals, w, label='SISEPUEDE Model', color='#FF9800', alpha=0.85)

    for i, (iv, mv) in enumerate(zip(inv_vals, mod_vals)):
        diff = mv - iv
        pct = abs(diff) / abs(iv) * 100 if abs(iv) > 0.01 else 0
        color = '#4CAF50' if pct <= 15 else '#FF5722'
        ax.text(i, max(iv, mv) + 0.5, f'{diff:+.1f}\n({pct:.0f}%)', ha='center', fontsize=7, color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(short_names, rotation=30, ha='right', fontsize=8)
    ax.set_ylabel('Emissions (MtCO₂e)')
    ax.set_title('Sector Totals: NIR Inventory vs Model (2022)', fontweight='bold')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'sector_totals.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  sector_totals.png")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 1: VIZ #4 — Top Category Gaps (color-coded)
# ═══════════════════════════════════════════════════════════════════════════
def plot_category_gaps():
    rows = []
    for _, row in targets.iterrows():
        vl = parse_vars(row)
        model_val = sum(tp7.get(v, 0) for v in vl if v in tp7.index)
        inv_val = row['inventory']
        diff = model_val - inv_val
        pct = abs(diff) / abs(inv_val) * 100 if abs(inv_val) > 0.01 else np.nan
        cat = row.get('category', row['ID'])
        label = f"{row['ID']}" if len(str(cat)) > 40 else str(cat)
        rows.append({'label': label, 'diff': diff, 'error_pct': pct, 'abs_diff': abs(diff)})

    df = pd.DataFrame(rows).dropna(subset=['error_pct']).sort_values('abs_diff', ascending=True).tail(20)

    fig, ax = plt.subplots(figsize=(12, 8))
    colors = []
    for _, r in df.iterrows():
        if r['error_pct'] <= 15:
            colors.append('#4CAF50')
        elif r['error_pct'] <= 25:
            colors.append('#FF9800')
        else:
            colors.append('#F44336')

    ax.barh(range(len(df)), df['diff'].values, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df['label'].values, fontsize=7)
    ax.set_xlabel('Model − Inventory (MtCO₂e)')
    ax.set_title('Top 20 Category Gaps by Absolute Error (2022)', fontweight='bold')
    ax.axvline(0, color='black', linewidth=0.8)
    ax.grid(axis='x', alpha=0.3)

    legend_elements = [
        mpatches.Patch(color='#4CAF50', label='≤15% error'),
        mpatches.Patch(color='#FF9800', label='15-25% error'),
        mpatches.Patch(color='#F44336', label='>25% error'),
    ]
    ax.legend(handles=legend_elements, loc='lower right')
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'category_gaps.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  category_gaps.png")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 1: VIZ #13 — DAG Network Graph
# ═══════════════════════════════════════════════════════════════════════════
def plot_dag():
    import networkx as nx

    G = nx.DiGraph()
    for src, tgts in DAG_AFFECTS.items():
        if src == 'wali':
            continue
        G.add_node(src)
        for tgt in tgts:
            G.add_edge(src, tgt)

    DAG_LAYERS = {
        'lvst': 0, 'lsmm': 0, 'agrc': 0, 'soil': 0, 'lndu': 0, 'frst': 0,
        'waso': 1, 'trww': 1, 'ippu': 2,
        'inen': 3, 'scoe': 3, 'trns': 3, 'entc': 4, 'fgtv': 5, 'ccsq': 5,
    }

    emissions = {}
    for node in G.nodes():
        col = f'emission_co2e_subsector_total_{node}'
        emissions[node] = abs(tp7.get(col, 0.1))

    layer_y = {}
    for node in G.nodes():
        layer = DAG_LAYERS.get(node, 3)
        layer_y.setdefault(layer, []).append(node)

    pos = {}
    for layer, nodes in sorted(layer_y.items()):
        n = len(nodes)
        for i, node in enumerate(sorted(nodes)):
            pos[node] = (layer * 2.5, (n - 1) / 2 - i)

    fig, ax = plt.subplots(figsize=(16, 8))
    node_sizes = [max(400, min(3500, emissions.get(n, 0.5) * 200)) for n in G.nodes()]
    node_colors = [SECTOR_COLORS.get(n, '#999') for n in G.nodes()]

    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes, node_color=node_colors,
                           alpha=0.9, edgecolors='white', linewidths=2)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color='#666', arrows=True,
                           arrowsize=15, arrowstyle='->', connectionstyle='arc3,rad=0.1',
                           alpha=0.5, width=1.2)

    labels = {n: f'{SUBSECTOR_NAMES.get(n, n)}\n{emissions.get(n, 0):.1f} Mt' for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, ax=ax, font_size=7, font_weight='bold')

    layer_names = {0: 'Step 1\nAFOLU', 1: 'Step 2\nWaste', 2: 'Step 3\nIPPU',
                   3: 'Step 4\nEnergy\nConsumption', 4: 'Step 5\nEnergy\nProduction', 5: 'Step 6\nFugitive'}
    for layer, name in layer_names.items():
        nodes_in = layer_y.get(layer, [])
        ax.text(layer * 2.5, max(len(nodes_in), 3) / 2 + 0.8, name,
                ha='center', fontsize=9, color='gray', style='italic')

    ax.set_title('SISEPUEDE DAG: Sector Dependencies\nNode size = emission magnitude at tp=7. '
                 'Arrows = cascade direction.', fontsize=12, fontweight='bold')
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'dag_network.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  dag_network.png")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 1: VIZ #7 — INEN Fuel Fractions Heatmap
# ═══════════════════════════════════════════════════════════════════════════
def plot_inen_heatmap():
    industries = ['agriculture_and_livestock', 'cement', 'chemicals', 'electronics', 'glass',
                  'lime_and_carbonite', 'metals', 'mining', 'other_product_manufacturing',
                  'paper', 'plastic', 'rubber_and_leather', 'textiles', 'wood']
    fuels = ['coal', 'coke', 'diesel', 'electricity', 'gasoline', 'hydrocarbon_gas_liquids',
             'kerosene', 'natural_gas', 'oil', 'solid_biomass']

    data = np.zeros((len(industries), len(fuels)))
    for i, ind in enumerate(industries):
        for j, fuel in enumerate(fuels):
            col = f'frac_inen_energy_{ind}_{fuel}'
            if col in df_input.columns:
                data[i, j] = df_input[col].iloc[0]

    fig, ax = plt.subplots(figsize=(14, 7))
    im = ax.imshow(data, cmap='YlOrRd', aspect='auto', vmin=0, vmax=0.6)

    ax.set_xticks(range(len(fuels)))
    ax.set_xticklabels([f.replace('_', '\n') for f in fuels], fontsize=7, rotation=0)
    ax.set_yticks(range(len(industries)))
    ax.set_yticklabels([ind.replace('_', ' ').title() for ind in industries], fontsize=8)

    for i in range(len(industries)):
        for j in range(len(fuels)):
            val = data[i, j]
            if val > 0.005:
                ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                        fontsize=6, color='white' if val > 0.3 else 'black')

    plt.colorbar(im, ax=ax, label='Demand Fraction', shrink=0.8)
    ax.set_title('INEN Fuel Demand Fractions by Industry (tp=0)\nα^D converted from IEA consumption fractions',
                 fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'inen_fuel_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  inen_fuel_heatmap.png")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 1: VIZ #5 — NemoMod Generation Mix
# ═══════════════════════════════════════════════════════════════════════════
def plot_generation_mix():
    tech_cols = [c for c in wide.columns if 'nemomod_entc_annual_production_by_technology_pp_' in c]
    if not tech_cols:
        print("  SKIP generation_mix.png (no NemoMod columns)")
        return

    baseline = wide[wide.get('primary_id', pd.Series([0]*len(wide))) == 0].copy()
    if len(baseline) == 0:
        baseline = wide.copy()

    tech_names = {c: c.replace('nemomod_entc_annual_production_by_technology_pp_', '').replace('_', ' ').title()
                  for c in tech_cols}
    tech_colors = {
        'coal': '#555555', 'gas': '#E74C3C', 'oil': '#E67E22', 'hydropower': '#3498DB',
        'solar': '#F1C40F', 'wind': '#85C1E9', 'biomass': '#27AE60', 'biogas': '#2ECC71',
        'waste incineration': '#8E44AD', 'nuclear': '#95A5A6', 'geothermal': '#D35400',
        'ocean': '#1ABC9C',
    }

    fig, ax = plt.subplots(figsize=(14, 6))
    tp = baseline['time_period'].values
    bottom = np.zeros(len(baseline))

    plotted = []
    for col in sorted(tech_cols):
        vals = baseline[col].values
        if np.max(np.abs(vals)) < 0.01:
            continue
        short = col.replace('nemomod_entc_annual_production_by_technology_pp_', '')
        color = tech_colors.get(short, '#999')
        ax.fill_between(tp, bottom, bottom + vals, label=short.replace('_', ' ').title(),
                        color=color, alpha=0.85)
        bottom += vals
        plotted.append(short)

    ax.set_xlabel('Time Period')
    ax.set_ylabel('Generation (PJ)')
    ax.set_title('NemoMod Electricity Generation Mix by Technology', fontweight='bold')
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=8)
    ax.grid(axis='y', alpha=0.3)
    ax.axvline(TP, color='red', linestyle='--', alpha=0.5, label=f'tp={TP}')
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'generation_mix.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  generation_mix.png")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 2: VIZ #8 — Manure Management by Species
# ═══════════════════════════════════════════════════════════════════════════
def plot_manure_management():
    species = ['cattle_dairy', 'cattle_nondairy', 'sheep', 'goats', 'horses', 'mules', 'pigs', 'chickens']
    systems = ['paddock_pasture_range', 'daily_spread', 'dry_lot', 'composting', 'solid_storage',
               'deep_bedding', 'poultry_manure', 'liquid_slurry', 'anaerobic_lagoon',
               'anaerobic_digester', 'incineration']

    mcf_colors = {
        'paddock_pasture_range': '#4CAF50', 'daily_spread': '#66BB6A', 'dry_lot': '#81C784',
        'composting': '#A5D6A7', 'solid_storage': '#FFF176', 'deep_bedding': '#FFD54F',
        'poultry_manure': '#FFB74D', 'liquid_slurry': '#E57373', 'anaerobic_lagoon': '#EF5350',
        'anaerobic_digester': '#FFA726', 'incineration': '#BDBDBD',
    }

    data = np.zeros((len(species), len(systems)))
    for i, sp in enumerate(species):
        for j, sys_name in enumerate(systems):
            col = f'frac_lvst_mm_{sp}_{sys_name}'
            if col in df_input.columns:
                data[i, j] = df_input[col].iloc[0]

    fig, ax = plt.subplots(figsize=(14, 6))
    bottom = np.zeros(len(species))
    for j, sys_name in enumerate(systems):
        vals = data[:, j]
        if np.max(vals) < 0.001:
            continue
        ax.barh(range(len(species)), vals, left=bottom, label=sys_name.replace('_', ' ').title(),
                color=mcf_colors.get(sys_name, '#999'), edgecolor='white', linewidth=0.5)
        bottom += vals

    ax.set_yticks(range(len(species)))
    ax.set_yticklabels([s.replace('_', ' ').title() for s in species], fontsize=9)
    ax.set_xlabel('Fraction')
    ax.set_title('Manure Management Systems by Species (tp=0)\n'
                 'Green = low MCF (paddock ~1.5%), Red = high MCF (liquid slurry ~35%)',
                 fontweight='bold')
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=7)
    ax.set_xlim(0, 1.05)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'manure_management.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  manure_management.png")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 2: VIZ #2 — Emission Trajectory (Stacked Area)
# ═══════════════════════════════════════════════════════════════════════════
def plot_emission_trajectory():
    baseline = wide[wide.get('primary_id', pd.Series([0]*len(wide))) == 0].copy()
    if len(baseline) == 0:
        baseline = wide.copy()

    subsectors = ['agrc', 'frst', 'lndu', 'lsmm', 'lvst', 'soil', 'waso', 'trww',
                  'ippu', 'inen', 'scoe', 'trns', 'entc', 'fgtv']
    cols_present = []
    for s in subsectors:
        col = f'emission_co2e_subsector_total_{s}'
        if col in baseline.columns:
            cols_present.append((s, col))

    fig, ax = plt.subplots(figsize=(14, 7))
    tp = baseline['time_period'].values
    bottom = np.zeros(len(baseline))

    for s, col in cols_present:
        vals = baseline[col].values
        if np.max(np.abs(vals)) < 0.01:
            continue
        ax.fill_between(tp, bottom, bottom + vals, label=SUBSECTOR_NAMES.get(s, s),
                        color=SECTOR_COLORS.get(s, '#999'), alpha=0.85)
        bottom += vals

    ax.set_xlabel('Time Period')
    ax.set_ylabel('Emissions (MtCO₂e)')
    ax.set_title('Emission Trajectory by Subsector (Baseline)', fontweight='bold')
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=8)
    ax.axvline(TP, color='red', linestyle='--', alpha=0.5)
    ax.text(TP + 0.3, ax.get_ylim()[1] * 0.95, f'tp={TP}\n(2022)', fontsize=8, color='red')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'emission_trajectory.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  emission_trajectory.png")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 2: VIZ #12 — Calibration Progress (mock from diff_report)
# ═══════════════════════════════════════════════════════════════════════════
def plot_calibration_progress():
    diag_dirs = sorted((PROJECT / "ssp_modeling" / "ssp_run_output").glob("calibration_*/diagnostics/diff_report.csv"))
    if len(diag_dirs) < 2:
        print("  SKIP calibration_progress.png (need ≥2 runs with diagnostics)")
        return

    progress = []
    for dr in diag_dirs:
        try:
            diff = pd.read_csv(dr)
            sig = diff[diff['inventory'].abs() > 0.01]
            total_err = sig['diff'].abs().sum()
            n_15 = (sig['error_pct'] <= 15).sum()
            progress.append({'run': dr.parent.parent.name[-15:], 'error': total_err, 'within_15': n_15, 'n': len(sig)})
        except Exception:
            continue

    if len(progress) < 2:
        print("  SKIP calibration_progress.png (insufficient data)")
        return

    df_p = pd.DataFrame(progress)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    ax1.plot(range(len(df_p)), df_p['error'], 'o-', color='#2196F3', linewidth=2, markersize=8)
    ax1.axhline(15, color='#4CAF50', linestyle='--', label='Target: 15 MtCO₂e')
    ax1.set_ylabel('Total Absolute Error (MtCO₂e)')
    ax1.set_xlabel('Iteration')
    ax1.set_title('Calibration Convergence', fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.bar(range(len(df_p)), df_p['within_15'], color='#4CAF50', alpha=0.8)
    ax2.axhline(df_p['n'].iloc[0] * 0.40, color='orange', linestyle='--', label='Target: 40%')
    ax2.set_ylabel('Categories within 15%')
    ax2.set_xlabel('Iteration')
    ax2.set_title('Category Accuracy', fontweight='bold')
    ax2.legend()
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUT_DIR / 'calibration_progress.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  calibration_progress.png")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 2: VIZ #10 — Fuel Mix Donuts
# ═══════════════════════════════════════════════════════════════════════════
def plot_fuel_donuts():
    configs = [
        ('Residential Heat', 'frac_scoe_heat_energy_residential_'),
        ('Commercial Heat', 'frac_scoe_heat_energy_commercial_municipal_'),
        ('Cement Energy', 'frac_inen_energy_cement_'),
    ]
    fuel_colors = {
        'coal': '#555', 'coke': '#777', 'diesel': '#E67E22', 'electricity': '#3498DB',
        'gasoline': '#E74C3C', 'hydrocarbon_gas_liquids': '#F39C12', 'hydrogen': '#1ABC9C',
        'kerosene': '#D35400', 'natural_gas': '#E74C3C', 'oil': '#E67E22',
        'solid_biomass': '#27AE60', 'solar': '#F1C40F', 'furnace_gas': '#95A5A6',
    }

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (title, prefix) in zip(axes, configs):
        cols = [c for c in df_input.columns if c.startswith(prefix)]
        vals, labels, colors = [], [], []
        for c in cols:
            v = df_input[c].iloc[0]
            if v > 0.005:
                fuel = c.replace(prefix, '').replace('_', ' ').title()
                vals.append(v)
                labels.append(f'{fuel}\n{v:.1%}')
                raw = c.replace(prefix, '')
                colors.append(fuel_colors.get(raw, '#999'))

        if vals:
            wedges, texts = ax.pie(vals, labels=labels, colors=colors, startangle=90,
                                   wedgeprops=dict(width=0.4, edgecolor='white'))
            for t in texts:
                t.set_fontsize(7)
        ax.set_title(title, fontweight='bold', fontsize=10)

    plt.suptitle('End-Use Fuel Mix (tp=0, demand fractions)', fontweight='bold', fontsize=12)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'fuel_donuts.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  fuel_donuts.png")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 2: VIZ #6 — Gas-Level Totals
# ═══════════════════════════════════════════════════════════════════════════
def plot_gas_totals():
    gas_data = {}
    for _, row in targets.iterrows():
        gas = row.get('gas', '')
        if not gas:
            continue
        vl = parse_vars(row)
        model_val = sum(tp7.get(v, 0) for v in vl if v in tp7.index)
        inv_val = row['inventory']
        if gas not in gas_data:
            gas_data[gas] = {'inventory': 0, 'model': 0}
        gas_data[gas]['inventory'] += inv_val
        gas_data[gas]['model'] += model_val

    gases = sorted(gas_data.keys())
    inv_vals = [gas_data[g]['inventory'] for g in gases]
    mod_vals = [gas_data[g]['model'] for g in gases]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(gases))
    w = 0.35
    ax.bar(x - w/2, inv_vals, w, label='NIR Inventory', color='#2196F3', alpha=0.85)
    ax.bar(x + w/2, mod_vals, w, label='SISEPUEDE Model', color='#FF9800', alpha=0.85)

    for i, (iv, mv) in enumerate(zip(inv_vals, mod_vals)):
        diff = mv - iv
        ax.text(i, max(iv, mv) + 0.3, f'{diff:+.1f}', ha='center', fontsize=8,
                color='#4CAF50' if abs(diff) / max(abs(iv), 0.01) <= 0.15 else '#FF5722')

    ax.set_xticks(x)
    ax.set_xticklabels(gases, fontsize=9)
    ax.set_ylabel('Emissions (MtCO₂e)')
    ax.set_title('Total Emissions by Gas: Inventory vs Model (2022)', fontweight='bold')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'gas_totals.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  gas_totals.png")


# ═══════════════════════════════════════════════════════════════════════════
# RUN ALL
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("Generating guide figures...")
    plot_sector_totals()
    plot_category_gaps()
    plot_dag()
    plot_inen_heatmap()
    plot_generation_mix()
    plot_manure_management()
    plot_emission_trajectory()
    plot_calibration_progress()
    plot_fuel_donuts()
    plot_gas_totals()
    print(f"\nAll figures saved to {OUT_DIR}/")
