# Investment & benefits crosswalk

Allocates the SISEPUEDE investment and cost-benefit paths across economic **agents**
(government / firms / households) and then across **SAM sectors**. Two independent
decompositions per path, each summing to 100%:

- **Agent split** (who finances it) — depends on financing judgment.
- **Cost vector** (what it buys) — a vector over SAM sectors + `IMPORTS`, independent of financing.

Final SAM allocation = `investment(sector) x cost_vector(sector)`.
Final agent allocation = `investment(sector) x agent_share(sector)`.

Source run: LEDS (LTS) vs BASE (no-action), `sisepuede_run_2026-07-16T18;06;11.475894`.
Units: billion 2019 USD, cumulative 2023-2050.

## Deliverable

`morocco_crosswalk_deliverable.xlsx` (recalc-clean). **Task 1** lives in the tabs:

- `T1_agent_split` — investment x {gov, firms, hh} shares + applied bn + a documented source per sector.
- `T1_cost_vectors` — share matrix, SAM destination x investment sector (blue = editable inputs; each column sums to 1).
- `T1_applied_SAM` — applied bn = cost-vector share x sector investment total (formulas).
- `T2_capex_by_tech` — NEMOMOD generation capex by technology; feeds the per-technology power cost vector.

The workbook also carries Tasks 2-5 and 7; Task 1 is self-contained in the tabs above.

### Task 1 headline (reconciles to 273.53 bn)

- Agent split applied: government 120.9, firms 129.1, households 23.6.
- Cost vector applied (top): construction 65.0, **IMPORTS 60.0 (~22%)**, machinery 32.4, R&D/support 24.1, forestry 22.6.
- `IMPORTS` is a synthetic destination inside the 100% (the SAM has no imports row): solar modules,
  wind turbines, EV drivetrains and heat pumps are largely imported.
- `territorial correction` (SAM row 43) is excluded — it is a balancing item, not a sector.
- The power path uses **separate technology cost vectors** (wind/solar/biogas weighted by the Task 2
  capex shares) instead of one generic power vector.

## Reproduce

Scripts (paths are absolute to this machine; adjust if moving):

- `crosswalk_data.py` — the Task 1 share tables (agent shares + cost vectors) with a source per share. **Edit shares here.**
- `ssp_extract.py` — loads the SISEPUEDE wide run output.
- `task2_generation.py` — NEMOMOD fuel savings + capex by technology (feeds the power cost vector).
- `assemble.py` — composes the power vector from Task 2 shares and validates every table sums to 1.0.
- `build_xlsx.py` — writes the workbook (all tasks) and is recalc'd with LibreOffice.

```
python task2_generation.py   # -> task2_capex.csv
python assemble.py           # validation + applied totals
python build_xlsx.py         # -> morocco_crosswalk_deliverable.xlsx
```
