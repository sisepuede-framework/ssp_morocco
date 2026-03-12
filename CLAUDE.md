# SISEPUEDE Calibration -- Autonomous Agent Protocol

## Quick Start (for resuming sessions)

```
Pipeline:  apply_step0_verified.py → apply_step1_calibration.py → run_calibration0.py
Diagnose:  ssp_modeling/output_postprocessing/scripts/compare_to_inventory.py \
           --targets ssp_modeling/output_postprocessing/data/invent/emission_targets_{country}_{year}.csv \
           --output WIDE_INPUTS_OUTPUTS.csv --tp 7
Read:      calibration_log.md (full audit trail), diagnostics/diff_report.csv (current gaps)
```

## Section 1: Mission

You are calibrating the SISEPUEDE climate emissions model. You start from a raw template CSV (~2420 columns, 56 rows) and must produce a calibrated `df_input_0.csv` that matches the country's national GHG inventory.

SISEPUEDE runs sectors in a fixed DAG: AFOLU -> CircularEconomy -> IPPU -> EnergyConsumption -> EnergyProduction (NemoMod/Julia LP) -> FugitiveEmissions. Use `compare_to_inventory.py` with the IPCC crosswalk (`emission_targets_{country}_{year}.csv`) to diagnose gaps.

**Key definitions:**
- **tp** = time period. tp=0 is the base year, tp=7 is typically the calibration year. Check config.yaml for actual year mapping.
- **mmm** in column names = billions (10^9). `gdp_mmm_usd` = GDP in billion USD.
- **EAR** = EmissionsActivityRatio. NemoMod parameter: emissions per unit of electricity generated (PJ).
- **NemoMod** = Julia-based LP energy optimizer. First run triggers Julia compilation (~5-10 min one-time).

The input CSV describes a country's economy, energy, agriculture, waste, and land use. Each row = one year (2015-2070). Emissions = activity data x emission factors. The calibration task is identifying WHICH inputs are wrong and fixing them using real data.

The raw template comes pre-populated with defaults — many from the wrong country, wrong IPCC region, or wrong scale. Replace these with country-specific values from the external data files.

### PDF Table Extraction

Most IPCC tables are already extracted to `ipcc_tables/*.csv` — use those first. If you need a new table, extract with `pdfplumber`, save to `ipcc_tables/`, and verify independently. IPCC tables often span 2-3 pages; check for continuations.

### Read the Documentation First

When you encounter something you don't understand, **read the SISEPUEDE documentation BEFORE guessing**:

```
sisepuede_docs/sisepuede.readthedocs.io/en/latest/
  sisepuede_concept.html  — Overall architecture, DAG, sector integration
  energy_consumption.html — INEN, SCOE, TRNS: how demand is computed
  energy_production.html  — NemoMod, MSP, EAR, capacity, fuel chains
  mathdoc_energy.html     — The demand formula, α^D vs α^C conversion
  afolu.html              — Livestock, crops, land use, soil, forestry
  circular_economy.html   — Waste, wastewater
  ippu.html               — Industrial processes, cement, F-gas
```

Also read the SISEPUEDE source code when docs are insufficient:
```
{SSP_PACKAGE}/models/energy_production.py  — NemoMod table generation, EAR computation
{SSP_PACKAGE}/models/afolu.py              — Livestock, land use Markov chain
{SSP_PACKAGE}/attributes/variable_definitions_*.csv — Column name definitions and units
{SSP_PACKAGE}/attributes/attribute_cat_*.csv — Category definitions
```

**Absolute rules:**
1. NEVER modify any file under the sisepuede package directory. Every fix goes through CSV inputs, config.yaml, or run_calibration0.py.
2. NEVER invent parameter values from training knowledge. Every value must be traceable to a file in this repo.
3. NEVER proceed to sector calibration until fundamentals (population, GDP, livestock) are verified against external data CSVs.

---

## Section 2: Environment

```
PROJECT_DIR  = <detect from git rev-parse --show-toplevel>
VENV         = <path to Python venv with sisepuede installed>
SSP_PACKAGE  = <VENV>/lib/python3.11/site-packages/sisepuede/
```

### Data Sources (all paths relative to PROJECT_DIR)

| Path | Contents |
|------|----------|
| `external_data/world_bank/*.csv` | Population, GDP, urbanization, transport indicators |
| `external_data/fao/*.csv` | Livestock populations, manure, fertilizer, crop/livestock emissions |
| `external_data/edgar/*.csv` | EDGAR v8.0 emissions by gas and IPCC category |
| `external_data/iea_comprehensive/*.csv` | IEA energy balance, TFC by sector, generation by source, coal/oil/gas production, imports, exports |
| `NDC Docs/*.pdf` | SNBC 2024 (English + French), Executive Summary |
| `NDC Docs/Additional docs/*.pdf` | BUR3 (French), NIR 2024 (French), LTS 2021 |
| `ipcc/*.pdf` | IPCC 2006 Vol 2-5 chapters |
| `ipcc_tables/*.csv` | Pre-extracted IPCC tables (verified via pdfplumber) |
| `sisepuede_docs/sisepuede.readthedocs.io/en/latest/*.html` | SISEPUEDE documentation |

### Cross-Country References

