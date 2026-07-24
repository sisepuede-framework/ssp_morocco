"""Task 2 — fuel cost savings and capex, both BY GENERATION TECHNOLOGY, from NEMOMOD.

Fuel savings = change in ENTC fuel consumption value (BASE - LEDS), by fuel, mapped to
the plant type that burns it. Renewables burn no fuel -> zero (correct; the saving shows
up as reduced coal/oil/gas fuel purchase). This is NOT the CB 'Fuel cost savings (power
sector)' row, which is a residual bucket of demand-side + allocated electricity costs.

Capex = discounted capital investment by generation technology (LEDS - BASE).

Outputs (millions of 2019 USD): build/task2_fuel_savings.csv, build/task2_capex.csv
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
# renewables consume no combustible fuel -> zero fuel savings, listed explicitly
RENEWABLES = ["pp_solar", "pp_wind", "pp_hydropower", "pp_geothermal", "pp_ocean"]

# ---------- FUEL SAVINGS BY TECH ----------
tv_prefix = "totalvalue_enfu_fuel_consumed_entc_fuel_"
rows = []
for c in cols_with_prefix(tv_prefix):
    fuel = c[len(tv_prefix):]
    if fuel == "electricity":            # own-use, not generation fuel
        continue
    tech = FUEL_TO_TECH.get(fuel)
    if tech is None:
        continue
    b = series(c, BASE).loc[YEARS]
    l = series(c, LEDS).loc[YEARS]
    saving = b - l                        # positive = fuel purchase avoided
    for y in YEARS:
        rows.append({"Year": y, "technology": tech, "fuel": fuel,
                     "fuel_saving_musd": saving.loc[y]})
fs = pd.DataFrame(rows)
fs_tech = fs.groupby(["Year", "technology"], as_index=False)["fuel_saving_musd"].sum()
# add renewables at zero for completeness
for t in RENEWABLES:
    add = pd.DataFrame({"Year": YEARS, "technology": t, "fuel_saving_musd": 0.0})
    fs_tech = pd.concat([fs_tech, add], ignore_index=True)
fs_tech.to_csv("task2_fuel_savings.csv", index=False)

# ---------- CAPEX BY TECH ----------
cap_prefix = "nemomod_entc_discounted_capital_investment_pp_"
rows = []
for c in cols_with_prefix(cap_prefix):
    tech = "pp_" + c[len(cap_prefix):]
    b = series(c, BASE).loc[YEARS]
    l = series(c, LEDS).loc[YEARS]
    inc = l - b                           # positive = extra investment in LTS
    for y in YEARS:
        rows.append({"Year": y, "technology": tech, "capex_incremental_musd": inc.loc[y]})
cx = pd.DataFrame(rows)
cx.to_csv("task2_capex.csv", index=False)

# ---------- reconciliation printout ----------
def cum(dfx, val, key="technology"):
    return dfx.groupby(key)[val].sum().sort_values(key=lambda s: -s.abs())

print("=== FUEL COST SAVINGS by technology (cumulative 2023-50, million 2019 USD) ===")
fsum = cum(fs_tech, "fuel_saving_musd")
for k, v in fsum.items():
    print(f"  {k:22s} {v/1000:9.2f} bn")
print(f"  {'TOTAL':22s} {fsum.sum()/1000:9.2f} bn   (CB 'power sector' row = 9.76 bn — different thing)")

print("\n=== CAPEX by technology (incremental LTS-BASE, cumulative 2023-50, million USD) ===")
csum = cum(cx, "capex_incremental_musd")
for k, v in csum.items():
    print(f"  {k:22s} {v/1000:9.2f} bn")
print(f"  {'NET TOTAL':22s} {csum.sum()/1000:9.2f} bn")
pos = cx[cx.capex_incremental_musd > 0].groupby("technology")["capex_incremental_musd"].sum()
print(f"  {'GROSS ADDITIONS':22s} {pos.sum()/1000:9.2f} bn  (positive builds only)")
print("  gross-addition shares (feed Task 1 power cost-vector):")
for k, v in (pos/pos.sum()).sort_values(ascending=False).items():
    print(f"    {k:20s} {v*100:5.1f}%")
