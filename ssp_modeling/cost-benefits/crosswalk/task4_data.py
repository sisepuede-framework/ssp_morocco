"""Task 4 — vehicle numbers (fleet) and energy-mix export.

Vehicles: fleet = VKT / annual-km-per-vehicle, the established approach
(trucks 60,000 km/yr from ssp_modeling/notebooks/transport/improve_transport_baseline.ipynb).
VKT comes straight from vehicle_distance_traveled_trns_<mode>_<fuel> (vehicle-km).

Energy mix: exported from the Tableau 'drivers' datasource (drivers_morocco.csv), the same
data behind the dashboard's energy-mix views.
"""
import os, re
import pandas as pd
from ssp_extract import load, LEDS, BASE, BAU, YEARS

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVERS = "/Users/fabianfuentes/git/ssp_morocco/ssp_modeling/tableau/data/drivers_morocco.csv"

# Number-of-vehicles logic RECONSTRUCTED from the Tableau workbook
# (Morocco_CaseStudy_2026_07_16.twb), sheets "EVs-Private" and "EVs-Public":
#   Value_road_ligth = [value]/12000     (private light-duty vehicles)
#   Value_public     = [value]/60000     (public transport AND road_heavy_freight; the
#                                         "EVs-Public" view plots both on Value_public)
# where [value] = vehicle_distance_traveled_trns_<mode>_<fuel> (vehicle-km).
DIVISOR = {"road_light": 12000, "public": 60000, "road_heavy_freight": 60000}
FLEET_MODES = list(DIVISOR.keys())

# Tableau strategy aliases (raw run code -> display label)
STRAT = {
    BASE:  "Business as Usual - CDN",     # Strategy TX:BASE
    BAU:   "Baseline Scenario - SNBC",    # bau  (PFLO:BAU)
    LEDS:  "LTS",                          # LEDS (PFLO:LEDS)
}
STRAT_RAW = {BASE: "BASE", BAU: "bau", LEDS: "LEDS"}
FUEL_ORDER = ["electricity", "gasoline", "diesel", "hydrocarbon_gas_liquids",
              "hydrogen", "biofuels", "natural_gas"]


def vehicles():
    """Long table: strategy, mode, fuel, Year, vkm, divisor, vehicles (= vkm/divisor)."""
    df = load()
    out = []
    for pid, label in STRAT.items():
        d = df[df.primary_id == pid].set_index("Year")
        for mode in FLEET_MODES:
            div = DIVISOR[mode]
            fuelcols = [c for c in df.columns
                        if re.match(rf"vehicle_distance_traveled_trns_{mode}_[a-z]", c)]
            for c in fuelcols:
                fuel = c[len(f"vehicle_distance_traveled_trns_{mode}_"):]
                for y in YEARS:
                    vkm = d.loc[y, c]
                    out.append({"strategy": label, "strategy_raw": STRAT_RAW[pid],
                                "mode": mode, "fuel": fuel, "source_var": c, "Year": y,
                                "vkm": vkm, "divisor": div, "vehicles": vkm / div})
    v = pd.DataFrame(out)
    v.to_csv(os.path.join(HERE, "task4_vehicles_detail.csv"), index=False)
    return v


def elec_production_pj():
    """Electricity production by technology (PJ) straight from the raw wide run, per scenario.
    Source: nemomod_entc_annual_production_by_technology_pp_<tech>. Returns
    {scenario_label: DataFrame(index=Year, columns=tech)} and the tech order."""
    df = load()
    prefix = "nemomod_entc_annual_production_by_technology_pp_"
    cols = [c for c in df.columns if c.startswith(prefix)]
    out = {}
    for pid, label in STRAT.items():
        d = df[df.primary_id == pid].set_index("Year")
        piv = pd.DataFrame({c[len(prefix):]: d[c] for c in cols}).loc[YEARS]
        out[label] = piv
    # order technologies by max share across all scenarios (big first)
    allsum = sum(out[l].sum() for l in out)
    order = allsum.sort_values(ascending=False).index.tolist()
    order = [t for t in order if allsum[t] > 0]
    return {l: out[l][order] for l in out}, order


def energy_mix():
    d = pd.read_csv(DRIVERS)
    d = d[d["strategy"] == "LEDS"]
    # electricity generation by technology
    gen = d[d["model_variable"] == "NemoMod Production by Technology"]
    gen_piv = gen.pivot_table(index="Year", columns="category_value", values="value", aggfunc="sum").fillna(0)
    # total energy demand by fuel
    tot = d[d["model_variable"] == "Total Energy Demand by Fuel"]
    tot_piv = tot.pivot_table(index="Year", columns="category_value", values="value", aggfunc="sum").fillna(0)
    # energy demand by fuel per demand sector
    sectors = {"Transportation": "Energy Demand by Fuel in Transportation",
               "Buildings (SCOE)": "Energy Demand by Fuel in SCOE",
               "Industrial Energy": "Energy Demand by Fuel in Industrial Energy"}
    sec_pivs = {}
    for lbl, mv in sectors.items():
        s = d[d["model_variable"] == mv]
        if len(s):
            sec_pivs[lbl] = s.pivot_table(index="Year", columns="category_value", values="value", aggfunc="sum").fillna(0)
    units = d.loc[d["model_variable"] == "NemoMod Production by Technology", "Units"].dropna().unique().tolist()
    return gen_piv, tot_piv, sec_pivs, units


if __name__ == "__main__":
    v = vehicles()
    print("=== vehicles 2050 by strategy (millions) — reconstructed with Tableau divisors ===")
    for mode in FLEET_MODES:
        print(f"-- {mode} (÷{DIVISOR[mode]}):")
        for lab in ["Business as Usual - CDN", "Baseline Scenario - SNBC", "LTS"]:
            m = v[(v["mode"] == mode) & (v.strategy == lab) & (v.Year == 2050)]
            tot = m["vehicles"].sum()/1e6
            ev = m[m.fuel == "electricity"]["vehicles"].sum()/1e6
            print(f"   {lab:30s} total {tot:6.2f}M  electric {ev:6.2f}M")
    gen, tot, secs, units = energy_mix()
    print("\nelectricity generation techs:", list(gen.columns), "units:", units)
    print("2050 generation shares:")
    s = gen.loc[2050]/gen.loc[2050].sum()
    for k, val in s.sort_values(ascending=False).items():
        if val > 0.005:
            print(f"  {k:20s} {val*100:5.1f}%")
