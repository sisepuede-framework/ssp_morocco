# Industry Sector — LT-LEDS Targets ↔ SISEPUEDE Mapping

*Source targets: Morocco's Quantitative SNBC / LT-LEDS (WB, 2024) — Industry sector, slide 4.*
*SISEPUEDE run validated against: `ssp_modeling/ssp_run_output/sisepuede_results_sisepuede_run_2026-05-20T12;42;19.976658/`.*
*Strategy `6004 — PFLO:LEDS` is the LEDS bundle used for validation. `primary_id 73073` is the corresponding scenario row.*
*Unit reference: 1 Ktep = 11.63 GWh = 0.041868 PJ; 1 TWh = 3.6 PJ.*

---

## Executive Summary

The LT-LEDS sets nine quantitative industry-sector targets across three horizons (2030, 2040, 2050) covering energy efficiency, fuel mix (green H2, NG, electricity share), distributed PV, waste-to-energy (IAA + DMA), and CCUS (phosphate process capture, microalgae, geological storage). All nine map to existing SISEPUEDE transformations or to a small number of explicit gaps where the model has no native representation.

**The single most important finding from this analysis: the LEDS strategy as currently defined in the repo (`strategy_id = 6004`) does not include a single industry-sector transformation.** Its 7-transformation bundle covers only AFOLU rice CH4, two ENTC electricity transformations, and four TRNS transformations. None of `INEN:INC_EFFICIENCY_*`, `INEN:SHIFT_FUEL_HEAT`, `ENTC:TARGET_CLEAN_HYDROGEN`, `WASO:INC_ENERGY_FROM_*`, `PFLO:INC_IND_CCS`, or `CCSQ:INC_CAPTURE` is wired in. The `_strategy_LEDS.yaml` files exist with calibrated magnitudes, but they are orphan files. As a result, the latest LEDS run returns BAU values for every industry-relevant output column, and progress against the LT-LEDS industry targets cannot be measured from the current dashboard data.

A secondary structural finding: three of the nine targets have a representation gap in SISEPUEDE that requires a custom proxy or a new model category — (i) **distributed PV** cannot be separated from utility-scale PV inside `pp_solar`; (ii) **microalgae carbon capture** has no native transformer and must be proxied via `CCSQ:INC_CAPTURE` with a post-processing split; (iii) **phosphate process emissions** are bundled into the IPPU `chemicals` category, which dominates Moroccan industrial CO2 but is not phosphate-pure.

The remaining six targets (industrial EE, NG share, electricity share, fossil share, RE share, IAA + DMA waste-to-energy mass) all have clean SSP output variables; once the LEDS strategy bundle is corrected, they can be displayed against target lines in Tableau with the variables identified below.

---

## 1. Targets at a Glance

| # | Target | 2030 | 2040 | 2050 | Owner agent | SSP transformation(s) |
|---|--------|------|------|------|-------------|------------------------|
| 1 | Industrial EE | −17% | −5% additional | −5% additional | A1 | `INEN:INC_EFFICIENCY_ENERGY`, `INEN:INC_EFFICIENCY_PRODUCTION` |
| 2 | Green H2 in industry | 288 Ktep (~12 PJ) | 6.7 TWh (~24 PJ) | 14.5 TWh (~52 PJ) | A2 | `INEN:SHIFT_FUEL_HEAT`, `ENTC:TARGET_CLEAN_HYDROGEN` |
| 3 | Natural gas in industry | 794 Ktep (~33 PJ) | — | 904 Ktep (~38 PJ) | A2 | `INEN:SHIFT_FUEL_HEAT` |
| 4 | Industry energy mix (elec / fossil / RE) | 30 / 43 / 27 % | 33 / 35 / 32 % | 36 / 26 / 39 % | A2 | `INEN:SHIFT_FUEL_HEAT` + `ENTC:TARGET_RENEWABLE_ELEC` |
| 5 | Distributed PV in industry | 1,500 MW | growth | 2,700 MW | A3 | `ENTC:TARGET_RENEWABLE_ELEC` (proxy only) |
| 6 | IAA waste-to-energy | 607 Ktep (~25 PJ) | "Biomass" | 645 Ktep (~27 PJ) | A4 | `WASO:INC_ENERGY_FROM_INCINERATION`, `WASO:INC_ENERGY_FROM_BIOGAS`, `WASO:INC_CAPTURE_BIOGAS`, `WASO:INC_ANAEROBIC_AND_COMPOST` |
| 7 | DMA waste-to-energy | 116 Ktep (~5 PJ) | — | 314 Ktep (~13 PJ) | A4 | same WASO transformations (MSW branch) |
| 8 | Phosphate process CCS | 25% captured | 50% captured | (carries over) | A5 | `PFLO:INC_IND_CCS` (chemicals proxy) |
| 9 | Engineered + biological CDR | — | — | 9.5 MtCO2e microalgae + 6 MtCO2e geological | A5 | `CCSQ:INC_CAPTURE` (proxy split in post-processing) |

---

## 2. Industrial Energy Efficiency

### Targets
- 2030: −17% Energy Efficiency (EE) in industry
- 2040: additional −5% EE (cumulative ~−22%)
- 2050: additional −5% EE (cumulative ~−27%)

### Plain-English interpretation
Morocco's LT-LEDS frames industrial EE as a percentage reduction in **final energy consumption / specific energy intensity** in the industry sector versus a reference (BAU) trajectory anchored at 2018 inventory. The −5% steps in 2040 and 2050 are **incremental** improvements on top of the prior milestone (interpreted as cumulative −17 / −22 / −27 % vs BAU by 2030/2040/2050). In SISEPUEDE the lever splits cleanly into two axes:
1. **Energy efficiency per unit fuel use** (boilers, motors, heat recovery) — fuel-side combustion efficiency.
2. **Production efficiency** (specific energy consumption per tonne of product) — process-side intensity.

Both reduce `energy_demand_inen_*` (PJ) for the same level of `prod_inen_*` activity.

### SSP transformation mapping

- **Code**: `TX:INEN:INC_EFFICIENCY_ENERGY`
- **YAML**: `ssp_modeling/transformations/transformation_inen_inc_efficiency_energy_strategy_LEDS.yaml`
- **Transformer module**: `TFR:INEN:INC_EFFICIENCY_ENERGY` (raises `efficfactor_enfu_industrial_energy_fuel_*`)
- **Key parameter(s)**: `magnitude: 0.3`, `vec_implementation_ramp.tp_0_ramp: 12` (ramp starts at tp=12 → 2030)
- **Relation to target**: Magnitude = max fractional increase in fuel-side efficiency factor by terminal year. A 0.3 (+30%) efficiency gain on the fuel side implies ~23% reduction in input PJ for the same useful energy, dominating the EE target (single lever overshoots the −17% combined target by 2030 if ramped early; current `tp_0_ramp=12` means it only *starts* ramping in 2030).

