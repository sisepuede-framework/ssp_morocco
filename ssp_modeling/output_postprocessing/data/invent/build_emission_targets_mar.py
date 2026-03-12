#!/usr/bin/env python3
"""
Build emission_targets_mar_2022.csv from NIR 2024 verified values.

Sources (all independently verified by blind agents):
  Tableau 19 p.92:   Energy module, raw CO2/CH4/N2O in Gg, 2022
  Tableau 27 p.107:  Energy CO2-only by subcategory, 2022
  Tableau 83 p.189:  Agriculture module, raw CO2/CH4/N2O in Gg, 2022
  Tableau 2  p.33:   Master summary by sector, Gg CO2eq, 2022
  Tableau 126 p.273: Waste module, raw CH4/N2O in Gg, 2022
  Tableau 55 p.150:  IPPU emissions detail, 2022

Activity data tables (for Layer 1 diagnostics):
  Tableau 29 p.112:  Energy fuel inputs (TJ), 1.A.1
  Tableau 33 p.119:  Manufacturing fuel inputs (TJ), 1.A.2
  Tableau 38 p.126:  Transport fuel consumption (TJ), 1.A.3
  Tableau 43 p.132:  Other sectors fuel consumption (TJ), 1.A.4
  Tableau 61 p.166:  IPPU production volumes (cement, lime, glass)
  Tableau 62 p.167:  IPPU emission factors (clinker, lime, glass)
  Tableau 67 p.172:  Metal production volumes
  Tableau 37 p.124:  Transport emissions by vehicle type

GWP (AR5): CH4=28, N2O=265
"""

import pandas as pd
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent
GWP_CH4 = 28
GWP_N2O = 265


# ═══════════════════════════════════════════════════════════════════════════
# NIR 2024 VALUES — Verified by independent blind agents
# ═══════════════════════════════════════════════════════════════════════════

# --- Tableau 19 p.92: Energy, raw Gg by subcategory ---
# Format: (IPCC_code, gas): raw_Gg
T19 = {
    # 1.A.1.a Electricity generation
    ('1A1a', 'CO2'): 32217.2539, ('1A1a', 'CH4'): 0.4334, ('1A1a', 'N2O'): 0.4720,
    # 1.A.1.b Refining (zero since 2016)
    ('1A1b', 'CO2'): 0.0, ('1A1b', 'CH4'): 0.0, ('1A1b', 'N2O'): 0.0,
    # 1.A.1.c Solid fuel production
    ('1A1c', 'CO2'): 0.0, ('1A1c', 'CH4'): 0.6552, ('1A1c', 'N2O'): 0.0,
    # 1.A.2 Manufacturing sub-industries
    ('1A2a', 'CO2'): 201.4543, ('1A2a', 'CH4'): 0.0050, ('1A2a', 'N2O'): 0.0008,  # Iron/steel
    ('1A2b', 'CO2'): 19.1980,  ('1A2b', 'CH4'): 0.0012, ('1A2b', 'N2O'): 0.0002,  # Non-ferrous metals
    ('1A2c', 'CO2'): 216.1656, ('1A2c', 'CH4'): 0.0141, ('1A2c', 'N2O'): 0.0020,  # Chemicals
    ('1A2d', 'CO2'): 102.3571, ('1A2d', 'CH4'): 0.0031, ('1A2d', 'N2O'): 0.0005,  # Paper
    ('1A2e', 'CO2'): 599.5452, ('1A2e', 'CH4'): 0.0311, ('1A2e', 'N2O'): 0.0054,  # Agro-food
    ('1A2f', 'CO2'): 3807.9491,('1A2f', 'CH4'): 0.2048, ('1A2f', 'N2O'): 0.0343,  # Non-metallic minerals
    ('1A2g', 'CO2'): 1516.2345,('1A2g', 'CH4'): 0.0592, ('1A2g', 'N2O'): 0.0114,  # Other
    # 1.A.2 total (for cross-check)
    ('1A2', 'CO2'): 6462.9038, ('1A2', 'CH4'): 0.3185, ('1A2', 'N2O'): 0.0547,
    # 1.A.3 Transport modes
    ('1A3a', 'CO2'): 83.6770,  ('1A3a', 'CH4'): 0.0006, ('1A3a', 'N2O'): 0.0023,   # Aviation
    ('1A3b', 'CO2'): 17431.1946,('1A3b', 'CH4'): 1.8526, ('1A3b', 'N2O'): 0.9032,  # Road
    ('1A3c', 'CO2'): 39.7395,  ('1A3c', 'CH4'): 0.0022, ('1A3c', 'N2O'): 0.0153,   # Rail
    ('1A3d', 'CO2'): 0.0,      ('1A3d', 'CH4'): 0.0,    ('1A3d', 'N2O'): 0.0,       # Waterborne
    ('1A3e', 'CO2'): 50.6550,  ('1A3e', 'CH4'): 0.0009, ('1A3e', 'N2O'): 0.0001,   # Pipeline
    # 1.A.3 total
    ('1A3', 'CO2'): 17605.2662, ('1A3', 'CH4'): 1.8563, ('1A3', 'N2O'): 0.9209,
    # 1.A.4 Other sectors
    ('1A4a', 'CO2'): 495.4420,  ('1A4a', 'CH4'): 8.4117, ('1A4a', 'N2O'): 0.1133,  # Commercial
    ('1A4b', 'CO2'): 7696.3403, ('1A4b', 'CH4'): 6.3498, ('1A4b', 'N2O'): 0.0887,  # Residential
    ('1A4c', 'CO2'): 2798.1605, ('1A4c', 'CH4'): 0.2164, ('1A4c', 'N2O'): 0.9310,  # Agriculture
    # 1.A.4 total
    ('1A4', 'CO2'): 10989.9428, ('1A4', 'CH4'): 14.9779, ('1A4', 'N2O'): 1.1330,
    # 1.B Fugitive
    ('1B', 'CO2'): 0.2559, ('1B', 'CH4'): 1.3587, ('1B', 'N2O'): 0.0,
}

