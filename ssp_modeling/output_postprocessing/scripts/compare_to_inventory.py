#!/usr/bin/env python3
"""
Compare SISEPUEDE model output to national GHG inventory.

Country-agnostic diagnostic tool. Works with any emission_targets_{country}_{year}.csv.

Usage:
  python compare_to_inventory.py \\
    --targets emission_targets_mar_2022.csv \\
    --output  WIDE_INPUTS_OUTPUTS.csv \\
    --tp 7 --threshold 0.15

  python compare_to_inventory.py ... --top 5           Show only top 5 flagged
  python compare_to_inventory.py ... --explain          Add learning annotations
  python compare_to_inventory.py ... --top 5 --explain  Combined

Outputs (saved to {output_dir}/diagnostics/):
  diff_report.csv      Full comparison with impact rank, components, trajectory
  flagged.csv          Component breakdown for flagged rows
  diagnostics.csv      Structural warnings (zero outputs, sign mismatches, etc.)
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path


# ---------------------------------------------------------------------------
# DAG dependency map (SISEPUEDE sector execution order and connections)
# ---------------------------------------------------------------------------

DAG_ORDER = {
    'lvst': 1, 'lsmm': 1, 'agrc': 1, 'soil': 1, 'lndu': 1, 'frst': 1,
    'waso': 2, 'trww': 2, 'wali': 2,
    'ippu': 3,
    'inen': 4, 'scoe': 4, 'trns': 4,
    'entc': 5, 'enfu': 5,
    'fgtv': 6,
    'ccsq': 7,
}

# "If you change parameters in subsector X, these other subsectors may also change"
DAG_AFFECTS = {
    'lvst':  ['lsmm', 'soil', 'lndu', 'agrc'],
    'lsmm':  ['soil'],
    'agrc':  ['soil', 'inen', 'entc'],
    'soil':  [],
    'lndu':  ['frst', 'soil', 'agrc'],
    'frst':  [],
    'waso':  ['entc'],
    'trww':  [],
    'ippu':  ['inen', 'entc'],
    'inen':  ['entc', 'fgtv'],
    'scoe':  ['entc', 'fgtv'],
    'trns':  ['entc', 'fgtv'],
    'entc':  ['fgtv'],
    'fgtv':  [],
    'ccsq':  [],
}

# Descriptions for IPCC aggregation categories (country-agnostic)
CATEGORY_DESCRIPTIONS = {
    'Electricity and Heat Generation': 'CO2/CH4/N2O from burning coal, gas, oil to generate electricity',
    'Fuel Production': 'Emissions from mining, refining, and processing fossil fuels',
    'Industrial Combustion': 'Fuel burning in factories (cement kilns, steel furnaces, chemical plants)',
    'Transportation': 'Vehicle exhaust from road, rail, aviation, and maritime transport',
    'Other Combustion': 'Fuel burning in homes (cooking, heating), offices, and farms',
    'Fugitive Emissions': 'Gas leaks from pipelines, abandoned mines, and fuel storage',
    'IPPU': 'Chemical reactions in industrial processes (calcination, metal smelting, refrigerant leaks)',
    'Livestock': 'Methane from animal digestion (enteric) and manure decomposition',
    'Agriculture and Managed Soil': 'N2O from fertilizer, manure on pastures, crop residues, and urea',
    'Solid Waste': 'Methane from organic waste decomposing in landfills and open dumps',
    'Wastewater Treatment': 'Methane and N2O from sewage treatment and untreated discharge',
    'CCSQ': 'Carbon captured and sequestered (negative emissions)',
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_targets(path):
    df = pd.read_csv(path)
    standard_cols = {'subsector_ssp','sector','subsector','category',
                     'aggregation_category','gas','ID','vars','ids',
                     'target_source','description','fixability','notes'}
    val_cols = [c for c in df.columns if c not in standard_cols]
    if not val_cols:
        raise SystemExit(f"ERROR: No country value column found in {path}")
    val_col = val_cols[-1]
    return df.rename(columns={val_col: 'inventory'})


def load_model_row(path, tp, strategy=0):
    df = pd.read_csv(path)
    if 'primary_id' in df.columns:
        df = df[(df['primary_id'] == strategy) & (df['time_period'] == tp)]
    else:
        df = df[df['time_period'] == tp]
    if len(df) == 0:
        raise SystemExit(f"ERROR: No data for tp={tp}, strategy={strategy}")
    return df.iloc[0]


def load_full_model(path, strategy=0):
    try:
        df = pd.read_csv(path)
        if 'primary_id' in df.columns:
            df = df[df['primary_id'] == strategy]
        return df
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_vars(row):
    v = row.get('vars', '')
    if pd.isna(v) or v == '':
        return []
    return [x.strip() for x in str(v).split(':') if x.strip()]


def sum_vars(var_list, row):
    return sum(row.get(v, 0.0) for v in var_list if v in row.index)


def short_name(v):
    return v.replace('emission_co2e_', '').replace('_nbmass', '')


# ---------------------------------------------------------------------------
# Core comparison
# ---------------------------------------------------------------------------

def build_diff(targets, model_row, full_model, tp, min_mag):
    # Get tp=0 row for trajectory
    tp0_row = None
    if full_model is not None:
        tp0 = full_model[full_model['time_period'] == 0]
        if len(tp0) > 0:
            tp0_row = tp0.iloc[0]

    rows = []
    for _, t in targets.iterrows():
        vl = parse_vars(t)
        found = [v for v in vl if v in model_row.index]
        total = sum(model_row[v] for v in found)

        # Top component
        top_var, top_val, top_share = '', 0.0, 0.0
        if found and abs(total) > 1e-8:
            vals = {v: model_row[v] for v in found}
            top_var = max(vals, key=lambda k: abs(vals[k]))
            top_val = vals[top_var]
            top_share = abs(top_val) / abs(total) * 100

        # tp=0 value for trajectory
        tp0_val = sum_vars(vl, tp0_row) if tp0_row is not None else np.nan

        rows.append({
            'model': total,
            'model_tp0': tp0_val,
            'n_vars': len(found),
            'n_missing': len(vl) - len(found),
            'top_component': short_name(top_var) if top_var else '',
            'top_component_value': top_val,
            'top_component_share': round(top_share, 1),
        })

    diff = targets.copy()
    r = pd.DataFrame(rows)
    for col in r.columns:
        diff[col] = r[col].values

    diff['diff'] = diff['model'] - diff['inventory']

    mask = diff['inventory'].abs() > min_mag
    diff['error_pct'] = np.nan
    diff.loc[mask, 'error_pct'] = (
        diff.loc[mask, 'diff'].abs() / diff.loc[mask, 'inventory'].abs() * 100
    )

    # Trajectory: growth from tp=0 to tp=calibration
    diff['model_growth_pct'] = np.nan
    tp0_mask = diff['model_tp0'].abs() > min_mag
    diff.loc[tp0_mask, 'model_growth_pct'] = (
        (diff.loc[tp0_mask, 'model'] - diff.loc[tp0_mask, 'model_tp0'])
        / diff.loc[tp0_mask, 'model_tp0'].abs() * 100
    )

    # Inventory share
    total_inv = diff['inventory'].abs().sum()
    diff['inventory_share'] = diff['inventory'].abs() / total_inv * 100 if total_inv > 0 else 0

    # Direction
    diff['direction'] = 'match'
    diff.loc[diff['diff'] > min_mag * 0.1, 'direction'] = 'over'
    diff.loc[diff['diff'] < -min_mag * 0.1, 'direction'] = 'under'

    # Impact rank
    diff['abs_impact_rank'] = diff['diff'].abs().rank(ascending=False, method='min').astype(int)

    # Source from targets CSV
    if 'target_source' in targets.columns:
        diff['target_source'] = targets['target_source'].values
    else:
        diff['target_source'] = ''

    # Fixability from targets CSV
    if 'fixability' in targets.columns:
        diff['fixability'] = targets['fixability'].values
    else:
        diff['fixability'] = ''

    # Reorder
    col_order = [
        'abs_impact_rank', 'ID', 'subsector_ssp', 'sector', 'category',
        'aggregation_category', 'gas',
        'inventory', 'model', 'model_tp0', 'diff', 'error_pct',
        'direction', 'model_growth_pct', 'inventory_share',
        'top_component', 'top_component_value', 'top_component_share',
        'fixability', 'n_vars', 'n_missing', 'target_source', 'vars',
    ]
    existing = [c for c in col_order if c in diff.columns]
    extra = [c for c in diff.columns if c not in col_order]
    diff = diff[existing + extra]

    return diff


def get_components(vars_str, model_row, top_n=5):
    vl = parse_vars({'vars': vars_str})
    c = [{'var': v, 'val': model_row.get(v, 0.0)} for v in vl if v in model_row.index]
    df = pd.DataFrame(c)
    if len(df) == 0:
        return df
    return df.reindex(df['val'].abs().sort_values(ascending=False).index).head(top_n)


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def run_diagnostics(targets, diff, model_row, full_model, tp, min_mag):
    w = []

    def add(rid, cat, gas, sec, inv, mod, issue, sev, detail):
        w.append(dict(ID=rid, category=cat, gas=gas, sector=sec,
                       inventory=inv, model=mod, issue=issue,
                       severity=sev, detail=detail))

    for idx, row in diff.iterrows():
        t = targets.iloc[idx]
        inv, mod, rid = row['inventory'], row['model'], row['ID']
        cat, gas, sec = row.get('category',''), row.get('gas',''), row.get('sector','')
        vl = parse_vars(t)

        if abs(inv) < min_mag and abs(mod) < min_mag:
            continue

        if abs(mod) < 1e-6 and abs(inv) > min_mag:
            zv = sum(1 for v in vl if v in model_row.index and abs(model_row[v]) < 1e-8)
            add(rid, cat, gas, sec, inv, mod, 'ZERO_OUTPUT', 'HIGH',
                f'Target={inv:.4f} but model=0. {zv}/{len(vl)} vars zero. Needs input values, not rescaling.')
            continue

        if inv * mod < 0 and abs(inv) > min_mag and abs(mod) > min_mag:
            add(rid, cat, gas, sec, inv, mod, 'SIGN_MISMATCH', 'HIGH',
                f'Inventory={inv:+.3f}, model={mod:+.3f}. Disagree on source vs sink.')

        if abs(inv) > min_mag and abs(mod) > min_mag:
            ratio = abs(mod / inv)
            if ratio > 10 or ratio < 0.1:
                add(rid, cat, gas, sec, inv, mod, 'MAGNITUDE_10X', 'HIGH',
                    f'Ratio={ratio:.1f}x. Possible unit error or missing fundamental parameter.')

        if len(vl) > 1 and abs(mod) > min_mag:
            vals = {v: model_row.get(v, 0.0) for v in vl if v in model_row.index}
            if vals:
                mx = max(abs(x) for x in vals.values())
                if mx / abs(mod) > 0.95:
                    dom = max(vals, key=lambda k: abs(vals[k]))
                    zeros = [v for v, x in vals.items() if abs(x) < 1e-8 and v != dom]
                    if zeros:
                        add(rid, cat, gas, sec, inv, mod, 'SINGLE_DOMINANCE', 'MEDIUM',
                            f'{short_name(dom)[:40]} is {mx/abs(mod)*100:.0f}% of total. {len(zeros)} other vars are zero.')

        missing = [v for v in vl if v not in model_row.index]
        if missing:
            add(rid, cat, gas, sec, inv, mod, 'MISSING_VARS', 'LOW',
                f'{len(missing)} expected vars not in model output.')

        if full_model is not None and tp > 0 and abs(inv) > min_mag:
            tp0 = full_model[full_model['time_period'] == 0]
            if len(tp0) > 0:
                v0 = sum_vars(vl, tp0.iloc[0])
                if abs(v0) > min_mag:
                    g = (mod - v0) / abs(v0)
                    if abs(g) > 1.0 or g < -0.5:
                        add(rid, cat, gas, sec, inv, mod, 'TRAJECTORY', 'MEDIUM',
                            f'Changed {g*100:+.0f}% from tp=0 ({v0:.3f}) to tp={tp} ({mod:.3f}).')

    for (_, sec), grp in diff.groupby(['subsector', 'sector']):
        co2 = grp[grp['gas'] == 'CO2']
        if len(co2) == 0 or co2.iloc[0]['inventory'] < min_mag:
            continue
        r_co2 = co2.iloc[0]['model'] / co2.iloc[0]['inventory']
        if abs(r_co2) < 0.01:
            continue
        for gn, gr in [('CH4', grp[grp['gas']=='CH4']), ('N2O', grp[grp['gas']=='N2O'])]:
            if len(gr) == 0 or gr.iloc[0]['inventory'] < min_mag * 0.1:
                continue
            r_g = gr.iloc[0]['model'] / gr.iloc[0]['inventory'] if abs(gr.iloc[0]['inventory']) > 1e-6 else 0
            if abs(r_co2 - 1) < 0.20 and abs(r_g - 1) > 0.50:
                add(gr.iloc[0]['ID'], gr.iloc[0].get('category',''), gn, sec,
                    gr.iloc[0]['inventory'], gr.iloc[0]['model'], 'GAS_RATIO', 'MEDIUM',
                    f'CO2 ratio={r_co2:.0%} but {gn} ratio={r_g:.0%}. Check {gn} EFs.')

    return pd.DataFrame(w) if w else pd.DataFrame()


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_header(title, width=80):
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def print_section(title):
    print()
    print(f"  {title}")
    print("  " + "-" * 76)


def print_explain(row, model_row):
    """Print learning annotations for a flagged row."""
    ssp = row.get('subsector_ssp', '')
    agg = row.get('aggregation_category', '')
    gas = row.get('gas', '')
    inv = row['inventory']
    mod = row['model']
    tp0 = row.get('model_tp0', np.nan)
    growth = row.get('model_growth_pct', np.nan)

    # WHAT
    desc = CATEGORY_DESCRIPTIONS.get(agg, '')
    if desc:
        print(f"      WHAT:  {desc}")

    # TRAJECTORY
    if not np.isnan(tp0) and not np.isnan(growth):
        print(f"      TRAJECTORY: tp=0 model={tp0:.3f}, tp=7 model={mod:.3f} ({growth:+.0f}% growth)")

    # DAG
    affected = DAG_AFFECTS.get(ssp, [])
    if affected:
        names = ', '.join(affected)
        print(f"      DAG:   Changing {ssp} parameters also affects: {names}")

    # FIXABILITY
    fix = row.get('fixability', '')
    if fix:
        print(f"      FIX:   {fix}")

    print()


def main():
    p = argparse.ArgumentParser(description='Compare SISEPUEDE output to GHG inventory')
    p.add_argument('--targets', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--tp', type=int, default=7)
    p.add_argument('--strategy', type=int, default=0)
    p.add_argument('--threshold', type=float, default=0.15)
    p.add_argument('--min-magnitude', type=float, default=0.01)
    p.add_argument('--out-dir', default=None)
    p.add_argument('--top', type=int, default=10, help='Show top N flagged categories (default: 10, 0=all)')
    p.add_argument('--explain', action='store_true', help='Add learning annotations (WHAT/TRAJECTORY/DAG)')
    args = p.parse_args()

    targets_path = Path(args.targets)
    output_path = Path(args.output)
    out_dir = Path(args.out_dir) if args.out_dir else output_path.parent / 'diagnostics'
    out_dir.mkdir(parents=True, exist_ok=True)
    threshold_pct = args.threshold * 100
    show_top = args.top if args.top > 0 else 9999

    # Load
    targets = load_targets(targets_path)
    model_row = load_model_row(output_path, args.tp, args.strategy)
    full_model = load_full_model(output_path, args.strategy)

    # Compare
    diff = build_diff(targets, model_row, full_model, args.tp, args.min_magnitude)
    diff.to_csv(out_dir / 'diff_report.csv', index=False)

    sig = diff[diff['inventory'].abs() > args.min_magnitude].copy()
    total_err = sig['diff'].abs().sum()
    n_15 = (sig['error_pct'] <= 15).sum()
    n_25 = (sig['error_pct'] <= 25).sum()
    n_flag = (sig['error_pct'] > threshold_pct).sum()

    # ── Verdict ──────────────────────────────────────────────────────
    status = "GOOD" if total_err < 10 and n_15 > len(sig) * 0.5 else "NEEDS WORK"
    print()
    print(f"  CALIBRATION: {total_err:.2f} MtCO2e | {n_15}/{len(sig)} within 15% | {status}")

    # ── Header ───────────────────────────────────────────────────────
    print_header("SISEPUEDE CALIBRATION DIAGNOSTIC REPORT")
    print(f"  Targets:    {targets_path.name}")
    print(f"  Model run:  {output_path.parent.name}")
    print(f"  Period:     tp={args.tp} (year {2015 + args.tp})")
    print(f"  Threshold:  {threshold_pct:.0f}%")

    # ── 1. Summary ───────────────────────────────────────────────────
    print_header("1. SUMMARY")
    print(f"  Total absolute error:  {total_err:8.2f} MtCO2e")
    print(f"  Categories evaluated:  {len(sig):8d}")
    print(f"  Within 15%:            {n_15:8d}  ({n_15/len(sig)*100:.0f}%)")
    print(f"  Within 25%:            {n_25:8d}  ({n_25/len(sig)*100:.0f}%)")
    print(f"  Exceeding threshold:   {n_flag:8d}")

    # ── 2. Sector totals ─────────────────────────────────────────────
    print_header("2. SECTOR TOTALS")
    print(f"  {'Sector':<35s} {'Inventory':>10s} {'Model':>10s} {'Diff':>10s} {'Error':>8s}")
    print("  " + "-" * 75)
    for sec in sorted(diff['sector'].unique()):
        sub = diff[diff['sector'] == sec]
        inv_t, mod_t = sub['inventory'].sum(), sub['model'].sum()
        if abs(inv_t) > 0.01:
            err = (mod_t - inv_t) / abs(inv_t) * 100
            print(f"  {sec:<35s} {inv_t:10.3f} {mod_t:10.3f} {mod_t-inv_t:+10.3f} {err:+7.1f}%")

    # ── 3. Flagged categories ────────────────────────────────────────
    flagged = sig[sig['error_pct'] > threshold_pct].sort_values('diff', key=abs, ascending=False)
    flagged_rows = []

    if len(flagged) > 0:
        shown = min(show_top, len(flagged))
        more = len(flagged) - shown
        print_header(f"3. FLAGGED CATEGORIES (showing {shown} of {len(flagged)})")
        print(f"  {'Category':<50s} {'Inventory':>10s} {'Model':>10s} {'Diff':>10s} {'Error':>8s}")
        print("  " + "-" * 90)

        for i, (_, row) in enumerate(flagged.iterrows()):
            if i >= show_top:
                break
            inv, mod, d, e = row['inventory'], row['model'], row['diff'], row['error_pct']
            cat_name = row.get('category', row['ID'])
            # Show ID with short description: "3.A.1:CH4 (Enteric Fermentation)"
            desc = cat_name.split(' - ', 1)[1] if ' - ' in str(cat_name) else ''
            label = f"{row['ID']} ({desc})" if desc else row['ID']
            print(f"  {label:<50s} {inv:10.3f} {mod:10.3f} {d:+10.3f} {e:7.1f}%")

            comps = get_components(row.get('vars',''), model_row, top_n=5)
            if len(comps) > 0:
                for _, c in comps.iterrows():
                    pct = c['val'] / mod * 100 if abs(mod) > 1e-6 else 0
                    print(f"    {short_name(c['var']):<55s} {c['val']:8.4f}  ({pct:5.1f}%)")
                    flagged_rows.append({
                        'parent_ID': row['ID'], 'inventory': inv, 'model': mod,
                        'diff': d, 'error_pct': e,
                        'component': c['var'], 'value': c['val'], 'share_pct': pct,
                    })

            if args.explain:
                print_explain(row, model_row)
            else:
                print()

        if more > 0:
            print(f"  ... {more} more flagged categories. Use --top 0 to see all.")

        if flagged_rows:
            pd.DataFrame(flagged_rows).to_csv(out_dir / 'flagged.csv', index=False)

    # ── 4-6. Diagnostics ─────────────────────────────────────────────
    diag = run_diagnostics(targets, diff, model_row, full_model, args.tp, args.min_magnitude)

    if len(diag) > 0:
        diag.to_csv(out_dir / 'diagnostics.csv', index=False)
        for sev, label in [('HIGH','4. HIGH-PRIORITY DIAGNOSTICS'),
                           ('MEDIUM','5. MEDIUM-PRIORITY DIAGNOSTICS'),
                           ('LOW','6. LOW-PRIORITY DIAGNOSTICS')]:
            sev_df = diag[diag['severity'] == sev]
            if len(sev_df) == 0:
                continue
            print_header(f"{label} ({len(sev_df)})")
            for issue, grp in sev_df.groupby('issue'):
                print_section(f"{issue} ({len(grp)})")
                for _, w in grp.iterrows():
                    print(f"    {w['ID']:<30s}  {w['detail'][:65]}")

    # ── 7. Next steps ────────────────────────────────────────────────
    if len(flagged) > 0:
        print_header("7. SUGGESTED NEXT STEPS")
        top3 = flagged.head(3)
        for i, (_, row) in enumerate(top3.iterrows()):
            ssp = row.get('subsector_ssp', '')
            d = row['diff']
            action = "increase" if d < 0 else "decrease"
            tc = row.get('top_component', '')
            affected = DAG_AFFECTS.get(ssp, [])
            cascade_note = f" (also affects: {', '.join(affected)})" if affected else ""

            cat_name = row.get('category', row['ID'])
            desc = cat_name.split(' - ', 1)[1] if ' - ' in str(cat_name) else ''
            id_label = f"{row['ID']} ({desc})" if desc else row['ID']
            print(f"  {i+1}. {id_label}: {action} {tc if tc else ssp} by ~{abs(row['error_pct']):.0f}%{cascade_note}")
        print()

    # ── 8. Output files ──────────────────────────────────────────────
    print_header("8. OUTPUT FILES")
    print(f"  {out_dir / 'diff_report.csv'}")
    if flagged_rows:
        print(f"  {out_dir / 'flagged.csv'}")
    if len(diag) > 0:
        print(f"  {out_dir / 'diagnostics.csv'}")
    print()


if __name__ == '__main__':
    main()