- **Code**: `TX:INEN:INC_EFFICIENCY_PRODUCTION`
- **YAML**: `ssp_modeling/transformations/transformation_inen_inc_efficiency_production_strategy_LEDS.yaml`
- **Transformer module**: `TFR:INEN:INC_EFFICIENCY_PRODUCTION` (lowers `consumpinit_inen_energy_tj_per_tonne_production_*` / `_pj_per_mmm_gdp_*`)
- **Key parameter(s)**: `magnitude: 0.4`, `vec_implementation_ramp.tp_0_ramp: 12`
- **Relation to target**: −40% specific energy consumption per tonne of product by terminal year. Stacked with the fuel-side 30%, the LEDS YAMLs combined are stronger than the −27% 2050 LT-LEDS endpoint, suggesting the YAMLs were tuned to "max ambition" rather than the LT-LEDS exact path.

### Output variables to display the target

- **WIDE_INPUTS_OUTPUTS columns** (PJ):
  - `energy_consumption_inen_total` — Total final energy consumption, INEN
  - `energy_consumption_electricity_inen_total`
  - `energy_demand_enfu_subsector_total_pj_inen_fuel_<fuel>` — by fuel
  - `energy_demand_inen_<industry>` — by industrial subsector
- **Tableau `decomposed_emissions_morocco_2018.csv` filter**: `sector = "1 - Energy"`, `subsector = "1.A.2 - Manufacturing Industries and Construction"` (CO2/CH4/N2O combustion emissions track EE indirectly).
- **Tableau `drivers_morocco.csv` filter**: `subsector = "Industrial Energy"`, `model_variable ∈ {"Energy Consumption from Industrial Energy", "Total Energy Consumption from Industrial Energy", "Energy Demand in Industrial Energy"}`; `Units = "PJ"`; `energy_subsector = "industrial_energy"`.
- **Suggested aggregation**: Sum `energy_consumption_inen_total` per Year per strategy, index to 2018 = 100, plot LEDS vs BASE; also % delta LEDS-vs-BASE for each milestone year.

### Run validation (strategy LEDS = 6004, primary_id = 73073, latest run)

| Variable | 2018 (tp=0) | 2030 (tp=12) | 2040 (tp=22) | 2050 (tp=32) | Units | % vs 2018 |
|---|---|---|---|---|---|---|
| `energy_consumption_inen_total` | 173.19 | 183.04 | 191.61 | 199.33 | PJ | +5.7 / +10.6 / +15.1 % |
| `energy_demand_enfu_subsector_total_pj_inen_fuel_electricity` | 33.93 | 37.24 | 40.21 | 42.89 | PJ | +9.8 / +18.5 / +26.4 % |
| `energy_demand_enfu_subsector_total_pj_inen_fuel_oil` | 43.79 | 47.93 | 51.61 | 54.91 | PJ | +9.5 / +17.8 / +25.4 % |

LEDS values are **identical to BASE (primary_id=0)** — the targets are not being applied in this run.

### Gaps / open questions
- **Critical**: Strategy 6004 (`PFLO:LEDS`) in `strategy_definitions.csv` does NOT include `TX:INEN:INC_EFFICIENCY_ENERGY_STRATEGY_LEDS` or `TX:INEN:INC_EFFICIENCY_PRODUCTION_STRATEGY_LEDS`. The two YAMLs exist but are orphans — the LEDS composite only chains ENTC/TRNS/AGRC LEDS transformations. INEN EE is effectively absent from the current LEDS scenario, which is why LEDS and BASE energy demand curves match exactly.
- The LT-LEDS target is "% EE", but SISEPUEDE applies two separate magnitudes (fuel efficiency 0.3 + production intensity 0.4) — a single composite % is not directly emitted; needs a derived ratio of `energy_consumption_inen_total / sum(prod_inen_*)` to express as energy intensity.
- "vs 2018" vs "vs BAU" ambiguity: SISEPUEDE outputs both BASE (BAU) and LEDS series, so the dashboard can show either reference; LT-LEDS Industry text should be confirmed (typically referenced to reference scenario/BAU, not 2018 absolute level).
- `tp_0_ramp = 12` means ramping starts in 2030 — so the −17% milestone is unreachable by 2030 under the current ramp; ramp should likely start earlier (tp = 0 or tp = 5) for the 2030 target to bind.

---

## 3. Fuel Mix & Green Hydrogen

### Targets
- 2030: H2 green = 288 Ktep (~3.35 TWh / 12.06 PJ); NG = 794 Ktep (~9.23 TWh / 33.24 PJ); INEN energy mix = 30% electricity / 43% fossil / 27% RE
- 2040: H2 green = 6.7 TWh (~24.12 PJ); PV + NG + Biomass + CCUS as enabling tech; mix = 33% electricity / 35% fossil / 32% RE
- 2050: H2 green = 14.5 TWh (~52.20 PJ); NG = 904 Ktep (~10.52 TWh / 37.85 PJ); mix = 36% electricity / 26% fossil / 39% RE

### Plain-English interpretation
- "H2 green" is national green-hydrogen *production* via electrolysis (powered by renewables) — best mapped to ENTC processing/refinement output (`prod_enfu_fuel_hydrogen_pj`, with technology split `fp_hydrogen_electrolysis`). It is NOT the same as industrial H2 consumption (`energy_demand_enfu_subsector_total_pj_inen_fuel_hydrogen`). Some share of produced H2 may be exported or used in transport/refining.
- "NG" in LEDS refers to *total industrial natural-gas consumption* (driven by gas-to-power, fertilizer and heat substitution), best read from `energy_demand_enfu_subsector_total_pj_inen_fuel_natural_gas` (and aggregate via `totalvalue_enfu_fuel_consumed_inen_fuel_natural_gas`).
- Mix shares are *final energy in industry* (INEN). Buckets: electricity = `fuel_electricity`; fossils = {natural_gas, coal, coke, oil, diesel, kerosene, furnace_gas, hydrocarbon_gas_liquids, gasoline}; RE = {biomass, biofuels, biogas, solar, geothermal, hydrogen, waste-renewable}.
- Unit conversions: 1 Ktep = 0.041868 PJ = 11.63 GWh; 1 TWh = 3.6 PJ.

### SSP transformation mapping
- **Code**: `TX:INEN:SHIFT_FUEL_HEAT_STRATEGY_LEDS`
  - **YAML**: `ssp_modeling/transformations/transformation_inen_shift_fuel_heat_strategy_LEDS.yaml`
  - **Transformer**: `TFR:INEN:SHIFT_FUEL_HEAT`
  - **Key parameters**: `frac_switchable = 0.9` (90% of switchable low/high-temp heat reassigned to clean fuels), `vec_implementation_ramp.tp_0_ramp = 12` (begin ramp at tp 12 ≈ 2027).
  - **Relation to target**: re-allocates `frac_inen_energy_<industry>_<fuel>` rows away from coal/oil/coke toward electricity, NG, biomass, hydrogen — drives the 30/43/27 → 36/26/39 mix shift.

- **Code**: `TX:ENTC:TARGET_CLEAN_HYDROGEN_STRATEGY_LEDS`
  - **YAML**: `ssp_modeling/transformations/transformation_entc_target_clean_hydrogen_strategy_LEDS.yaml`
  - **Transformer**: `TFR:ENTC:TARGET_CLEAN_HYDROGEN`
  - **Key parameters**: `magnitude = 0.95` (95% of H2 production from clean technologies — electrolysis + reformation_ccs), `tp_0_ramp = 12`.
  - **Relation to target**: sets the share of hydrogen produced via `fp_hydrogen_electrolysis` vs grey routes; drives `prod_enfu_fuel_hydrogen_pj` to the 288 Ktep / 6.7 TWh / 14.5 TWh trajectory.