Cross-country repos (sibling directories like `../ssp_bulgaria/`, `../ssp_mexico/`) are optional. Use them to discover which parameters (LEVERS) exist. Country VALUES must come from country-specific data.

### SISEPUEDE Version Check

Verify EAR efficiency fix: `grep -n "arr_entc_eff_techs" {SSP_PACKAGE}/models/energy_production.py`. If no results, ENTC CO2 is structurally understated with no CSV workaround.

### config.yaml
The raw config may point to the wrong input file. After building your calibrated CSV, either update config.yaml or always pass `--input-file df_input_0.csv`.

### run_calibration0.py

Verify/update `ssp_modeling/notebooks/run_calibration0.py`. It should:
1. Load SISEPUEDE, read config.yaml, run strategy 0 (baseline)
2. Output to timestamped `ssp_run_output/calibration_{YYYYMMDD_HHMMSS}/`: `WIDE_INPUTS_OUTPUTS.csv`, `emissions_table_baseline.csv`, `emissions_stack_baseline.png`
3. Call `compare_to_inventory.py` → `diagnostics/diff_report.csv`, `diagnostics/flagged.csv`, `diagnostics/diagnostics.csv`
4. Accept: `--strategies`, `--input-file`, `--end-year`, `--baseline-only`, `--no-energy`

Key imports:
```python
import sisepuede as si
import sisepuede.manager.sisepuede_file_structure as sfs
import sisepuede.manager.sisepuede_models as sm
import sisepuede.transformers as trf
from ssp_transformations_handler.GeneralUtils import GeneralUtils
```

---

## Section 3: Verification Protocol

Every parameter change MUST follow this chain. No exceptions.

### Before changing any parameter:

1. **Verify the column exists.** `grep -c "column_name" raw_template.csv`. If 0, STOP.
2. **Read the source document.** Cite: file path, page/row number, exact value read.
3. **Check units.** Population=persons, GDP=billion USD, energy=PJ (outputs)/GJ/HH (SCOE res)/TJ/mmm_GDP (SCOE comm, INEN), livestock=head, EFs=tCO2/TJ or kg_gas/head, fractions 0-1.
4. **Check fraction group sums.** ALL fractions must sum to 1.0 at every time period.
5. **Predict DAG cascade.** "Changing [param] at Step [N] propagates to Steps [N+1,...] via [edges]."
6. **Independent verification.** For critical values, re-read the source file to confirm the extracted value. Cross-check against a second independent source where available (e.g., verify an FAO value against a BUR3 table, or an IPCC EF against the NIR methodology section).

**Online data**: You may search the web for data not in the repo (census occupancy, plant specs, production volumes). Every web-sourced value must be cross-checked: find the same data point from a second independent source. Only accept if both converge within 10%.

### Source citation format for calibration_log.md:

```
Parameter: [column_name]
Old: [value], New: [value]
Source: [file path], Detail: [row/page, exact value read]
Calculation: [how derived], Cross-check: [second source]
Fraction group verified: [group] sums to 1.000
```

---

## Section 4: Mandatory Preflight Gates

Do NOT skip. Do NOT proceed to sector calibration until ALL gates pass.

### GATE 1: Population
Read `external_data/world_bank/` for population. Compare against `population_gnrl_rural + population_gnrl_urban` at tp=0. If >5% off, STOP and fix.

### GATE 2: GDP Scale
Read World Bank GDP. Compare against `gdp_mmm_usd` at tp=0. Do NOT change GDP without rescaling ALL intensity parameters (TJ/mmm_GDP).

### GATE 3: Occupancy Rate
Research average household size. HH count = population / occupancy. Drives ALL residential energy demand.

### GATE 4: Livestock Populations
Read `external_data/fao/` by species. Compare against `pop_lvst_initial_*` at tp=0.

### GATE 5: Fertilizer
Read FAO fertilizer data. Check `qtyinit_soil_synthetic_fertilizer_kt` at tp=0. Verify nutrient content (N), not product weight.

### GATE 6: Fuel Import Fractions
Research fuel production/import status from IEA data. Set `frac_enfu_fuel_demand_imported_pj_fuel_*` accordingly.

### GATE 7: Climate Classification
Research IPCC climate zone. Check `frac_agrc_*_cl1_*` and `_cl2_*` columns match.

### GATE 7b: Fuel Exports
Check ALL `exports_enfu_pj_fuel_*`. Template may have fuel exports from the BASE COUNTRY. Zero any fuel the country does NOT export. Check IEA trade data (`external_data/iea_comprehensive/`).

### GATE 7c: Waste Baseline
Read NIR waste tables. Compare `qty_waso_initial_municipal_waste_tonne_per_capita` and `frac_waso_*` composition fractions against NIR values. Template waste data is almost always from the base country. Also check `frac_waso_landfill_gas_recovered` — template may have ~1.0 (industrialized country) when actual value is near 0.

### GATE 7d: IPPU Production Volumes
Read BUR3/NIR for cement and other industrial production volumes. Compare against `prodinit_ippu_*_tonne` at tp=0. Template values from the base country will be wildly wrong.

