"""Task 1 crosswalk share tables — documented judgment.

Two INDEPENDENT decompositions of each investment path, each summing to 100%:
  (A) AGENT_SHARES   : investment sector -> {government, firms, households}  (financing)
  (B) COST_VECTORS   : investment sector -> {SAM destination: share}         (supply chain)
Final SAM allocation = investment_total(sector) * COST_VECTORS(sector).
Final agent allocation = investment_total(sector) * AGENT_SHARES(sector).

'Imports' is a synthetic destination inside the cost-vector 100% (SAM has no imports row):
solar modules, wind turbines, EV drivetrains and heat pumps are largely imported, so
allocating them domestically would overstate the domestic activity effect.

Power (EN - Power Industry) is split into a generation block (85%, itself split across
technologies using Task 2 gross-addition capex shares) and a transmission/grid block (15%),
each with its own cost vector — the tech-level capex from Task 2 is what lets us do this.
"""

# ---- SAM destinations (short key -> display label from Morocco_SAM_sector.xlsx) ----
SAM = {
    "crops": "crops",
    "forestry": "forestry",
    "livestock": "livestock",
    "fishery": "fishery and aquaculture",
    "extractive": "Extractive activities",
    "food_bev": "food manufacturing and beverage",
    "textile": "textile manufacturing and clothes",
    "wood": "Wood product manufacturing",
    "coking_refining": "coking and refining production",
    "chemical": "chemical products",
    "pharma": "pharmaceutical products",
    "rubber": "rubber manufacturing",
    "metalwork": "metalwork manufacturing",
    "computer_electronic": "Manufacture of computer, electronic and optical products",
    "electrical_equip": "electrical equipment manufacturing",
    "machinery_equip": "machinery and equipment manufacturing",
    "transport_equip": "transport equipment manufacturing",
    "other_manuf": "other manufacturing",
    "elec_coal": "electricity generation - coal",
    "elec_oil": "electricity generation - oil",
    "elec_gas": "electricity generation - natural gas",
    "elec_hydro": "electricity generation - hydro",
    "elec_wind": "electricity generation - wind",
    "elec_solar": "electricity generation - solar",
    "elec_other": "electricity generation - other sources",
    "elec_transmission": "electricity transmission and distribution",
    "gas_manuf": "gas manufacture, distribution",
    "water_sewerage": "water supply and sewerage",
    "construction": "construction",
    "repair_motor": "repair of motor vehicles and motorcycles",
    "transport_warehouse": "transport and warehouse",
    "accommodation_food": "Accommodation, Food and service activities",
    "info_comm": "Information and communication",
    "financial": "financial and insurance activities",
    "real_estate": "real estate",
    "rnd_support": "research and development; travel agencies; support activities",
    "public_admin": "public administration",
    "education_health": "education; health and social work",
    "other_services": "other services",
    "imports": "IMPORTS (rest of world)",   # synthetic destination
}

AGENTS = ["government", "firms", "households"]

# =====================================================================
# (A) AGENT (FINANCING) SHARES  — each row sums to 1.0
# key = investment sector label (exactly as in investment_requirements file)
# value = (gov, firms, hh, source)
# =====================================================================
AGENT_SHARES = {
 "EN - Power Industry":
   (0.25, 0.70, 0.05,
    "Morocco RE build-out is predominantly private IPP (MASEN/ACWA Power PPAs) with "
    "state offtake via ONEE; ~25% public/SOE (ONEE grid-side generation), ~5% distributed "
    "rooftop PV by households. Judgment informed by IEA Morocco 2023 & World Bank MAR energy PPPs."),
 "EN - Building":
   (0.10, 0.30, 0.60,
    "Building heat-pump / efficiency retrofits are mostly owner-financed: households "
    "(residential) 60%, commercial firms 30%, government 10% (public buildings). Our judgment."),
 "EN - Transportation":
   (0.05, 0.40, 0.55,
    "EV purchases: private households 55%, commercial/fleet firms 40%, public fleets 5%. "
    "Our judgment (Morocco has no large public EV programme yet)."),
 "EN - Industrial combustion":
   (0.05, 0.95, 0.00,
    "Industrial fuel-switch / heat equipment is financed by industrial firms; ~5% public "
    "co-funding via decarbonisation support. Our judgment."),
 "IN - Industrial processes":
   (0.05, 0.95, 0.00,
    "Cement/steel material-efficiency retrofits financed by industrial firms; minor public "
    "co-funding. Our judgment."),
 "Waste - Solid waste":
   (0.80, 0.20, 0.00,
    "Solid-waste management is a municipal/public responsibility with private operators "
    "(delegated management, e.g. Averda/SOS-NDD): government 80%, firms 20%. Our judgment "
    "informed by Morocco PNDM waste programme."),
 "Waste - Wastewater treatment (trww)":
   (0.85, 0.15, 0.00,
    "Wastewater treatment (ONEP/ONEE-Eau, municipal utilities) is public-led with private "
    "delegated operators: government 85%, firms 15%. Our judgment informed by PNA sanitation programme."),
 "Waste - Wastewater (liquid waste)":
   (0.85, 0.15, 0.00, "Zero investment in this path; shares carried for completeness."),
 "AG - Livestock (manure)":
   (0.50, 0.50, 0.00, "Zero investment in this path; shares carried for completeness."),
 "LULUCF - Forest land":
   (0.85, 0.10, 0.05,
    "Reforestation is government-led (Eaux et Forets / Forets du Maroc 2020-2030 programme) "
    "85%, private forestry firms 10%, community/household woodlots 5%. Our judgment."),
}