- `TX:ENFU:ADJ_EXPORTS` is generic (scalar 0.8 on fuel exports). Only relevant if Morocco exports green H2 — currently does not touch INEN NG, so out of scope here.

### Output variables to display the targets
- **H2 green production** — WIDE: `prod_enfu_fuel_hydrogen_pj` (PJ) and the four ENTC technology columns `nemomod_entc_*_fp_hydrogen_electrolysis|gasification|reformation|reformation_ccs`. Tableau drivers filter: `model_variable = "Fuel Production"`, `category_value = "fuel_hydrogen"`, `Units = PJ`. Chart: line vs. target points 12.06 / 24.12 / 52.20 PJ.
- **H2 industrial consumption** — WIDE: `energy_demand_enfu_subsector_total_pj_inen_fuel_hydrogen` and `totalvalue_enfu_fuel_consumed_inen_fuel_hydrogen`. Drivers filter: `subsector = "Energy Fuels"`, `category_value = "fuel_hydrogen"`, `energy_subsector = "Industrial Energy"`.
- **NG industrial consumption** — WIDE: `energy_demand_enfu_subsector_total_pj_inen_fuel_natural_gas`. Same Tableau filter with `category_value = "fuel_natural_gas"`.
- **Electricity / fossil / RE share** — derived in post-processing. Numerator: sum of `energy_demand_enfu_subsector_total_pj_inen_fuel_<f>` over each bucket; denominator: sum of all `energy_demand_enfu_subsector_total_pj_inen_fuel_*`. Implement in `output_postprocessing/scr/data_prep_new_mapping.r`. Chart: 100% stacked area, three lines vs target dots.
- **Biomass enabling-tech (2040)** — WIDE: `energy_demand_enfu_subsector_total_pj_inen_fuel_biomass`. Tableau drivers `category_value = "fuel_biomass"`.
- **Decomposed emissions** filter: `sector = "Energy"`, `subsector = "Industrial Energy"` (combustion CO2 by fuel) and `subsector = "Energy Technology"` (H2-electrolysis-related grid emissions).

### Run validation (strategy LEDS, primary_id = 73073, latest run)
| Variable | 2018 | 2030 | 2040 | 2050 | Units | Target match? |
|---|---|---|---|---|---|---|
| `prod_enfu_fuel_hydrogen_pj` | 0.00 | 3.16 | 24.61 | 33.05 | PJ | 2040 hits target (24.12 PJ); 2030 short by ~75% (target 12.06); 2050 short by ~37% (target 52.2). |
| `energy_demand_enfu_subsector_total_pj_inen_fuel_hydrogen` | 0.00 | 0.00 | 0.00 | 0.00 | PJ | FAIL — H2 never enters INEN. |
| `energy_demand_enfu_subsector_total_pj_inen_fuel_natural_gas` | 3.45 | 3.67 | 3.89 | 4.09 | PJ | FAIL — only 4 PJ vs 33–38 PJ target. |
| Derived electricity share INEN | 20.5% | 21.4% | 22.0% | 22.6% | % | FAIL — target 30/33/36%. |
| Derived fossil share INEN | 71.7% | 71.1% | 70.6% | 70.2% | % | FAIL — target 43/35/26%. |

### Gaps / open questions
- The current `PFLO:LEDS` strategy (id 6004) does NOT include `TX:INEN:SHIFT_FUEL_HEAT_STRATEGY_LEDS` or `TX:ENTC:TARGET_CLEAN_HYDROGEN_STRATEGY_LEDS` in `transformation_specification` — only DEC_LOSSES, TARGET_RENEWABLE_ELEC, transport. INEN fuel shares and NG/H2 industrial uptake are therefore still BAU. Fix: add both LEDS variants to strategy 6004 spec.
- H2-production trajectory (24.6 PJ in 2040) lands close to target without the INEN_LEDS transformation — likely seeded by base `prod_enfu_fuel_hydrogen_pj` exogenous inputs; need to confirm whether `magnitude = 0.95` raises 2050 toward 52 PJ when wired in.
- Unit conventions: WIDE is in PJ; LT-LEDS uses Ktep/TWh. Convert in `data_prep_drivers.r` and store both for Tableau axes.
- "RE share" semantics: does the LT-LEDS treat electrolysis-H2 as RE in industry (double-count vs. RE-electricity feedstock)? Confirm with planning team before computing.
- H2 green vs. grey: distinguish via ENTC technology columns (`fp_hydrogen_electrolysis` = green, `fp_hydrogen_reformation` = grey, `fp_hydrogen_reformation_ccs` = blue) and `nemomod_entc_*` activity outputs; a derived `h2_green_share` post-processing field is needed.

---

## 4. Distributed PV in Industry

### Targets
- 2030: 1,500 MW (1.5 GW) distributed PV in industry
- 2040: continued growth (no explicit MW stated in LT-LEDS)
- 2050: 2,700 MW (2.7 GW) distributed PV in industry

### Plain-English interpretation
"Distributed PV" in Morocco's LT-LEDS refers to decentralized, on-site solar photovoltaic installations at industrial facilities — self-consumption rooftop/ground-mounted arrays serving the host plant, as opposed to utility-scale solar farms feeding the grid (covered by Noor / MASEN). It reduces grid electricity imports of the industrial consumer and may include partial feed-in of surplus. **SISEPUEDE does NOT represent distributed PV natively.** The ENTC subsector has a single `pp_solar` technology that lumps all solar generation capacity (utility-scale + distributed), and INEN tracks industrial fuel mix by share (`frac_inen_energy_*_solar`) but not by installed MW. The 1.5 GW / 2.7 GW industrial-PV target must therefore be tracked indirectly as (i) a slice of `pp_solar` total capacity, or (ii) by the implied electricity displaced via `frac_inen_energy_*_electricity` combined with the ENTC renewable share.

### SSP transformation mapping
- **Code**: `TX:ENTC:TARGET_RENEWABLE_ELEC_STRATEGY_LEDS`
- **YAML**: `ssp_modeling/transformations/transformation_entc_target_renewable_elec_strategy_LEDS.yaml`
- **Transformer**: `TFR:ENTC:TARGET_RENEWABLE_ELEC`
- **Key parameter(s)**:
  - `categories_entc_renewable: [pp_solar, pp_wind, pp_hydropower]` — the three renewables eligible to meet the target
  - `dict_entc_renewable_target_msp: {pp_solar: 0.31, pp_wind: 0.32, pp_hydropower: 0.32}` — minimum share of production by 2050 (solar = 31%)
  - `magnitude: 0.95` — 95% of electricity from renewables by final period
  - `vec_implementation_ramp` (tp_0_ramp = 8 → 2023 start, 21 ramp periods → ~2044 full)
