"""Task 2 — fuel cost savings and capex, both BY GENERATION TECHNOLOGY, from NEMOMOD.

Fuel savings = change in ENTC fuel consumption value (BASE - LEDS), by fuel, mapped to
the plant type that burns it. Renewables burn no fuel -> zero (correct; the saving shows
up as reduced coal/oil/gas fuel purchase). This is NOT the CB 'Fuel cost savings (power
sector)' row, which is a residual bucket of demand-side + allocated electricity costs.

Capex = discounted capital investment by generation technology (LEDS - BASE).

Emits both the aggregated series and the RAW BASE/LEDS detail so the workbook can show the
calculation transparently:
  build/task2_fuel_savings.csv   build/task2_fuel_detail.csv
  build/task2_capex.csv          build/task2_capex_detail.csv
Values are in millions of 2019 USD (the native NEMOMOD unit); the workbook divides by 1000
to show bn and names the exact source column for every raw number.
"""
import pandas as pd
from ssp_extract import load, series, BASE, LEDS, YEARS, cols_with_prefix

df = load()

# ---- fuel -> plant technology map (power sector) ----
FUEL_TO_TECH = {
    "coal": "pp_coal", "natural_gas": "pp_gas", "oil": "pp_oil",
    "crude": "pp_oil", "diesel": "pp_oil", "kerosene": "pp_oil",
    "biomass": "pp_biomass", "biogas": "pp_biogas",
    "waste": "pp_waste_incineration", "nuclear": "pp_nuclear",
    "coke": "pp_coal", "furnace_gas": "pp_gas",
    "hydrocarbon_gas_liquids": "pp_gas",
}
RENEWABLES = ["pp_solar", "pp_wind", "pp_hydropower", "pp_geothermal", "pp_ocean"]

# ---------- FUEL SAVINGS: raw detail (base, leds) + aggregated ----------
tv_prefix = "totalvalue_enfu_fuel_consumed_entc_fuel_"
detail = []
for c in cols_with_prefix(tv_prefix):
    fuel = c[len(tv_prefix):]
    if fuel == "electricity":            # own-use, not generation fuel
        continue
    tech = FUEL_TO_TECH.get(fuel)
    if tech is None:
        continue
    b = series(c, BASE).loc[YEARS]
    l = series(c, LEDS).loc[YEARS]
    if (b.abs().sum() + l.abs().sum()) < 1e-6:   # skip fuels with no ENTC use at all
        continue
    for y in YEARS:
        detail.append({"Year": y, "fuel": fuel, "technology": tech, "source_var": c,
                       "base_musd": b.loc[y], "leds_musd": l.loc[y]})
fd = pd.DataFrame(detail)
fd.to_csv("task2_fuel_detail.csv", index=False)

fs = fd.copy()
fs["fuel_saving_musd"] = fs["base_musd"] - fs["leds_musd"]
fs_tech = fs.groupby(["Year", "technology"], as_index=False)["fuel_saving_musd"].sum()
for t in RENEWABLES:
    fs_tech = pd.concat([fs_tech, pd.DataFrame({"Year": YEARS, "technology": t, "fuel_saving_musd": 0.0})],
                        ignore_index=True)
fs_tech.to_csv("task2_fuel_savings.csv", index=False)

# ---------- CAPEX: raw detail (base, leds) + aggregated ----------
cap_prefix = "nemomod_entc_discounted_capital_investment_pp_"
cdetail = []
for c in cols_with_prefix(cap_prefix):
    tech = "pp_" + c[len(cap_prefix):]
    b = series(c, BASE).loc[YEARS]
    l = series(c, LEDS).loc[YEARS]
    if (b.abs().sum() + l.abs().sum()) < 1e-6:
        continue
    for y in YEARS:
        cdetail.append({"Year": y, "technology": tech, "source_var": c,
                        "base_musd": b.loc[y], "leds_musd": l.loc[y]})
cd = pd.DataFrame(cdetail)
cd.to_csv("task2_capex_detail.csv", index=False)

cx = cd.copy()
cx["capex_incremental_musd"] = cx["leds_musd"] - cx["base_musd"]
cx[["Year", "technology", "capex_incremental_musd"]].to_csv("task2_capex.csv", index=False)

if __name__ == "__main__":
    print("fuel detail rows:", len(fd), " fuels:", sorted(fd.fuel.unique()))
    print("capex detail rows:", len(cd), " techs:", sorted(cd.technology.unique()))
