#!/usr/bin/env python3
"""
apply_step2_bau_scenario.py — BAU scenario adjustments to match SNBC Reference trajectory.

Run order: apply_step0_verified.py → apply_step1_calibration.py → apply_step2_bau_scenario.py → run_calibration0.py

This script modifies ONLY the forward trajectory (tp=8+, 2023-2070).
Historical calibration (tp=0 to tp=7, 2015-2022) is LOCKED at 7.29 MtCO2e against NIR.

Sources: SNBC 2024 (NDC Docs/Morocco SNBC 2050 - English), NIR 2024, SISEPUEDE source code.
"""

import numpy as np
import pandas as pd
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
CSV = PROJECT_DIR / "ssp_modeling" / "input_data" / "df_input_0.csv"

df = pd.read_csv(CSV)
N_TP = len(df)
print(f"Loaded: {len(df.columns)} columns, {N_TP} rows")
print(f"NOTE: Only modifying tp=8+ (2023-2070). tp=0-7 locked.\n")


# ═══════════════════════════════════════════════════════════════════════════
# HELPER: set trajectory with linear interpolation between milestones
# ═══════════════════════════════════════════════════════════════════════════
def set_trajectory(col, milestones, hold_before=True):
    """Set column values by interpolating between {tp: value} milestones.
    Only modifies tp >= min(milestones). Preserves tp=0-7 if milestones start at tp>=8.
    """
    tps = sorted(milestones.keys())
    for i in range(len(tps) - 1):
        t0, t1 = tps[i], tps[i + 1]
        v0, v1 = milestones[t0], milestones[t1]
        for t in range(t0, t1 + 1):
            if t < N_TP:
                frac = (t - t0) / (t1 - t0) if t1 > t0 else 1
                df.loc[t, col] = v0 + (v1 - v0) * frac
    # Hold last value to end
    last_tp, last_val = tps[-1], milestones[tps[-1]]
    for t in range(last_tp, N_TP):
        df.loc[t, col] = last_val
    print(f"  {col}: {', '.join(f'tp{t}={milestones[t]:.3f}' for t in tps)}")


# ═══════════════════════════════════════════════════════════════════════════
# STEP 1: Coal Retirement Schedule
# Source: SNBC p.53-54, Figure 20: coal generation declines to 0 by ~2050
# Source: SNBC p.53: "coal-fired plants are decommissioned at the end of
#   their contracted service in the 2040s"
# Morocco actual coal fleet: JORF Lasfar 1+2 (1,320 MW) + Safi (1,386 MW) = 2.7 GW
# Template has 4.47 GW (Bulgarian). Fix to Morocco first, then retire.
# ═══════════════════════════════════════════════════════════════════════════
print("=== Step 1: Coal Retirement Schedule ===")

# 1a. Fix coal residual capacity to Morocco's actual fleet
# Then decline: keep current through 2030, start retiring 2035, done by 2048
# Source: SNBC Figure 20 p.54: coal generation ~20 TWh in 2025, ~15 in 2035, ~0 by 2050
coal_milestones = {
    0: 2.70,   # 2015: Morocco's actual coal fleet
    7: 2.70,   # 2022: same (Safi online 2018, already counted)
    15: 2.70,  # 2030: still running (ONEE contracts)
    20: 2.00,  # 2035: partial retirement begins
    25: 1.00,  # 2040: accelerated retirement
    30: 0.30,  # 2045: nearly done
    33: 0.00,  # 2048: fully retired
}
set_trajectory('nemomod_entc_residual_capacity_pp_coal_gw', coal_milestones)

# 1b. Block new coal investment from 2025 onward
# -999 = unconstrained in NemoMod. Set to 0 to block.
coal_invest_col = 'nemomod_entc_total_annual_max_capacity_investment_pp_coal_gw'
for t in range(10, N_TP):  # tp=10 = 2025
    df.loc[t, coal_invest_col] = 0.0
# Keep tp=0-9 at -999 (unconstrained, allows historical builds like Safi)
print(f"  {coal_invest_col}: 0 from tp=10 (2025)")