# --- Tableau 83 p.189-190: Agriculture, raw Gg ---
T83 = {
    # 3.A Enteric by species (CH4 Gg)
    ('3A_dairy', 'CH4'): 96.20,
    ('3A_nondairy', 'CH4'): 61.97,
    ('3A_sheep', 'CH4'): 109.00,
    ('3A_other', 'CH4'): 57.83,  # includes goats, horses, mules, camels
    ('3A_pigs', 'CH4'): 0.01,
    # 3.A total
    ('3A', 'CH4'): 325.01,
    # 3.B Manure by species
    ('3B_dairy', 'CH4'): 9.36, ('3B_dairy', 'N2O'): 0.55,
    ('3B_nondairy', 'CH4'): 1.28, ('3B_nondairy', 'N2O'): 0.10,
    ('3B_sheep', 'CH4'): 4.44, ('3B_sheep', 'N2O'): 0.64,
    ('3B_pigs', 'CH4'): 0.01, ('3B_pigs', 'N2O'): 0.00,
    ('3B_other', 'CH4'): 4.97, ('3B_other', 'N2O'): 0.33,
    ('3B_indirect', 'N2O'): 1.30,
    # 3.B totals
    ('3B', 'CH4'): 20.06, ('3B', 'N2O'): 2.91,
    # 3.C Rice
    ('3C', 'CH4'): 0.44,
    # 3.D Soil N2O by source
    ('3D1a', 'N2O'): 2.78,   # Synthetic fertilizer
    ('3D1b', 'N2O'): 2.77,   # Organic (manure applied)
    ('3D1c', 'N2O'): 11.20,  # Pasture deposits
    ('3D1d', 'N2O'): 5.96,   # Crop residues
    ('3D2', 'N2O'): 7.38,    # Indirect
    # 3.D total
    ('3D', 'N2O'): 30.10,
    # 3.H Urea
    ('3H', 'CO2'): 88.0,  # already CO2
}

# --- Tableau 126 p.273: Waste, raw Gg ---
T126 = {
    ('5A', 'CH4'): 133.02, ('5A', 'N2O'): 0.0,
    ('5D', 'CH4'): 78.43,  ('5D', 'N2O'): 2.84,
}

# --- Tableau 55 p.150 + Tableau 2 p.33: IPPU, Gg CO2eq ---
T_IPPU = {
    '2A1_cement': 4546.9,
    '2A2_lime': 155.1,
    '2A3_glass': 17.2,
    '2A4_ceramics': 87.4,
    '2C1_steel': 152.6,
    '2C5_lead': 26.6,
    '2C6_zinc': 118.3,
    '2D1_lubricants': 28.7,
    '2D2_paraffin': 0.76,
    '2D4_solvents': 17.4,
    '2F_hfc': 758.3,
}