### GATE 8: IEA Energy Balance
Read `external_data/iea_comprehensive/` CSVs. **First verify the path exists.** Extract for 2015 (tp=0) and 2022 (tp=7): total electricity generation + mix, industry/residential/commercial/transport TFC + fuel splits, fuel import/export profile, refining capacity. Record in `calibration_log.md` under "IEA Reference Data."

### GATE 9: NIR/SNBC Sector Targets
Read NIR/SNBC PDFs. Extract sector emission targets for the calibration year with page/figure citations. Compare against EDGAR targets — NIR values are authoritative.

### GATE 10: inf/NaN scan
Must return 0 corrupt columns before any run.

---

## Section 5: The DAG

```
              ┌───────────────────────────┐
              │ Socioeconomic (ECON+GNRL) │
              │ population, GDP, HH count │
              └─────────────┬─────────────┘
                            │ feeds ALL sectors
                            ▼
  ┌─────────────────────────────────────────────────────┐
  │ Step 1: AFOLU                                       │
  │ LNDU → FRST → AGRC → LVST → LSMM → SOIL           │
  │ (land)  (forest) (crops) (livestock) (manure) (N2O) │
  └──┬──────────┬──────────┬────────────────────────────┘
     │food loss │crop yield│biogas
     │dung→MSW  │mass      │
     ▼          ▼          ▼
  ┌──────────────────┐
  │ Step 2: CircEcon │──────────────────────────────────┐
  │ WALI→TRWW→WASO   │                                  │
  └──┬───────────────┘                                  │
     │recycled waste                                    │
     ▼                                                  │
  ┌──────────────────┐                                  │
  │ Step 3: IPPU     │                                  │
  │ cement,HFC,metals│                                  │
  └──┬───────────────┘                                  │
     │production volumes                                │
     ▼                                                  ▼
  ┌───────────────────────────────────────────────────────┐
  │ Step 4: EnergyConsumption                             │
  │ CCSQ → INEN → SCOE → TRNS                            │
  │ (CCS) (industry) (buildings) (transport)              │
  └──┬────────────────────────────────────────────────────┘
     │fuel demand (electricity, gas, oil, coal, biomass)
     ▼
  ┌───────────────────────────────────────────────────────┐
  │ Step 5: EnergyProduction (NemoMod LP)                 │
  │ ENTC + ENFU + ENST                                    │
  │ Dispatches generation. coal/gas burn, imports, builds │
  └──┬────────────────────────────────────────────────────┘
     │production volumes, imports, exports
     ▼
  ┌───────────────────────────────────────────────────────┐
  │ Step 6: FugitiveEmissions (FGTV)                      │
  │ CH4 from fuel extraction, refining, flaring           │
  └───────────────────────────────────────────────────────┘
```

### Critical Cascades

1. **Electrification**: INEN/SCOE electricity fractions -> electricity demand -> NemoMod coal/gas -> ENTC CO2 -> FGTV
2. **Production-Demand**: `prodinit_ippu_*` x `consumpinit_inen_*` x `frac_inen_energy_*` = fuel demand (3 multiplicative factors — errors compound)
3. **HWP**: `prodinit_ippu_wood_tonne` -> INEN energy -> NemoMod electricity. Wrong wood production inflates ENTC by 10-30x
4. **Waste-Energy**: Waste biogas/incineration -> NemoMod supply. Capping waste_incineration at 0 GW breaks feasibility

### DAG Reasoning Protocol

For each failing sector, BEFORE proposing a fix:
1. **Trace UPSTREAM**: What feeds this sector? Is the error inherited?
2. **Trace DOWNSTREAM**: What will move if I fix this? By how much?
3. **Check SHARED DRIVERS**: If 2+ sectors wrong in same direction, look for shared upstream cause
4. **Predict FULL CASCADE**: Walk the pipeline through ALL subsequent steps

---

## Section 6: Build df_input_0.csv (Step 0)

Write `apply_step0_verified.py` that reads external data and produces `df_input_0.csv`. Every parameter must have a source comment.

### 6.1 Socioeconomic
Population from World Bank CSVs. Urban/rural split from urbanization CSV. Occupancy from census research.

### 6.2 Livestock
Populations from FAO at 2015. Enteric EFs from `ipcc/V4_Ch10_Livestock.pdf` Tables 10.10-10.11 (select correct region). Body masses, N excretion from same chapter. For sheep/goat: if country breed weights differ from IPCC reference, apply the weight-scaling formula in V4_Ch10 (livestock characterization section).

**Manure management** (`frac_lvst_mm_{animal}_{system}`): High-leverage parameter. MCFs vary ~30x across systems (paddock ~0.015 vs liquid slurry ~0.47). Read IPCC Table 10.17 for MCFs at country's temperature. Research actual management (extensive vs confined). If LSMM CH4 is below target, template likely over-allocates to paddock.

### 6.3 Soil and Fertilizer
Fertilizer from FAO. Read BUR3 for which IPCC methodology (2006 vs 2019R) — soil N2O EFs differ 2-5x. Back-calculate EF1 from inventory target, but ensure it falls within IPCC uncertainty range. If not, investigate other inputs before forcing an unrealistic EF.

### 6.4 Energy -- SCOE (Buildings)
Read IEA residential/commercial TFC. Back-calculate: residential intensity = TFC / HH count, commercial = TFC / GDP.