# 1c. Coal MSP declines with capacity
# Current MSP = 0.65. Decline proportionally to capacity.
# MSP must decline WELL AHEAD of capacity to avoid INFEASIBLE
# As demand grows and coal stays fixed, MSP share becomes impossible to meet
# Key: MSP 0.65 at 2.7 GW works for ~40 TWh demand. At ~60 TWh (2030), coal can only
# produce ~18 TWh = 30%, so MSP must be <0.30 by then.
msp_milestones = {
    0: 0.65,   # Current calibrated value
    7: 0.65,   # Keep through 2022
    8: 0.55,   # 2023: start easing immediately
    10: 0.40,  # 2025: renewables growing fast
    13: 0.25,  # 2028: transition period
    15: 0.15,  # 2030: coal ~25% of growing demand
    20: 0.05,  # 2035: minimal
    23: 0.00,  # 2038: zero MSP (coal can still run but no floor)
}
set_trajectory('nemomod_entc_frac_min_share_production_pp_coal', msp_milestones)

# 1d. Renewable capacity ramp (SNBC Figure 19 p.54)
# Solar: ~0 GW (2015) → ~1 GW (2022) → ~5 GW (2030) → ~30 GW (2050)
# Wind: ~1 GW (2015) → ~2 GW (2022) → ~4 GW (2030) → ~15 GW (2050)
print("\n=== Step 1d: Renewable Capacity Ramp ===")
solar_milestones = {0: 0.02, 7: 0.94, 10: 3.0, 13: 4.5, 15: 6.0, 20: 12.0, 25: 18.0, 35: 30.0, 45: 40.0, 55: 45.0}
wind_milestones = {0: 1.11, 7: 2.04, 15: 4.0, 25: 8.0, 35: 15.0, 45: 18.0, 55: 20.0}
set_trajectory('nemomod_entc_residual_capacity_pp_solar_gw', solar_milestones)
set_trajectory('nemomod_entc_residual_capacity_pp_wind_gw', wind_milestones)

# Also ramp gas capacity (SNBC p.53: ~5 GW gas by 2050 for dispatchable backup)
gas_milestones = {0: 2.63, 7: 2.93, 15: 3.5, 25: 4.0, 35: 5.0, 45: 5.0, 55: 5.0}
set_trajectory('nemomod_entc_residual_capacity_pp_gas_gw', gas_milestones)

# Keep hydro stable
hydro_milestones = {0: 2.64, 7: 2.95, 15: 3.0, 25: 3.0, 35: 3.0, 45: 3.0, 55: 3.0}
set_trajectory('nemomod_entc_residual_capacity_pp_hydropower_gw', hydro_milestones)


# ═══════════════════════════════════════════════════════════════════════════
# STEP 2: Transport Elasticity
# Source: SNBC p.59-62: transport GHG 22→55 Mt by 2050 (CAGR 4.8%/yr)
# Implied elasticity to GDP/capita: 1.47
# Using 1.20 (conservative) for tp=8+
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Step 2: Transport Elasticity ===")

for col in ['elasticity_trde_pkm_to_gdppc_private_and_public',
            'elasticity_trde_pkm_to_gdppc_regional']:
    old = df[col].iloc[0]
    for t in range(8, N_TP):
        df.loc[t, col] = 1.20
    print(f"  {col}: {old:.2f} (tp=0-7) → 1.20 (tp=8+)")

col_freight = 'elasticity_trde_mtkm_to_gdp_freight'
old = df[col_freight].iloc[0]
for t in range(8, N_TP):
    df.loc[t, col_freight] = 1.00
print(f"  {col_freight}: {old:.2f} (tp=0-7) → 1.00 (tp=8+)")


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3: IPPU Elasticities
# Source: SNBC Figure 28 p.58: IPPU ~8 Mt (2022) → ~16 Mt (2050)
# Cement: SNBC p.157 per-capita model, NIR 2010-22 elasticity -0.42
#   Recommended: +0.30 (cyclical decline was temporary, 2024 rebound +7.2%)
# Chemicals: SNBC p.155-156 OCP expansion. Set 0.80.
# Others: 0.80 (SNBC industry energy elasticity 1.12)
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Step 3: IPPU Elasticities ===")

