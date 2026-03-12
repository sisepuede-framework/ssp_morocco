# BAU Scenario Design: Matching SNBC Reference Trajectory

## Problem Statement

The historical calibration matches the NIR 2022 inventory well (7.29 MtCO2e error, 16/34 within 15%). But the forward trajectory diverges from the SNBC Reference Scenario:

| Year | SNBC Ref | Model | Gap |
|------|----------|-------|-----|
| 2022 | ~100 Mt | 96.3 Mt | -4% |
| 2030 | ~125 Mt | 103.5 Mt | -17% |
| 2050 | ~200 Mt | 136.0 Mt | -32% |

The divergence comes from structural differences between SISEPUEDE's elasticity-driven demand model and the SNBC's LEAP+NEMO framework (activity analysis, vehicle stock turnover, end-use models).

## Sector-Level Composition Gap (SNBC Figure 15, p.51)

| Sector | SNBC 2050 | Model 2050 | Gap | Root Cause |
|--------|----------|-----------|-----|-----------|
| Electricity/ENTC | 3 Mt | 112 Mt | +109 Mt | No coal retirement in model |
| Transport | 55 Mt | 30 Mt | -25 Mt | Transport elasticity too low |
| Industry-energy | 23 Mt | 10 Mt | -13 Mt | Industry elasticity too low |
| Industry-process | 10 Mt | 3 Mt | -7 Mt | Cement elasticity -2.0 |
| Buildings | 17 Mt | 28 Mt | +11 Mt | Residential elasticity too high |
| Waste | 12 Mt | 12 Mt | OK | |
| FGTV/Other | 10 Mt | 0 Mt | -10 Mt | FGTV EFs zeroed too aggressively |

## SNBC-Derived Elasticities (from SNBC Annex 1, verified by research agent)

| Sector | SNBC Method | SNBC Implied Elasticity | NIR Historical | Current Model |
|--------|-----------|----------------------|---------------|--------------|
| Cement | Per capita (APC/MHUPV) | 0.3-0.5 | -0.42 (2010-22) | -2.00 |
| Industry energy | Value-added by subsector | 1.12 | 0.54 | 0.50 |
| Commercial | GDP-linked (tertiary output) | 1.5-2.0 | 0.30 | 0.00 |
| Transport | Vehicle stock turnover (108 techs) | 1.47 | 0.71 | 0.80 |
| Residential | Per HH + income | ~1.0 | 0.82 | 0.96 |

Source: SNBC pp.154-162, NIR Tableaux 43/61, IEA historical data.

## Implementation Plan (Two-Phase Approach)

### Phase 1: Historical Calibration (tp=0 to tp=7) — LOCKED
Already done. 7.29 MtCO2e against NIR. Do not modify.

### Phase 2: Forward Trajectory (tp=8 to tp=35) — THIS DOCUMENT

#### Priority 1: Coal Retirement Schedule
SNBC: coal-fired plants decommissioned by late 2040s (ONEE capital plan, SNBC p.53-54).
Model: NemoMod keeps coal forever and builds more.

Columns to set (time-varying trajectory):
- `nemomod_entc_residual_capacity_pp_coal_gw`: 2.2 → 0 GW by tp=33 (2048)
- `nemomod_entc_total_annual_max_capacity_investment_pp_coal_gw`: 0 from tp=10+
- `nemomod_entc_total_annual_max_capacity_pp_coal_gw`: decline matching residual
- `nemomod_entc_frac_min_share_production_pp_coal`: decline to 0 matching capacity

Impact: ~109 Mt by 2050. This is the single largest fix.

#### Priority 2: Transport Elasticity
SNBC: motorization wave, 22→55 Mt (CAGR 4.8%/yr). Implied elasticity 1.47.
Model: 19→30 Mt (CAGR 1.6%/yr). Current elasticity 0.80.

Columns (time-varying, one value per row):
- `elasticity_trde_pkm_to_gdppc_private_and_public`: 0.80 (tp=0-7) → 1.20 (tp=8+)
- `elasticity_trde_pkm_to_gdppc_regional`: 0.80 (tp=0-7) → 1.20 (tp=8+)
- `elasticity_trde_mtkm_to_gdp_freight`: 0.80 (tp=0-7) → 1.00 (tp=8+)

Impact: ~25 Mt by 2050.

#### Priority 3: Cement/IPPU Elasticity
SNBC: IPPU doubles 6→16 Mt (OCP expansion + cement recovery).
Model: IPPU declines 6→3 Mt (cement elasticity -2.0).