`consumpinit_scoe_tj_per_mmmgdp_other_se` MUST be 0. IEA gives CONSUMPTION fractions; SISEPUEDE needs DEMAND fractions — read `mathdoc_energy.html` for conversion.

**SCOE biomass mapping**: Check whether inventory targets include/exclude biomass CO2. SISEPUEDE may compare building CO2 using only non-biomass (`nbmass`) output vars — check the `vars` column in targets CSV. Wrong interpretation creates 30-40% target error.

### 6.5 Energy -- INEN (Industry)
Read IEA industry TFC. SISEPUEDE needs PER-INDUSTRY fractions for 12 industries. Start with aggregate IEA mix, adjust from SNBC/BUR3. Production elasticities must be CONSTANT across ALL time periods.

### 6.6 Energy -- Transport
Read IEA transport TFC. Determine road fuel mix (diesel vs gasoline). Validate demand against IEA.

### 6.7 Energy -- NemoMod / ENTC
**Thermal efficiency** (key lever with EAR fix): Back-calculate from grid EF, generation mix (IEA), fuel EFs (IPCC T2.2). Research actual power fleet.

**MSP**: Constrain coal/wind/hydro at their IEA generation shares; gas/oil/solar form the flexible (unconstrained) pool. Total MSP sum ~0.90-0.95 (not 1.0). Over-constraining → INFEASIBLE.

**Cap non-existent technologies**: Set max capacity AND max investment to 0 GW. Keep biogas + waste_incineration with small residual capacity.

### 6.8 IPPU
Cement production from BUR3 process CO2. HFC: read BUR3 actual emissions, compute scaling factor.

### 6.9 Waste
NIR for waste per capita and composition. MCFs from IPCC Table 3.1 matching country's waste infrastructure.

### 6.10 Wastewater
Read BUR3 for IPCC version used for WW N2O EFs. 2006 vs 2019R values differ by 3x.

### 6.11 Land Use
For arid/semi-arid countries, wetland transitions (`pij_lndu_*_to_wetlands`) should be zero.

`lndu_reallocation_factor` (eta): multi-sector lever. **Sweep after all other AFOLU parameters are set** (0.00-0.40, step 0.05). Higher eta preserves pasture (better livestock) but increases land conversion (higher soil N2O/CO2). Pick eta minimizing TOTAL error.

### 6.12 LULUCF (Optional)
**Structural warning**: LULUCF is the hardest sector to calibrate. SISEPUEDE models land-use transitions via a Markov chain (transition probabilities between land types each period), not carbon stock accounting. The model tracks flows from conversion, not standing biomass stocks. Expect structural gaps of 5-15 MtCO2e even after calibration. Document all gaps.

**Why it's hard**: LULUCF emissions depend on three things SISEPUEDE handles differently from other sectors:
1. **Land area transitions** — driven by `pij_lndu_*` transition probabilities and `lndu_reallocation_factor` (eta). These determine HOW MUCH land converts each period.
2. **Carbon density per hectare** — SOC reference values, biomass factors, and sequestration rates. These determine HOW MUCH CO2 each hectare of conversion emits/removes.
3. **Historical accumulation** — forest carbon pools and HWP decay depend on decades of history that the model starts fresh at tp=0.

**4.A Forest Land** (typically the largest LULUCF category):
- Read NIR LULUCF table for CRF 4.A target. This is usually a NET REMOVAL (negative CO2).
- The crosswalk maps 4.A to: `frst_sequestration_primary`, `frst_sequestration_secondary`, `frst_sequestration_mangroves`, `frst_harvested_wood_products`, `frst_forest_fires`, plus CH4 from fires.
- **Sequestration calibration**: `ef_frst_sequestration_*_kt_co2_ha` controls the per-hectare uptake rate. Scale these to match NIR 4.A, but first decompose the NIR target — does it include HWP? Fire? If the NIR nets fire+HWP into 4.A (common), you need to account for what SISEPUEDE models vs what it doesn't.
- **HWP cascade**: `prodinit_ippu_wood_tonne` feeds INEN energy demand AND creates FRST carbon pools. Getting wood production wrong creates errors in BOTH energy (ENTC CO2 via electricity demand) AND forestry (HWP CO2 release). Check wood production against FAO roundwood data.
- **Fire**: SISEPUEDE models fire emissions (CH4) from forests but may understate fire CO2. If NIR 4.A includes large fire CO2, this is a structural gap — document it.

**4.B Cropland** (often a net removal from perennial biomass):
- Maps to: `agrc_biomass_fruits`, `agrc_biomass_nuts`, `agrc_biomass_other_woody_perennial`, plus `lndu_drained_organic_soils_croplands`.
- Perennial crop expansion (olives, citrus, argan) creates biomass sinks. The template may understate these if the base country has less perennial agriculture.
- Drained organic soils: if the country has negligible peatland drainage, this component should be near zero.

**4.C Grassland**:
- Maps to: `lndu_biomass_sequestration_grasslands`, `lndu_biomass_sequestration_pastures`, `lndu_drained_organic_soils_pastures`.
- Driven by grassland/pasture area changes from the land use transition matrix. If pasture is expanding (higher eta), grassland sequesters more; if contracting, it emits.