- **Relation to target**: The 31% MSP for `pp_solar` is system-wide (utility + distributed). Distributed-industry PV is **implicitly bundled inside this share** — there is no MW carve-out parameter. The LEDS least-cost solver (`TX:ENTC:LEAST_COST_SOLUTION`, scaled by `acceleration_factor: 2.0`) then determines the installed GW.

Note: there is no `transformation_entc_least_cost_solution_strategy_LEDS.yaml`; LEDS inherits the default `TX:ENTC:LEAST_COST_SOLUTION` parameters via `PFLO:LEDS` (strategy_id 6004).

### Output variables to display the target
- **WIDE_INPUTS_OUTPUTS** (units = **GW**):
  - `nemomod_entc_total_annual_generation_capacity_pp_solar` — total installed solar capacity (proxy)
  - `nemomod_entc_residual_capacity_pp_solar_gw` — legacy / pre-existing capacity
  - `nemomod_entc_annual_production_by_technology_pp_solar` — PJ generated (cross-check)
  - INEN side: `energy_demand_enfu_subsector_total_pj_inen_fuel_solar` and `frac_inen_energy_<industry>_solar` (37 industry-cat columns) — direct industrial solar use
- **Tableau `drivers_morocco`**: filter `subsector = "Energy Technology"` and `model_variable` containing `total_annual_generation_capacity_pp_solar`
- **Tableau `decomposed_emissions`**: not directly relevant (PV is zero-emission); use to show CO2 displaced in `entc_generation` total
- **Suggested chart**: line of `pp_solar` capacity (GW) over 2018–2050 with horizontal reference lines at 1.5 GW (2030) and 2.7 GW (2050); stacked share-of-RE-capacity area; secondary axis showing industrial solar energy demand (PJ).

### Run validation (strategy LEDS = primary_id 73073, run 2026-05-20T12;42;19)
| Variable | 2018 | 2030 | 2040 | 2050 | Units | vs target |
|---|---|---|---|---|---|---|
| `total_annual_generation_capacity_pp_solar` | 1.58 | 4.76 | 14.63 | 26.29 | GW | System-wide `pp_solar` ≫ 1.5 / 2.7 GW industrial target (target is a subset) |
| `residual_capacity_pp_solar_gw` | 0.80 | 0.94 | 0.94 | 0.00 | GW | Legacy stock retires by 2050 |

Total `pp_solar` is roughly 3–10× the industrial-PV target because it includes utility-scale Noor and grid solar; **the target is a floor the run clearly meets in aggregate**, but distributed-only progress cannot be confirmed from these columns alone.

### Gaps / open questions
- **Critical model gap**: SISEPUEDE has no `pp_solar_distributed` vs `pp_solar_utility` split. Distributed PV is invisible as a separate technology in ENTC. Reporting against the 1.5 / 2.7 GW target requires either (a) an external assumption (e.g., assume X% of total `pp_solar` is distributed-industrial), or (b) inferring from INEN solar energy demand × industrial load factor → back-calculate MW.
- The LEDS YAML sets a **31% solar MSP system-wide**, not a MW floor for industry — the model could over- or under-shoot the distributed target while still hitting the renewable share.
- Whether industrial-sector solar self-consumption is double-counted between ENTC (`pp_solar`) and INEN (`frac_inen_energy_*_solar`) needs confirmation; if INEN solar is treated as direct fuel use (off-grid PV), it would be outside `pp_solar` and the 1.5 / 2.7 GW target should be tracked there instead.
- 2040 target value is qualitative ("continued growth") — needs stakeholder clarification for a quantitative validation row.

---

## 5. Waste-to-Energy (IAA + DMA)

### Targets
- 2030: IAA = 607 Ktep (~25.4 PJ / ~7.06 TWh); DMA = 116 Ktep (~4.86 PJ / ~1.35 TWh)
- 2040: no explicit Ktep number — LT-LEDS table just lists "Biomass" as a residual mix item
- 2050: IAA = 645 Ktep (~27.0 PJ / ~7.50 TWh); DMA = 314 Ktep (~13.1 PJ / ~3.65 TWh)
- (1 Ktep = 11.63 GWh = 0.041868 PJ)

### Plain-English interpretation
- **IAA** = *Industries Agro-Alimentaires* — agro-food industrial waste (olive pomace, sugar bagasse, dairy/abattoir sludge, food-processing residues) burned/digested to deliver heat or biogas to industrial processes. In SISEPUEDE this is **ISW** (industrial solid waste) with the `food`/`sludge`/`wood`/`yard` composition channels, plus the `biogas_food`/`biogas_sludge` anaerobic-digestion streams.
- **DMA** = *Déchets Ménagers et Assimilés* — municipal solid waste (incineration/SRF + landfill-gas recovery + anaerobic digestion of the organic fraction). In SISEPUEDE this is **MSW** with `frac_waso_msw_incinerated_recovered_for_energy` + landfill-gas capture (`frac_waso_landfill_gas_recovered` × `frac_waso_lgc_recovered_for_energy`).
- The Ktep number is **energy delivered** (combustion output, demand-side). SISEPUEDE natively reports **waste mass routed to energy recovery** (tonnes) on the WASO side and **fuel demand by industry** (PJ) on the ENFU/INEN side. Translating Ktep ↔ tonnes requires net calorific value (`energydensity_gravimetric_enfu_gj_per_tonne_fuel_biomass`, `_fuel_biogas`).

### SSP transformation mapping
- **Code**: `TX:WASO:INC_ENERGY_FROM_INCINERATION` → `TX:WASO:INC_ENERGY_FROM_INCINERATION_STRATEGY_LEDS`
  - **YAML**: `ssp_modeling/transformations/transformation_waso_inc_energy_from_incineration{,_strategy_LEDS}.yaml`
  - **Transformer**: `TFR:WASO:INC_ENERGY_FROM_INCINERATION`
  - **Key parameter**: `magnitude: 0.85` (target share of incinerated ISW+MSW that delivers useful energy), `tp_0_ramp: 12` (ramp to 2027)
  - **Relation to target**: Both **IAA** (via ISW incineration) and **DMA** (via MSW incineration) — drives `frac_waso_isw_incinerated_recovered_for_energy` and `frac_waso_msw_incinerated_recovered_for_energy` to 0.85
- **Code**: `TX:WASO:INC_ENERGY_FROM_BIOGAS` → `TX:WASO:INC_ENERGY_FROM_BIOGAS_STRATEGY_LEDS`
  - **YAML**: `transformation_waso_inc_energy_from_biogas{,_strategy_LEDS}.yaml`
  - **Transformer**: `TFR:WASO:INC_ENERGY_FROM_BIOGAS`
  - **Key parameter**: `magnitude: 0.85` — share of captured biogas (anaerobic digesters + landfills) routed to energy use; ramp tp_0 = 12
  - **Relation to target**: Both **IAA** (biogas from agro-food sludge/food channels) and **DMA** (landfill-gas + MSW organic digestion). Touches all horizons via the ramp.
- **Code**: `TX:WASO:INC_CAPTURE_BIOGAS` → `_STRATEGY_LEDS`
  - **YAML**: `transformation_waso_inc_capture_biogas{,_strategy_LEDS}.yaml`
  - **Transformer**: `TFR:WASO:INC_CAPTURE_BIOGAS`
  - **Key parameter**: `magnitude: 0.85` → `frac_waso_landfill_gas_recovered` & anaerobic gas recovery. Necessary precondition to **deliver** the biogas energy.