# --- Activity Data (Layer 1) ---
# Tableau 43 p.132: Fuel consumption TJ
ACTIVITY = {
    'fuel_tj_1A1_total_2022': 349785.98,
    'fuel_tj_1A1_liquid_2022': 43640.28,
    'fuel_tj_1A1_solid_2022': 296867.19,
    'fuel_tj_1A1_gas_2022': 5565.54,
    'fuel_tj_1A2_total_2022': 78653.77,
    'fuel_tj_1A3_total_2022': 239912.37,
    'fuel_tj_1A4a_commercial_2022': 36475.59,
    'fuel_tj_1A4b_residential_2022': 141843.84,
    'fuel_tj_1A4b_residential_2015': 121233.52,
    'fuel_tj_1A4c_agriculture_2022': 38609.00,
    # Tableau 61 p.166: Production volumes 2022
    'prod_cement_mt_2022': 12.49,
    'prod_lime_kt_2022': 205.6,
    'prod_glass_t_2022': 171550,
    'prod_ceramics_t_2022': 196228,
    # Tableau 67 p.172: Metal production 2022
    'prod_steel_kt_2022': 1907,
    'prod_lead_kt_2022': 51.17,
    'prod_zinc_kt_2022': 68.78,
    # Tableau 62 p.167: IPPU EFs
    'ef_clinker_tco2_per_t': 0.51,
    'clinker_fraction': 0.70,
    'ckd_correction': 1.02,
    'ef_lime_tco2_per_t': 0.75,
    'ef_glass_tco2_per_t': 0.20,
    'ef_steel_tco2_per_t': 0.08,
    'ef_lead_tco2_per_t': 0.52,
    'ef_zinc_tco2_per_t': 1.72,
    # Tableau 37 p.124: Transport by vehicle type (Gg CO2eq)
    'trns_cars_ggco2eq_2022': 9959.34,
    'trns_light_trucks_ggco2eq_2022': 415.18,
    'trns_heavy_trucks_buses_ggco2eq_2022': 7263.99,
    'trns_motorcycles_ggco2eq_2022': 83.90,
}


def gg_to_mt(gg, gas='CO2'):
    """Convert raw Gg of a gas to MtCO2e."""
    gwp = {'CO2': 1, 'CH4': GWP_CH4, 'N2O': GWP_N2O, 'CO2eq': 1, 'HFCS': 1, 'PFCS': 1}
    return gg * gwp.get(gas, 1) / 1000.0


# ═══════════════════════════════════════════════════════════════════════════
# BUILD ROWS
# ═══════════════════════════════════════════════════════════════════════════

# Each row: (subsector_ssp, sector, subsector, category, agg_cat, gas, ID, vars, target_MtCO2e)
# vars = colon-separated SISEPUEDE output column names

rows = []
idx = 0

def add(ssp, sector, subsec, cat, agg, gas, vid, vrs, val, source=''):
    global idx
    idx += 1
    rows.append({
        'subsector_ssp': ssp,
        'sector': sector,
        'subsector': subsec,
        'category': cat,
        'aggregation_category': agg,
        'gas': gas,
        'ID': vid,
        'vars': vrs,
        'ids': f"{idx}:{vid}",
        'target_source': source,
        'MAR': round(val, 6),
    })

# --- 1.A.1 Electricity Generation ---
gen_pp = lambda g: ':'.join([f'emission_co2e_{g}_entc_generation_pp_{t}' for t in
    ['biogas','biomass','coal','coal_ccs','gas','gas_ccs','geothermal','hydropower',
     'nuclear','ocean','oil','solar','waste_incineration','wind']])
gen_pp_co2 = lambda: ':'.join([f'emission_co2e_co2_entc_generation_pp_{t}' for t in
    ['biogas','coal','coal_ccs','gas','gas_ccs','geothermal','hydropower',
     'nuclear','ocean','oil','solar','waste_incineration','wind']])

add('entc','1 - Energy','1.A.1 - Energy Industries','1.A.1.a - Electricity and Heat','Electricity and Heat Generation','CH4',
    '1.A.1.a:CH4', gen_pp('ch4'), gg_to_mt(T19[('1A1a','CH4')],'CH4'))
add('entc','1 - Energy','1.A.1 - Energy Industries','1.A.1.a - Electricity and Heat','Electricity and Heat Generation','CO2',
    '1.A.1.a:CO2', gen_pp_co2(), gg_to_mt(T19[('1A1a','CO2')],'CO2'))
add('entc','1 - Energy','1.A.1 - Energy Industries','1.A.1.a - Electricity and Heat','Electricity and Heat Generation','N2O',
    '1.A.1.a:N2O', gen_pp('n2o'), gg_to_mt(T19[('1A1a','N2O')],'N2O'))

# 1.A.1.c Fuel production (mining/extraction)
fp_vars_ch4 = 'emission_co2e_ch4_entc_fuel_mining_and_extraction_me_coal:emission_co2e_ch4_entc_fuel_mining_and_extraction_me_crude:emission_co2e_ch4_entc_fuel_mining_and_extraction_me_natural_gas'
add('entc','1 - Energy','1.A.1 - Energy Industries','1.A.1.c - Solid Fuel Production','Fuel Production','CH4',
    '1.A.1.c:CH4', fp_vars_ch4, gg_to_mt(T19[('1A1c','CH4')],'CH4'))