**4.B-4.C SOC (Soil Organic Carbon)**:
- Read `ipcc_tables/V4_Ch2_Table2.3_SOC_reference.csv` for the correct climate/soil zone SOC reference value.
- For arid/semi-arid countries, SOC ref ~38 tC/ha (NOT 50-80 for humid climates). Verify against NIR methodology.
- SOC change = (SOC_new - SOC_old) x area converted. Even 5 tC/ha error x 100 kha = 1.8 MtCO2e.
- **Sensitivity trap**: SOC factors are the single most sensitive AFOLU parameters. Small changes (5-10%) cause multi-MtCO2e swings. Only adjust with strong NIR evidence.

**4.D Wetlands**: Maps to `lndu_biomass_sequestration_wetlands` + `lndu_wetlands` CH4. For arid countries, typically small. Verify `pij_lndu_*_to_wetlands` = 0 if no wetland expansion.

**4.E Settlements**: Maps to `lndu_biomass_sequestration_settlements`. Usually small; driven by urban expansion consuming forest/cropland.

**Strategy**:
1. Set `INCLUDE_LULUCF = False` in the targets build script (default). Enable only after all other sectors are calibrated.
2. Calibrate LULUCF AFTER all other sectors — this isolates LULUCF errors from the energy/waste/IPPU cascade.
3. Start with 4.A (largest). Adjust `ef_frst_sequestration_*` scale to match NIR net removal.
4. Then 4.B-4.C. These are coupled through the transition matrix — changes to cropland area affect grassland and vice versa.
5. Accept structural gaps in fire CO2, historical HWP accumulation, and SOC dynamics. Document each with rationale.

### 6.13 Final Pre-Run Checks
1. inf/NaN scan: must be 0
2. ALL fraction groups sum to 1.0
3. Back up: `cp df_input_0.csv df_input_0.csv.bak_step0`

---

## Section 7: Calibration Loop (Step 1+)

```
1. RUN: python run_calibration0.py --baseline-only --input-file df_input_0.csv
2. DIAGNOSE: read diagnostics/diff_report.csv — verdict, sector totals, flagged categories
3. TRACE DAG: for top 3 failures, trace upstream/downstream
4. VERIFY SOURCES: read the actual file justifying the fix
5. APPLY FIX: Scale, Don't Replace. Log in calibration_log.md
6. CHECK REGRESSIONS: flag any sector worsened by >0.5 MtCO2e
7. GO TO 1
```

### Diagnosis: Sector Error to Parameter Fix

Read `diagnostics/diff_report.csv` (ranked by absolute gap). Map the failing category to SISEPUEDE output columns (`emission_co2e_{gas}_{subsector}_{detail}`). Decompose into sub-components at tp=7. Trace to input parameters:

| Wrong output | Check these inputs |
|---|---|
| `entc_generation_pp_coal` | `efficfactor_entc_*_pp_coal`, MSP, residual capacity |
| `inen_*_{industry}` | `prodinit_ippu_{industry}`, `consumpinit_inen_*_{industry}`, `frac_inen_energy_{industry}_*` |
| `scoe_*` | `consumpinit_scoe_gj_per_hh_*`, `frac_scoe_heat_energy_*` |
| `waso_*` | `qty_waso_initial_*_tonne_per_capita`, `mcf_waso_*`, `frac_waso_*` |
| `lvst_entferm_*` | `pop_lvst_*`, `ef_lvst_entferm_*` |
| `lsmm_*` | `frac_lvst_mm_*`, `mcf_lsmm_*` |
| `soil_*` | `qtyinit_soil_synthetic_fertilizer_kt`, `ef_soil_*`, `frac_soil_*` |
| `trns_*` | `deminit_trde_*`, `fuelefficiency_trns_*`, `frac_trns_*` |

For multiplicative formulas, check each term against external data. The term furthest from the reference is the one to fix.

### Scale, Don't Replace
1. `factor = target / current_tp0_value`
2. Multiply entire column by factor (preserves trajectory shape)
3. For fraction groups: scale target, rebalance others to sum to 1.0

### Undershooting = Overshooting
If model output is BELOW target, MCFs/EFs/activity data are too LOW — iterate upward. The diff measures absolute error in both directions.