- **Code**: `TX:WASO:INC_ANAEROBIC_AND_COMPOST`
  - **YAML**: `transformation_waso_inc_anaerobic_and_compost.yaml` (no LEDS variant exists)
  - **Key parameters**: `magnitude_biogas: 0.475`, `magnitude_compost: 0.475` — directs food/yard/sludge to biogas instead of landfill/incineration. **Upstream feedstock for IAA** biogas.
- **Code**: `TX:INEN:SHIFT_FUEL_HEAT_STRATEGY_LEDS` (covered by Section 3) — the resulting biogas/biomass PJ must show up as `energy_demand_enfu_subsector_total_pj_inen_fuel_biomass` / `_biogas` for industry to actually consume it. Without an INEN biomass-share lift, lifting WASO recovery just exports it to ENTC.

### Output variables to display the targets

For **IAA** (industrial waste → industry energy):
- WIDE columns: `qty_waso_isw_recovered_for_energy_incineration_tonne` (tonnes/yr), `gasrecovered_waso_biogas_anaerobic_tonne` (tonnes/yr), `frac_waso_isw_incinerated_recovered_for_energy` (fraction), `energy_demand_enfu_subsector_total_pj_inen_fuel_biomass` (PJ), `energy_demand_enfu_subsector_total_pj_inen_fuel_biogas` (PJ)
- Tableau `decomposed_emissions_morocco_2018.csv`: filter `subsector == "Solid Waste"` AND `model_variable LIKE 'qty_waso_%recovered_for_energy%' OR 'gasrecovered_waso_biogas_anaerobic_%'`
- Tableau `drivers_morocco.csv`: filter `subsector == "Solid Waste"`, `Code IN ('qty_waso_isw_recovered_for_energy_incineration_tonne','gasrecovered_waso_biogas_anaerobic_tonne')`; for delivered energy use `Code = 'energy_demand_enfu_subsector_total_pj_inen_fuel_biomass'`
- **Aggregation**: `IAA_Ktep = (qty_isw_recovered_tonne × NCV_biomass_GJ/tonne + gasrecovered_anaerobic_tonne × NCV_biogas_GJ/tonne) / 41.868`; chart = stacked area (incineration vs anaerobic) by year, with horizontal target lines at 607 (2030) and 645 (2050).

For **DMA** (municipal waste → energy):
- WIDE columns: `qty_waso_msw_recovered_for_energy_incineration_tonne`, `gasrecovered_waso_biogas_landfills_tonne`, `frac_waso_msw_incinerated_recovered_for_energy`, `frac_waso_landfill_gas_recovered`, `frac_waso_lgc_recovered_for_energy`
- Tableau filter same `subsector="Solid Waste"`, model_variable on the qty_/gasrecovered_ variants for MSW/landfills.
- **Aggregation**: `DMA_Ktep = (qty_msw_recovered_tonne × NCV_msw + gasrecovered_landfills_tonne × NCV_biogas) / 41.868`; chart = same with target lines 116 (2030), 314 (2050).

### Run validation (strategy LEDS, primary_id = 73073)

| Variable | 2018 | 2030 | 2040 | 2050 | Units | Target match? |
|---|---|---|---|---|---|---|
| `qty_waso_isw_recovered_for_energy_incineration_tonne` | 5,495 | 7,443 | 10,166 | 13,662 | tonne/yr | **NO** — at ~15 GJ/t this ≈ 0.0027 Ktep in 2050 vs 645 Ktep target (5 orders of magnitude short) |
| `qty_waso_msw_recovered_for_energy_incineration_tonne` | 5,629 | 6,036 | 6,423 | 6,769 | tonne/yr | **NO** — ~0.0011 Ktep vs 314 Ktep target |
| `gasrecovered_waso_biogas_anaerobic_tonne` | 11,726 | 13,668 | 15,675 | 17,867 | tonne/yr | **NO** — biogas-to-IAA channel inert |
| `energy_demand_enfu_subsector_total_pj_inen_fuel_biomass` | 13.36 | 13.48 | 13.78 | 14.09 | PJ | **Partial** — 14.09 PJ ≈ 337 Ktep, well below combined 645 + 314 = 959 Ktep target |
| `energy_demand_enfu_subsector_total_pj_inen_fuel_biogas` | 0 | 0 | 0 | 0 | PJ | **NO** — biogas does not reach industry in current run |
| `frac_waso_isw/msw_incinerated_recovered_for_energy` | 0.063 | 0.063 | 0.063 | 0.063 | fraction | **NO ramp** — LEDS strategy 6004 does **not** include any WASO transformations |

### Gaps / open questions
1. **Critical**: `ATTRIBUTE_STRATEGY.csv` shows strategy 6004 (`PFLO:LEDS`) lists only ENTC/TRNS/AGRC transformations. **None of `TX:WASO:INC_ENERGY_FROM_INCINERATION_STRATEGY_LEDS`, `TX:WASO:INC_ENERGY_FROM_BIOGAS_STRATEGY_LEDS`, `TX:WASO:INC_CAPTURE_BIOGAS_STRATEGY_LEDS` is bundled into the LEDS run.** LEDS = baseline for waste-to-energy. The 0.85 magnitudes and ramps are defined but inactive.
2. **IAA vs DMA separation**: SISEPUEDE separates ISW (industrial) from MSW (municipal) at the *incineration* node (`qty_waso_isw_…` vs `qty_waso_msw_…`) — this maps cleanly to IAA/DMA. But the *biogas/anaerobic* and *landfill-gas* streams are NOT split ISW vs MSW (single `gasrecovered_waso_biogas_anaerobic_tonne` aggregates both food-industry sludge and household organics). Attribution of biogas to IAA vs DMA needs an exogenous splitting assumption.
3. **Energy delivered to industry**: traceable only via `energy_demand_enfu_subsector_total_pj_inen_fuel_biomass/_biogas`, but SISEPUEDE does not preserve the WASO→INEN provenance — biomass burned in industry could equally come from forestry/wood waste (AFOLU side). Need an exogenous "share of INEN biomass from waste origin" indicator, or reverse-derive from the `qty_waso_*_recovered_for_energy` variables × NCV.
4. **Unit conversion ambiguity**: `frac_waso_isw_incinerated_recovered_for_energy` is a fraction of *the incinerated portion of non-recycled ISW* — to translate to Ktep one must chain: total ISW generated × non-recycled fraction × incinerated fraction × recovered-for-energy fraction × NCV. Net-calorific-value defaults (`energydensity_gravimetric_enfu_gj_per_tonne_fuel_biomass/_biogas`) drive the result and should be locked to LEDS assumptions.
5. **Magnitude gap**: even at the design magnitude of 0.85, the resulting tonnage × NCV is several orders of magnitude below the LT-LEDS Ktep target. Either the WASO base-stock (total ISW + MSW generated) is too low in the Morocco calibration, or the LT-LEDS target counts waste streams that SISEPUEDE classifies elsewhere (e.g. olive pomace under AFOLU residues, sugar bagasse under crop residues). **Recommend cross-checking total ISW/MSW generation against ADEME/Morocco statistics before tuning.**