# --- 1.A.2 Manufacturing (total — can't split by industry in vars without knowing exact column names per industry) ---
inen_vars = lambda g: ':'.join([f'emission_co2e_{g}_inen_{ind}' for ind in
    ['metals','chemicals','plastic','paper','electronics','glass','other_product_manufacturing',
     'recycled_glass','recycled_metals','recycled_paper','recycled_plastic',
     'recycled_rubber_and_leather','recycled_textiles','recycled_wood',
     'lime_and_carbonite','mining','wood','cement','rubber_and_leather','textiles']])
inen_co2_vars = lambda: ':'.join([f'emission_co2e_co2_inen_nbmass_{ind}' for ind in
    ['metals','chemicals','plastic','paper','electronics','glass','other_product_manufacturing',
     'recycled_glass','recycled_metals','recycled_paper','recycled_plastic',
     'recycled_rubber_and_leather','recycled_textiles','recycled_wood',
     'lime_and_carbonite','mining','wood','cement','rubber_and_leather','textiles']])

add('inen','1 - Energy','1.A.2 - Manufacturing','1.A.2 - Manufacturing','Industrial Combustion','CH4',
    '1.A.2:CH4', inen_vars('ch4'), gg_to_mt(T19[('1A2','CH4')],'CH4'))
add('inen','1 - Energy','1.A.2 - Manufacturing','1.A.2 - Manufacturing','Industrial Combustion','CO2',
    '1.A.2:CO2', inen_co2_vars(), gg_to_mt(T19[('1A2','CO2')],'CO2'))
add('inen','1 - Energy','1.A.2 - Manufacturing','1.A.2 - Manufacturing','Industrial Combustion','N2O',
    '1.A.2:N2O', inen_vars('n2o'), gg_to_mt(T19[('1A2','N2O')],'N2O'))

# --- 1.A.3 Transport (total) ---
trns_vars = lambda g: ':'.join([f'emission_co2e_{g}_trns_{m}' for m in
    ['aviation','road_light','public','road_heavy_freight','road_heavy_regional',
     'powered_bikes','rail_freight','rail_passenger','water_borne','human_powered']])

add('trns','1 - Energy','1.A.3 - Transport','1.A.3 - Transport','Transportation','CH4',
    '1.A.3:CH4', trns_vars('ch4'), gg_to_mt(T19[('1A3','CH4')],'CH4'))
add('trns','1 - Energy','1.A.3 - Transport','1.A.3 - Transport','Transportation','CO2',
    '1.A.3:CO2', trns_vars('co2'), gg_to_mt(T19[('1A3','CO2')],'CO2'))
add('trns','1 - Energy','1.A.3 - Transport','1.A.3 - Transport','Transportation','N2O',
    '1.A.3:N2O', trns_vars('n2o'), gg_to_mt(T19[('1A3','N2O')],'N2O'))

# --- 1.A.4 Other Sectors (split into 3 sub-rows per gas) ---
# 1.A.4.a Commercial
add('scoe','1 - Energy','1.A.4 - Other Sectors','1.A.4.a - Commercial','Other Combustion','CH4',
    '1.A.4.a:CH4', 'emission_co2e_ch4_scoe_commercial_municipal', gg_to_mt(T19[('1A4a','CH4')],'CH4'))
add('scoe','1 - Energy','1.A.4 - Other Sectors','1.A.4.a - Commercial','Other Combustion','CO2',
    '1.A.4.a:CO2', 'emission_co2e_co2_scoe_nbmass_commercial_municipal', gg_to_mt(T19[('1A4a','CO2')],'CO2'))
add('scoe','1 - Energy','1.A.4 - Other Sectors','1.A.4.a - Commercial','Other Combustion','N2O',
    '1.A.4.a:N2O', 'emission_co2e_n2o_scoe_commercial_municipal', gg_to_mt(T19[('1A4a','N2O')],'N2O'))

# 1.A.4.b Residential
add('scoe','1 - Energy','1.A.4 - Other Sectors','1.A.4.b - Residential','Other Combustion','CH4',
    '1.A.4.b:CH4', 'emission_co2e_ch4_scoe_residential', gg_to_mt(T19[('1A4b','CH4')],'CH4'))
add('scoe','1 - Energy','1.A.4 - Other Sectors','1.A.4.b - Residential','Other Combustion','CO2',
    '1.A.4.b:CO2', 'emission_co2e_co2_scoe_nbmass_residential', gg_to_mt(T19[('1A4b','CO2')],'CO2'))
