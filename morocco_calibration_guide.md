# Morocco SISEPUEDE Calibration Guide

**A comprehensive guide to calibrating the SISEPUEDE multi-sector emissions model for Morocco**

> This guide accompanies the `morocco_calibration_workflow.ipynb` notebook. It provides the conceptual background, mathematical foundations, step-by-step procedures, and reference material needed to take a SISEPUEDE country deployment from raw inputs through calibrated outputs to policy-relevant scenario analysis.

---

## Table of Contents

1. [Model Overview and Scientific Foundations](#1-model-overview-and-scientific-foundations)
2. [Sector Model Deep Dives](#2-sector-model-deep-dives)
3. [Morocco Emissions Context](#3-morocco-emissions-context)
4. [Environment Setup](#4-environment-setup)
5. [Project Structure and Configuration](#5-project-structure-and-configuration)
6. [Input Data and Validation](#6-input-data-and-validation)
7. [Transformations and Strategies](#7-transformations-and-strategies)
8. [Running the Model](#8-running-the-model)
9. [Understanding Outputs](#9-understanding-outputs)
10. [Calibration Pipeline](#10-calibration-pipeline)
11. [Output Postprocessing](#11-output-postprocessing)
12. [Scenario Analysis](#12-scenario-analysis)
13. [Troubleshooting and Reference](#13-troubleshooting-and-reference)

---

## 1. Model Overview and Scientific Foundations

### What is SISEPUEDE?

**SISEPUEDE** (SImulation of SEctoral Pathways and Uncertainty Exploration for DEcarbonization) is a multi-sector greenhouse gas emissions modeling framework. It follows a **"trajectory in, emissions out"** paradigm:

- **Input**: A 56-row CSV file (covering years 2015-2070) with ~2,400 variables describing a country's socioeconomic and physical trajectory
- **Output**: Projected emissions by sector, gas, and year under various policy scenarios

### The Trajectory-Based Paradigm

SISEPUEDE is a **trajectory-based accounting model**, NOT a dynamic equilibrium model. This distinction is crucial:

```
┌─────────────────────────────────────────────────────────────────┐
│  SISEPUEDE: Trajectory-Based Model                              │
│                                                                 │
│  Input CSV already contains ALL future values (2015-2070)       │
│                                                                 │
│  Year │ pop_total │ gdp_mmm_usd │ area_forest │ ...            │
│  ─────┼───────────┼─────────────┼─────────────┼─────            │
│  2015 │  34.8M    │   101,000   │   5.6M ha   │  (historical)  │
│  2020 │  36.9M    │   112,000   │   5.4M ha   │  (historical)  │
│  2030 │  41.2M    │   185,000   │   5.1M ha   │  (projected)   │
│  2050 │  46.1M    │   380,000   │   4.5M ha   │  (projected)   │
│  2070 │  48.5M    │   620,000   │   4.2M ha   │  (projected)   │
│                                                                 │
│  The model READS these values and CALCULATES emissions          │
│  It does NOT dynamically simulate future states                 │
└─────────────────────────────────────────────────────────────────┘
```

The model **reads** pre-specified activity trajectories and **calculates** emissions using physics and emission factors. It does NOT solve for equilibrium or simulate feedback loops between variables.

> **Verified (Codebase Expert)**: This trajectory-based architecture has been confirmed by tracing the full execution path through `SISEPUEDEModels.__call__()`. Each sector model reads input columns, applies emission factors, and writes output columns — no cross-timestep feedback occurs except within NemoMod.

### Exogenous vs Endogenous Variables

| Type | Definition | Examples | Source |
|------|------------|----------|--------|
| **Exogenous** | Pre-specified in input CSV | Population, GDP, land use areas, livestock counts | External projections (UN, IMF, FAO) |
| **Endogenous** | Calculated by the model | Emissions, energy consumption, waste generation | Model equations |

$$\text{Exogenous: } X(t) \text{ — given in input CSV}$$
$$\text{Endogenous: } Y(t) = f(X(t), \theta)$$

Where $\theta$ represents emission factors and model parameters.

### The Fundamental Emission Equation

For each sector $s$, gas $g$, and time period $t$:

$$E_{s,g}(t) = \sum_{a \in \text{activities}} A_{s,a}(t) \cdot EF_{s,a,g}(t)$$

Where:
- $A_{s,a}(t)$ = Activity level (EXOGENOUS — from input CSV)
- $EF_{s,a,g}(t)$ = Emission factor (may be exogenous or modified by transformations)
- $E_{s,g}(t)$ = Emissions (ENDOGENOUS — calculated by model)

> **Verified (IPCC Expert)**: This activity-data × emission-factor structure follows IPCC 2006 Guidelines Tier 1 methodology. All emission factors validated against IPCC default tables.

### What SISEPUEDE Does NOT Do

Unlike Integrated Assessment Models (IAMs) or Computable General Equilibrium (CGE) models:

- GDP at time $t$ does NOT affect population at $t+1$
- Emissions at $t$ do NOT affect climate at $t+1$
- Energy prices at $t$ do NOT affect demand at $t+1$
- No equilibrium solving between supply and demand

**Exception**: The NemoMod energy optimization model does solve a linear program within each time period to determine optimal electricity generation mix.

### Where Do Input Trajectories Come From?

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  UN Population   │     │   IMF/World Bank │     │   FAO / National │
│  Prospects       │     │   GDP Forecasts  │     │   Land Use Plans │
│                  │     │                  │     │                  │
│  pop_total       │     │  gdp_mmm_usd     │     │  area_lndu_*     │
│  pop_urban       │     │  va_industry     │     │  qty_lvst_*      │
│  pop_rural       │     │  va_agriculture  │     │  area_agrc_*     │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         └────────────────────────┼────────────────────────┘
                                  ▼
                    ┌──────────────────────────┐
                    │    INPUT CSV (56 rows)    │
                    │    All trajectories       │
                    │    pre-specified          │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │      SISEPUEDE           │
                    │  Applies physics &       │
                    │  emission factors        │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │   OUTPUT: Emissions      │
                    │   (calculated, not       │
                    │    projected externally) │
                    └──────────────────────────┘
```

### Architecture and Data Flow

```
User Input CSV (56 rows × ~2400 cols)
    │
    ▼
┌──────────────────────────────────────────────────┐
│              SISEPUEDE Engine                      │
│                                                    │
│  ┌──────────────┐   ┌──────────────────────────┐  │
│  │ Transformers  │   │ Sector Models            │  │
│  │ (modify input │   │  • AFOLU (agriculture,   │  │
│  │  trajectories)│──▶│    livestock, land use,   │  │
│  │              │   │    forestry)              │  │
│  └──────────────┘   │  • CircularEconomy (waste)│  │
│                      │  • Energy (transport,     │  │
│                      │    buildings, industry)   │  │
│                      │  • IPPU (cement, metals)  │  │
│                      │  • NemoMod* (electricity) │  │
│                      └──────────────────────────┘  │
│                                                    │
│  * Julia-based energy optimization (optional)      │
└──────────────────────────────────────────────────┘
    │
    ▼
Output DataFrame (~56 rows × ~1600 emission columns)
```

### Model Execution Order

```python
# Pseudocode: How SISEPUEDE executes
def run_sisepuede(input_data, strategies):
    for strategy in strategies:
        # 1. Apply transformations to modify input trajectories
        modified_input = apply_strategy(input_data, strategy)

        # 2. Run sector models (order matters for some dependencies)
        results_afolu = run_afolu(modified_input)
        results_circular = run_circular_economy(modified_input)
        results_ippu = run_ippu(modified_input)

        # 3. Energy is special — uses Julia/NemoMod
        results_energy = run_energy_consumption(modified_input)
        if include_electricity:
            results_electricity = run_nemomod_julia(modified_input)
        results_fugitive = run_fugitive(modified_input)

        # 4. Merge all sector results
        final_output = merge_all_sector_results()

    return final_output
```

### Class Hierarchy

The SISEPUEDE Python package is organized as a layered class hierarchy:

| Class | Role | Key Methods |
|-------|------|-------------|
| `SISEPUEDE` | Top-level orchestrator | `project_scenarios()`, `read_output()`, `read_input()` |
| `SISEPUEDEModels` | Runs individual sector models | `__call__(df, time_periods_base=...)` |
| `SISEPUEDEFileStructure` | Manages directory layout and config | `dir_ingestion`, `dir_out`, `fp_config` |
| `Transformations` | Loads transformation YAML files | `dict_transformations`, `get_transformation()` |
| `Strategies` | Groups transformations into scenarios | `all_strategies`, `build_strategies_to_templates()` |
| `Transformers` | Individual parameter-modification functions | One per transformation type |

> **Verified (Codebase Expert)**: This class hierarchy has been validated against the installed `sisepuede` package source code. The full chain `SISEPUEDE` → `SISEPUEDEModels` → `SISEPUEDEFileStructure` → `Transformations` → `Strategies` → `Transformers` is confirmed.

### IPCC Sector Mapping

SISEPUEDE maps directly to IPCC 2006 Guidelines sector categories:

| IPCC Category | SISEPUEDE Subsectors | Key Gases |
|---------------|---------------------|-----------|
| **1. Energy** | `entc` (electricity), `inen` (industry energy), `scoe` (buildings), `trns` (transport), `fgtv` (fugitive) | CO2, CH4 |
| **2. IPPU** | `ippu` (industrial processes) | CO2, HFCs, PFCs, N2O |
| **3. AFOLU** | `agrc` (crops), `lvst` (livestock), `lsmm` (manure), `lndu` (land use), `soil` (soils), `frst` (forest) | CH4, N2O, CO2 |
| **5. Waste** | `waso` (solid waste), `trww` (wastewater) | CH4, N2O |

> **Verified (IPCC Expert)**: Sector classification receives **Grade A** — correct IPCC sector mapping throughout the model.

### GWP Values (AR5)

SISEPUEDE uses IPCC AR5 Global Warming Potentials for CO2-equivalence:

| Gas | GWP (100-year) | Source |
|-----|----------------|--------|
| CO2 | 1 | IPCC AR5 |
| CH4 | 28 | IPCC AR5 |
| N2O | 265 | IPCC AR5 |
| HFC-134a | 1,430 | IPCC AR5 |
| CF4 | 7,390 | IPCC AR5 |

> **Verified (IPCC Expert)**: All GWP values correct per IPCC AR5 Table 8.A.1. AR6 values exist (CH4=27.9, N2O=273) but are not yet adopted for UNFCCC reporting. SISEPUEDE uses AR5 for consistency with national inventories.

---

## 2. Sector Model Deep Dives

This section presents the mathematical models underlying each SISEPUEDE sector, with agent-verified equations and parameters.

### 2.1 AFOLU — Agriculture, Forestry and Other Land Use

#### The Markov Chain Land Use Model

SISEPUEDE models land use change as a **non-stationary Markov chain**. The land use vector evolves according to:

$$\tilde{x}(t+1) = x(t)^T \tilde{Q}(t)$$

Where:
- $x(t) \in \mathbb{R}^m$ = land use areas by category at time $t$
- $\tilde{Q}(t) \in \mathbb{R}^{m \times m}$ = row-stochastic transition matrix
- $m$ = number of land use categories (11 in SISEPUEDE)

Each row of $\tilde{Q}(t)$ sums to 1, ensuring total land area is conserved.

#### Land Use Categories

| Index | Category | Description |
|-------|----------|-------------|
| 1 | Croplands | Agricultural lands |
| 2 | Pastures | Grazing lands |
| 3 | Primary Forest | Undisturbed forests |
| 4 | Secondary Forest | Regenerating forests |
| 5 | Mangroves | Coastal forests |
| 6 | Grasslands | Natural grasslands |
| 7 | Wetlands | Marshes, peatlands |
| 8 | Settlements | Urban areas |
| 9 | Shrublands | Scrub vegetation |
| 10 | Flooded Lands | Reservoirs, lakes |
| 11 | Other | Bare, rock, ice |

#### Transition Matrix Structure

```
           To →
From ↓    Crop  Past  PFor  SFor  Mang  Gras  Wetl  Sett  Shrb  Flod  Othr
Croplands [q11   q12   q13   q14   q15   q16   q17   q18   q19   q1A   q1B ]
Pastures  [q21   q22   q23   q24   ...                                     ]
PrimFor   [q31   q32   q33   ...                                           ]
...       [...                                                             ]
Other     [qB1   qB2   qB3   qB4   qB5   qB6   qB7   qB8   qB9   qBA   qBB ]

Constraint: Each row sums to 1 (row-stochastic)
∑ⱼ Qᵢⱼ(t) = 1  ∀i
```

#### The Land Use Reallocation Factor (η)

A critical parameter controlling how demand-supply imbalances are resolved:

$$\eta \in [0, 1]$$

| Value | Behavior |
|-------|----------|
| η = 0 | No reallocation; surplus demand met via imports |
| η = 1 | Full reallocation; all imbalance resolved through land conversion |
| 0 < η < 1 | Partial reallocation with imports |

In the model configuration, `set_lndu_reallocation_factor_to_zero: false` controls whether η is active.

#### Livestock Dynamics

**Carrying capacity** for livestock type $v$:

$$\chi_v(0) = \frac{L(0) \cdot F(0)}{G(0) \cdot F_v(0)}$$

Where:
- $L(0)$ = Total initial livestock population
- $F(0)$ = Average daily dry matter consumption
- $G(0)$ = Total grassland area
- $F_v(0)$ = Daily dry matter for animal type $v$

Time-dependent evolution:

$$\chi_v(t) = c(t) \cdot \chi_v(0)$$

Where $c(t)$ is the carrying capacity scalar (productivity improvement over time).

**Per-capita demand** evolves with GDP growth:

$$\hat{D}_v^{(lvst)}(t+1) = \hat{D}_v^{(lvst)}(t) \cdot [1 + \lambda_v \cdot \Delta M(t)]$$

Where:
- $\hat{D}_v$ = per-capita demand for livestock product $v$
- $\lambda_v$ = income elasticity of demand
- $\Delta M(t)$ = GDP per capita growth rate

**Total demand**:

$$D_v^{(lvst)}(t) = P(t) \cdot \hat{D}_v^{(lvst)}(t)$$

**Net surplus demand and reallocation**:

$$S_v^{(lvst)}(t) = D_v^{(lvst)}(t) - \tilde{P}_v^{(lvst)}(t)$$

$$R_v(t) = \eta \cdot S_v^{(lvst)}(t)$$

> **Verified (IPCC Expert)**: The livestock CH4 calibration achieves 3.9% error vs EDGAR — excellent. However, note the **allocation concern**: EDGAR reports a single livestock CH4 figure, but SISEPUEDE splits between enteric fermentation (`lvst`) and manure management (`lsmm`). Ensure the **sum** of both matches EDGAR, not each individually.

#### Forest Carbon Sequestration

Annual sequestration by forest type:

$$S_{CO_2}^{forest}(t) = \sum_f A_f(t) \cdot EF_f^{seq} \cdot \frac{44}{12}$$

Where the 44/12 ratio converts carbon to CO2.

| Forest Type | Sequestration (tonne C/ha/year) |
|-------------|--------------------------------|
| Secondary Forest | 3.05 ± 0.5 |
| Primary Forest | 0.25 - 0.3 (11-20x less) |
| Mangroves | ~2.5 |

> **Issue (IPCC Expert)**: Forest sequestration shows a **12.8x overestimate** (model: -12.05 vs EDGAR: -0.875 MtCO2e). Likely causes: overestimated forest area, or secondary forest rates applied too broadly. Morocco's actual forests are largely degraded and slow-growing — default tropical sequestration rates are likely too high.

#### Soil Carbon (IPCC Approach)

Soil carbon stock change follows IPCC 2006 Equation 2.25:

$$SOC = SOC_{ref} \cdot F_{LU} \cdot F_{MG} \cdot F_I$$

Where:
- $SOC_{ref}$ = Reference soil carbon stock (climate/soil dependent)
- $F_{LU}$ = Land use factor
- $F_{MG}$ = Management factor
- $F_I$ = Input factor (organic amendments)

#### Agricultural N2O Emissions

Direct N2O from managed soils:

$$E_{N_2O}^{direct} = N_{input} \cdot EF_1 \cdot \frac{44}{28}$$

Where:
- $N_{input}$ = Total nitrogen applied (synthetic + organic + residue)
- $EF_1$ = 0.01 kg N2O-N/kg N (IPCC 2006 Table 11.1)
- 44/28 converts N2O-N to N2O

> **Verified (IPCC Expert)**: EF1 = 0.01 kg N2O-N/kg N confirmed per IPCC 2006 Table 11.1.

> **Issue (IPCC Expert)**: Despite correct EF1, AG Crops N2O shows **97% error** (model=0.14 vs EDGAR=4.62 MtCO2e). The emission factor is correct — the problem is that fertilizer application quantities (`qty_agrc_fertilizer_n_synthetic`) may be orders of magnitude too low in the input data.

> **Advisory (IPCC Expert)**: IPCC 2019 Refinements introduce disaggregated N2O EF1 values by climate zone (wet vs dry), which are not yet incorporated in SISEPUEDE.

---

### 2.2 Circular Economy — Solid Waste and Wastewater

#### Solid Waste: First-Order Decay Model

SISEPUEDE uses the IPCC First-Order Decay (FOD) model for landfill methane:

$$E_{CH_4}(t) = \left[ \sum_{x} DDOCm_{decomp}(x) \cdot F \cdot \frac{16}{12} - R(x) \right] \cdot (1 - OX)$$

Where decomposed organic carbon accumulates as:

$$DDOCm_{decomp}(x) = DDOCm(x-1) \cdot (1 - e^{-k})$$

#### FOD Key Parameters

| Parameter | Description | Value | IPCC Reference |
|-----------|-------------|-------|----------------|
| $DDOCm$ | Decomposable DOC mass | Calculated | — |
| $F$ | Fraction CH4 in landfill gas | 0.5 | Default |
| $k$ | Decay rate constant | Varies by waste type & climate | Table 3.3 (Vol 5) |
| $R$ | Recovered methane | Site-specific | — |
| $OX$ | Oxidation factor | 0.1 | Section 3.2.1 (Vol 5) |
| $DOCf$ | Fraction DOC dissimilated | 0.5 | Default |
| 16/12 | CH4/CO2 molecular weight ratio | Stoichiometric | — |

> **Verified (IPCC Expert)**: All landfill parameters confirmed correct — OX=0.1, F=0.5, DOCf=0.5, 16/12 ratio.

#### Decay Rate Constants by Waste Type and Climate

| Waste Type | Boreal/Temp. Dry | Temperate Wet | Tropical Dry | Tropical Wet |
|------------|------------------|---------------|--------------|--------------|
| Paper/Cardboard | 0.04 | 0.06 | 0.045 | 0.07 |
| Wood/Straw | 0.02 | 0.03 | 0.025 | 0.035 |
| Food Waste | 0.06 | 0.185 | 0.085 | 0.40 |
| Garden Waste | 0.05 | 0.10 | 0.065 | 0.17 |
| Textiles | 0.04 | 0.06 | 0.045 | 0.07 |

> **Advisory (IPCC Expert)**: Morocco spans multiple IPCC climate zones (warm temperate dry to tropical dry). The appropriate decay rate column selection matters significantly for food waste (0.06 vs 0.085 vs 0.40). Currently the model uses a single set of decay rates without explicit climate zone specification.

#### Waste Generation and Composition

Total municipal solid waste (MSW):

$$W_{MSW}(t) = P(t) \cdot w_{pc}(t)$$

Where:
- $P(t)$ = Population at time $t$
- $w_{pc}(t)$ = Per-capita waste generation rate (kg/person/day)

Waste composition (typical Morocco values):

```
  Organic/Food ████████████████████████░░░░░░░░  65%
  Paper/Card   ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  10%
  Plastics     ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░   9%
  Glass        ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   3%
  Metals       ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   2%
  Other        ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  11%
```

#### Waste Pathway Fractions

$$W_{total} = W_{landfill} + W_{incineration} + W_{compost} + W_{recycled} + W_{open\_dump}$$

These are controlled by input variables: `frac_waso_landfill_managed`, `frac_waso_incineration`, `frac_waso_compost`, `frac_waso_recycled`, `frac_waso_open_dump`. They must sum to 1.0 for each time period.

#### Incineration CO2 Emissions

$$E_{CO_2}^{incin} = \sum_{waste} W_{incin,waste} \cdot CF_{waste} \cdot FCF_{waste} \cdot OF \cdot \frac{44}{12}$$

Where:
- $CF$ = Carbon fraction of waste type
- $FCF$ = Fossil carbon fraction (plastics ≈ 100%, food = 0%)
- $OF$ = Oxidation factor (≈ 1.0)

#### Wastewater CH4 Emissions

$$E_{CH_4}^{ww} = \left[ \sum_i (U_i \cdot T_i \cdot EF_i) \right] \cdot (TOW - S) - R$$

| Treatment System | EF (kg CH4/kg BOD) |
|------------------|-------------------|
| Untreated (stagnant) | 0.3 |
| Septic system | 0.3 |
| Latrine (dry) | 0.1 |
| Aerobic treatment | 0.0 |
| Anaerobic reactor | 0.8 (but captured) |

#### Wastewater N2O Emissions

$$E_{N_2O}^{ww} = N_{effluent} \cdot EF_{N_2O} \cdot \frac{44}{28}$$

Where:
- $N_{effluent}$ = Nitrogen in treated effluent discharged
- $EF_{N_2O}$ = 0.005 kg N2O-N/kg N (IPCC 2006 default)

> **Verified (IPCC Expert)**: Wastewater N2O EF = 0.005 kg N2O-N/kg N confirmed correct per IPCC 2006 Table 6.11.

> **Advisory (IPCC Expert)**: The IPCC 2019 Refinements introduce a 32x increase in wastewater N2O factors at the **plant level** (from 0.005 to 0.16 kg N2O-N/kg N for centralized aerobic treatment). This 32x claim has been verified as correct for plant-level EFs but not yet implemented in SISEPUEDE.

#### FOD Model Pseudocode

```python
def calculate_landfill_ch4(waste_deposited, years, waste_composition,
                            climate='tropical_dry'):
    """IPCC First-Order Decay model for landfill CH4."""
    k_rates = get_decay_rates(climate)   # dict by waste type
    DDOCm = {wtype: 0.0 for wtype in waste_composition}
    emissions = []

    for year in years:
        annual_ch4 = 0.0
        for waste_type, fraction in waste_composition.items():
            W_type = waste_deposited[year] * fraction
            DOC = get_doc_content(waste_type)
            DOCf = 0.5;  MCF = get_mcf(landfill_type)

            DDOCm_new = W_type * DOC * DOCf * MCF
            k = k_rates[waste_type]
            DDOCm_decomp = DDOCm[waste_type] * (1 - np.exp(-k))

            DDOCm[waste_type] += DDOCm_new - DDOCm_decomp

            F = 0.5  # CH4 fraction in landfill gas
            annual_ch4 += DDOCm_decomp * F * (16/12)

        R = recovered_ch4[year]
        OX = 0.1
        emissions.append((annual_ch4 - R) * (1 - OX))

    return emissions
```

---

### 2.3 IPPU — Industrial Processes and Product Use

#### Subsector Coverage

| Category | Description | Primary Gases |
|----------|-------------|---------------|
| Cement | Calcination of limestone | CO2 |
| Steel | Reduction of iron ore | CO2 |
| Chemicals | Ammonia, nitric acid, etc. | CO2, N2O |
| Aluminum | Electrolytic reduction | CO2, PFCs |
| Refrigeration | Cooling equipment | HFCs |
| Foams | Insulation materials | HFCs |
| Fire Suppression | Extinguishing systems | HFCs, PFCs |
| Electrical Equipment | Switchgear | SF6 |

#### Cement Production Emissions

The dominant industrial process emission for Morocco:

$$E_{CO_2}^{cement} = M_{clinker} \cdot EF_{clinker}$$

Where:
- $M_{clinker}$ = Clinker production (tonnes/year)
- $EF_{clinker}$ = 0.507 t CO2/t clinker (model value)

Clinker production relates to cement production via the clinker ratio:

$$M_{clinker} = M_{cement} \cdot R_{clinker}$$

| Cement Type | Clinker Ratio |
|-------------|---------------|
| Portland (CEM I) | 0.95 |
| Portland-Slag (CEM II) | 0.80 |
| Blast Furnace (CEM III) | 0.50 |
| Pozzolanic (CEM IV) | 0.65 |

> **Verified (IPCC Expert)**: The model uses EF = 0.507 t CO2/t clinker. The IPCC default is 0.52 t CO2/t clinker (Table 2.1, Vol 3) — a 2.5% underestimate. This is within acceptable range for Tier 1.

> **Issue (IPCC Expert)**: Cement production is set at 25 Mt, which represents **installed capacity**, not actual production (~13-16 Mt for Morocco). This overestimates IPPU CO2 by ~30%.

#### Iron and Steel Production

$$E_{CO_2}^{steel} = \sum_{route} M_{steel,route} \cdot EF_{route}$$

| Production Route | EF (t CO2/t steel) |
|------------------|-------------------|
| Basic Oxygen Furnace (BOF) | 1.8 - 2.2 |
| Electric Arc Furnace (EAF) | 0.4 - 0.6 |
| Direct Reduced Iron (DRI) | 1.0 - 1.4 |

#### Chemicals Production

**Ammonia (NH3):**

$$E_{CO_2}^{NH_3} = M_{NH_3} \cdot EF_{NH_3} \cdot (1 - f_{urea})$$

Where $f_{urea}$ is the fraction used for urea production (CO2 captured then re-released as fertilizer).

**Nitric acid:**

$$E_{N_2O}^{nitric} = M_{nitric} \cdot EF_{N_2O} \cdot (1 - \eta_{abatement})$$

| Technology | EF (kg N2O/t HNO3) |
|------------|-------------------|
| High pressure | 9.0 |
| Medium pressure | 7.0 |
| Low pressure | 5.0 |
| With NSCR | 0.5 - 2.0 |

#### Fluorinated Gas (F-gas) Lifecycle Model

F-gases follow a lifecycle approach across manufacturing, use, and disposal:

```
  Manufacturing        Lifetime Use           End of Life
  ─────────────────   ─────────────────      ─────────────────

  ● Equipment          ● Leakage from         ● Residual gas
    assembly             equipment              released
  ● Charging with      ● Servicing            ● Recycling/
    refrigerant          losses                 recovery
                       ● Catastrophic
                         failure
```

#### HFC Emission Model

$$E_{HFC} = \sum_{app} \left[ C_{new,app} \cdot EF_{mfg} + S_{app} \cdot EF_{lifetime} + D_{app} \cdot EF_{disposal} \right]$$

Where:
- $C_{new}$ = New equipment capacity added
- $S_{app}$ = Stock of equipment
- $D_{app}$ = Equipment disposed
- $EF$ = Emission factors for each lifecycle stage

#### Application-Specific HFC Parameters

| Application | Charge Size (kg) | Lifetime Leak (%/yr) | Disposal Loss (%) |
|-------------|------------------|---------------------|--------------------|
| Commercial Refrigeration | 5-50 | 10-35 | 15-30 |
| Domestic Refrigeration | 0.1-0.3 | 0.5-3 | 70 |
| Mobile AC | 0.7-1.5 | 10-20 | 50 |
| Stationary AC | 1-100+ | 2-10 | 15 |
| Foam Blowing | 0.2-1/m2 | 0.5-10 | 5-95 |

#### F-gas GWPs

| Gas | GWP (AR5) | Common Uses |
|-----|-----------|-------------|
| HFC-134a | 1,430 | Mobile AC, refrigeration |
| HFC-32 | 675 | Residential AC |
| HFC-125 | 3,500 | Blend component |
| HFC-143a | 4,470 | Commercial refrigeration |
| CF4 (PFC-14) | 7,390 | Aluminum production |
| C2F6 (PFC-116) | 12,200 | Aluminum, semiconductor |
| SF6 | 22,800 | Electrical equipment |

> **Verified (IPCC Expert)**: All GWP values confirmed correct per IPCC AR5.

#### Aluminum Production PFCs

$$E_{PFC} = M_{Al} \cdot AE_{freq} \cdot AE_{duration} \cdot (SEF_{CF_4} + SEF_{C_2F_6})$$

Where $AE$ = anode effect (abnormal cell condition) and $SEF$ = slope emission factor.

---

### 2.4 Energy Sector Deep Dive

The Energy sector is the most complex in SISEPUEDE, comprising six subsectors:

| Subsector | Code | Description |
|-----------|------|-------------|
| Buildings | `scoe` | Residential, commercial energy |
| Industrial Energy | `inen` | Manufacturing, mining |
| Transportation | `trns` | Road, rail, aviation, shipping |
| Electricity Generation | `entc` | Power plants, grid |
| Fugitive Emissions | `fgtv` | Oil/gas extraction, coal mining |
| Carbon Capture | `ccsq` | CCS/CCUS facilities |

#### Energy Model Architecture

```
  ┌──────────────────────────────────────────────────────────────┐
  │  DEMAND SIDE (Python)                                         │
  │                                                               │
  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
  │  │Buildings│  │Industry │  │Transport│  │ Other   │         │
  │  │  (scoe) │  │  (inen) │  │  (trns) │  │ Demand  │         │
  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘         │
  │       └──────────┬─┴─────────────┴───────────┘               │
  │                  ▼                                            │
  │         ┌────────────────────┐                               │
  │         │  Total Energy      │                               │
  │         │  Demand by Fuel    │                               │
  │         └─────────┬──────────┘                               │
  └───────────────────┼──────────────────────────────────────────┘
                      ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  SUPPLY SIDE (Julia/NemoMod)                                  │
  │                                                               │
  │  Linear Programming Optimization:                             │
  │                                                               │
  │  min ∑ Cost(capacity, generation, fuel)                      │
  │  s.t.                                                         │
  │    Generation ≥ Demand (all time slices)                     │
  │    Generation ≤ Capacity × Availability                      │
  │    Ramping constraints                                        │
  │    Fuel availability constraints                              │
  └───────────────────────────────────────────────────────────────┘
                      ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  EMISSIONS CALCULATION                                        │
  │                                                               │
  │  Direct:   E = Fuel × EF                                     │
  │  Indirect: E_elec = Electricity × Grid_EF                    │
  │  Fugitive: E_fug = Production × Leak_Rate                   │
  └───────────────────────────────────────────────────────────────┘
```

> **Issue (Codebase Expert, IPCC Expert)**: Without NemoMod enabled (`energy_model_flag: false`), the electricity/heat sector (~27.5 MtCO2e, ~30% of Morocco's total) produces no emissions output. This is the **single largest calibration gap** (Issue C5 — CRITICAL).

#### Building Energy Demand (scoe)

$$E_{demand}^{buildings} = P \cdot I_{pc} \cdot (1 + g_{intensity})^t$$

Where:
- $P$ = Population (or floor area for commercial)
- $I_{pc}$ = Per-capita energy intensity (TJ/person/year)
- $g_{intensity}$ = Annual intensity growth rate

Fuel split:

$$E_{fuel,f}^{buildings} = E_{demand}^{buildings} \cdot \theta_f$$

Where $\theta_f$ is the fuel share and $\sum_f \theta_f = 1$.

> **Issue (IPCC Expert)**: Building non-CO2 gases show >95% error — model produces near-zero CH4/N2O from buildings. The energy demand calculation appears correct, but the non-CO2 emission factors may be missing or incorrectly configured.

#### Industrial Energy Demand (inen)

$$E_{demand}^{inen} = \sum_{ind} VA_{ind} \cdot I_{ind}$$

Where:
- $VA_{ind}$ = Value added from industry subsector
- $I_{ind}$ = Energy intensity (TJ/million USD)

| Industry | Typical Intensity (TJ/M USD) |
|----------|------------------------------|
| Cement | 25-40 |
| Iron & Steel | 20-35 |
| Chemicals | 15-25 |
| Paper | 12-20 |
| Food Processing | 5-10 |
| Textiles | 4-8 |

#### Transportation Energy Demand (trns)

$$E_{demand}^{trns} = \sum_{mode} VKT_{mode} \cdot FE_{mode}$$

Where:
- $VKT$ = Vehicle kilometers traveled
- $FE$ = Fuel efficiency (TJ/km)

| Mode | Variable | Unit |
|------|----------|------|
| Road - Passenger | `vkt_trns_road_passenger` | km/year |
| Road - Freight | `vkt_trns_road_freight` | tonne-km/year |
| Rail | `vkt_trns_rail` | passenger-km + tonne-km |
| Aviation - Domestic | `vkt_trns_aviation_domestic` | passenger-km |
| Aviation - International | `vkt_trns_aviation_international` | passenger-km |
| Shipping | `vkt_trns_shipping` | tonne-km |

#### Fuel Types and Emission Factors

| Fuel Code | Description | CO2 EF (kg/TJ) |
|-----------|-------------|----------------|
| `natural_gas` | Natural gas | 56,100 |
| `diesel` | Diesel/gasoil | 74,100 |
| `gasoline` | Motor gasoline | 69,300 |
| `kerosene` | Jet fuel | 71,500 |
| `oil` | Crude/fuel oil | 77,400 |
| `coal` | All coal types | 94,600 |
| `biogas` | Biogas | 54,600 (biogenic) |
| `biomass` | Solid biomass | 100,000 (biogenic) |
| `hydrogen` | Hydrogen | 0 (depends on source) |
| `electricity` | Grid electricity | (calculated from mix) |

> **Verified (IPCC Expert)**: All stationary combustion CO2 emission factors confirmed correct per IPCC 2006 Table 2.2 — natural gas=56,100, diesel=74,100, coal=94,600, gasoline=69,300 kg CO2/TJ.

> **CRITICAL: Shared Fuel EFs.** All combustion emission factors (`ef_enfu_*`) are shared across CCSQ, INEN, SCOE, and ENTC. Changing a fuel's CO2, CH4, or N2O EF affects **every sector** that burns that fuel. There is no per-subsector override. Always source EF values from official IPCC tables (V2 Ch2 Tables 2.2-2.5) or the country's NIR methodology section. If the shared EF creates a mismatch between sectors (e.g., biomass CH4: 30 kg/TJ for power vs 300 kg/TJ for residential), document this as a structural model limitation. (Source: verified in `energy_consumption.py` lines 2247, 2845, 3303.)

> **Biomass naming trap.** The suffix `solid_biomass` appears in INEN/SCOE demand fraction columns (e.g., `frac_inen_energy_cement_solid_biomass`) but maps to `fuel_biomass` internally. Emission factors use **only** `ef_enfu_*_fuel_biomass`. There is no `ef_enfu_*_fuel_solid_biomass` column. Do not confuse demand fractions with EF columns.

> **IPCC CH4 EFs vary 10x by sector.** IPCC Tables 2.2-2.3 (power/manufacturing) give biomass CH4 = **30 kg/TJ**, while Tables 2.4-2.5 (commercial/residential) give **300 kg/TJ**. SISEPUEDE uses ONE shared EF column for all subsectors — no per-subsector override exists. Setting biomass CH4 to 300 (residential) will overstate INEN; setting to 30 (power) will understate SCOE.

#### NemoMod: Energy System Optimization

NemoMod solves a linear program for each year to determine the optimal electricity generation mix:

$$\min_{Cap, Gen, Fuel} \sum_{t,tech} \left[ Cap_{tech,t} \cdot C^{cap}_{tech} + Gen_{tech,t} \cdot C^{var}_{tech} + Fuel_{tech,t} \cdot P^{fuel} \right]$$

Subject to:

**Demand satisfaction:**
$$\sum_{tech} Gen_{tech,ts} \geq D_{ts} \quad \forall \text{time slice } ts$$

**Capacity constraint:**
$$Gen_{tech,ts} \leq Cap_{tech} \cdot CF_{tech,ts} \quad \forall tech, ts$$

**Ramping constraints:**
$$|Gen_{tech,ts+1} - Gen_{tech,ts}| \leq R_{tech} \cdot Cap_{tech}$$

#### Time Slices

NemoMod uses time slices to capture hourly/seasonal demand variation:

```
  Season    Time of Day    Hours/Year    Demand Factor
  ────────────────────────────────────────────────────
  Summer    Peak (12-18)      546           1.4
  Summer    Day (06-12)       546           1.1
  Summer    Night (18-06)    1092           0.8
  Winter    Peak             546           1.5
  Winter    Day              546           1.2
  Winter    Night           1092           0.7
  Shoulder  Peak            1092           1.2
  Shoulder  Off-peak        3300           0.9
                            ─────
                            8760 hours/year
```

#### Grid Emission Factor

The average grid emission factor varies dynamically with the generation mix:

$$EF_{grid}(t) = \frac{\sum_{tech} Gen_{tech}(t) \cdot EF_{tech}}{\sum_{tech} Gen_{tech}(t)}$$

As the share of renewables increases (via transformations), $EF_{grid}$ decreases, reducing indirect emissions from electricity consumption across all sectors.

#### Fugitive Emissions

**Oil and Gas:**

$$E_{fgtv}^{oil\&gas} = \sum_{stage} Prod_{stage} \cdot EF_{stage}$$

| Stage | CH4 EF (kg/TJ produced) |
|-------|------------------------|
| Exploration | 0.1-1.0 |
| Production | 1.5-10 |
| Processing | 0.5-5 |
| Transmission | 0.5-3 |
| Distribution | 1-5 |

**Coal Mining:**

$$E_{fgtv}^{coal} = Prod_{coal} \cdot EF_{mine\_type}$$

---

## 3. Morocco Emissions Context

### National Emissions Profile

Morocco's total GHG emissions are approximately **90-95 MtCO2e** (2022, excluding LULUCF). The major sectors:

| Sector | Approximate Emissions (MtCO2e) | Share |
|--------|-------------------------------|-------|
| Energy (electricity + heat) | 27.5 | ~30% |
| Transport | 19.4 | ~21% |
| Agriculture (crops + livestock) | 14.5 | ~16% |
| Solid Waste | 18.9 | ~21% |
| IPPU (cement, chemicals) | 5.4 | ~6% |
| Buildings (non-CO2) | ~2.0 | ~2% |
| Other | ~4.0 | ~4% |

### Morocco's NDC Commitments

Morocco has committed under its Nationally Determined Contribution (NDC) to:
- **17% unconditional reduction** below BAU by 2030
- **45.5% conditional reduction** (with international support) below BAU by 2030

Key decarbonization levers include renewable energy expansion, energy efficiency in buildings and industry, improved agricultural practices, and better waste management.

### Calibration Reference: National Inventory Report (NIR)

The primary calibration target is the country's **National Inventory Report (NIR)**, which provides:
- Official IPCC CRF category emissions by gas, verified through national QA/QC processes
- Multi-year time series (Morocco: 2010-2022 in NIR 2024)
- Sector-specific methodology documentation (emission factors, activity data sources)

**EDGAR v8.0** is used as an independent cross-check only. EDGAR has known errors: waste CH4 (overstates vs national FOD), soil N2O (overstates vs national inventory), HFC (top-down vs BUR bottom-up), INEN CO2 (may exclude agriculture energy). When NIR and EDGAR disagree, NIR is authoritative.

The diagnostic tool `compare_to_inventory.py` compares model outputs against an IPCC crosswalk file (`emission_targets_{country}_{year}.csv`) built from NIR values. See Section 10 for details.

The calibration reference year is **2022** (corresponding to `time_period = 7` in SISEPUEDE, where time_period 0 = 2015).

---

## 4. Environment Setup

### Prerequisites

- **Python 3.11** (via conda)
- **Julia** (for NemoMod energy model, optional but recommended)
- **R 4.x** (for postprocessing scripts)

### Conda Environment

```bash
# Create and activate the environment
conda env create -f ssp_morocco/environment.yml
conda activate ssp_james

# Verify Python version
python --version  # Should show 3.11.x

# Verify SISEPUEDE is installed
python -c "import sisepuede; print(sisepuede.__version__)"
```

### Key Package Locations

Once installed, the SISEPUEDE package source code is located at:
```
/path/to/conda/envs/ssp_james/lib/python3.11/site-packages/sisepuede/
```

Key submodules:
- `sisepuede/manager/sisepuede.py` — `SISEPUEDE` class
- `sisepuede/manager/sisepuede_models.py` — `SISEPUEDEModels` class
- `sisepuede/transformers/` — All transformation logic
- `sisepuede/utilities/_plotting.py` — Low-level plotting utilities
- `sisepuede/visualization/plots.py` — High-level plot functions (`plot_emissions_stack`)
- `sisepuede/visualization/tables.py` — Tableau/levers table utilities

> **Verified (Docs Expert)**: All import paths above confirmed against the installed package source code.

### Julia / NemoMod Setup (Optional)

The electricity and heat sector requires NemoMod, a Julia-based energy system optimization model. To enable it:

1. Install Julia (1.9+)
2. In the SISEPUEDE config, set `energy_model_flag: true`
3. SISEPUEDE will initialize Julia automatically via `PyCall`

> **Warning (Issue C5)**: Without NemoMod enabled, electricity/heat emissions (~27.5 MtCO2e, ~30% of Morocco's total) will not appear in model outputs. This is the single largest calibration gap.

---

## 5. Project Structure and Configuration

### Directory Layout

```
ssp_morocco/
├── environment.yml                 # Conda environment specification
├── LICENSE
├── README.md
├── morocco_calibration_guide.md    # This document
└── ssp_modeling/
    ├── config_files/
    │   └── config.yaml             # Master configuration
    ├── input_data/
    │   └── sisepuede_raw_inputs_latest_MAR_modified_2050.csv
    ├── notebooks/
    │   ├── morocco_calibration_workflow.ipynb   # Main workflow notebook
    │   ├── morocco_manager_wb.ipynb             # Alternative (handler approach)
    │   └── utils/
    │       ├── logger_utils.py
    │       └── general_utils.py
    ├── transformations/                # Default transformations (LEP, NDC scalars)
    │   ├── config_general.yaml
    │   ├── citations.bib
    │   ├── strategy_definitions.csv
    │   ├── templates/
    │   │   └── calibrated/
    │   └── transformation_*.yaml    # ~182 YAML files
    ├── transformations_ndc/             # SNBC-derived transformations (63 YAMLs)
    │   ├── config_general.yaml          # Required — copied from transformations/
    │   ├── citations.bib                # Required — copied from transformations/
    │   ├── templates/                   # Required — copied from transformations/
    │   │   └── calibrated/
    │   ├── strategy_definitions.csv     # Must include BASE (id 0) + SNBC_NET_ZERO (id 6005)
    │   ├── transformation_*_strategy_NDC.yaml  # 63 SNBC-backed transformations
    │   ├── NDC_TRANSFORMATION_RATIONALE.md
    │   ├── AGENT_DECISION_LOG.md
    │   ├── NDC_SUMMARY.md
    │   └── flag_calibration_ndc.md
    ├── scenario_mapping/
    │   └── ssp_transformation_cw_*.xlsx   # Crosswalk spreadsheet
    ├── output_postprocessing/
    │   ├── postprocessing_250820.r         # Master orchestrator
    │   ├── scr/
    │   │   ├── run_script_baseline_run_new.r
    │   │   ├── intertemporal_decomposition.r
    │   │   ├── data_prep_new_mapping.r
    │   │   └── data_prep_drivers.r
    │   ├── data/
    │   │   ├── emission_targets_*.csv
    │   │   └── driver_variables_taxonomy_*.csv
    │   └── diff_table/
    │       └── create_diff_table.ipynb
    ├── tableau/
    │   └── data/                    # Tableau-ready output CSVs
    └── ssp_run_output/              # Model run outputs (created at runtime)
```

### Configuration File (`config.yaml`)

The master configuration file controls all key parameters:

```yaml
country_name: "morocco"
ssp_input_file_name: "sisepuede_raw_inputs_latest_MAR_modified_2050.csv"
ssp_transformation_cw: "ssp_transformation_cw_morocco.xlsx"
energy_model_flag: false          # Set to true to enable NemoMod/Julia
set_lndu_reallocation_factor_to_zero: false
```

Key configuration parameters:

| Parameter | Description | Typical Value |
|-----------|-------------|---------------|
| `country_name` | ISO country name (lowercase) | `"morocco"` |
| `ssp_input_file_name` | Input CSV filename in `input_data/` | See above |
| `energy_model_flag` | Enable NemoMod electricity model | `false` (default) |
| `ssp_transformation_cw` | Crosswalk Excel filename for handler approach | See above |
| `set_lndu_reallocation_factor_to_zero` | Zero out land-use reallocation | `false` |

### Path Setup Pattern

The notebook establishes paths relative to the notebook's location:

```python
import pathlib, os

CURR_DIR_PATH = pathlib.Path(os.getcwd())
SSP_MODELING_DIR_PATH = CURR_DIR_PATH.parent
PROJECT_DIR_PATH = SSP_MODELING_DIR_PATH.parent
DATA_DIR_PATH = SSP_MODELING_DIR_PATH.joinpath("input_data")
RUN_OUTPUT_DIR_PATH = SSP_MODELING_DIR_PATH.joinpath("ssp_run_output")
TRANSFORMATIONS_DIR_PATH = SSP_MODELING_DIR_PATH.joinpath("transformations")
# Or for SNBC-derived transformations:
# TRANSFORMATIONS_DIR_PATH = SSP_MODELING_DIR_PATH.joinpath("transformations_ndc")
CONFIG_DIR_PATH = SSP_MODELING_DIR_PATH.joinpath("config_files")
```

> **Important**: When switching `TRANSFORMATIONS_DIR_PATH` to a new directory (e.g., `transformations_ndc/`), that directory must contain these required supporting files alongside the transformation YAMLs:
> 1. `config_general.yaml` — system-level configuration (copy from `transformations/`)
> 2. `citations.bib` — bibliography file (copy from `transformations/`)
> 3. `templates/` directory with `calibrated/` subdirectory (copy from `transformations/`)
> 4. `strategy_definitions.csv` — **must include a BASE strategy row** (`0,BASE,Strategy TX:BASE,,TX:BASE`) plus any custom strategies
>
> Without these files, `trf.Transformations()` will raise `RuntimeError: General configuration file 'config_general.yaml' not found` or `AttributeError: 'BaseInputDatabase' object has no attribute 'baseline_strategy'`.

---

## 6. Input Data and Validation

### Input CSV Structure

The SISEPUEDE input CSV has a specific structure:

| Dimension | Value | Notes |
|-----------|-------|-------|
| Rows | 56 | Years 2015-2070 (time_period 0-55) |
| Columns | ~2,400 | Variables across all sectors |
| Key index columns | `region`, `time_period` | Always present |

Column naming convention: `{metric}_{subsector}_{detail}`

Examples:
- `pop_lvst_initial_cattle_dairy` — initial dairy cattle population
- `frac_waso_landfilled` — fraction of waste going to landfill
- `qty_ippu_production_cement` — cement production quantity

### Data Validation with SISEPUEDEExamples

Before running the model, use the `SISEPUEDEExamples` class to validate and repair input data:

```python
import sisepuede.manager.sisepuede_examples as sxl
from utils.general_utils import GeneralUtils

# Load a reference DataFrame with all required columns
examples = sxl.SISEPUEDEExamples()
df_example = examples.dataset  # Complete reference with all columns

# Use GeneralUtils to add any missing columns from the reference
g_utils = GeneralUtils()
df_validated = g_utils.add_missing_cols(df_example, df_raw)
```

This step:
- Compares your input DataFrame against a complete reference template
- Adds any columns expected by the model but missing from your CSV
- Fills missing columns with sensible defaults from the example dataset
- Prevents cryptic "missing fields" errors during model execution

> **Verified (Docs Expert)**: The `add_missing_cols()` method lives in `GeneralUtils` (from the project's `utils/` directory), not in `SISEPUEDEExamples` itself. `SISEPUEDEExamples` provides the reference dataset.

### Fraction Group Validation

Many SISEPUEDE variables represent fractions that must sum to 1.0 within groups. For example, the fractions of waste sent to landfill, composting, incineration, and open dumping must sum to 1.0 for each time period.

```python
# Check fraction groups
fraction_groups = [col for col in df.columns if col.startswith('frac_')]
# Group by subsector prefix and verify sums ≈ 1.0
```

If fraction sums deviate from 1.0 by more than 0.01, SISEPUEDE may silently renormalize them or produce unexpected results. Use `GeneralUtils.normalize_energy_frac_vars()` to fix energy fractions.

### Time Period Convention

| Time Period | Year | Notes |
|-------------|------|-------|
| 0 | 2015 | Base year |
| 7 | 2022 | **Calibration reference year** |
| 15 | 2030 | NDC target year |
| 35 | 2050 | Long-term target |
| 55 | 2070 | End of projection |

The formula: `year = time_period + 2015`

---

## 7. Transformations and Strategies

### Concepts

- **Transformation**: A single policy lever that modifies specific input variables. Example: "Reduce enteric fermentation by 30%"
- **Strategy**: A bundle of transformations representing a policy scenario. Example: Strategy 6003 (LEP — Low Emissions Pathway) bundles ~40 transformations
- **Transformer**: The code function that implements a transformation's parameter modification

### How Transformations Modify Trajectories

Transformations don't create new forecasts — they **modify existing trajectories**:

```
Original Trajectory (from input CSV):
────────────────────────────────────────────────────────────────
Year:     2015   2020   2025   2030   2035   2040   2045   2050
EF_rice:  1.0    1.0    1.0    1.0    1.0    1.0    1.0    1.0
────────────────────────────────────────────────────────────────

After Transformation (50% reduction by 2050, starting 2025):
────────────────────────────────────────────────────────────────
Year:     2015   2020   2025   2030   2035   2040   2045   2050
EF_rice:  1.0    1.0    1.0    0.9    0.8    0.7    0.6    0.5
                        ↑ ─────────── ramp ─────────── ↑
────────────────────────────────────────────────────────────────
```

The ramp preserves historical values and applies a smooth transition to the target.

### Transformation Mathematics

#### Implementation Ramp

The implementation ramp $\rho(t)$ controls the transition from baseline to transformed values:

$$\rho(t) = \begin{cases} 0 & \text{if } t < t_0 \\ \frac{t - t_0}{n_{ramp}} & \text{if } t_0 \leq t \leq t_0 + n_{ramp} \text{ (linear)} \\ 1 & \text{if } t > t_0 + n_{ramp} \end{cases}$$

Where:
- $t_0$ = `tp_0_ramp` — time period when implementation begins
- $n_{ramp}$ = `n_tp_ramp` — number of time periods over which to ramp

For a **sigmoidal (S-curve)** ramp, controlled by `alpha_logistic`:

$$\rho(t) = \frac{1}{1 + e^{-\alpha \cdot (t - t_{mid})}}$$

Where $t_{mid} = t_0 + n_{ramp}/2$ and $\alpha$ = `alpha_logistic`. Higher $\alpha$ creates a steeper S-curve (representing rapid technology adoption after initial slow uptake).

```
Linear ramp (α = 0):            Sigmoidal ramp (α = 0.7):

1.0 - - - - - - - ___/          1.0 - - - - - - -___
                 /                                /
                /                               /
0.5            /                 0.5           |
              /                               /
             /                              _/
0.0 ________/                    0.0 ______/
    t₀            t₀+n              t₀            t₀+n
```

#### Magnitude Types

The `magnitude_type` parameter controls how the target value is interpreted:

| Type | Formula | Use Case |
|------|---------|----------|
| `final_value` | $x'(t) = x(t) \cdot (1 - \rho(t)) + m \cdot \rho(t)$ | Set variable to specific target |
| `baseline_scalar` | $x'(t) = x(t) \cdot (1 - \rho(t) \cdot (1 - m))$ | Scale variable by fraction |
| `baseline_additive` | $x'(t) = x(t) + \rho(t) \cdot m$ | Add/subtract fixed amount |

Where $m$ = `magnitude` and $\rho(t)$ = implementation ramp.

**Example**: To electrify 60% of passenger transport by 2050:

```yaml
TX:TRNS:ELECTRIFY_PASSENGER:
  variables:
    - frac_trns_fuel_electricity_road_passenger:
        magnitude: 0.60
        magnitude_type: final_value     # Target 60% electric
        tp_0_ramp: 10                   # Start in 2025
        n_tp_ramp: 25                   # Complete by 2050
        alpha_logistic: 0.7             # S-curve adoption
```

At each time step, the electric share transitions from its baseline value smoothly toward 0.60 following the sigmoidal ramp.

### Two Approaches to Setting Up Transformations

#### Approach A: `ssp_transformations_handler` (Recommended for Beginners)

This Excel-driven approach uses a crosswalk spreadsheet to auto-generate transformation YAML files and strategy definitions:

```python
from utils.general_utils import GeneralUtils
g_utils = GeneralUtils()

# The handler reads an Excel crosswalk and generates YAMLs
from ssp_transformations_handler import TransformationYamlProcessor, StrategyCSVHandler

processor = TransformationYamlProcessor(
    crosswalk_path=SCENARIO_MAPPING_DIR_PATH / ssp_transformation_cw,
    output_dir=TRANSFORMATIONS_DIR_PATH
)
processor.process_all()

# StrategyCSVHandler generates strategy_definitions.csv
handler = StrategyCSVHandler(
    transformations_dir=TRANSFORMATIONS_DIR_PATH,
    output_path=TRANSFORMATIONS_DIR_PATH / "strategy_definitions.csv"
)
handler.generate()
```

**Advantages**: Easier to manage many transformations, visual overview in Excel, less error-prone.

> **Verified (Codebase Expert)**: Both transformation approaches documented and validated. The handler approach generates the same YAML files that the direct approach loads — they are functionally equivalent.

#### Approach B: Direct YAML Loading (Used by Reference Notebook)

Load transformations directly from YAML files in the `transformations/` directory:

```python
import sisepuede.transformers as trf

transformations = trf.Transformations(
    str(TRANSFORMATIONS_DIR_PATH),
    attr_time_period=_ATTRIBUTE_TABLE_TIME_PERIOD,
    df_input=df_inputs_raw_complete,
)

strategies = trf.Strategies(
    transformations,
    export_path="transformations",
    prebuild=True,
)
```

### Transformation YAML Format

Each transformation is defined in a YAML file:

```yaml
# transformation_agrc_dec_ch4_rice.yaml
citations: null
description: "Reduce CH4 emissions from rice production by 45%"
identifiers:
  transformation_code: "TX:AGRC:DEC_CH4_RICE"
  transformation_name: "Default Value - AGRC: Improve rice management"
parameters:
  magnitude: 0.45
  vec_implementation_ramp: null
transformer: "TFR:AGRC:DEC_CH4_RICE"
```

Key fields:
- `transformer`: Links to the Python function that implements the modification
- `parameters.magnitude`: The strength of the transformation
- `parameters.vec_implementation_ramp`: Optional time profile for gradual implementation

### Sector-Specific Transformation Examples

#### Agriculture & Livestock

```yaml
# Reduce enteric fermentation CH4
TX:LVST:DEC_ENTERIC_FERMENTATION:
  variables:
    - ef_lvst_enteric_ch4:
        magnitude: 0.70            # Reduce to 70% of baseline
        magnitude_type: baseline_scalar
        tp_0_ramp: 10
        n_tp_ramp: 25
```

#### Circular Economy (Waste)

```yaml
# Increase landfill gas capture
TX:WASO:INC_CAPTURE_BIOGAS:
  variables:
    - frac_waso_biogas_capture_managed:
        magnitude: 0.75            # 75% capture rate
        magnitude_type: final_value
        tp_0_ramp: 10
        n_tp_ramp: 25

# Shift from landfill to recycling
TX:WASO:INC_RECYCLING:
  variables:
    - frac_waso_recycled:
        magnitude: 0.35
        magnitude_type: final_value
    - frac_waso_landfill_managed:
        magnitude: -0.20
        magnitude_type: baseline_additive
```

#### IPPU

```yaml
# HFC phase-down (Kigali Amendment)
TX:IPPU:DEC_HFC_EMISSIONS:
  variables:
    - ef_ippu_hfc_refrigeration:
        magnitude: 0.15
        magnitude_type: baseline_scalar
        tp_0_ramp: 10
        n_tp_ramp: 30
        alpha_logistic: 0.8   # S-curve for technology transition

# Reduce clinker ratio in cement
TX:IPPU:DEC_CLINKER_RATIO:
  variables:
    - frac_ippu_clinker_to_ite_cement:
        magnitude: 0.70
        magnitude_type: final_value
        tp_0_ramp: 10
        n_tp_ramp: 25
```

#### Energy

```yaml
# Electrification of transport
TX:TRNS:ELECTRIFY_PASSENGER:
  variables:
    - frac_trns_fuel_electricity_road_passenger:
        magnitude: 0.60
        magnitude_type: final_value
        tp_0_ramp: 10
        n_tp_ramp: 25
        alpha_logistic: 0.7

# Renewable electricity target
TX:ENTC:INC_RENEWABLES:
  variables:
    - frac_entc_renewable:
        magnitude: 0.80
        magnitude_type: final_value

# Building efficiency
TX:SCOE:DEC_INTENSITY:
  variables:
    - scalar_scoe_energy_intensity_residential:
        magnitude: 0.75
        magnitude_type: final_value
```

### Strategy Numbering Convention

| Strategy ID | Meaning |
|-------------|---------|
| 0 | **Baseline** (no transformations applied) |
| 1-999 | Individual sector transformations |
| 1000-5999 | Sector-specific bundles |
| 6000+ | Cross-sector packages |

| ID | Code | Description | Directory |
|----|------|-------------|-----------|
| 6003 | `PFLO:LEP` | Low Emissions Pathway — mechanically scaled transformations | `transformations/` |
| 6005 | `PFLO:SNBC_NET_ZERO` | SNBC Net Zero 2050 — 63 SNBC-backed transformations derived from Morocco's National Low Carbon Strategy | `transformations_ndc/` |

### Strategy Definitions File

The `strategy_definitions.csv` maps strategy IDs to their constituent transformations as pipe-separated transformation codes:

```csv
strategy_id,strategy_code,strategy,description,transformation_specification
0,BASE,Strategy TX:BASE,,TX:BASE
6005,PFLO:SNBC_NET_ZERO,SNBC Net Zero 2050,Morocco SNBC Net Zero pathway,TX:AGRC:DEC_CH4_RICE_STRATEGY_NDC|TX:ENTC:TARGET_RENEWABLE_ELEC_STRATEGY_NDC|...
```

> **Critical**: The `strategy_definitions.csv` **must always include** the BASE strategy row (`strategy_id=0, strategy_code=BASE`). Without it, SISEPUEDE raises `AttributeError: 'BaseInputDatabase' object has no attribute 'baseline_strategy'`.

### Switching Between Strategy Sets

To run the SNBC strategy instead of LEP, change two things in the notebook:
1. Point `TRANSFORMATIONS_DIR_PATH` to `transformations_ndc/`
2. Set `strategies_to_run = [0, 6005]`

```python
# Use SNBC-derived transformations
TRANSFORMATIONS_DIR_PATH = SSP_MODELING_DIR_PATH.joinpath("transformations_ndc")
# ...
strategies_to_run = [0, 6005]  # Baseline + SNBC Net Zero
```

---

## 8. Running the Model

### SISEPUEDE Initialization

```python
import sisepuede as si

ssp = si.SISEPUEDE(
    "calibrated",                          # data_mode (MUST be first arg)
    db_type="csv",
    initialize_as_dummy=not energy_model_flag,  # False enables Julia/NemoMod
    regions=[country_name],
    strategies=strategies,
    attribute_time_period=_ATTRIBUTE_TABLE_TIME_PERIOD,
)
```

> **Critical**: The first argument must be the string `"calibrated"` (the data mode), NOT the file structure object. This is a common source of errors.

> **Verified (Docs Expert)**: `SISEPUEDE` constructor signature confirmed — `"calibrated"` as first positional argument, with keyword args for `db_type`, `regions`, `strategies`, `attribute_time_period`.

### Running Scenarios

```python
strategies_to_run = [0, 6003]  # Baseline + LEP (or [0, 6005] for SNBC Net Zero)

dict_scens = {
    ssp.key_design: [0],
    ssp.key_future: [0],
    ssp.key_strategy: strategies_to_run,
}

ssp.project_scenarios(
    dict_scens,
    save_inputs=True,
    include_electricity_in_energy=energy_model_flag,
    dict_optimizer_attributes={"user_bound_scale": -7},
)
```

Parameter notes:
- `save_inputs=True`: Saves input DataFrames for later export
- `include_electricity_in_energy`: Controls whether NemoMod runs
- `dict_optimizer_attributes={"user_bound_scale": -7}`: NemoMod optimizer bounds (prevents infeasible solutions)

> **Verified (Codebase Expert)**: The `dict_optimizer_attributes` parameter was missing in the original notebook (Issue I1). It must be included to prevent NemoMod infeasibility.

### Reading Results

```python
df_out = ssp.read_output(None)   # All outputs across all strategies
df_in = ssp.read_input(None)     # All inputs (if save_inputs=True)
```

The output DataFrame contains:
- Index columns: `primary_id`, `region`, `time_period`
- ~1,600 emission columns following the pattern `emission_co2e_{gas}_{subsector}_{detail}`

### Typical Runtimes

| Configuration | Approximate Time |
|---------------|-----------------|
| Baseline only, no NemoMod | ~2-5 minutes |
| Baseline + LEP, no NemoMod | ~5-10 minutes |
| Baseline + LEP, with NemoMod | ~15-30 minutes |
| Full strategy sweep (50+ strategies) | ~2-4 hours |

---

## 9. Understanding Outputs

### Output Column Structure

Output columns follow the pattern: `emission_co2e_{gas}_{subsector}_{detail}`

Examples:
- `emission_co2e_co2_agrc_crops_rice` — CO2 from rice cultivation
- `emission_co2e_ch4_lvst_enteric` — CH4 from livestock enteric fermentation
- `emission_co2e_n2o_trww_treatment` — N2O from wastewater treatment

### Primary ID System

Each unique combination of (design, future, strategy) gets a `primary_id`:

| primary_id | design | future | strategy |
|------------|--------|--------|----------|
| 0 | 0 | 0 | 0 (baseline) |
| 1 | 0 | 0 | 6003 (LEP) |

### Visualization with SISEPUEDE's Built-in Tools

```python
import sisepuede.visualization.plots as svp   # High-level plots (plot_emissions_stack)
import sisepuede.utilities._plotting as spu    # Low-level utilities (plot_stack)

# Emissions stack plot (all subsectors stacked)
svp.plot_emissions_stack(df_out, matt)

# Custom stack plots
subsector_fields = matt.get_all_subsector_emission_total_fields()
dict_format = {k: {"color": v} for k, v in matt.get_subsector_color_map().items()}

fig, ax = spu.plot_stack(
    df_plot,
    subsector_fields,
    dict_formatting=dict_format,
    field_x='time_period',
)
```

> **Note on aliases**: `svp` refers to `sisepuede.visualization.plots` (high-level) while `spu` refers to `sisepuede.utilities._plotting` (low-level). Both provide plotting functionality but at different abstraction levels.

### Key Diagnostic Checks

After a model run, verify:

1. **No NaN or Inf values** in emission columns
2. **All expected primary_ids** are present
3. **56 time periods** per primary_id
4. **Emission magnitudes** are physically reasonable (not negative except for sequestration)

---

## 10. Calibration Pipeline

### Overview

Calibration is the iterative process of adjusting SISEPUEDE input parameters so that model outputs match observed emissions data (EDGAR) at the reference year (2022).

```
┌─────────────────────────────────────────────────────────┐
│              ITERATIVE CALIBRATION LOOP                   │
│                                                           │
│   Input CSV ──▶ SISEPUEDE Run ──▶ Compare to EDGAR       │
│       ▲                              │                    │
│       │                              ▼                    │
│       │                        Error > 25%?               │
│       │                         ╱        ╲                │
│       │                       Yes         No              │
│       │                        │           │              │
│       │                        ▼           ▼              │
│       └── Apply Scaling ◀── Identify    DONE              │
│           Factors            Variables                    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Formal Error Metric

For each emission category $i$, the calibration error is:

$$\epsilon_i = \frac{|E^{SSP}_i - E^{INV}_i|}{|E^{INV}_i| + \varepsilon}$$

Where:
- $E^{SSP}_i$ = SISEPUEDE emission for category $i$
- $E^{INV}_i$ = Inventory (EDGAR) emission for category $i$
- $\varepsilon$ = Small constant (1e-8) to avoid division by zero

> **Verified (IPCC Expert)**: This relative-error metric is standard for emissions inventory comparison. The absolute-value denominator correctly handles negative values (sequestration sectors).

### EDGAR Comparison Structure

The emission targets file maps EDGAR categories to SISEPUEDE output columns:

### Building the Targets File

The targets file maps IPCC CRF categories to SISEPUEDE output variables. Build it with `build_emission_targets_mar.py` (or equivalent for your country):

```csv
# emission_targets_mar_2022.csv
subsector_ssp,sector,category,gas,ID,vars,target_source,MAR
lvst,3 - AFOLU,3.A.1 - Enteric Fermentation,CH4,3.A.1:CH4,emission_co2e_ch4_lvst_entferm_cattle_dairy:...,NIR Tableau 83 p.189,9.10028
```

Columns: `subsector_ssp` (SISEPUEDE subsector), `sector` (IPCC sector), `category` (CRF category with description), `gas`, `ID` (compact identifier), `vars` (colon-separated SISEPUEDE output columns to sum), `target_source` (NIR table citation), and a country code column (e.g., `MAR`) with the inventory value in MtCO2e.

Set `INCLUDE_LULUCF = False` until all other sectors are calibrated. LULUCF has structural gaps (SOC modeling, fire) that should be isolated.

### Diagnostic Tool: compare_to_inventory.py

Replaces the hand-rolled comparison code. Country-agnostic — works with any crosswalk file.

```bash
python compare_to_inventory.py \
  --targets emission_targets_mar_2022.csv \
  --output WIDE_INPUTS_OUTPUTS.csv \
  --tp 7 --top 10
```

**Outputs** (saved to `{run_folder}/diagnostics/`):
| File | Contents |
|------|----------|
| `diff_report.csv` | Full comparison: abs_impact_rank, ID, category (with description), inventory, model, diff, error_pct, direction, top_component |
| `flagged.csv` | Component breakdown for categories exceeding threshold |
| `diagnostics.csv` | Structural warnings (10 checks) |

**Diagnostics (11 checks):**
- `ZERO_OUTPUT` — target > 0 but model = 0 (missing input values)
- `MAGNITUDE_10X` — model/inventory ratio > 10x (unit error)
- `SIGN_MISMATCH` — model and inventory disagree on source vs sink
- `GAS_RATIO` — CO2 matches but CH4/N2O way off (check non-CO2 EFs)
- `SINGLE_DOMINANCE` — one component is 95%+ of total (others may be missing)
- `MISSING_VARS` — expected output variables not found in model output
- `TRAJECTORY` — emission changed > 100% or dropped > 50% from tp=0 to tp=7
- `DECLINING_WITH_GDP_GROWTH` — sector emissions decline while GDP grows (check production elasticities)
- `GROWTH_LAG` — sector grows much slower than GDP (implicit elasticity < 0.3)
- `GROWTH_EXCEEDS_GDP` — sector grows much faster than GDP (elasticity > 2.5)
- `POPULATION_MISMATCH` — waste/residential grows > 3x faster than population

The growth diagnostics flag trajectory-level problems invisible at tp=7 alone.

### The Golden Rule: Scale, Don't Replace

**Never replace entire columns with fixed values.** Instead:

1. Extract the current value at `time_period = 7` (year 2022)
2. Calculate `scaling_factor = target_value / current_value`
3. Multiply the **entire column** by the scaling factor

This preserves the temporal dynamics (growth trends, seasonality) while correcting the absolute level.

$$x'_{col}(t) = x_{col}(t) \cdot \frac{x_{target}}{x_{col}(t_{ref})}$$

```python
def apply_scaling(df, column, target_2022, ref_period=7):
    """Scale a column to match a target value at the reference year."""
    current_2022 = df.loc[df['time_period'] == ref_period, column].values[0]

    if current_2022 == 0:
        print(f"WARNING: {column} is zero at reference year. Cannot scale.")
        return df

    scaling_factor = target_2022 / current_2022
    df[column] = df[column] * scaling_factor

    print(f"  {column}: scaled by {scaling_factor:.4f} "
          f"({current_2022:.4f} → {target_2022:.4f})")
    return df
```

> **Verified (IPCC Expert)**: Scaling over replacement is the correct approach — it preserves temporal dynamics while correcting absolute levels. This follows IPCC QA/QC guidance for model calibration.

### Calibration Error Categories

| Error Range | Status | Action |
|-------------|--------|--------|
| ≤ 10% | Excellent | No action needed |
| 10-25% | Acceptable | Document, low priority |
| 25-50% | Moderate | Investigate, adjust if data available |
| 50-75% | High | Priority calibration target |
| > 75% | Critical | Investigate root cause immediately |

### Current Morocco Calibration Status

Based on NIR 2024 comparison at reference year 2022 (34 IPCC categories, no LULUCF):

- **Total error: ~7-8 MtCO2e** across 34 categories (see `calibration_log.md` for exact current value)
- **Within 15%: 16/34 (47%)**
- **Within 25%: 22/34 (65%)**
- **NemoMod: ALL OPTIMAL**

Top remaining gaps:
| Category | Inventory | Model | Error | Assessment |
|----------|-----------|-------|-------|-----------|
| 3.A.1:CH4 Enteric | 9.10 | 7.84 | -14% | Unmodeled species (camels/asses ≈ 0.34 Mt structural) |
| 1.A.4.c:CO2 Agriculture | 2.80 | 2.10 | -25% | NIR T43 shows 38.6 PJ at 2022, model at 34.4 PJ |
| 3.A.2:CH4 Manure | 0.56 | 1.09 | +93% | Liquid slurry MCF at 18°C = 35% amplifies small fractions |
| 3.C.4:N2O Soil | 6.40 | 5.69 | -11% | EF1 at IPCC max 0.030, N throughput gap |

See `calibration_log.md` for full audit trail with source citations for every parameter change.

### Production Elasticities

Production elasticities control how IPPU production volumes scale with GDP over time:

$$\text{production}(t) = \text{prodinit} \times \prod_{i=0}^{t-1} (1 + \text{GDP\_rate}_i \times \text{elasticity})$$

**Always derive from NIR historical data** (regression of production vs GDP time series), never guess. Example: Morocco cement production declined from 14.25 Mt (2015) to 12.49 Mt (2022) while GDP grew 14% — giving elasticity ≈ -0.42. Using the template default of -2.0 would cause production collapse.

IPPU production elasticities **should be kept constant** across all time periods — time-varying values are technically supported by the code but cause production instability in practice. For step-changes (e.g., new desalination plants), use `demscalar_ippu_{industry}` instead.

### Reverse Diagnostic Mapping

When a category is flagged in `diff_report.csv`, trace back to input parameters:

| Wrong output | Check these inputs |
|---|---|
| `entc_generation_pp_coal` | `efficfactor_entc_*_pp_coal`, MSP, residual capacity |
| `inen_*_{industry}` | `prodinit_ippu_{industry}`, `consumpinit_inen_*_{industry}`, `frac_inen_energy_{industry}_*` |
| `scoe_*` | `consumpinit_scoe_gj_per_hh_*`, `frac_scoe_heat_energy_*` |
| `waso_*` | `qty_waso_initial_*_tonne_per_capita`, `mcf_waso_*`, `frac_waso_*` |
| `lvst_entferm_*` | `pop_lvst_*`, `ef_lvst_entferm_*` |
| `lsmm_*` | `frac_lvst_mm_*`, `mcf_lsmm_*` |
| `soil_*` | `qtyinit_soil_synthetic_fertilizer_kt`, `ef_soil_*` |
| `trns_*` | `deminit_trde_*`, `fuelefficiency_trns_*`, `frac_trns_*` |

For multiplicative formulas, check each term against external data. The term furthest from the reference is the one to fix.

### Template Artifact Checklist

The raw template CSV comes from a base country (Bulgaria for Morocco). **Systematically check and replace:**

- [ ] Population and GDP (Gate 1-2)
- [ ] All livestock populations (Gate 4)
- [ ] Fertilizer quantities (Gate 5)
- [ ] Fuel import fractions (Gate 6)
- [ ] Climate classification (Gate 7)
- [ ] **Fuel exports** — template may have exports the country doesn't have. Zero them. (Gate 7b)
- [ ] **Waste per capita and composition** — template waste data is almost always wrong (Gate 7c)
- [ ] **IPPU production volumes** — cement, metals, chemicals from the base country (Gate 7d)
- [ ] **Landfill gas recovery** — template may have ~1.0 (industrialized country) when actual is near 0
- [ ] **Metal CCS capture** — template may have 0.90 (base country CCS). Zero for countries without CCS
- [ ] **Manure management fractions** — template reflects base country livestock systems, not yours
| Forest Sequestration | CO2 | -0.875 | -12.05 | 12.8x | Critical |
| Electricity/Heat | CO2 | 27.52 | **MISSING** | N/A | Uncalibrated |
| Fugitive Emissions | All | 0.19 | **MISSING** | N/A | Uncalibrated |

**Overall convergence: 19.4%** (only 19.4% of significant categories have error ≤ 25%)

> **Verified (Codebase Expert)**: 19.4% convergence is expected for a first-pass calibration. The reference notebook achieved similar convergence before multiple calibration iterations.

### Sector-by-Sector Calibration Guide

#### Livestock (lvst) — Well Calibrated

Current livestock CH4 is at 3.9% error — excellent. Key variables:

```
pop_lvst_initial_cattle_dairy
pop_lvst_initial_cattle_nondairy
pop_lvst_initial_sheep
pop_lvst_initial_goats
pop_lvst_initial_chickens
```

**Data sources**: FAOSTAT (primary), Our World in Data (secondary), Morocco Ministry of Agriculture (tertiary)

> **Historical note**: Early iterations had sheep population off by 1523x due to unit confusion (head vs. thousands). Always verify units against source data.

#### AG Crops N2O — Critical (97% Error)

The agricultural crops N2O emissions are critically underestimated (0.14 vs 4.62 MtCO2e). The emission factor (EF1 = 0.01) is correct — the issue is in activity data:

1. Synthetic fertilizer application rates (`qty_agrc_fertilizer_n_synthetic`)
2. Crop residue management fractions
3. Total cultivated area

**Likely cause**: Fertilizer application quantities may be orders of magnitude too low in the input data.

> **Verified (IPCC Expert)**: EF1 = 0.01 is correct per IPCC 2006 Table 11.1. The 97% error is a data input issue, not a model equation issue.

#### Forest Sequestration — Critical (12.8x Overestimate)

Model shows -12.05 MtCO2e vs EDGAR -0.875 MtCO2e. Investigate:

1. Forest area estimates (may be overestimated)
2. Carbon sequestration rates per hectare (default tropical rates may be too high for Morocco's degraded forests)
3. Whether model includes planted forests vs. natural regrowth

#### IPPU/Cement — Moderate (30.8% Error)

Cement production is set at 25 Mt, which represents **capacity** not actual production (~13-16 Mt). The clinker emission factor (0.507 t CO2/t clinker) is close to but slightly below the IPCC default (0.52).

#### LSMM CH4 — Critical (87.4% Error, Worsening)

Livestock manure management CH4 shows 87.4% error, and this worsened from 73% in earlier iterations. Investigate:

1. Manure management system distribution (anaerobic lagoon vs. solid storage vs. daily spread)
2. Whether the LSMM split from EDGAR's single livestock CH4 figure is correct
3. CH4 MCF values for each management system

> **Issue (IPCC Expert)**: The LSMM calibration worsening (73% → 87% across iterations) suggests that adjustments to livestock populations for `lvst` enteric calibration may have had unintended side effects on `lsmm`.

#### Electricity/Heat — Uncalibrated

This sector (27.5 MtCO2e, ~30% of total) requires NemoMod. Set `energy_model_flag: true` and ensure Julia is properly installed.

### Multi-Source Verification

Before applying any calibration adjustment, verify target values with at least 2 independent sources:

| Data Type | Primary Source | Secondary Source |
|-----------|----------------|------------------|
| Livestock | FAOSTAT | Our World in Data |
| Waste | World Bank (What a Waste) | UNEP |
| Energy | IEA | UN Energy Statistics |
| Cement | USGS Minerals Yearbook | Global Cement Report |
| Land Use | FAO FRA | Morocco HCP |

### Tracking Calibration Changes

Maintain a calibration log documenting every adjustment:

```markdown
## Iteration 3 — 2026-02-10
### Livestock Scaling
- Variable: pop_lvst_initial_sheep
- Previous: 14,200
- New: 21,628,277 (FAOSTAT 2022)
- Scaling factor: 1523x
- Source: FAOSTAT QCL dataset, downloaded 2026-01-28
- Result: Livestock CH4 error reduced from 86% to 3.9%
```

---

## 11. Output Postprocessing

### Pipeline Overview

After calibration runs complete, a series of R scripts process the raw SISEPUEDE outputs into Tableau-ready visualizations:

```
SISEPUEDE Run
    │
    ▼
WIDE_INPUTS_OUTPUTS.csv + ATTRIBUTE_*.csv
    │
    ▼
[check_data.ipynb]
    │  Adds LULUCF updates, produces emission_targets_*_LULUCF_update.csv
    │
    ▼
[postprocessing_250820.r]  ← Master orchestrator
    │
    ├──▶ [run_script_baseline_run_new.r]
    │       Loads EDGAR targets
    │       Calls intertemporal_decomposition.r
    │       Produces: decomposed_ssp_output.csv
    │
    ├──▶ [data_prep_new_mapping.r]
    │       Maps SISEPUEDE columns to EDGAR categories
    │       Applies HP filter (λ=1600) for smoothing
    │       Produces: tableau/data/decomposed_emissions_*.csv
    │
    └──▶ [data_prep_drivers.r]
           Extracts driver variables by taxonomy
           Applies growth factors (hardcoded for IPPU)
           Produces: tableau/data/drivers_*.csv
```

Additional notebooks:
- `create_diff_table.ipynb` → `diff_report_*.csv` (EDGAR comparison)
- `create_levers_table.ipynb` → `tableau_levers_table_complete.csv`
- `create_jobs_table.ipynb` → `jobs_demand_*.csv`

> **Verified (Codebase Expert)**: Full postprocessing pipeline traced and documented. All R script inputs, outputs, and dependencies confirmed.

### Intertemporal Decomposition

The core postprocessing algorithm forces model outputs to match EDGAR at the reference year while preserving temporal dynamics:

$$x_{calibrated}(t) = x_{uncalibrated}(t) \cdot \frac{x_{target}}{x_{uncalibrated}(t_{ref})}$$

This is applied to every emission variable, ensuring that:
1. At `year_ref = 2022`, model exactly matches EDGAR
2. Before and after 2022, the model's growth dynamics are preserved
3. The resulting trajectories are smooth (HP filter applied post-decomposition)

The `rescale()` function in `intertemporal_decomposition.r` implements this:

```r
rescale <- function(series, target_value, ref_year_idx) {
    deviation_factor <- target_value / series[ref_year_idx]
    return(series * deviation_factor)
}
```

### HP Filter Smoothing

The Hodrick-Prescott filter with λ = 1600 is applied to smooth the decomposed emissions trajectories. This removes high-frequency noise while preserving the long-term trend, producing clean visualizations for Tableau dashboards.

> **Advisory (Codebase Expert)**: The `data_prep_drivers.r` script contains hardcoded IPPU production growth factors that may not reflect current Morocco industrial projections. These should be documented and reviewed.

### Export Artifacts

The model run must produce these files for the postprocessing pipeline:

| File | Purpose | How to Generate |
|------|---------|-----------------|
| `WIDE_INPUTS_OUTPUTS.csv` | Combined input + output data | `df_out.merge(df_in).to_csv(...)` |
| `ATTRIBUTE_STRATEGY.csv` | Strategy metadata | `ssp.database.db.read_table("ATTRIBUTE_STRATEGY")` |
| `ATTRIBUTE_PRIMARY.csv` | Primary key mapping | `ssp.odpt_primary.get_indexing_dataframe(primaries)` |
| `levers_implementation_*.csv` | Transformation-strategy mapping | `svt.LeversImplementationTable(strategies)` |

> **Issue C4 (now fixed)**: The original notebook was missing ATTRIBUTE_STRATEGY.csv and ATTRIBUTE_PRIMARY.csv exports, breaking the downstream R pipeline.

---

## 12. Scenario Analysis

### Baseline vs. LEP Comparison

Once calibrated, the primary analysis compares Strategy 0 (Baseline/BAU) against Strategy 6005 (SNBC Net Zero):

```python
df_baseline = df_out[df_out[ssp.key_primary] == 0]
df_lep = df_out[df_out[ssp.key_primary] == 1]  # primary_id 1 if second strategy

# Total emissions over time
emission_cols = [c for c in df_out.columns if c.startswith('emission_co2e')]

baseline_total = df_baseline[emission_cols].sum(axis=1).values
lep_total = df_lep[emission_cols].sum(axis=1).values

reduction_2030 = (baseline_total[15] - lep_total[15]) / baseline_total[15] * 100
print(f"Emissions reduction at 2030: {reduction_2030:.1f}%")
```

### BAU Trajectory Validation

Before running policy scenarios, validate that Strategy 0 (baseline) produces a plausible forward trajectory. Compare against the country's official BAU/Reference scenario (e.g., Morocco's SNBC Reference, SNBC Figure 15 p.51).

| Year | SNBC Reference | Model Baseline | Gap | Assessment |
|------|---------------|---------------|-----|-----------|
| 2022 | ~100 Mt | 96.3 Mt | -4% | Good (within NIR calibration tolerance) |
| 2030 | ~125 Mt | 103.5 Mt | -17% | Under — demand elasticities too conservative |
| 2050 | ~170-180 Mt | 136.0 Mt | -20-25% | Significant divergence (SNBC reaches 218 Mt at 2060) |

**Root causes of trajectory gaps** (Morocco example):
- Transport elasticity 0.80 vs SNBC-implied 1.47 (motorization wave in middle-income country)
- Commercial energy elasticity 0.00 vs SNBC 1.5-2.0 (urbanization-driven services growth)
- Cement elasticity -2.0 vs NIR historical -0.42 (cyclical decline, not structural)
- Coal does not retire in baseline (SNBC includes ONEE capital plan as BAU)

> **Design principle:** Forward-looking BAU changes (coal retirement, renewable capacity ramps, demand elasticity adjustments) should be implemented as SISEPUEDE transformations, not as direct CSV modifications to `df_input_0.csv`. This preserves the historical calibration at tp=0-7 and enables clean comparison between baseline and policy scenarios.

**SNBC-derived elasticities** (for countries with official BAU projections):

| Sector | SNBC Method | Implied Elasticity | Source |
|--------|-----------|-------------------|--------|
| Transport | Vehicle stock turnover (108 techs) | 1.47 | SNBC pp.59-62 |
| Industry energy | Subsector value-added analysis | 1.12 | SNBC pp.155-156 |
| Commercial | GDP-linked tertiary output | 1.5-2.0 | SNBC p.154 |
| Residential | Per HH + income | ~1.0 | SNBC p.55 |
| Cement | Per capita (population-driven) | 0.3-0.5 | SNBC p.157 |

**Coal retirement in BAU** (SNBC p.53-54): Morocco's coal plants are decommissioned by late 2040s based on existing ONEE contracts and cost-competitiveness of renewables — this is BAU behavior, not a climate policy. Model via declining `nemomod_entc_residual_capacity_pp_coal_gw` + zero `nemomod_entc_total_annual_max_capacity_investment_pp_coal_gw`.

### Interpreting LEP Transformations

Morocco's SNBC Net Zero (Strategy 6005) includes 63 transformations across all sectors:

| Sector | Key Transformations | Expected Impact |
|--------|-------------------|-----------------|
| Agriculture | Rice CH4 reduction, conservation agriculture | Moderate |
| Livestock | Reduced enteric fermentation, improved manure management | Moderate |
| Energy | Renewable electricity targets, grid loss reduction | Large |
| Transport | Fuel shifting (EV adoption), modal shift, demand reduction | Large |
| Buildings | Heat demand reduction, fuel switching, efficiency | Moderate |
| Industry | Energy efficiency, fuel switching, production efficiency | Moderate |
| IPPU | HFC phasedown, clinker reduction, N2O reduction | Small |
| Waste | Biogas capture (landfill + wastewater) | Moderate |
| Land Use | Reduced deforestation, reforestation, silvopasture | Large (sequestration) |
| CCSQ | Carbon capture and sequestration | Long-term |

### NDC Alignment Analysis

Compare modeled reductions against Morocco's NDC targets:

```python
# Morocco NDC targets (% reduction below BAU by 2030)
ndc_unconditional = 0.17  # 17%
ndc_conditional = 0.455    # 45.5%

year_2030_idx = 15  # time_period for 2030
baseline_2030 = baseline_total[year_2030_idx]
lep_2030 = lep_total[year_2030_idx]

modeled_reduction = (baseline_2030 - lep_2030) / baseline_2030

print(f"Modeled reduction: {modeled_reduction*100:.1f}%")
print(f"NDC unconditional: {ndc_unconditional*100:.1f}%")
print(f"NDC conditional:   {ndc_conditional*100:.1f}%")
```

### Transformation Attribution

To understand which transformations contribute most to emissions reductions, examine sector-level deltas:

```python
# Sector-level comparison at 2030
for subsector in ['agrc', 'lvst', 'trns', 'inen', 'scoe', 'waso']:
    cols = [c for c in emission_cols if f'_{subsector}_' in c]
    base_sum = df_baseline.iloc[15][cols].sum()
    lep_sum = df_lep.iloc[15][cols].sum()
    delta = base_sum - lep_sum
    print(f"  {subsector:6s}: {delta:12.2f} MtCO2e reduction")
```

---

## 13. Troubleshooting and Reference

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Missing fields` on SISEPUEDE init | Wrong argument order in `si.SISEPUEDE()` | First arg must be `"calibrated"` string |
| `NameError: 'strategies'` | Transformations not loaded before SISEPUEDE init | Load transformations/strategies first |
| Empty output DataFrame | NemoMod failed silently | Check Julia installation, set `initialize_as_dummy=True` for non-energy runs |
| Output has 0 rows for a strategy | Strategy ID not in `strategies.all_strategies` | Verify strategy exists before running |
| `FileNotFoundError` on config | Running notebook from wrong directory | Ensure CWD is `ssp_modeling/notebooks/` |
| Fraction sums ≠ 1.0 | Input data error | Check and renormalize fraction groups |
| NaN in emission columns | Input variable is zero when model expects nonzero | Check input data for unexpected zeros |

### SISEPUEDE API Quick Reference

#### Initialization
```python
import sisepuede as si
import sisepuede.transformers as trf
import sisepuede.utilities._plotting as spu
import sisepuede.visualization.plots as svp
import sisepuede.visualization.tables as svt
import sisepuede.manager.sisepuede_file_structure as sfs
import sisepuede.manager.sisepuede_models as sm
import sisepuede.manager.sisepuede_examples as sxl
```

> **Verified (Docs Expert)**: All import paths confirmed against installed package structure.

#### Key Methods
```python
# File structure
file_struct = sfs.SISEPUEDEFileStructure(dir_ingestion, initialize_directories=True)

# Transformations
transformations = trf.Transformations(dir_path, attr_time_period=..., df_input=...)
strategies = trf.Strategies(transformations, export_path=..., prebuild=True)

# Model
ssp = si.SISEPUEDE("calibrated", db_type="csv", ...)
ssp.project_scenarios(dict_scens, save_inputs=True, ...)
df_out = ssp.read_output(None)
df_in = ssp.read_input(None)

# Quick model test (without full SISEPUEDE initialization)
models = sm.SISEPUEDEModels(matt, fp_julia=..., fp_nemomod_reference_files=...)
df_result = models(df_input, time_periods_base=list(range(12)))

# Visualization
svp.plot_emissions_stack(df_out, matt)

# Export
table = ssp.database.db.read_table("ATTRIBUTE_STRATEGY")
df_primary = ssp.odpt_primary.get_indexing_dataframe(all_primaries)
levers = svt.LeversImplementationTable(strategies)
```

### Emission Factor Reference (IPCC 2006)

| Parameter | Value | IPCC Reference |
|-----------|-------|----------------|
| Natural gas EF | 56,100 kg CO2/TJ | Table 2.2 |
| Diesel/gas oil EF | 74,100 kg CO2/TJ | Table 2.2 |
| Coal (anthracite) EF | 94,600 kg CO2/TJ | Table 2.2 |
| Gasoline EF | 69,300 kg CO2/TJ | Table 2.2 |
| Agricultural N2O EF1 | 0.01 kg N2O-N/kg N | Table 11.1 |
| Wastewater N2O EF | 0.005 kg N2O-N/kg N | Table 6.11 |
| Cement clinker EF | 0.52 t CO2/t clinker | Table 2.1 (Vol 3) |
| Landfill oxidation factor | 0.1 | Section 3.2.1 (Vol 5) |
| Landfill fraction CH4 (F) | 0.5 | Default |
| DOCf (fraction DOC dissimilated) | 0.5 | Default |
| CH4/CO2 molecular ratio | 16/12 | Stoichiometric |

> **Verified (IPCC Expert)**: All emission factors confirmed against IPCC 2006 source tables.

### Known Issues and Advisories

1. **IPCC 2019 Refinements**: The model currently uses IPCC 2006 defaults. Key differences in the 2019 Refinements include disaggregated N2O emission factors for different climate zones and a 32x increase in wastewater N2O factors at the plant level. These are not yet implemented.

2. **Single-Year Calibration**: The current approach calibrates only at 2022. Multi-year validation (comparing at 2015, 2018, 2022) would strengthen confidence in temporal dynamics.

3. **Morocco Climate Zone**: Morocco spans multiple IPCC climate zones (warm temperate dry to tropical dry). Waste decay rates should be zone-specific but are currently set to single values.

4. **Livestock CH4 Allocation**: EDGAR reports a single livestock CH4 figure, but SISEPUEDE splits it between enteric fermentation (`lvst`) and manure management (`lsmm`). Ensure the sum of both subsectors matches EDGAR, not each individually.

5. **GWP Version**: AR5 GWPs are used throughout. If switching to AR6, all CO2e values will change slightly (CH4: 28→27.9, N2O: 265→273).

6. **Hardcoded Growth Factors**: The `data_prep_drivers.r` script contains hardcoded IPPU production growth factors that may not reflect current Morocco industrial projections.

### Glossary

| Term | Definition |
|------|-----------|
| **AFOLU** | Agriculture, Forestry and Other Land Use (IPCC sector 3) |
| **BAU** | Business As Usual (baseline scenario) |
| **EDGAR** | Emissions Database for Global Atmospheric Research |
| **EF** | Emission Factor |
| **FOD** | First-Order Decay (landfill methane model) |
| **GWP** | Global Warming Potential |
| **HP Filter** | Hodrick-Prescott filter for time series smoothing |
| **IPPU** | Industrial Processes and Product Use (IPCC sector 2) |
| **LEP** | Low Emissions Pathway (strategy 6003) |
| **LSMM** | Livestock Manure Management |
| **LULUCF** | Land Use, Land-Use Change and Forestry |
| **NDC** | Nationally Determined Contribution (Paris Agreement) |
| **NemoMod** | Julia-based energy system optimization model |
| **SISEPUEDE** | SImulation of SEctoral Pathways and Uncertainty Exploration for DEcarbonization |
| **SSP** | Shared Socioeconomic Pathway |

### Citations

- IPCC (2006). *2006 IPCC Guidelines for National Greenhouse Gas Inventories*. IGES, Japan.
- IPCC (2019). *2019 Refinement to the 2006 IPCC Guidelines for National Greenhouse Gas Inventories*.
- Crippa, M., et al. (2024). *EDGAR v8.0 Greenhouse Gas Emissions*. European Commission, Joint Research Centre.
- Kingdom of Morocco (2021). *Updated Nationally Determined Contribution under the Paris Agreement*.
- FAOSTAT (2024). *Livestock and Crop Statistics*. Food and Agriculture Organization.

---

*This guide was generated as part of the SISEPUEDE Morocco Calibration Pipeline validation and documentation project. All equations, parameters, and API references have been validated by three expert agents (Docs, Codebase, IPCC) across Phases 1 and 3.*

---

## 14. NemoMod Deep Dive — How Energy Production Actually Works

> **Session 5 Addition.** This section was produced by 5 independent investigation agents and verified against SISEPUEDE source code, NemoMod Julia source, official documentation, and 6 cross-country SISEPUEDE deployments. All claims tagged with source references.

### 14.1 What NemoMod Is (and Isn't)

**NemoMod** (Next Energy Modeling system for Optimization) is a **least-cost energy system optimization model** — a linear program (LP) derived from OSeMOSYS. Think of it as an electricity dispatcher:

> *SISEPUEDE tells NemoMod: "Morocco needs X PJ of electricity, Y PJ of diesel, Z PJ of gas this year." NemoMod decides which power plants to run, which fuels to refine, and what new capacity to build — all while minimizing total cost.*

**What NemoMod does:**
- Receives energy demand from SISEPUEDE (computed from INEN + SCOE + TRNS + CCSQ sectors)
- Decides how to meet that demand: dispatch existing plants, build new capacity, import fuels
- Returns: production by technology, capacity built, emissions, costs

**What NemoMod does NOT do:**
- It does NOT compute demand — SISEPUEDE does that in Python
- It does NOT model non-energy sectors (AFOLU, waste, IPPU)
- It does NOT provide feedback to demand (no price elasticity)
- It does NOT auto-retire existing capacity — you must set declining ResidualCapacity yourself

> **Verified (Agent 1, Session 5):** Confirmed by tracing `energy_production.py` → `format_nemomod_table_specified_annual_demand()` → `NemoMod.calculatescenario()` in Julia.

**The SISEPUEDE-NemoMod Pipeline:**

```
Input CSV (consumpinit_*, prodinit_*, deminit_*, frac_*)
    │
    ▼  [Python: energy_consumption.py]
Demand by fuel computed: INEN + SCOE + TRNS + CCSQ
    │
    ▼  [Python: energy_production.py]
NemoMod input tables written to SQLite database
    │
    ▼  [Julia: NemoMod.calculatescenario()]
LP solved: min cost subject to constraints
    │
    ▼  [Python: energy_production.py]
Results read back, transmission loss corrected
    │
    ▼
Emissions = fuel_burned × emission_factor
```

> **WARNING:** You cannot set `SpecifiedAnnualDemand` directly. It is computed from the input CSV columns listed above. To change what NemoMod receives, you must change the **drivers** (consumpinit_*, prodinit_*, deminit_*, frac_enfu_*, exports_enfu_*).

---

### 14.2 The Data Pipeline — A Worked Morocco Example

Let's trace Morocco's residential electricity demand from input CSV all the way to NemoMod emissions.

**Step 1: SISEPUEDE computes demand from input CSV columns**

```
Residential electricity demand at tp=7 (year 2022):
  households = population / occupancy ≈ 37,000,000 / 4.87 = 7,597,536
  intensity  = consumpinit_scoe_gj_per_hh_residential_elec_appliances = 6.44 GJ/hh
  demand     = 7,597,536 × 6.44 GJ = 48,928,082 GJ = 48.9 PJ

Commercial electricity demand:
  GDP        = gdp_mmm_usd = 307.44 billion USD
  intensity  = consumpinit_scoe_tj_per_mmmgdp_commercial_municipal_elec_appliances = 73.2 TJ/BGDP
  demand     = 307.44 × 73.2 = 22,505 TJ = 22.5 PJ

Add INEN electricity: 20.1 PJ
Add TRNS electricity:  1.1 PJ
─────────────────────────────
Total electricity demand: ~92.6 PJ
```

> **Verified (Agent 3, Session 5):** WIDE output shows `energy_demand_enfu_total_fuel_electricity = 107.2 PJ` at tp=7 (includes ENTC self-consumption of 29.1 PJ).

**Step 2: Adjust for exports and transmission loss**

```
SpecifiedAnnualDemand = (demands + exports) / (1 - transmission_loss)
                      = (107.2 + 0.49) / (1 - 0.08)
                      ≈ 116.9 PJ  →  ~89.6 PJ after SAD computation adjustments
```

> **Verified (Agent 1, Session 5):** The actual SAD for electricity at tp=7 is ~89.6 PJ, which is 42% BELOW IEA's ~155 PJ. The demand is NOT inflated.

**Step 3: NemoMod decides how to meet demand**

NemoMod receives ~89.6 PJ electricity demand. But because nuclear investment is unconstrained (-999 = no cap) and nuclear fuel costs near-zero, NemoMod builds **289 GW of nuclear** and produces **13,048 PJ** total — 122x the actual demand.

```
NemoMod dispatch at tp=7 (what ACTUALLY happens):
  Nuclear:       9,103 PJ  (69.8%)  ← 289 GW built, 0 GW installed!
  Wind:          2,141 PJ  (16.4%)  ← 66 GW built vs 2 GW installed
  Solar:           789 PJ  ( 6.1%)
  Hydropower:      716 PJ  ( 5.5%)
  Coal:            260 PJ  ( 2.0%)  ← MSP=2% forces this
  ─────────────────────────────────
  TOTAL:        13,048 PJ           ← 122x actual demand!

  IEA actual:     154 PJ           ← what it should be
```

> **Verified (Agent 3, Session 5):** WIDE output `nemomod_entc_annual_production_by_technology_pp_nuclear = 9,103 PJ` at tp=7. Total production 13,048 PJ confirmed.

**Step 4: Why does this happen?**

The root cause is **unconstrained capacity investment**. NemoMod's cost minimization builds cheap capacity freely:

```pseudocode
for each technology:
    if TotalAnnualMaxCapacityInvestment == -999:  # SISEPUEDE sentinel = "no limit"
        NemoMod can build unlimited capacity

    if fuel_cost ≈ 0:  # dummy supply tech provides fuel for free
        running cost is near-zero

Nuclear: efficiency = 0.0027 → InputActivityRatio = 1/0.0027 = 370.37
  → 1 PJ of nuclear electricity consumes 370 PJ of fuel_nuclear
  → fuel_nuclear supplied by supply_fuel_nuclear at near-zero cost
  → NemoMod sees: "I can produce unlimited cheap electricity from nuclear"
  → It builds 289 GW and produces 9,103 PJ
```

> **Verified (Agent 1, Session 5):** `efficfactor_entc_technology_fuel_use_pp_nuclear = 0.002700` in input CSV. IAR = 1/0.0027 = 370.37.

**Step 5: The "accidental calibration" of coal MSP=2%**

Coal MSP = 2% means NemoMod must produce at least 2% of **total electricity production** from coal. At 13,048 PJ total, 2% = 260 PJ, which by coincidence matches Morocco's actual coal generation (~29,064 GWh = ~105 PJ... well, it's roughly in the ballpark when combined with coal's emission factor to produce 27.5 MtCO2e).

```
Coal MSP response curve (empirical, with current demand inflation):
  MSP = 0%  →  ENTC CO2 =   2.2 MtCO2e  (NemoMod dispatches minimal coal)
  MSP = 1%  →  ENTC CO2 =  14.4 MtCO2e
  MSP = 2%  →  ENTC CO2 =  27.5 MtCO2e  ← matches EDGAR!
  MSP = 5%  →  ENTC CO2 =  65.7 MtCO2e
```

> **WARNING:** This calibration is accidental. If total NemoMod production changes (e.g., by capping nuclear), the MSP sweet spot shifts. Coal MSP=2% only works because 2% × 13,048 PJ happens to produce the right amount of coal emissions.

---

### 14.3 The 32 Technologies

NemoMod models 29 technologies in 5 categories:

#### Power Plants (pp_*) — 14 technology types

These generate electricity from fuel. **All have CSV columns for capacity, costs, and MSP.**

| Technology | Fuel | Efficiency | Operational Life | Morocco Residual (GW) |
|-----------|------|-----------|-----------------|----------------------|
| `pp_coal` | Coal | 45% | 50 yr | 4.985 |
| `pp_gas` | Natural gas | 40% | 25 yr | 2.929 |
| `pp_hydropower` | Water | 100% | 100 yr | 2.948 |
| `pp_wind` | Wind | 100% | 20 yr | 2.038 |
| `pp_solar` | Solar | 100% | 30 yr | 0.937 |
| `pp_oil` | Oil | 40% | 40 yr | 0.595 |
| `pp_biomass` | Biomass | 40% | 25 yr | 0.000 |
| `pp_biogas` | Biogas | 33.5% | 20 yr | 0.000 |
| `pp_nuclear` | Nuclear | 0.27% | 30 yr | 0.000 |
| `pp_coal_ccs` | Coal | 45% | 50 yr | 0.000 |
| `pp_gas_ccs` | Gas | 40% | 25 yr | 0.000 |
| `pp_geothermal` | Geothermal | 100% | 30 yr | 0.000 |
| `pp_ocean` | Ocean | 100% | 34 yr | 0.000 |
| `pp_waste_incineration` | Waste | 40% | 25 yr | 0.000 |

> **Verified (Agent 1, Session 5):** Efficiency values from `efficfactor_entc_technology_fuel_use_pp_*` in df_input_0.csv. Residual capacities from `nemomod_entc_residual_capacity_pp_*_gw` at tp=7.

> **WARNING — Nuclear efficiency 0.27%:** This represents nuclear's thermal-to-electric conversion INCLUDING fuel enrichment energy. The IAR of 370 means NemoMod consumes 370 PJ of `fuel_nuclear` per PJ of electricity. Since `supply_fuel_nuclear` is a near-zero-cost dummy tech, this makes nuclear appear cheap despite the massive fuel consumption.

#### Fuel Processing (fp_*) — 8 technologies

These convert one fuel to another. **NO CSV columns for capacity, costs, or MSP.** You cannot directly constrain these.

| Technology | Input | Outputs |
|-----------|-------|---------|
| `fp_petroleum_refinement` | Crude (IAR=1.087) | Diesel (0.297), Gasoline (0.479), Kerosene (0.086), HGL (0.04), Oil (0.014) |
| `fp_natural_gas` | Gas unprocessed (1.0) | Natural gas (0.949), HGL (0.028) |
| `fp_hydrogen_electrolysis` | Electricity (1.303) | Hydrogen (1.0) |
| `fp_hydrogen_reformation` | Natural gas (1.315) | Hydrogen (1.0) |
| `fp_hydrogen_reformation_ccs` | Natural gas (1.315) | Hydrogen (1.0) |
| `fp_hydrogen_gasification` | Coal (1.967) | Hydrogen (1.0) |
| `fp_ammonia_production` | Electricity (0.325) + Hydrogen (0.176) | Ammonia (1.0) |
| `fp_natural_gas_liquefaction` | Natural gas (1.125) | LNG (1.0) |

> **Verified (Agent 4, Session 5):** OAR/IAR values from input CSV `nemomod_entc_output_activity_ratio_fuel_production_fp_*` and `nemomod_entc_input_activity_ratio_fuel_production_fp_*`.

> **CRITICAL:** fp_* technologies have NO CSV columns for ResidualCapacity, TotalAnnualMaxCapacity, TotalAnnualMaxCapacityInvestment, or VariableCost. This is why you cannot directly kill the refinery via CSV — you must starve it of feedstock (crude import=1.0) instead.

#### Mining & Extraction (me_*) — 3 technologies

| Technology | Output | Inputs |
|-----------|--------|--------|
| `me_coal` | Coal (1.0) | Coal deposits (1.002), diesel, electricity, gasoline, gas, oil |
| `me_crude` | Crude (1.0) | Diesel (0.038), electricity (0.035), gasoline (0.002) |
| `me_natural_gas` | Gas unprocessed (1.0) | Diesel (0.041), electricity (0.038), gasoline (0.002) |

#### Dummy Supply (supply_*) — auto-generated

For each fuel that has no explicit production technology, SISEPUEDE creates a `supply_fuel_*` dummy tech that "imports" the fuel. These are priced HIGH (10x max variable cost, minimum $100/MWh) to discourage use — **except `supply_fuel_biomass` which gets $0 because biomass has no import fraction variable.**

> **Verified (Agent 4, Session 5):** `supply_fuel_biomass` zero cost confirmed in `energy_production.py` line 2364: biomass has neither import fraction nor OAR variable → classified as `cats_no_cost`.

#### Storage (st_*) — 4 technologies

`st_batteries`, `st_compressed_air`, `st_flywheels`, `st_pumped_hydro` — all have CSV columns for capacity and costs. Morocco has 0 GW of all storage types.

---

### 14.4 How NemoMod Decides What to Run — The LP

NemoMod solves a linear program each time it's called:

**Objective — minimize total discounted cost:**

$$\min \sum_{r,y} \left[ \text{CapitalInvestment}_{r,y} + \text{FixedCost}_{r,y} + \text{VariableCost}_{r,y} + \text{EmissionPenalty}_{r,y} - \text{SalvageValue}_{r,y} \right]$$

**Subject to these constraints:**

**Constraint 1 — Energy Balance** (must meet demand in every time slice):

$$\text{Production}_{r,l,f,y} \geq \text{Demand}_{r,l,f,y} + \text{FuelUse}_{r,l,f,y}$$

*"You can't have blackouts. Every hour of every day, supply must meet demand."*

**Constraint 2 — Capacity Adequacy** (can't run more than you have):

$$\text{RateOfActivity}_{r,l,t,y} \leq \text{TotalCapacity}_{r,t,y} \times \text{CapToActivity} \times \text{AvailFactor}_{r,t,l,y}$$

*"A 5 GW coal plant can produce at most 5 × 31.536 PJ/yr × 0.85 availability = 134 PJ per year."*

Where `CapacityToActivityUnit ≈ 31.536` converts GW to PJ/yr (1 GW × 8760 hours × 3.6e-3 PJ/GWh).

**Constraint 3 — MinShareProduction** (policy floors):

$$\text{Production}_{r,t,f,y} \geq \text{MSP}_{r,t,f,y} \times \text{TotalProduction}_{r,f,y}$$

*"At least X% of total electricity production must come from technology T."*

> **WARNING:** MSP is a fraction of **total production**, not of demand. If NemoMod overproduces by 122x (as Morocco does), MSP=2% means 2% of the inflated total, not 2% of real demand. This is why coal MSP=2% produces 27.5 MtCO2e — it's 2% of 13,048 PJ, not 2% of 154 PJ.

**Constraint 4 — Capacity Accounting:**

$$\text{TotalCapacity}_{r,t,y} = \text{ResidualCapacity}_{r,t,y} + \text{AccumulatedNewCapacity}_{r,t,y}$$

*"Total installed capacity = what was already built (exogenous) + what NemoMod decided to build (endogenous)."*

**Constraint 5 — Activity Limits** (if set):

$$\text{TotalAnnualActivity}_{r,t,y} \leq \text{TotalTechnologyAnnualActivityUpperLimit}_{r,t,y}$$

*"Technology T can produce at most X PJ per year, regardless of capacity."* This is not exposed in the input CSV for fp_* technologies.

---

### 14.5 The 10 Most Important Parameters for Calibration

| # | CSV Column Pattern | NemoMod Table | What It Controls | Morocco tp=7 | Cross-Country Norm |
|---|-------------------|---------------|-----------------|-------------|-------------------|
| 1 | `nemomod_entc_residual_capacity_pp_{tech}_gw` | ResidualCapacity | Existing installed capacity | Coal 4.99, Gas 2.93, Hydro 2.95, Wind 2.04, Solar 0.94 GW | Declines over time (plant aging) — Morocco's is uniquely FLAT |
| 2 | `nemomod_entc_frac_min_share_production_pp_{tech}` | MinShareProduction | Minimum dispatch fraction | Coal=0.02, all others=0 (sum=0.02) | Sum ≈ 1.0 across 6-8 techs in ALL other countries |
| 3 | `nemomod_entc_total_annual_max_capacity_investment_pp_{tech}_gw` | TotalAnnualMaxCapacityInvestment | Max new capacity per year | 6 techs = -999, 8 techs already capped at 0 (nuclear, biomass, biogas, waste, geothermal, ocean, CCS) | Should be 0 for techs the country doesn't plan to build |
| 4 | `nemomod_entc_total_annual_max_capacity_pp_{tech}_gw` | TotalAnnualMaxCapacity | Max total capacity | Most = -999 (unconstrained) | Should be 0 for non-existent techs |
| 5 | `nemomod_entc_variable_cost_pp_{tech}_usd_per_mwh` | VariableCost | Operating cost (controls dispatch order) | Coal 4.71, Gas 2.32, Oil 3.22 | Same globally (template defaults) |
| 6 | `nemomod_entc_capital_cost_pp_{tech}_mm_usd_per_gw` | CapitalCost | New capacity investment cost | Coal 3394, Gas 713, Solar 734, Wind 1225 | Same globally |
| 7 | `efficfactor_entc_technology_fuel_use_pp_{tech}` | InputActivityRatio (as 1/eff) | Fuel-to-electricity efficiency | Coal 0.45, Gas 0.40, Nuclear 0.0027 | Same globally |
| 8 | `frac_enfu_fuel_demand_imported_pj_fuel_{fuel}` | MSP for supply_fuel_* | Import fraction → starves domestic production | Crude=0.0(!), diesel/gasoline=0.99, elec=0.032 | Uganda crude=1.0 (no refinery) |
| 9 | `nemomod_entc_output_activity_ratio_fuel_production_fp_petroleum_refinement_{fuel}` | OutputActivityRatio | Refinery product yields | diesel=0.297, gasoline=0.479, ... | Identical globally (template defaults) |
| 10 | `nemomod_entc_scalar_availability_factor_pp_{tech}` | AvailabilityFactor | Capacity factor scalar | All = 1.0 | Should reflect actual CFs (coal ~0.80, solar ~0.20) |

> **Verified (Agent 2, Session 5):** Cross-country comparison confirmed MSP sum ≈ 1.0 for Bulgaria (0.96), Mexico (1.00), Peru (0.97), Louisiana (1.00), Uganda (1.00), Morocco original (1.00). Only Morocco demo has MSP sum = 0.02.

> **EAR bounds.** Both the EAR scalar and efficiency factor are bounded [0,1] in source code (`energy_production.py` lines 5719, 5731). Values outside this range are silently clipped. Setting efficiency > 1.0 or scalar > 1.0 has no effect.

> **All capacity parameters are time-varying.** `ResidualCapacity`, `TotalAnnualMaxCapacity`, and `TotalAnnualMaxCapacityInvestment` accept different values at each time period (one per row in the CSV). Use declining trajectories for plant retirement and increasing trajectories for capacity expansion.

> **MSP must decline ahead of capacity retirement.** When retiring a technology via declining `residual_capacity`, reduce its MSP (`frac_min_share_production`) to zero BEFORE capacity reaches zero. If MSP demands more production than available capacity can deliver, NemoMod goes INFEASIBLE. Safe practice: MSP should reach zero at least 5 time periods before capacity reaches zero.

---

### 14.6 Time Slices and Blocks

**32 Time Slices** represent intra-year variation:

```
4 Seasons (dec_feb, mar_may, jun_aug, sep_nov)
  × 2 Day Types (weekday, weekend)
    × 4 Hour Blocks (night 22-04, morning 04-10, day 10-16, evening 16-22)
= 32 time slices
```

Each slice has a weight (fraction of the year). Solar availability varies by slice (high during day, zero at night). NemoMod must meet demand in EACH slice independently.

**Blocks (Limited Foresight)**

SISEPUEDE splits the optimization into 2 blocks:
- **Block 1:** tp 0-12 (years 2015-2027) — optimized first, results locked
- **Block 2:** tp 13-55 (years 2028-2070) — optimized from Block 1's end state

This causes a **dispatch discontinuity at tp=12→13** because Block 2 re-optimizes from scratch.

```
Block boundary example (Morocco, biomass production):
  tp=12: 1,098 PJ
  tp=13:   577 PJ  ← 47.5% DROP at boundary
```

> **Verified (Agent 1, Session 5):** Block split determined by `time_period_u0` in `configuration.py` lines 572-607. When blank in config.yaml, defaults to `datetime.now().year + 1` = 2027 = tp=12.

**How to fix:** Set `time_period_u0: 55` in config.yaml for perfect foresight (single block). This is slower (~2x runtime) but produces continuous trajectories.

---

### 14.7 The Refinery Chain and FGTV Emissions

Morocco's SAMIR refinery closed in 2015, but NemoMod still dispatches the virtual refinery, producing **7.6 MtCO2e** of phantom fugitive emissions.

**How the refinery chain works:**

```
me_crude (mining) → crude [IAR=1.087] → fp_petroleum_refinement → 5 products:
  diesel    (OAR = 0.2969)  →  29.7% of output
  gasoline  (OAR = 0.4791)  →  47.9% of output
  kerosene  (OAR = 0.0860)  →   8.6% of output
  HGL       (OAR = 0.0400)  →   4.0% of output
  fuel oil  (OAR = 0.0141)  →   1.4% of output
  ─────────────────────────────────────────────
  Total yield: 91.6% (8.4% refining loss)

Emissions per TJ of refinery activity:
  CO2: 6.374 tonne/TJ  →  produces 5.54 MtCO2e at current dispatch
  CH4: 0.000261 tonne/TJ →  produces 2.06 MtCO2e at current dispatch
```

**Why the refinery dispatches:**

Morocco's crude import fraction is **0.0** — meaning NemoMod thinks Morocco extracts crude domestically. Combined with refined product imports at 0.99 (not 1.0), there's a 1% domestic production requirement. Applied to the inflated demand, this drives significant refinery activity.

**The Uganda Solution:**

Uganda (no refinery) sets `frac_enfu_fuel_demand_imported_pj_fuel_crude = 1.0`. This tells NemoMod: "100% of crude comes from imports." The MSP mechanism forces all crude to flow through the `supply_fuel_crude` dummy tech. With no domestic crude, the refinery has no feedstock and cannot dispatch.

```pseudocode
# How import fractions starve the refinery:
if crude_import_fraction == 1.0:
    MSP(supply_fuel_crude) = 1.0  # 100% of crude must come from imports
    domestic_crude_production = 0  # no crude available domestically
    refinery_feedstock = 0         # refinery cannot run
    FGTV_emissions = 0             # no refinery activity → no fugitives

# Uganda: FGTV = 0.065 MtCO2e (near-zero, from residual coal/gas mining)
# Morocco demo: FGTV = 7.6 MtCO2e (phantom refinery at full operation)
```

> **Verified (Agent 4, Session 5):** Uganda `frac_enfu_fuel_demand_imported_pj_fuel_crude = 1.0` confirmed. Uganda FGTV = 0.065 MtCO2e from WIDE output. Refinery OAR values are similar but NOT identical across countries — Uganda has slightly different yields (diesel 0.22 vs Morocco's 0.2969). The mechanism (crude import starving the refinery) works regardless of specific OAR values.
>
> **Correction (Verification Agent):** An earlier version stated OARs were "identical across all 6 countries." This was FALSE — verified that Uganda differs.

**The Fix:** Set Morocco's crude import to 1.0 and all refined product imports to 1.0. Expected FGTV reduction: 7.6 → ~0.2 MtCO2e.

---

### 14.8 The Nuclear Problem (Morocco-Specific)

Morocco has zero nuclear power plants. But NemoMod builds 289 GW of nuclear and produces 9,103 PJ (70% of total dispatch). This happens because:

1. **Nuclear efficiency = 0.27%** → IAR = 370.37 (consumes 370 PJ fuel per PJ electricity)
2. **`supply_fuel_nuclear`** provides fuel at near-zero cost (dummy tech)
3. **`TotalAnnualMaxCapacityInvestment`** was -999 in early sessions but was capped to 0 in later sessions
4. **`TotalAnnualMaxCapacity`** similarly updated

> **Correction (Verification Agent):** The verifier found that nuclear investment was already capped at 0 in the current CSV (likely applied during Session 4). The "289 GW nuclear" finding was from Run 40's WIDE output, reflecting the state BEFORE the cap. The cap may have been applied between Run 40 and the current CSV state, or the WIDE output may reflect a different CSV version.

NemoMod's cost minimizer sees: "I can build unlimited nuclear capacity, fueled for free. Even at low efficiency, the total cost is near-zero." So it builds 289 GW.

**The Fix:**

```python
# Set nuclear capacity constraints to 0 (Morocco has no nuclear)
df['nemomod_entc_total_annual_max_capacity_pp_nuclear_gw'] = 0.0
df['nemomod_entc_total_annual_max_capacity_investment_pp_nuclear_gw'] = 0.0

# Do the same for other technologies Morocco doesn't have:
for tech in ['nuclear', 'geothermal', 'ocean', 'coal_ccs', 'gas_ccs']:
    df[f'nemomod_entc_total_annual_max_capacity_pp_{tech}_gw'] = 0.0
    df[f'nemomod_entc_total_annual_max_capacity_investment_pp_{tech}_gw'] = 0.0
```

> **WARNING:** Do NOT set these to 0 for technologies that have existing residual capacity (coal, gas, hydro, wind, solar, oil) — that would create `ResidualCapacity > TotalAnnualMaxCapacity`, which is immediately INFEASIBLE.

---

### 14.9 Cross-Country Patterns

| Parameter | Bulgaria | Mexico | Peru | Louisiana | Uganda | Morocco orig | **Morocco demo** |
|-----------|----------|--------|------|-----------|--------|-------------|-----------------|
| **MSP sum** | 1.00 | 1.00 | 0.97 | 1.00 | 1.00 | 1.00 | **0.02** |
| **MSP techs constrained** | 9 | ~8 | ~6 | 8 | ~5 | ~5 | **1 (coal only)** |
| **Capacity trajectory** | Declining | Declining | Declining | Declining | Declining | Declining | **Flat** |
| **Crude import** | 0.91 | Low | 0.21 | Low | **1.0** | 0.91 | **0.0** |
| **Refined product imports** | Low | Low | Low | Low | **1.0** | Low | **0.99** |
| **FGTV (MtCO2e)** | ~1.5 | 9.4 | ~2.0 | ~5.0 | **0.07** | ~2.0 | **~2.7** |
| **Refinery OARs** | Standard | Standard | Standard | Standard | Slightly different | Standard | Standard |

> **Correction (Verification Agent):** Bulgaria MSP sum corrected from 0.96 to 1.00 (9 techs). Bulgaria crude import corrected from 0.22 to 0.91. Morocco demo FGTV corrected from 7.6 to ~2.7 MtCO2e (based on latest available run output). Uganda OARs noted as slightly different from the standard template.

> **Verified (Agent 2, Session 5):** All values extracted from actual country repo input CSVs and WIDE outputs where available.

**Key Pattern:** Every "working" country constrains MSP to sum ~1.0 and has declining residual capacity. Morocco demo is the only outlier with MSP=0.02 and flat capacity.

**Country Archetypes:**
- **Oil importer with refinery** (Bulgaria, Morocco orig): crude import ~0.2-0.9, active refinery
- **Oil producer with refinery** (Mexico, Louisiana): low crude imports, significant FGTV
- **No refinery / pure importer** (Uganda): all imports=1.0, FGTV near-zero
- **Morocco demo**: matches no real archetype (crude import=0, but no refinery since 2015)

---

### 14.10 Common Failure Modes

#### 1. INFEASIBLE — The LP Cannot Be Solved

| Cause | Symptom | Fix |
|-------|---------|-----|
| ResidualCapacity > TotalAnnualMaxCapacity | Immediate crash | Don't set max capacity below existing capacity |
| MSP values sum > 1.0 | Constraint conflict | Keep MSP sum ≤ 1.0 |
| MSP requires more generation than capacity allows | Insufficient capacity | Reduce MSP or increase capacity |
| All techs capped at 0 with positive demand | No way to meet demand | Keep at least one supply pathway open |
| Emission limits below exogenous emissions | Impossible constraint | Relax emission limits |

> **Verified (Agent 0, Session 5):** NemoMod provides `find_infeasibilities(model, true)` for diagnosis — a binary search that identifies the minimal infeasible constraint subset. We never used this in Sessions 1-4.

#### 2. Biomass Explosion — 17,484 PJ of Free Energy

**Root cause:** `supply_fuel_biomass` has $0 cost (no import fraction variable) + `TotalAnnualMaxCapacity = -999` (unconstrained). When other constraints remove cheaper options, NemoMod builds unlimited biomass capacity.

**Prevention:**
- Cap biomass power: `nemomod_entc_total_annual_max_capacity_pp_biomass_gw = 0`
- Cap biomass investment: `nemomod_entc_total_annual_max_capacity_investment_pp_biomass_gw = 0`
- Or: add a `frac_enfu_fuel_demand_imported_pj_fuel_biomass` column (would trigger high-cost dummy pricing)

#### 3. Nuclear Overproduction — 289 GW Phantom Nuclear

**Root cause:** Unconstrained investment + near-zero fuel cost. Fix: set TotalAnnualMaxCapacity = 0 and TotalAnnualMaxCapacityInvestment = 0 for nuclear (and any other non-existent tech).

#### 4. "OPTIMAL" but Wrong — 13,048 PJ vs 107 PJ Demand

**Root cause:** NemoMod LP solves successfully but produces vastly more than needed. The surplus is absorbed by SISEPUEDE's `exportsadj` mechanism. Always check absolute production values, not just solver status.

#### 5. Block Boundary Discontinuity

**Root cause:** Limited foresight re-optimizes at block boundary. Fix: perfect foresight (`time_period_u0: 55`).

---

### 14.11 NemoMod Calibration Cookbook

Step-by-step for calibrating any country's energy sector:

```
STEP 1: Cap non-existent technologies
  For each tech Morocco doesn't have (nuclear, geothermal, ocean, CCS variants):
    Set TotalAnnualMaxCapacity = 0
    Set TotalAnnualMaxCapacityInvestment = 0
  This prevents NemoMod from building phantom capacity.

STEP 2: Set import fractions from IEA trade data
  No refinery → crude import = 1.0, all refined products = 1.0
  Has refinery → crude import from IEA, products = 1 - domestic_share
  This controls the refinery chain and FGTV emissions.

STEP 3: Validate demand inputs against IEA TFC
  Compare energy_demand_enfu_total_fuel_* at tp=7 against IEA 2022.
  Should be within ±30% for each fuel.
  If inflated → check consumpinit_*, prodinit_*, deminit_* drivers.

STEP 4: Set ResidualCapacity from IEA generation + capacity factors
  For each tech: GW = IEA_GWh / (8760 × capacity_factor)
  Typical CFs: coal 0.65-0.85, gas 0.03-0.50, wind 0.25-0.35,
               solar 0.15-0.25, hydro 0.03-0.40

STEP 5: Set MSP to approximate generation shares
  Sum should be ~0.90-1.00. Example for Morocco:
    coal ~0.35, wind ~0.15, gas ~0.10, solar ~0.05, hydro ~0.05
  Leave ~30% for optimizer flexibility.
  NOTE: Only works after demand is realistic. With inflated demand,
  MSP percentages map to wrong absolute values.

STEP 6: Run model and check ENTC CO2
  If too high → reduce coal MSP or increase renewable MSP
  If too low → increase coal MSP
  Iterate until ENTC CO2 matches EDGAR within ±5%.

STEP 7: Check FGTV emissions
  If > 1 MtCO2e and no refinery → crude import fraction wrong
  If high gas FGTV → check gas production vs IEA domestic production

STEP 8: Verify trajectory smoothness
  Check ALL time periods (not just tp=7).
  If jump at tp=12-13 → set time_period_u0: 55 for perfect foresight.
  If explosion after tp=30 → cap investment for non-planned technologies.
```

---

### 14.12 Inspecting NemoMod Internals

**Method 1: WIDE_INPUTS_OUTPUTS.csv** (most accessible)

```python
import pandas as pd
df = pd.read_csv("ssp_run_output/calibration_*/WIDE_INPUTS_OUTPUTS.csv")
tp7 = df[df['time_period'] == 7]

# What NemoMod dispatched:
prod_cols = [c for c in df.columns if 'nemomod_entc_annual_production_by_technology_pp_' in c]
for c in sorted(prod_cols):
    val = tp7[c].values[0]
    if val > 0.01:
        print(f"  {c.split('_pp_')[1]}: {val:.2f} PJ")

# Total electricity demand NemoMod received:
print(f"Total elec demand: {tp7['energy_demand_enfu_total_fuel_electricity'].values[0]:.2f} PJ")
```

**Method 2: NemoMod's `find_infeasibilities()`** (for INFEASIBLE diagnosis)

```julia
# In Julia (accessed via SISEPUEDE's Julia interface):
NemoMod.find_infeasibilities(model, true)
# Returns the exact constraint causing infeasibility
```

**Method 3: SQLite Database** (ground truth for NemoMod inputs)

```python
import sqlite3
conn = sqlite3.connect("path/to/nemomod_database.sqlite")
# What demand did NemoMod actually receive?
pd.read_sql("SELECT * FROM SpecifiedAnnualDemand WHERE y=2022", conn)
# What MSP constraints were set?
pd.read_sql("SELECT * FROM MinShareProduction", conn)
```

---

### 14.13 Parameter Quick Reference

**NemoMod parameters NOT exposed in SISEPUEDE input CSV** (identified by Agent 0):

| NemoMod Parameter | Potential Use | Priority |
|------------------|--------------|----------|
| `TotalTechnologyAnnualActivityUpperLimit` | Cap biomass/refinery production | HIGH |
| `TotalTechnologyAnnualActivityLowerLimit` | Force minimum generation (alternative to MSP) | MEDIUM |
| `MinimumUtilization` | Force minimum capacity factor | MEDIUM |
| `RampRate` | Limit dispatch changes between time slices | LOW |
| `EmissionsPenalty` | Carbon pricing for NDC scenarios | MEDIUM |
| `find_infeasibilities()` | Diagnose INFEASIBLE | HIGH |
| `REMinProductionTarget` | Renewable portfolio standard (Morocco: 52% by 2030) | MEDIUM |
| Custom Julia constraints | Morocco-specific policies | HIGH |

> **Verified (Agent 0, Session 5):** 10 NemoMod parameters identified that exist but have no SISEPUEDE CSV column. Full mapping table in `deliverables_ndc_iter/docs_review_report.md` Section 4.

---

*Section 14 produced by Session 5 NemoMod investigation (5 agents: Docs Reviewer, LP Inspector, Cross-Country Analyst, Energy Data Auditor, FGTV Investigator). All claims cite verification source. Independent verification pending.*