---

## 6. CCUS — Phosphates, Microalgae & Geological Storage

### Targets
- 2030: 25% phosphate emissions captured
- 2040: 50% phosphate emissions captured
- 2050: 9.5 MtCO2e microalgae + 6 MtCO2e geological storage

### Plain-English interpretation
Morocco's phosphate industry (OCP) is the dominant industrial CO2 point source. The 2030/2040 targets are *process-emission capture rates* on phosphate (fertilizer / phosphoric acid / ammonia) production — an **IPPU** boundary issue, with co-benefits on the combustion (INEN) side because phosphate sites also burn fossil fuels for heat. The 2050 targets are *negative-emission* magnitudes split between **biological CDR** (microalgae ponds absorbing flue-gas CO2) and **engineered geological storage** (CO2 injected into saline aquifers / depleted reservoirs). In SISEPUEDE these map to two distinct modules: `PFLO:INC_IND_CCS` (sector-wide industrial CCS, hits both IPPU and INEN) and `CCSQ:INC_CAPTURE` (engineered carbon removal, conceptually DAC but the magnitude lever is generic MtCO2 captured). Microalgae has **no native transformer** and must be proxied.

### SSP transformation mapping
- **Code**: `TX:PFLO:INC_IND_CCS`
  - **YAML**: `ssp_modeling/transformations/transformation_pflo_inc_ind_ccs_strategy_LEDS.yaml`
  - **Transformer**: `TFR:PFLO:INC_IND_CCS`
  - **Key parameters**: `dict_magnitude_eff: 0.9` (capture *effectiveness* once installed), `dict_magnitude_prev: null` (defaults to maximum *prevalence* — fraction of facilities equipped). Effective capture share ≈ prev × eff. Ramp `tp_0_ramp: 12` (≈ 2027). Drives `frac_ippu_production_with_co2_capture_chemicals|cement|...` and `gasrf_ippu_co2_capture_*`.
  - **Relation to target**: Serves the **25 % (2030) and 50 % (2040) phosphate capture** targets via the "chemicals" IPPU category (where phosphate/fertilizer sits) plus INEN combustion at the same sites.

- **Code**: `TX:CCSQ:INC_CAPTURE`
  - **YAML**: `ssp_modeling/transformations/transformation_ccsq_inc_capture_strategy_LEDS.yaml`
  - **Transformer**: `TFR:CCSQ:INC_CAPTURE`
  - **Key parameter**: `magnitude: 50.0` MtCO2/yr by final period, ramp `tp_0_ramp: 12`. Drives `qty_ccsq_mt_co2_captured_sequestered_by_direct_air_capture` and the negative `emission_co2e_co2_ccsq_direct_air_capture`.
  - **Relation to target**: Serves the **2050 6 MtCO2e geological storage** target (and is the only available proxy for the **9.5 MtCO2e microalgae** target). Default 50 Mt overshoots Morocco's 15.5 Mt combined 2050 ambition — needs down-scaling.

- **Related (not in scope but adjacent)**: `TX:IPPU:DEC_CLINKER_STRATEGY_LEDS` reduces cement clinker share; affects denominator of IPPU capture share but is not phosphate-specific.

### Output variables to display the targets
**WIDE_INPUTS_OUTPUTS:**
- Phosphate-process CCS share: `frac_ippu_production_with_co2_capture_chemicals` (unitless 0–1) — interpret "chemicals" as the OCP/phosphate proxy.
- Captured mass at chemicals: `gasrecovered_ippu_mt_co2_capture_chemicals` (MtCO2).
- Gross phosphate process emissions (denominator): `emission_co2e_co2_ippu_production_chemicals` (MtCO2e).
- Engineered storage / DAC: `qty_ccsq_mt_co2_captured_sequestered_by_direct_air_capture` (MtCO2) and net `emission_co2e_co2_ccsq_direct_air_capture` (MtCO2e, negative when removing).
- Subsector totals: `emission_co2e_subsector_total_ccsq`, `emission_co2e_subsector_total_ippu`.

**Tableau `decomposed_emissions_morocco_2018.csv`:** filter `sector == "5 - CCSQ"`, `Gas == "CO2"` for engineered + microalgae proxy; `sector == "4 - IPPU"`, `subsector` containing chemicals, `Gas == "CO2"` with `value_original < value` to read net-of-capture.

**Tableau `drivers_morocco.csv`:** filter `subsector == "Carbon Capture and Sequestration"`, `model_variable == "qty_ccsq_mt_co2_captured_sequestered_by_direct_air_capture"`; and `subsector == "Industrial Processes and Product Use"`, `model_variable` matching `frac_ippu_production_with_co2_capture_chemicals`.

**Suggested chart**: stacked area, 2018–2050, three layers — *phosphate process capture* (IPPU chemicals captured Mt) + *microalgae proxy* (share of CCSQ allocated to bio-CDR) + *geological storage* (remaining CCSQ share); overlay LT-LEDS target markers at 2030/2040/2050.

### Run validation (strategy LEDS, primary_id 73073)
| Variable | 2018 | 2030 | 2040 | 2050 | Units | vs target |
|---|---|---|---|---|---|---|
| `frac_ippu_production_with_co2_capture_chemicals` | 0.00 | 0.00 | 0.00 | 0.00 | share | **Misses 25%/50%** |
| `gasrecovered_ippu_mt_co2_capture_chemicals` | 0.00 | 0.00 | 0.00 | 0.00 | MtCO2 | n/a |
| `qty_ccsq_mt_co2_captured_sequestered_by_direct_air_capture` | 0.0 | 0.0 | 0.0 | 0.0 | MtCO2 | **Misses 15.5 Mt** |
| `emission_co2e_co2_ippu_production_chemicals` (denominator) | 0.00 | 0.00 | 0.00 | 0.00 | MtCO2e | gross-emission slot is empty |

**Critical gap:** `ATTRIBUTE_STRATEGY.csv` row `6004 PFLO:LEDS` contains only ENTC/TRNS/AGRC LEDS transformations — **neither `TX:PFLO:INC_IND_CCS_STRATEGY_LEDS` nor `TX:CCSQ:INC_CAPTURE_STRATEGY_LEDS` is in the LEDS bundle**, so the run output is identical to BASE for all CCS columns. The LEDS strategy must be re-defined to include both before re-running.