add('scoe','1 - Energy','1.A.4 - Other Sectors','1.A.4.b - Residential','Other Combustion','N2O',
    '1.A.4.b:N2O', 'emission_co2e_n2o_scoe_residential', gg_to_mt(T19[('1A4b','N2O')],'N2O'))

# 1.A.4.c Agriculture energy
add('inen','1 - Energy','1.A.4 - Other Sectors','1.A.4.c - Agriculture Energy','Other Combustion','CH4',
    '1.A.4.c:CH4', 'emission_co2e_ch4_inen_agriculture_and_livestock', gg_to_mt(T19[('1A4c','CH4')],'CH4'))
add('inen','1 - Energy','1.A.4 - Other Sectors','1.A.4.c - Agriculture Energy','Other Combustion','CO2',
    '1.A.4.c:CO2', 'emission_co2e_co2_inen_nbmass_agriculture_and_livestock', gg_to_mt(T19[('1A4c','CO2')],'CO2'))
add('inen','1 - Energy','1.A.4 - Other Sectors','1.A.4.c - Agriculture Energy','Other Combustion','N2O',
    '1.A.4.c:N2O', 'emission_co2e_n2o_inen_agriculture_and_livestock', gg_to_mt(T19[('1A4c','N2O')],'N2O'))

# --- 1.B Fugitive ---
fgtv_vars = lambda g: ':'.join([f'emission_co2e_{g}_fgtv_fuel_{f}' for f in ['coal','oil','natural_gas']])
add('fgtv','1 - Energy','1.B - Fugitive','1.B - Fugitive','Fugitive Emissions','CH4',
    '1.B:CH4', fgtv_vars('ch4'), gg_to_mt(T19[('1B','CH4')],'CH4'))
add('fgtv','1 - Energy','1.B - Fugitive','1.B - Fugitive','Fugitive Emissions','CO2',
    '1.B:CO2', fgtv_vars('co2'), gg_to_mt(T19[('1B','CO2')],'CO2'))

# --- 2 IPPU ---
add('ippu','2 - IPPU','2.A - Mineral Industry','2.A.1 - Cement','IPPU','CO2',
    '2.A.1:CO2', 'emission_co2e_co2_ippu_production_cement', gg_to_mt(T_IPPU['2A1_cement'],'CO2eq'))
add('ippu','2 - IPPU','2.A - Mineral Industry','2.A.2 - Lime','IPPU','CO2',
    '2.A.2:CO2', 'emission_co2e_co2_ippu_production_lime_and_carbonite', gg_to_mt(T_IPPU['2A2_lime'],'CO2eq'))
add('ippu','2 - IPPU','2.A - Mineral Industry','2.A.3 - Glass','IPPU','CO2',
    '2.A.3:CO2', 'emission_co2e_co2_ippu_production_glass', gg_to_mt(T_IPPU['2A3_glass'],'CO2eq'))
add('ippu','2 - IPPU','2.C - Metal Industry','2.C - Metals','IPPU','CO2',
    '2.C:CO2', 'emission_co2e_co2_ippu_production_metals', gg_to_mt(T_IPPU['2C1_steel']+T_IPPU['2C5_lead']+T_IPPU['2C6_zinc'],'CO2eq'))
add('ippu','2 - IPPU','2.D - Non-Energy Products','2.D - Non-Energy Products','IPPU','CO2',
    '2.D:CO2', 'emission_co2e_co2_ippu_production_product_use_lubricants:emission_co2e_co2_ippu_product_use_product_use_lubricants:emission_co2e_co2_ippu_production_product_use_paraffin_wax:emission_co2e_co2_ippu_product_use_product_use_paraffin_wax:emission_co2e_co2_ippu_product_use_product_use_other',
    gg_to_mt(T_IPPU['2D1_lubricants']+T_IPPU['2D2_paraffin']+T_IPPU['2D4_solvents'],'CO2eq'))
add('ippu','2 - IPPU','2.F - F-gases','2.F - HFC','IPPU','HFCS',
    '2.F:HFCS', 'emission_co2e_hfcs_ippu_product_use_product_use_ods_refrigeration:emission_co2e_hfcs_ippu_product_use_product_use_ods_other',
    gg_to_mt(T_IPPU['2F_hfc'],'CO2eq'))

# --- 3 Agriculture ---
# 3.A.1 Enteric (total — model doesn't split enteric by species in output)
lvst_vars = ':'.join([f'emission_co2e_ch4_lvst_entferm_{s}' for s in
    ['cattle_dairy','cattle_nondairy','buffalo','sheep','goats','horses','mules','pigs','chickens']])