# =====================================================================
# (B) COST VECTORS — supply chain of what each investment buys.
# Each dict sums to 1.0 over SAM keys (incl. 'imports'). Source noted per sector.
# =====================================================================

# Power sub-block cost vectors (per generation technology + transmission).
# Import shares reflect that turbines/modules are largely imported.
CV_POWER = {
 # wind: turbines (machinery/transport-equip, ~55% imported despite Tangier assembly),
 # balance-of-plant construction, grid connection, engineering
 "wind": {"imports": 0.50, "machinery_equip": 0.10, "transport_equip": 0.05,
          "construction": 0.18, "electrical_equip": 0.07, "metalwork": 0.05, "rnd_support": 0.05},
 # solar PV: modules almost entirely imported, inverters imported, mounting/EPC local
 "solar": {"imports": 0.60, "electrical_equip": 0.08, "construction": 0.17,
           "metalwork": 0.05, "rnd_support": 0.05, "computer_electronic": 0.05},
 # biogas / other: more civil works, engines partly imported
 "biogas": {"imports": 0.35, "machinery_equip": 0.15, "construction": 0.30,
            "metalwork": 0.10, "rnd_support": 0.10},
 "nuclear": {"imports": 0.55, "construction": 0.25, "machinery_equip": 0.10, "rnd_support": 0.10},
 "transmission": {"construction": 0.45, "electrical_equip": 0.20, "metalwork": 0.10,
                  "machinery_equip": 0.08, "imports": 0.12, "rnd_support": 0.05},
}
CV_POWER_SRC = ("Technology cost-vectors from IRENA renewable power generation cost breakdowns "
                "(turbine/module vs BoP vs EPC shares) and Morocco local-content data (Siemens "
                "Gamesa Tangier wind assembly). Import shares: PV modules & wind nacelles largely "
                "imported. Generation split across technologies uses Task 2 gross-addition capex "
                "shares (wind 66%, solar 26%, biogas 6%, nuclear 2%).")
# Split of the EN - Power Industry path between generation and transmission/grid
POWER_GEN_SHARE = 0.85   # generation capex (55.8bn) vs total power path (65.5bn) ~= 0.85
POWER_TRN_SHARE = 0.15

COST_VECTORS = {
 "EN - Building": (
   {"imports": 0.45, "electrical_equip": 0.15, "construction": 0.25,
    "machinery_equip": 0.05, "wood": 0.03, "rnd_support": 0.07},
   "Heat pumps / efficient appliances largely imported (~45%); installation & building-shell "
   "works domestic construction. IEA heat-pump trade data + our judgment."),
 "EN - Transportation": (
   {"imports": 0.55, "transport_equip": 0.15, "repair_motor": 0.10,
    "electrical_equip": 0.08, "construction": 0.07, "rnd_support": 0.05},
   "EV drivetrains/batteries largely imported (~55%); local vehicle assembly (Renault/Stellantis "
   "Morocco), charger install & road works domestic. Our judgment + Morocco automotive sector data."),
 "EN - Industrial combustion": (
   {"imports": 0.40, "machinery_equip": 0.25, "metalwork": 0.12,
    "construction": 0.10, "electrical_equip": 0.08, "rnd_support": 0.05},
   "Industrial heat pumps / electric boilers / fuel-switch equipment partly imported; balance "
   "domestic machinery, metalwork, install. Our judgment."),
 "IN - Industrial processes": (
   {"machinery_equip": 0.30, "metalwork": 0.15, "construction": 0.20,
    "chemical": 0.10, "imports": 0.15, "rnd_support": 0.10},
   "Cement/steel efficiency retrofits: process equipment (partly imported), civil works, "
   "alternative-materials chemistry, engineering. Our judgment."),
 "Waste - Solid waste": (
   {"construction": 0.40, "machinery_equip": 0.20, "transport_equip": 0.10,
    "imports": 0.12, "rnd_support": 0.08, "other_services": 0.10},
   "Waste collection/sorting/composting/biogas: civil works, plant & collection vehicles "
   "(partly imported), operations. Our judgment informed by PNDM."),
 "Waste - Wastewater treatment (trww)": (
   {"construction": 0.55, "machinery_equip": 0.15, "water_sewerage": 0.12,
    "imports": 0.08, "rnd_support": 0.06, "chemical": 0.04},
   "WWTP construction dominant; pumps/membranes partly imported; utility operation & treatment "
   "chemicals. Our judgment informed by PNA."),
 "LULUCF - Forest land": (
   {"forestry": 0.35, "crops": 0.15, "rnd_support": 0.15, "public_admin": 0.10,
    "other_services": 0.10, "construction": 0.08, "transport_warehouse": 0.07},
   "Reforestation is labour- & seedling-intensive: nursery/forestry output, land prep, "
   "extension & support services, public administration. Very low import content. Our judgment."),
 # zero-investment paths carried with a neutral vector for completeness
 "Waste - Wastewater (liquid waste)": ({"construction": 1.0}, "Zero investment; placeholder."),
 "AG - Livestock (manure)": ({"construction": 1.0}, "Zero investment; placeholder."),
}