### Gaps / open questions
- **Microalgae has no native transformer.** Recommended proxy: re-purpose `CCSQ:INC_CAPTURE` with `magnitude = 15.5` (Mt by 2050) and post-process by splitting `qty_ccsq_mt_co2_captured_sequestered_by_direct_air_capture` 9.5/6.0 into "biological" vs "geological" labels in `data_prep_new_mapping.r`. Long-term: add a real `TFR:CCSQ:INC_CAPTURE_BIO` category under `cat_ccsq`.
- **Phosphate is not a first-class IPPU category.** It is bundled into `chemicals`. Either (a) accept "chemicals" as the phosphate proxy (OCP dominates Moroccan chemical-industry CO2) or (b) fork a new `cat_industry = phosphate` with its own `ef_ippu_tonne_co2_per_tonne_production_phosphate` and `frac_ippu_production_with_co2_capture_phosphate`.
- **Geological storage units**: confirm `qty_ccsq_*` is MtCO2 (driver taxonomy implies yes); the LEDS `magnitude: 50` therefore reads as 50 MtCO2/yr by 2050 — far above the 6 MtCO2 target. Re-scale to 15.5.
- **Strategy assembly bug**: add `TX:PFLO:INC_IND_CCS_STRATEGY_LEDS` and `TX:CCSQ:INC_CAPTURE_STRATEGY_LEDS` to strategy 6004 (`PFLO:LEDS`) and re-run; current `2026-05-20T12;42;19` outputs cannot validate CCS targets.

---

## 7. Cross-Target Gaps & Open Questions

### 7.1 Strategy 6004 (`PFLO:LEDS`) is incomplete for the industry sector
The most consequential issue. The current `transformation_specification` for strategy 6004 is:

```
TX:AGRC:DEC_CH4_RICE_STRATEGY_LEDS |
TX:ENTC:DEC_LOSSES_STRATEGY_LEDS |
TX:ENTC:TARGET_RENEWABLE_ELEC_STRATEGY_LEDS |
TX:TRNS:INC_EFFICIENCY_ELECTRIC_STRATEGY_LEDS |
TX:TRNS:SHIFT_FUEL_LIGHT_DUTY_STRATEGY_LEDS |
TX:TRNS:SHIFT_FUEL_MEDIUM_DUTY_STRATEGY_LEDS |
TX:TRNS:SHIFT_FUEL_PUBLIC_STRATEGY_LEDS
```

**Missing transformations that should be added before the next LEDS run:**

- `TX:INEN:INC_EFFICIENCY_ENERGY_STRATEGY_LEDS`
- `TX:INEN:INC_EFFICIENCY_PRODUCTION_STRATEGY_LEDS`
- `TX:INEN:SHIFT_FUEL_HEAT_STRATEGY_LEDS`
- `TX:ENTC:TARGET_CLEAN_HYDROGEN_STRATEGY_LEDS`
- `TX:WASO:INC_ENERGY_FROM_INCINERATION_STRATEGY_LEDS`
- `TX:WASO:INC_ENERGY_FROM_BIOGAS_STRATEGY_LEDS`
- `TX:WASO:INC_CAPTURE_BIOGAS_STRATEGY_LEDS`
- `TX:PFLO:INC_IND_CCS_STRATEGY_LEDS`
- `TX:CCSQ:INC_CAPTURE_STRATEGY_LEDS`
- Optionally: any relevant `IPPU:*` reductions (HFCs, N2O, PFCs, clinker) that the LT-LEDS mentions for industry beyond what is in this slide.

Without these, every column in the run validation tables above will continue to read BAU values regardless of what the YAMLs say. This should be the first remediation step.

### 7.2 Ramp timing (`tp_0_ramp = 12`)
All five industry transformations use `vec_implementation_ramp.tp_0_ramp = 12`, which starts the ramp at time period 12 ≈ 2030. The −17% EE target, the 30/43/27 mix, the 288 Ktep H2 industrial use, and the 25% phosphate capture are all **2030 milestones** — they cannot bind if the lever starts ramping in the same year it should already be met. Recommend `tp_0_ramp = 0` (start ramp at base year) or `tp_0_ramp = 5` (2023) for industry-sector LEDS transformations, with a 10–15 period ramp window.

### 7.3 Unit conventions
LT-LEDS uses Ktep and TWh; SISEPUEDE WIDE outputs are in PJ; capacity outputs are in GW. The mapping requires the conversions to be applied in `output_postprocessing/scr/data_prep_drivers.r` and `data_prep_new_mapping.r`. Store both source-unit and converted columns so Tableau can render either axis.

| Source unit | Conversion | SI unit |
|---|---|---|
| 1 Ktep | × 0.041868 | PJ |
| 1 Ktep | × 11.63 | GWh |
| 1 TWh | × 3.6 | PJ |
| 1 MW | × 0.001 | GW |

### 7.4 Targets with no native SSP representation
| Target | Native SSP representation? | Proxy / workaround |
|---|---|---|
| Distributed PV (1.5 / 2.7 GW) | No — `pp_solar` is utility + distributed lumped | Either back-derive from INEN solar fuel demand, or assume an exogenous distributed share of `pp_solar` |
| Microalgae 9.5 MtCO2e | No — no biological-CDR transformer | Split `qty_ccsq_*` 9.5/6.0 in `data_prep_new_mapping.r` |
| Phosphate-only process capture | No — bundled into IPPU `chemicals` | Use "chemicals" as proxy (Morocco OCP dominates), or add a new `cat_industry = phosphate` category |
| IAA vs DMA biogas split | Partial — incineration node splits ISW/MSW, biogas node aggregates | Exogenous split fraction in post-processing |

### 7.5 Calibration sanity check (waste mass)
At the LEDS magnitude of 0.85, the run produces ~14 kt/yr of recovered industrial waste — five orders of magnitude below the LT-LEDS 645 Ktep IAA target (which implies roughly 1.5–2 Mt/yr of waste fed to energy at typical NCVs). Either the Morocco WASO base-stock is too low, or the LT-LEDS target counts waste streams that SISEPUEDE classifies under AFOLU residues (olive pomace, sugar bagasse). Cross-check `factor_waso_generated_*` calibration against ADEME / Morocco municipal & industrial waste statistics.

---

## 8. Recommended Tableau Views (one per target)

| View | Chart | Series (from `drivers_morocco.csv` unless noted) | Target overlay |
|---|---|---|---|
| **EE intensity** | Line | `Energy Demand in Industrial Energy` (PJ), summed by `subsector = Industrial Energy`, indexed 2018 = 100 | Horizontal lines at 83 (2030), 78 (2040), 73 (2050) |
| **Industrial H2 uptake** | Line | `Energy Demand` × `category_value = fuel_hydrogen` × `energy_subsector = Industrial Energy` (PJ) | Target points at 12 / 24 / 52 PJ |
| **National green H2 production** | Line + bar | `Fuel Production` × `fuel_hydrogen` (PJ) + ENTC stacked bar of `fp_hydrogen_*` technologies | Target points at 12 / 24 / 52 PJ |
| **Industrial NG** | Line | `Energy Demand` × `fuel_natural_gas` × `Industrial Energy` (PJ) | Target points at 33 (2030), 38 (2050) PJ |
| **INEN mix shares** | 100% stacked area | Computed: electricity / fossil / RE shares of total `energy_demand_enfu_subsector_total_pj_inen_fuel_*` | Three reference lines per year (30/43/27 → 33/35/32 → 36/26/39) |
| **Total solar capacity (with distributed marker)** | Line + horizontal lines | `nemomod_entc_total_annual_generation_capacity_pp_solar` (GW) | Reference lines at 1.5 (2030) and 2.7 (2050) GW — caveat: utility + distributed |
| **IAA waste-to-energy** | Stacked area | Computed Ktep from `qty_waso_isw_recovered_for_energy_incineration_tonne` + biogas share allocated to IAA × NCV | Target points 607 (2030), 645 (2050) Ktep |
| **DMA waste-to-energy** | Stacked area | Computed Ktep from MSW incineration + landfill-gas energy use × NCV | Target points 116 (2030), 314 (2050) Ktep |
| **Phosphate capture share** | Line | `frac_ippu_production_with_co2_capture_chemicals` (%) | Reference lines at 25% (2030), 50% (2040) |
| **CCSQ negative emissions split** | Stacked area | `qty_ccsq_mt_co2_captured_sequestered_by_direct_air_capture` (MtCO2) split into bio (9.5/15.5) and geo (6/15.5) via post-processing | Targets 9.5 + 6 = 15.5 MtCO2 in 2050 |