add('lvst','3 - AFOLU','3.A - Livestock','3.A.1 - Enteric Fermentation','Livestock','CH4',
    '3.A.1:CH4', lvst_vars, gg_to_mt(T83[('3A','CH4')],'CH4'))

# 3.A.2 Manure CH4
lsmm_ch4_vars = ':'.join([f'emission_co2e_ch4_lsmm_{s}' for s in
    ['anaerobic_digester','anaerobic_lagoon','composting','daily_spread','deep_bedding',
     'dry_lot','incineration','liquid_slurry','paddock_pasture_range','poultry_manure','storage_solid']])
add('lsmm','3 - AFOLU','3.A - Livestock','3.A.2 - Manure Management','Livestock','CH4',
    '3.A.2:CH4', lsmm_ch4_vars, gg_to_mt(T83[('3B','CH4')],'CH4'))

# 3.A.2 Manure direct N2O
lsmm_n2o_dir = ':'.join([f'emission_co2e_n2o_lsmm_direct_{s}' for s in
    ['anaerobic_digester','anaerobic_lagoon','composting','daily_spread','deep_bedding',
     'dry_lot','incineration','liquid_slurry','paddock_pasture_range','poultry_manure','storage_solid']])
n2o_3b_direct = T83[('3B','N2O')] - T83[('3B_indirect','N2O')]
add('lsmm','3 - AFOLU','3.A - Livestock','3.A.2 - Manure Management','Livestock','N2O',
    '3.A.2:N2O', lsmm_n2o_dir, gg_to_mt(n2o_3b_direct,'N2O'))

# 3.C.6 Manure indirect N2O
lsmm_n2o_ind = ':'.join([f'emission_co2e_n2o_lsmm_indirect_{s}' for s in
    ['anaerobic_digester','anaerobic_lagoon','composting','daily_spread','deep_bedding',
     'dry_lot','incineration','liquid_slurry','paddock_pasture_range','poultry_manure','storage_solid']])
add('lsmm','3 - AFOLU','3.C - Aggregate sources','3.C.6 - Indirect N2O from Manure','Agriculture and Managed Soil','N2O',
    '3.C.6:N2O', lsmm_n2o_ind, gg_to_mt(T83[('3B_indirect','N2O')],'N2O'))

# 3.C.3 Urea
add('soil','3 - AFOLU','3.C - Aggregate sources','3.C.3 - Urea','Agriculture and Managed Soil','CO2',
    '3.C.3:CO2', 'emission_co2e_co2_soil_urea_use', gg_to_mt(T83[('3H','CO2')],'CO2eq'))

# 3.C.4 Direct soil N2O (all sources EXCEPT crop residues)
n2o_soil_minus_residue = T83[('3D','N2O')] - T83[('3D1d','N2O')] - T83[('3D2','N2O')]
# Wait — 3.C.4 is "direct N2O from managed soils" which is 3.D.1 (all direct sources)
# The model vars are soil_fertilizer + soil_mineral_soils + soil_organic_soils
# These capture direct N2O from fertilizer + pasture + organic amendments
# Crop residues are in agrc subsector. Indirect is... also in soil subsector?
# For safety, set target = 3.D total - crop residues = everything the soil subsector handles
n2o_soil_target = T83[('3D','N2O')] - T83[('3D1d','N2O')]
add('soil','3 - AFOLU','3.C - Aggregate sources','3.C.4 - Direct N2O from soils','Agriculture and Managed Soil','N2O',
    '3.C.4:N2O', 'emission_co2e_n2o_soil_fertilizer:emission_co2e_n2o_soil_mineral_soils:emission_co2e_n2o_soil_organic_soils',
    gg_to_mt(n2o_soil_target,'N2O'))

# 3.C.5 Crop residue N2O
add('agrc','3 - AFOLU','3.C - Aggregate sources','3.C.5 - Crop Residue N2O','Agriculture and Managed Soil','N2O',
    '3.C.5:N2O', 'emission_co2e_n2o_agrc_crop_residues', gg_to_mt(T83[('3D1d','N2O')],'N2O'))

# --- 4 Waste ---
waso_vars = ':'.join([f'emission_co2e_ch4_waso_{t}_{w}' for t in ['landfilled','open_dump'] for w in
    ['chemical_industrial','food','glass','metal','nappies','other','paper','plastic',
     'rubber_leather','sludge','textiles','wood','yard']])
add('waso','4 - Waste','4.A - Solid Waste','4.A - Solid Waste','Solid Waste','CH4',
    '4.A:CH4', waso_vars, gg_to_mt(T126[('5A','CH4')],'CH4'))

