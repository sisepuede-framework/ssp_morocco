# BAU Scenario Design Prompt: Match SNBC Reference Trajectory

## Context

The historical calibration is DONE and LOCKED. Do not modify any parameter at tp=0 through tp=7 (2015-2022). The baseline matches the NIR 2024 inventory at 7.29 MtCO2e total error across 34 IPCC categories.

The task now is to adjust the FORWARD trajectory (tp=8 through tp=55, 2023-2070) so that SISEPUEDE's Strategy 0 (baseline) reproduces Morocco's SNBC Reference Scenario.

## Why This Matters

Every NDC mitigation strategy is measured as: `BAU emissions - strategy emissions = mitigation potential`. If BAU is 32% too low by 2050, all mitigation estimates are wrong. The SNBC Reference is the official BAU that Morocco's climate commitments are measured against.

## The Gap

| Year | SNBC Reference | Current Model | Gap |
|------|---------------|--------------|-----|
| 2022 | ~100 Mt | 96.3 Mt | -4% (OK) |
| 2030 | ~125 Mt | 103.5 Mt | -17% |
| 2050 | ~200 Mt | 136.0 Mt | -32% |

## Design Brief

Read `ssp_modeling/notebooks/bau_scenario_design.md` for the full implementation plan with:
- Sector-by-sector composition comparison (SNBC Figure 15 vs model)
- SNBC-derived elasticities with page citations
- Column names and mechanisms (verified in SISEPUEDE source code)
- 6 prioritized implementation actions
- Validation targets at 2030 and 2050

## Implementation Order

### Step 1: Coal Retirement Schedule (biggest impact: ~109 Mt by 2050)

SNBC says coal plants retire by late 2040s (ONEE capital plan). Our NemoMod keeps coal forever.

**Create `apply_step2_bau_scenario.py`** (runs AFTER step1, BEFORE run_calibration0.py):

```python
# Coal retirement: SNBC p.53-54, Figure 20
# Morocco has ~2.2 GW coal. ONEE plan: no new coal, retire by ~2048.
coal_cap = 'nemomod_entc_residual_capacity_pp_coal_gw'
coal_invest = 'nemomod_entc_total_annual_max_capacity_investment_pp_coal_gw'
coal_max = 'nemomod_entc_total_annual_max_capacity_pp_coal_gw'
coal_msp = 'nemomod_entc_frac_min_share_production_pp_coal'

# Set declining trajectory for residual capacity
# tp=7 (2022): 2.2 GW, tp=15 (2030): 1.5 GW, tp=25 (2040): 0.5 GW, tp=33 (2048): 0 GW
# Interpolate linearly between milestones
```

Key constraints:
- `residual_capacity` declines from 2.2 → 0 GW
- `max_capacity_investment` = 0 from tp=10 onward (no new coal after 2025)
- `frac_min_share_production` (MSP) declines in parallel — otherwise INFEASIBLE
- Verify renewable capacity grows to absorb demand (check SNBC Figure 19)

### Step 2: Transport Elasticity (impact: ~25 Mt by 2050)

SNBC projects motorization wave: transport 22→55 Mt. Implied elasticity 1.47.

```python
# Time-varying elasticity: historical (tp=0-7) stays at 0.80, forward (tp=8+) rises
for col in ['elasticity_trde_pkm_to_gdppc_private_and_public',
            'elasticity_trde_pkm_to_gdppc_regional']:
    df.loc[df.index > 7, col] = 1.20  # SNBC: 1.47, start conservative
df.loc[df.index > 7, 'elasticity_trde_mtkm_to_gdp_freight'] = 1.00
```

### Step 3: IPPU Elasticities (impact: ~7 Mt by 2050)

```python
# Cement: -2.0 → +0.30 (SNBC per-capita model, NIR 2010-22: -0.42, 2024 rebound +7.2%)
df['elasticity_ippu_cement_production_to_gdp'] = 0.30

# Other industries: 0.50 → 0.80 (SNBC industry energy elasticity 1.12)
for industry in ['chemicals', 'metals', 'glass', 'paper', 'textiles', ...]:
    df[f'elasticity_ippu_{industry}_production_to_gdp'] = 0.80
```

### Step 4: Commercial SCOE (impact: ~5 Mt by 2050)

```python
# Time-varying: 0.00 (tp=0-7) → 0.50 (tp=8+)
for col in ['elasticity_scoe_enerdem_per_mmmgdp_commercial_municipal_heat_energy_to_gdppc',
            'elasticity_scoe_enerdem_per_mmmgdp_commercial_municipal_elec_appliances_to_gdppc']:
    df.loc[df.index > 7, col] = 0.50
```

### Step 5: Renewable Capacity Ramp (supporting coal exit)

SNBC Figure 19: solar + wind capacity grows from ~3 GW to 60+ GW by 2050.

```python
# Solar: ~1 GW (2022) → ~30 GW (2050)
# Wind: ~2 GW (2022) → ~15 GW (2050)
# Source: SNBC Figure 19 p.54
```

### Step 6: Residential Elasticity Correction

SNBC: residential 12→17 Mt (modest). Model: 15→28 Mt (too fast). Reduce residential elasticity for forward period.

## Validation Protocol

After each priority, run:
```bash
python run_calibration0.py --baseline-only --input-file df_input_0.csv
```

Check THREE things:
1. **tp=7 (2022) still matches NIR** — no regression from historical calibration
2. **tp=15 (2030) matches SNBC** — sector totals within 15% of Figure 15
3. **tp=35 (2050) matches SNBC** — sector totals within 20% (accept wider tolerance for 28-year projection)

Use compare_to_inventory.py for tp=7. For tp=15 and tp=35, extract sector totals directly from WIDE_INPUTS_OUTPUTS.csv and compare against SNBC Figure 15 values.

## Sources (all in repo)

| Source | Path | Key Data |
|--------|------|----------|
| SNBC 2024 | NDC Docs/Morocco SNBC 2050 - LEDS Nov2024 - English - Unpublished.pdf | Fig 2 (total), Fig 15 (sectors), Fig 19-26 (per sector), pp.154-162 (assumptions) |
| NIR 2024 | NDC Docs/Additional docs/Maroc - Rapport National d'Inventaire... | T43 (energy by sector), T61 (IPPU production) |
| Design brief | ssp_modeling/notebooks/bau_scenario_design.md | Full analysis with column names |
| Calibration log | calibration_log.md | Historical calibration audit trail |
| Current input | ssp_modeling/input_data/df_input_0.csv | Calibrated baseline (DO NOT modify tp=0-7) |

## Key Technical Notes

- **Time-varying elasticities ARE supported** for SCOE and transport (verified: `_toolbox.py` line 3141)
- **IPPU production elasticities**: keep constant for stability. Use `demscalar_ippu_{industry}` for step-changes.
- **NemoMod capacity**: all three columns (`residual_capacity`, `max_capacity_investment`, `total_annual_max_capacity`) are time-varying (one value per row)
- **MSP must decline with coal capacity** — otherwise INFEASIBLE
- **Do not run two NemoMod instances in parallel** — Julia compilation conflict
- **Coal efficiency (0.22)**: will become irrelevant as capacity → 0, but don't change it (affects tp=7)