### When to Stop Calibrating a Sector
- **Structural gap**: No CSV parameter can fix it (e.g., model doesn't represent the process). Document and move on.
- **Diminishing returns**: Last 3 changes each improved by <0.1 MtCO2e.
- **Oscillation**: Fixing this sector worsens another by similar magnitude across iterations.
- **Physical bounds**: Required parameter value is outside IPCC uncertainty range.

### Priority Order
Fix by largest absolute error first. **Re-rank from the latest diff report after each run.** Default starting order: Waste CH4 → IPPU CO2 → INEN CO2 → ENTC CO2 → Livestock CH4 → LSMM CH4 → Transport CO2 → SCOE CO2 → Soil N2O → FGTV.

### Quick Iteration: `--no-energy` First
Use `--no-energy` (~30 sec) for AFOLU, CircularEconomy, IPPU. Switch to full runs (~3-5 min) for ENTC, FGTV, and cascade effects.

### NemoMod Troubleshooting

**INFEASIBLE**: Check MSP sum (must be <1.0), capacity vs MSP (can capacity support the floor?), zero-capacity techs with activity requirements (biogas, waste_incineration need >0 GW), fuel supply pathways.

**OPTIMAL but wrong**: OPTIMAL means LP solved, not that dispatch is correct. Check `nemomod_entc_annual_production_by_technology_pp_*` against IEA. Check for unrealistic new capacity.

### Background Execution
Launch full runs with `run_in_background=true`. While waiting: read docs for next sector, prepare verification, plan next fixes. `--no-energy` runs are fast enough for foreground.

---

## Section 8: Known Behaviors

### Model Mechanics
- **Calibrate at tp=0, validate at tp=7.** Model projects from initial conditions.
- **SpecifiedAnnualDemand is computed, not settable.** Driven by INEN/SCOE/TRNS.
- **NemoMod builds unlimited capacity by default.** OPTIMAL ≠ correct production.
- **Block boundary at tp=12-13.** NemoMod 2-block optimization; dispatch may jump. Structural.
- **EAR formula**: `EAR = fuel_EF × scalar / efficiency`. Post-EAR-fix, `efficfactor_entc_*` controls ENTC emissions.
- **EAR scalar bounded 0-1, efficiency bounded 0-1** in source code. Values outside this range are silently clipped.

### Sensitivity Traps
- **Soil carbon factors** are extremely sensitive. Small changes → multi-MtCO2e swings.
- **Availability factor** does NOT increase ENTC emissions — NemoMod compensates with new capacity.
- **Production elasticities must be CONSTANT.** Time-varying values cause production collapse.

### NemoMod-Specific
- **MSP**: Only constrain the flexible dispatch pool. Over-constraining → INFEASIBLE.
- **Cap non-existent techs** at 0 GW capacity AND investment. Keep biogas + waste_incineration.
- **Import fractions** control FGTV, not OARs or EFs.

### IPCC CH4 EFs Vary 10x by Sector
Tables 2.2-2.5 in V2_Ch2 give DIFFERENT CH4 EFs for the SAME fuel by combustion scale:
- T2.2-T2.3 (power/manufacturing): biomass CH4 = **30 kg/TJ**
- T2.4-T2.5 (commercial/residential): biomass CH4 = **300 kg/TJ**

SISEPUEDE uses ONE shared EF column (`ef_enfu_stationary_combustion_tonne_ch4_per_tj_fuel_*`) for CCSQ, INEN, and SCOE simultaneously. No per-subsector override exists.

### Shared Fuel EFs Across ALL Energy Sectors
ALL combustion EFs (`ef_enfu_*`) are shared across CCSQ, INEN, SCOE, and ENTC. Changing a fuel's CO2, CH4, or N2O EF affects every sector that burns that fuel. To adjust ENTC emissions independently, use the EAR scalar or efficiency factor — not the base fuel EF.

### Template Artifacts
- **Dual biomass EF columns**: SISEPUEDE has `ef_enfu_*_fuel_biomass` AND `ef_enfu_*_fuel_solid_biomass`. Both must be set or one keeps the base country default.
- **Metal CCS capture**: Template may have `gasrf_ippu_co2_capture_metals = 0.90` (base country CCS). Zero this for countries without CCS.
- **IEA scaling overrides**: Production volumes set early get overridden by the IEA energy scaling block. Set production AFTER scaling.
- **Agriculture energy**: `consumpinit_inen_energy_total_pj_agriculture_and_livestock` may be 2-3x actual in template. Verify against NIR.

### Cascade Patterns
- Reducing agriculture electricity demand → less coal dispatch → lower ENTC CO2. Recalibrate coal efficiency each time demand changes.
- Elevated EF1 (>0.01) amplifies crop residue N content scaling — two curve-fitted parameters compound errors.

---

## Section 9: Reference Data

### Reference Hierarchy

```
1. NIR / National Inventory (NDC Docs/Additional docs/) -- Official inventory. USE FOR TARGETS + METHODOLOGY.
2. SNBC / NDC (NDC Docs/*.pdf) -- Official BAU projections. USE FOR SECTOR TARGETS.
3. IEA (external_data/iea_comprehensive/) -- USE FOR ENERGY.
4. EDGAR v8.0 (external_data/edgar/) -- Cross-check only. Known errors.
5. FAO / World Bank (external_data/fao/, external_data/world_bank/) -- USE FOR SOCIOECONOMIC.
6. Cross-country SISEPUEDE -- USE FOR FINDING LEVERS, not values.
7. IPCC 2006/2019 (ipcc/*.pdf, ipcc_tables/*.csv) -- Regional tables, not global defaults.
```

### IPCC Table Quick Reference

| PDF File | Tables | Content |
|----------|--------|---------|
| V4_Ch10_Livestock.pdf | T10.10-11, T10.17, T10.19 | Enteric EFs, manure MCFs by temp, N excretion |
| V4_Ch11_N2O_Soils.pdf | T11.1-3 | Soil N2O EFs, crop residue N, leaching fractions |
| V5_Ch3_SWDS.pdf | T3.1, T3.3 | Waste MCFs, decay rates by climate |
| V5_Ch6_Wastewater.pdf | T6.8 | WW N2O EFs (2006 vs 2019R) |
| V2_Ch2_Stationary.pdf | T2.2-T2.5 | Fuel CO2/CH4/N2O EFs by sector |

Pre-extracted CSVs in `ipcc_tables/`: `V2_Ch2_Table2.2_fuel_CO2_EFs.csv`, `V4_Ch10_Table10.10_*.csv`, `V4_Ch10_Table10.11_*.csv`, `V4_Ch10_Table10.12_body_mass.csv`, `V4_Ch10_Table10.17_manure_MCF_by_temp.csv`, `V4_Ch10_Table10.19_N_excretion.csv`, `V4_Ch11_Table11.1_*.csv`, `V4_Ch11_Table11.3_*.csv`, `V5_Ch3_Table3.1_MCF.csv`, `V5_Ch3_Table3.3_decay_rates.csv`, `V4_Ch2_Table2.3_SOC_reference.csv`.

### MCF Temperature Dependence
MCFs from IPCC Table 10.17 vary by average annual temperature. Liquid/Slurry: 17%@10°C, 35%@18°C, 50%@22°C, 78%@27°C. Lagoon: 66%@10°C, 77%@18°C, 80%@28°C. Pasture: 1.0%(cool), 1.5%(temperate), 2.0%(warm).

### EDGAR Known Errors
Waste CH4 (EDGAR overstates vs national FOD), Soil N2O (EDGAR >> national inventory), HFC (EDGAR top-down >> BUR bottom-up), INEN CO2 (EDGAR may exclude agriculture energy that SISEPUEDE includes). Always cross-check EDGAR against NIR/SNBC — NIR is authoritative.

### Inventory Comparison Approach

Build `emission_targets_{country}_{year}.csv` with columns: `subsector_ssp`, `sector`, `category`, `gas`, `ID`, `vars` (colon-separated SISEPUEDE output column names), `target_source`, `{COUNTRY_CODE}`. The `vars` column maps each IPCC category to the SUM of specific model output columns. Run `compare_to_inventory.py` → `diagnostics/diff_report.csv`, `flagged.csv`, `diagnostics.csv`. Country-agnostic — same script for any country with a crosswalk file. LULUCF optional (`INCLUDE_LULUCF` toggle in build script).

### Key Formulas

```
ENTC CO2:  EAR (tCO2/PJ) = fuel_EF × scalar / efficiency
           emission (MtCO2e) = sum(EAR × generation_PJ) / 1000
Soil N2O:  emission = (direct_N × EF1 + pasture_N × EF3 + leaching_N × EF5) × 44/28 × GWP
Waste CH4: FOD model (memory effects). Approx: waste_gen × DOC × DOCf × MCF × F × 16/12 × (1-R)
```

### NIR Key Data Points

Read the NIR table of contents or master summary table. Extract these data points (table names and page numbers vary by country):
- **Master emissions summary**: ALL sectors x years in Gg CO2eq (single-page inventory overview)
- **Energy subcategories**: raw CO2/CH4/N2O by CRF 1.A subcategory (1.A.1 through 1.B)
- **Fuel consumption by end-use**: TJ for commercial, residential, agriculture separately
- **Agriculture by species/source**: CH4/N2O for enteric, manure, soil by animal type and N source
- **Soil N inputs**: fertilizer, manure, pasture, crop residue in t N/yr
- **LULUCF by CRF 4 subcategory**: CO2/CH4/N2O for 4.A through 4.E
- **Waste**: CH4/N2O for solid waste and wastewater separately

**Caution**: NIR text sometimes contradicts tables. Always trust table values over text claims.

---

## Section 10: Anti-Patterns

### Preflight
1. **Skipping preflight gates.** Wrong population cascades to every sector.
2. **Trusting EDGAR without national inventory cross-check.**
3. **Copying cross-country values without country-specific sourcing.**
4. **Changing GDP scale without rescaling all intensity parameters.**

### Calibration
5. **Trial-and-error without DAG reasoning.** Always trace before touching.
6. **Compensating for wrong fundamentals.** If per-HH energy seems extreme, check HH count first.
7. **Scaling EFs without physical justification.** Must cite IPCC regional table + page.
8. **Calibrating at tp=7 instead of tp=0.** Model projects from tp=0.
9. **Time-varying production elasticities.** Use constant values.
10. **Inventing values from training knowledge.** Every value must be from a file in this repo.

### Energy
11. **Ignoring α^D vs α^C.** IEA = consumption fractions. SISEPUEDE = demand fractions.
12. **Capping biogas/waste_incineration at 0 GW.** Breaks NemoMod feasibility.
13. **MSP on all technologies.** Over-constrains LP. Only flexible pool.
14. **Running two NemoMod instances in parallel.** Julia compilation conflict.

---

## Section 11: Calibration Log

Maintain `calibration_log.md` in the project root:

```markdown
## Run N: YYYY-MM-DD HH:MM
Output: ssp_run_output/calibration_{timestamp}/
Error: XX.XX MtCO2e | <=15%: N | <=25%: N | NemoMod: OPTIMAL

### Changes Applied
| Parameter | Old | New | Source | Detail | Fraction OK? |
|-----------|-----|-----|--------|--------|-------------|

### Diagnosis
- Top errors, DAG trace, hypothesis, findings
```

---

## Section 12: Success Criteria

- **Total inventory error**: <=15 MtCO2e (using IPCC crosswalk)
- **Categories within 15%**: >=40% of evaluated categories
- **Categories within 25%**: >=55% of evaluated categories
- **NemoMod**: ALL OPTIMAL
- **Trajectory**: Smooth (no >10% jumps between consecutive periods)
- **Every parameter change**: Logged with source citation
- **Structural gaps**: Documented with rationale

### Stopping Rules
- No change improves total error by >0.5 MtCO2e
- Oscillation detected across iterations
- All remaining gaps are structural and documented

---

## Section 13: Verification Gates

### Before First Run
- [ ] All Section 4 Preflight Gates passed (Gates 1-10, including 7b-7d)
- [ ] config.yaml or `--input-file` points to correct CSV
- [ ] SISEPUEDE EAR fix verified (`grep arr_entc_eff_techs`) or documented as absent

### Before Changing ENTC Parameters
- [ ] Read energy production documentation
- [ ] Grep source code for parameter name
- [ ] EAR fix present
- [ ] MSP sum < 1.0

### Before Changing Any Fraction Group
- [ ] Discover group: grep CSV header for columns matching the prefix (e.g., `frac_inen_energy_cement_*`) — all matches form one group
- [ ] List ALL columns in group
- [ ] Verify current sum at tp=0 and tp=7
- [ ] After change, sum = 1.0 at ALL time periods

### After Every Run
- [ ] NEMOMOD_ALL_OPTIMAL=YES
- [ ] Read `diagnostics/diff_report.csv`
- [ ] Review HIGH diagnostics (zero outputs, sign mismatches, 10x errors)
- [ ] Compare against previous run — flag regressions >1 MtCO2e
- [ ] Log in calibration_log.md

---

## Section 14: Verification Best Practices

For high-stakes values (NDC targets, emission factors driving >1 MtCO2e), source from two DIFFERENT file types rather than re-reading the same file. Examples:
- Verify an IPCC EF from `ipcc_tables/*.csv` against the NIR methodology section (different document, same data point)
- Verify IEA generation mix from `external_data/iea_comprehensive/` against SNBC energy chapter figures
- Verify FAO livestock populations against NIR agriculture chapter tables
- Verify cement production from BUR3 process CO2 back-calculation against SNBC industry chapter

If two independent sources disagree by >10%, investigate which is more authoritative before proceeding.

---

## Section 15: Worked Examples

### Example 1: Phantom Fuel Exports (FGTV)
**Diff report**: FGTV CH4 = 0.72 MtCO2e, target = 0.0 MtCO2e.
**DAG trace**: FGTV ← EnergyProduction ← NemoMod dispatching domestic gas production to satisfy exports.
**Investigation**: `exports_enfu_pj_fuel_natural_gas = 215` in template. Bulgaria exports gas; the calibration country does not. IEA trade data (`external_data/iea_comprehensive/`) confirms zero gas exports.
**Fix**: Set `exports_enfu_pj_fuel_natural_gas = 0` across all time periods.
**Result**: FGTV CH4 dropped to ~0.0 MtCO2e. One line, one column.
**Lesson**: Always check Gate 7b. Template fuel exports are the most common source of phantom FGTV emissions.

### Example 2: Landfill Gas Recovery (Waste CH4)
**Diff report**: Waste CH4 = 0.5 MtCO2e, target = 4.25 MtCO2e (undershooting by 3.75).
**DAG trace**: WASO ← MCF x waste generation x DOC. All look reasonable. But recovery fraction is suppressing output.
**Investigation**: `frac_waso_landfill_gas_recovered = 0.997` in template. Bulgaria has extensive landfill gas recovery infrastructure. The calibration country has ~2% recovery (66 unmanaged dumps, 32% managed landfill, NIR p.271).
**Fix**: Set `frac_waso_landfill_gas_recovered = 0.02`.
**Result**: Waste CH4 rose from 0.5 to ~3.8 MtCO2e. Remaining gap addressed through MCF and waste-per-capita adjustments.
**Lesson**: Template artifacts from industrialized base countries can suppress entire sectors by 90%+.

### Example 3: Agriculture Energy Cascade (INEN → ENTC)
**Diff report**: ENTC CO2 = 22.5 MtCO2e, target = 18.0 MtCO2e (overshooting by 4.5).
**DAG trace**: ENTC ← NemoMod ← electricity demand ← INEN (industry) ← agriculture energy demand.
**Investigation**: `consumpinit_inen_energy_total_pj_agriculture_and_livestock = 76.5` PJ in template. NIR Tableau 43 p.132 shows agriculture fuel consumption = 32.9 PJ. Template is 2.3x actual.
**Fix**: Scale agriculture energy to 32.9 PJ. Set agriculture fuel fractions to diesel-dominant (58% diesel, 27% electricity — tractors, not factories). Recalibrate coal efficiency from 0.27 → 0.23 to compensate for reduced demand.
**Result**: ENTC CO2 dropped by ~3 MtCO2e. But coal efficiency at 0.23 is very low — this signals the demand reduction exposed a structural issue (NemoMod over-dispatches coal when total demand drops).
**Lesson**: Fixing upstream demand changes downstream dispatch. Always recalibrate ENTC efficiency after changing any INEN/SCOE demand parameter. Anti-pattern #3: compensating for wrong fundamentals.