trww_ch4 = ':'.join([f'emission_co2e_ch4_trww_{p}' for p in
    ['treated_advanced_aerobic_treatment','treated_advanced_anaerobic_treatment',
     'treated_latrine_improved_treatment','treated_latrine_unimproved_treatment',
     'treated_primary_treatment','treated_secondary_aerobic_treatment',
     'treated_secondary_anaerobic_treatment','treated_septic_treatment',
     'untreated_no_sewerage_treatment','untreated_with_sewerage_treatment']])
add('trww','4 - Waste','4.D - Wastewater','4.D - Wastewater','Wastewater Treatment','CH4',
    '4.D:CH4', trww_ch4, gg_to_mt(T126[('5D','CH4')],'CH4'))

trww_n2o = ':'.join([f'emission_co2e_n2o_trww_{p}' for p in
    ['treated_advanced_aerobic_effluent','treated_advanced_aerobic_treatment',
     'treated_advanced_anaerobic_effluent','treated_advanced_anaerobic_treatment',
     'treated_latrine_improved_effluent','treated_latrine_improved_treatment',
     'treated_latrine_unimproved_effluent','treated_latrine_unimproved_treatment',
     'treated_primary_effluent','treated_primary_treatment',
     'treated_secondary_aerobic_effluent','treated_secondary_aerobic_treatment',
     'treated_secondary_anaerobic_effluent','treated_secondary_anaerobic_treatment',
     'treated_septic_effluent','treated_septic_treatment',
     'untreated_no_sewerage_effluent','untreated_no_sewerage_treatment',
     'untreated_with_sewerage_effluent','untreated_with_sewerage_treatment']])
add('trww','4 - Waste','4.D - Wastewater','4.D - Wastewater','Wastewater Treatment','N2O',
    '4.D:N2O', trww_n2o, gg_to_mt(T126[('5D','N2O')],'N2O'))

# --- CRF 4 LULUCF (OPTIONAL — not all countries have inventory data for this) ---
# Set INCLUDE_LULUCF = False to exclude these rows from the targets file
INCLUDE_LULUCF = False

# --- CRF 4 LULUCF (from NIR Tableau 2 p.34 + Tableau 113 p.233) ---
# 4.A Forest Land: -952.72 Gg CO2e (biomass growth - harvest - fire + HWP + DOM + SOC)
# Maps to: frst subsector (sequestration + HWP + fire CH4)
frst_vars = ':'.join([
    'emission_co2e_co2_frst_sequestration_primary',
    'emission_co2e_co2_frst_sequestration_secondary',
    'emission_co2e_co2_frst_sequestration_mangroves',
    'emission_co2e_co2_frst_harvested_wood_products',
    'emission_co2e_co2_frst_forest_fires',
    'emission_co2e_ch4_frst_methane_primary',
    'emission_co2e_ch4_frst_methane_secondary',
    'emission_co2e_ch4_frst_methane_mangroves',
])
add('frst','4 - LULUCF','4.A - Forest Land','4.A - Forest Land','Forest Land','CO2eq',
    '4.A:CO2eq', frst_vars, gg_to_mt(-952.72, 'CO2eq'))

# 4.B Croplands: -431.36 Gg CO2e (perennial crop biomass + SOC)
# Maps to: agrc biomass columns (fruits, nuts, woody perennials) + lndu drained organic cropland
cropland_vars = ':'.join([
    'emission_co2e_co2_agrc_biomass_fruits',
    'emission_co2e_co2_agrc_biomass_nuts',
    'emission_co2e_co2_agrc_biomass_bevs_and_spices',
    'emission_co2e_co2_agrc_biomass_other_woody_perennial',
    'emission_co2e_co2_lndu_drained_organic_soils_croplands',
])
add('agrc','4 - LULUCF','4.B - Cropland','4.B - Cropland','Cropland','CO2',
    '4.B:CO2', cropland_vars, gg_to_mt(-431.36, 'CO2eq'))

# 4.C Grasslands: +113.59 Gg CO2e (grassland degradation, SOC loss)
# Maps to: lndu biomass sequestration grasslands + lndu drained organic pastures
# Note: POOR mapping — model doesn't separate grassland SOC well
grassland_vars = ':'.join([
    'emission_co2e_co2_lndu_biomass_sequestration_grasslands',
    'emission_co2e_co2_lndu_biomass_sequestration_pastures',
    'emission_co2e_co2_lndu_drained_organic_soils_pastures',
])
add('lndu','4 - LULUCF','4.C - Grassland','4.C - Grassland','Grassland','CO2',
    '4.C:CO2', grassland_vars, gg_to_mt(113.59, 'CO2eq'))