Column (constant, code constraint for IPPU):
- `elasticity_ippu_cement_production_to_gdp`: -2.0 → +0.30
- `elasticity_ippu_chemicals_production_to_gdp`: 0.50 → 0.80 (OCP expansion)
- Other IPPU industries: 0.50 → 0.80

For OCP step-changes (desalination plants):
- `demscalar_ippu_chemicals`: ramp from 1.0 to 1.5+ at commissioning dates

Impact: ~7 Mt by 2050.

#### Priority 4: Commercial SCOE
SNBC: tertiary energy triples by 2050 (urbanization + services growth).
Model: flat (elasticity 0.00).

Columns (time-varying):
- `elasticity_scoe_enerdem_per_mmmgdp_commercial_municipal_heat_energy_to_gdppc`: 0.00 → 0.50
- `elasticity_scoe_enerdem_per_mmmgdp_commercial_municipal_elec_appliances_to_gdppc`: 0.00 → 0.50

Impact: ~5 Mt by 2050.

#### Priority 5: Renewable Capacity Ramp
SNBC Fig 19: Solar + wind capacity grows from ~3 GW to 60+ GW by 2050.
NemoMod may build renewables automatically if cost-competitive, but explicit capacity targets help.

Columns:
- `nemomod_entc_residual_capacity_pp_solar_gw`: ramp matching SNBC Fig 19
- `nemomod_entc_residual_capacity_pp_wind_gw`: ramp matching SNBC Fig 19

#### Priority 6: Residential Elasticity Correction
SNBC: residential 12→17 Mt (modest growth). Model: 15→28 Mt (too fast).
Current residential elasticity 0.96 is too high for BAU.

Column:
- `elasticity_scoe_enerdem_per_hh_residential_heat_energy_to_gdppc`: 0.96 → 0.70 (tp=8+)

## Key SISEPUEDE Levers (from source code analysis)

| Lever | Column Pattern | Time-varying? | Use |
|-------|---------------|---------------|-----|
| Coal retirement | `nemomod_entc_residual_capacity_pp_coal_gw` | Yes (per row) | Declining installed capacity |
| Block new coal | `nemomod_entc_total_annual_max_capacity_investment_pp_coal_gw` | Yes | 0 from stop year |
| Capacity ceiling | `nemomod_entc_total_annual_max_capacity_pp_coal_gw` | Yes | Hard upper bound |
| Production growth | `elasticity_ippu_{industry}_production_to_gdp` | Yes (keep constant for stability) | GDP-linked growth |
| Production shocks | `demscalar_ippu_{industry}` | Yes | Step-changes (desalination) |
| Energy demand shocks | `scalar_inen_energy_demand_{industry}` | Yes | Direct demand multiplier |
| Transport growth | `elasticity_trde_*_to_gdppc_*` | Yes | Motorization wave |
| Transport shocks | `demscalar_trde_{category}` | Yes | Exact trajectory match |
| SCOE elasticity | `elasticity_scoe_enerdem_per_*` | Yes | Buildings demand growth |

## Validation Targets

Run and check at tp=15 (2030) and tp=35 (2050) against SNBC Figure 15:

| Sector | SNBC 2030 | SNBC 2050 | Tolerance |
|--------|----------|----------|-----------|
| Electricity | ~33 Mt | ~3 Mt | 15% |
| Buildings | ~13 Mt | ~17 Mt | 15% |
| Industry-energy | ~12 Mt | ~23 Mt | 20% |
| Industry-process | ~7 Mt | ~10 Mt | 20% |
| Transport | ~26 Mt | ~55 Mt | 15% |
| Agriculture | ~19 Mt | ~20 Mt | 15% |
| Waste | ~8 Mt | ~12 Mt | 15% |

## Sources

- SNBC 2024 English (NDC Docs/Morocco SNBC 2050 - LEDS Nov2024 - English - Unpublished.pdf)
  - Figure 2 p.12: Total Reference trajectory
  - Figure 15 p.51: Sector-level Reference stacked bars
  - Figure 19-20 p.54: Electricity capacity and generation mix
  - Figure 21 p.55: Grid electricity emissions
  - Figure 22-25 pp.55-56: Buildings energy demand and emissions
  - Figure 26 p.57: Industry energy demand
  - pp.154-162: LEAP model assumptions (GDP, population, sector methodology)
- NIR 2024 Tableaux 43, 61 (production and energy data for elasticity validation)
- SISEPUEDE source code: ippu.py, energy_consumption.py, energy_production.py, _toolbox.py