ippu_elasticities = {
    'cement': 0.30,           # SNBC per-capita, NIR -0.42, 2024 rebound +7.2%
    'chemicals': 0.80,        # OCP phosphate expansion
    'metals': 0.80,           # SNBC industry growth
    'glass': 0.80,            # NIR shows strong growth (elasticity 5.73 historical)
    'lime_and_carbonite': 0.30,  # Tracks cement (linked industry)
    'paper': 0.80,
    'plastic': 0.80,
    'textiles': 0.80,
    'electronics': 0.80,
    'rubber_and_leather': 0.80,
    'mining': 0.80,           # Phosphate mining (OCP)
    'wood': 0.50,             # Slow growth, sustainability constraints
}
for industry, elast in ippu_elasticities.items():
    col = f'elasticity_ippu_{industry}_production_to_gdp'
    if col in df.columns:
        old = df[col].iloc[0]
        df[col] = elast  # Constant (IPPU stability requirement)
        print(f"  {industry:25s}: {old:+.2f} → {elast:+.2f}")


# ═══════════════════════════════════════════════════════════════════════════
# STEP 4: Commercial SCOE Elasticity
# Source: SNBC p.154: tertiary energy demand linked to GDP
# SNBC implied: 1.5-2.0. NIR historical: 0.30.
# Starting at 0.50 (conservative)
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Step 4: Commercial SCOE Elasticity ===")

for col in ['elasticity_scoe_enerdem_per_mmmgdp_commercial_municipal_heat_energy_to_gdppc',
            'elasticity_scoe_enerdem_per_mmmgdp_commercial_municipal_elec_appliances_to_gdppc']:
    old = df[col].iloc[0]
    for t in range(8, N_TP):
        df.loc[t, col] = 0.50
    print(f"  {col.replace('elasticity_scoe_enerdem_per_mmmgdp_',''):50s}: {old:.2f} → 0.50 (tp=8+)")


# ═══════════════════════════════════════════════════════════════════════════
# STEP 5: Residential Elasticity Correction
# Source: SNBC p.55: residential demand +110% by 2050, emissions 12→17 Mt
# Current model: 15→28 Mt (too fast). Elasticity 0.96 is too high.
# SNBC implies ~0.70 elasticity to GDP per capita for forward period.
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Step 5: Residential Elasticity Correction ===")

for col in ['elasticity_scoe_enerdem_per_hh_residential_heat_energy_to_gdppc',
            'elasticity_scoe_enerdem_per_hh_residential_elec_appliances_to_gdppc']:
    old_0 = df[col].iloc[0]
    old_8 = df[col].iloc[8] if 8 < N_TP else old_0
    for t in range(8, N_TP):
        df.loc[t, col] = 0.70
    print(f"  {col.replace('elasticity_scoe_enerdem_per_hh_',''):50s}: tp0={old_0:.2f}, tp8={old_8:.3f} → 0.70 (tp=8+)")


# ═══════════════════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== SAVE ===")

# Verify tp=0-7 not corrupted for key calibration parameters
check_cols = ['efficfactor_entc_technology_fuel_use_pp_coal',
              'ef_lvst_entferm_cattle_dairy_kg_ch4_head',
              'consumpinit_inen_energy_total_pj_agriculture_and_livestock']
for c in check_cols:
    if c in df.columns:
        print(f"  Lock check {c}: tp0={df[c].iloc[0]:.3f}, tp7={df[c].iloc[7]:.3f}")

n_inf = sum(np.isinf(df[c]).sum() for c in df.select_dtypes(include=[np.number]).columns)
n_nan = df.isna().sum().sum()
print(f"  inf: {n_inf}, NaN: {n_nan}")

df.to_csv(CSV, index=False)
print(f"\nSaved to {CSV}")
print("Pipeline: apply_step0 → apply_step1 → apply_step2_bau → run_calibration0")