All views should expose the `strategy` dimension (BASE vs LEDS vs any sub-strategy) so the LEDS gap discussed in 7.1 is visible directly in the dashboard.

---

## Appendix A — Output Variable Index

| Variable (WIDE) | Units | Driver `model_variable` (drivers_morocco) | Tableau `subsector` filter | Used for |
|---|---|---|---|---|
| `energy_consumption_inen_total` | PJ | Total Energy Consumption from Industrial Energy | Industrial Energy | EE |
| `energy_demand_enfu_subsector_total_pj_inen_fuel_*` | PJ | Energy Demand (by fuel) | Industrial Energy | EE, fuel mix shares |
| `prod_enfu_fuel_hydrogen_pj` | PJ | Fuel Production (fuel_hydrogen) | Energy Fuels | Green H2 production |
| `nemomod_entc_*_fp_hydrogen_*` | PJ (gen) | NemoMod Production by Technology | Energy Technology | H2 green vs grey split |
| `nemomod_entc_total_annual_generation_capacity_pp_solar` | GW | Total Annual Generation Capacity | Energy Technology | PV target |
| `frac_inen_energy_<industry>_solar` | fraction | (component of mix-share) | Industrial Energy | INEN-side solar |
| `qty_waso_isw_recovered_for_energy_incineration_tonne` | tonne/yr | (qty recovered) | Solid Waste | IAA waste-to-energy |
| `qty_waso_msw_recovered_for_energy_incineration_tonne` | tonne/yr | (qty recovered) | Solid Waste | DMA waste-to-energy |
| `gasrecovered_waso_biogas_anaerobic_tonne` | tonne/yr | Biogas Recovered | Solid Waste | IAA+DMA biogas |
| `gasrecovered_waso_biogas_landfills_tonne` | tonne/yr | Landfill Gas Recovered | Solid Waste | DMA landfill gas |
| `energy_demand_enfu_subsector_total_pj_inen_fuel_biomass` | PJ | Energy Demand (fuel_biomass) | Industrial Energy | IAA delivered energy |
| `energy_demand_enfu_subsector_total_pj_inen_fuel_biogas` | PJ | Energy Demand (fuel_biogas) | Industrial Energy | IAA+DMA delivered energy |
| `frac_ippu_production_with_co2_capture_chemicals` | fraction | Fraction Production with CO2 Capture | Industrial Processes and Product Use | Phosphate CCS share |
| `gasrecovered_ippu_mt_co2_capture_chemicals` | MtCO2 | (captured mass) | Industrial Processes and Product Use | Phosphate capture mass |
| `qty_ccsq_mt_co2_captured_sequestered_by_direct_air_capture` | MtCO2 | DAC mass | Carbon Capture and Sequestration | Microalgae + geological proxy |
| `emission_co2e_co2_ccsq_direct_air_capture` | MtCO2e (neg) | (net emission) | Carbon Capture and Sequestration | Net CCSQ contribution |
| `emission_co2e_subsector_total_ippu` | MtCO2e | (subsector total) | Industrial Processes and Product Use | IPPU net |

## Appendix B — LEDS Run Validation Snapshot

Run: `sisepuede_results_sisepuede_run_2026-05-20T12;42;19.976658`, strategy 6004 (`PFLO:LEDS`), primary_id 73073.

| Target area | Variable | 2030 | 2050 | Target | Status |
|---|---|---|---|---|---|
| EE | `energy_consumption_inen_total` (PJ) | 183.0 | 199.3 | −17% / −27% vs 2018 | ❌ Reads +5.7% / +15.1% (BAU) |
| Green H2 production | `prod_enfu_fuel_hydrogen_pj` | 3.16 | 33.05 | 12 / 52 PJ | ⚠️ 2040 OK, 2030 short, 2050 short |
| Industrial H2 use | `energy_demand_enfu_..._inen_fuel_hydrogen` | 0 | 0 | >0 | ❌ Never enters INEN |
| Industrial NG | `energy_demand_enfu_..._inen_fuel_natural_gas` | 3.67 | 4.09 | 33 / 38 PJ | ❌ Order of magnitude low |
| Solar capacity (proxy) | `total_annual_generation_capacity_pp_solar` | 4.76 | 26.29 | 1.5 / 2.7 GW (industrial only) | ⚠️ Aggregate >> target, distributed not isolated |
| IAA waste recovery | `qty_waso_isw_recovered_for_energy_incineration_tonne` | 7,443 | 13,662 | 607 / 645 Ktep | ❌ Multiple orders of magnitude low |
| DMA waste recovery | `qty_waso_msw_recovered_for_energy_incineration_tonne` | 6,036 | 6,769 | 116 / 314 Ktep | ❌ Multiple orders of magnitude low |
| Phosphate capture | `frac_ippu_production_with_co2_capture_chemicals` | 0 | 0 | 25% / 50% | ❌ Lever not active |
| Engineered CDR | `qty_ccsq_mt_co2_captured_sequestered_by_direct_air_capture` | 0 | 0 | 15.5 MtCO2 (2050) | ❌ Lever not active |

Root cause for all ❌/⚠️: strategy 6004 omits industry-sector LEDS transformations (see Section 7.1).

---

## Appendix C — Agent Network Used to Produce This Document

This document was produced by an orchestrated network of five thematic agents working in parallel, each scoped to one target family:

- **A1** — Industrial Energy Efficiency (`INEN:INC_EFFICIENCY_*`)
- **A2** — Fuel Mix & Green H2 (`INEN:SHIFT_FUEL_HEAT`, `ENTC:TARGET_CLEAN_HYDROGEN`)
- **A3** — Distributed PV in Industry (`ENTC:TARGET_RENEWABLE_ELEC`)
- **A4** — Waste-to-Energy IAA + DMA (`WASO:INC_ENERGY_FROM_*`, `WASO:INC_CAPTURE_BIOGAS`)
- **A5** — CCUS — Phosphates, Microalgae, Geological (`PFLO:INC_IND_CCS`, `CCSQ:INC_CAPTURE`)

Each agent independently inspected the relevant YAMLs, the `strategy_definitions.csv`, the WIDE output of the latest LEDS run, and the Tableau-bound files (`decomposed_emissions_morocco_2018.csv`, `drivers_morocco.csv`), then returned a markdown fragment following a shared template. The orchestrator (this conversation) consolidated, added cross-target sections, and verified the shared finding that strategy 6004 omits all industry transformations.