# 4.D Wetlands: -197.24 Gg CO2e (wetland biomass + SOC)
# Maps to: lndu biomass sequestration wetlands + lndu CH4 wetlands
wetland_vars = ':'.join([
    'emission_co2e_co2_lndu_biomass_sequestration_wetlands',
    'emission_co2e_ch4_lndu_wetlands',
])
add('lndu','4 - LULUCF','4.D - Wetlands','4.D - Wetlands','Wetlands','CO2eq',
    '4.D:CO2eq', wetland_vars, gg_to_mt(-197.24, 'CO2eq'))

# 4.E Settlements: +738.92 Gg CO2e (urban expansion onto forest/cropland/grassland)
# Maps to: lndu conversion columns TO settlements
settlement_vars = ':'.join([
    'emission_co2e_co2_lndu_conversion_croplands_to_settlements',
    'emission_co2e_co2_lndu_conversion_forests_primary_to_settlements',
    'emission_co2e_co2_lndu_conversion_forests_secondary_to_settlements',
    'emission_co2e_co2_lndu_conversion_grasslands_to_settlements',
    'emission_co2e_co2_lndu_conversion_pastures_to_settlements',
    'emission_co2e_co2_lndu_conversion_shrublands_to_settlements',
    'emission_co2e_co2_lndu_conversion_other_to_settlements',
])
add('lndu','4 - LULUCF','4.E - Settlements','4.E - Settlements','Settlements','CO2',
    '4.E:CO2', settlement_vars, gg_to_mt(738.92, 'CO2eq'))

# --- 5 CCSQ ---
add('ccsq','5 - CCSQ','5 - CCSQ','5 - CCSQ','CCSQ','CO2',
    '5:CO2', 'emission_co2e_co2_ccsq_direct_air_capture', 0.0)

# ═══════════════════════════════════════════════════════════════════════════
# BUILD DATAFRAME AND SAVE
# ═══════════════════════════════════════════════════════════════════════════

df = pd.DataFrame(rows)

# Remove LULUCF rows if not included (not all countries have LULUCF inventory data)
if not INCLUDE_LULUCF:
    df = df[~df['sector'].str.startswith('4 - LULUCF')].reset_index(drop=True)

# Assign target sources based on sector (Morocco NIR 2024 table references)
source_rules = [
    ('1 - Energy', 'NIR Tableau 19 p.92'),
    ('2 - IPPU', 'NIR Tableau 55 p.150'),
    ('3 - AFOLU', 'NIR Tableau 83 p.189-190'),
    ('4 - LULUCF', 'NIR Tableau 2 p.34 + Tableau 113 p.233'),
    ('4 - Waste', 'NIR Tableau 126 p.273'),
    ('5 - CCSQ', 'N/A'),
]
for sector_prefix, source in source_rules:
    mask = df['sector'].str.startswith(sector_prefix[:3])
    empty_mask = mask & (df['target_source'] == '')
    df.loc[empty_mask, 'target_source'] = source

out_path = OUTPUT_DIR / "emission_targets_mar_2022.csv"
df.to_csv(out_path, index=False)

# Also save activity data as JSON for the diagnostic script
import json
act_path = OUTPUT_DIR / "activity_data_mar_2022.json"
with open(act_path, 'w') as f:
    json.dump(ACTIVITY, f, indent=2)

# ═══════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("emission_targets_mar_2022.csv — Generated from NIR 2024")
print("=" * 80)
print(f"Rows: {len(df)}")
print(f"Total inventory: {df['MAR'].sum():.3f} MtCO2e")

# Cross-checks
nir_totals = {
    'Energy': 68508.3 / 1000,
    'IPPU': 5909.2 / 1000,
    'Agriculture': 18510.6 / 1000,
    'Waste': 6672.4 / 1000,
}
for sector_name, nir_val in nir_totals.items():
    model_val = df[df['sector'].str.contains(sector_name[:4], case=False)]['MAR'].sum()
    diff = model_val - nir_val
    status = "✓" if abs(diff) < 0.05 else "⚠"
    print(f"  {sector_name:12s}: {model_val:.3f} (NIR: {nir_val:.3f}, diff: {diff:+.3f}) {status}")

# Show all non-zero targets with human-readable category names
print(f"\nNon-zero targets:")
for _, r in df[df['MAR'] > 0.001].sort_values('MAR', ascending=False).iterrows():
    print(f"  {r['ID']:30s} {r['MAR']:10.6f} MtCO2e  ({r['category']})")

print(f"\nFiles: {out_path}")
print(f"        {act_path}")
