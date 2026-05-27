"""
Construye dos CSVs a partir de df_input_1.csv:
  - df_input_baseline_mix.csv:  mix BAU 62% coal / 15% wind / 10% gas / 4% oil / 4% solar / 5% hydro (constante)
  - df_input_renewable_2050.csv: rampa 2030->2050 hasta 95% renovables (solar/wind/hydro/biomass)

Time periods en df_input_1.csv: t=0..55 -> 2015..2070.
Año pivote para inicio de la transición: t=15 (2030).
Año objetivo 95% renovables: t=35 (2050). Se mantiene 2050..2070.
"""
import pandas as pd
import numpy as np
from pathlib import Path

SRC = Path("/Users/fabianfuentes/git/ssp_morocco/ssp_modeling/input_data/df_input_1.csv")
OUT_BASE = SRC.parent / "df_input_baseline_mix.csv"
OUT_REN = SRC.parent / "df_input_renewable_2050.csv"

df = pd.read_csv(SRC)
n = len(df)  # 56

# --- 1. MSP baseline (constante) ---------------------------------------------
MSP_BASE = {
    "pp_coal":        0.62,
    "pp_wind":        0.15,
    "pp_gas":         0.10,
    "pp_oil":         0.04,
    "pp_solar":       0.04,
    # suma = 0.95; el 5% restante lo absorbe el LP (tipicamente pp_hydropower por su residual capacity)
}
ALL_PP = [
    "pp_biogas", "pp_biomass", "pp_coal", "pp_coal_ccs", "pp_gas", "pp_gas_ccs",
    "pp_geothermal", "pp_hydropower", "pp_nuclear", "pp_ocean", "pp_oil",
    "pp_solar", "pp_waste_incineration", "pp_wind",
]

def msp_col(tech):  return f"nemomod_entc_frac_min_share_production_{tech}"
def inv_col(tech):  return f"nemomod_entc_total_annual_max_capacity_investment_{tech}_gw"
def cap_col(tech):  return f"nemomod_entc_total_annual_max_capacity_{tech}_gw"
def mpi_col(tech):  return f"frac_entc_max_elec_production_increase_to_satisfy_msp_{tech}"

# --- 2. Construir baseline ---------------------------------------------------
df_base = df.copy()

# fijar MSP baseline (constante todo el horizonte)
for t in ALL_PP:
    df_base[msp_col(t)] = MSP_BASE.get(t, 0.0)

# Aflojar topes de inversion en tecnologias que la estrategia renovable va a necesitar:
# pp_wind hoy = 0.2 GW/yr -> -999 (sin tope), pp_biomass hoy = 0 -> -999
# pp_solar/pp_hydropower ya estan en -999.
for t in ["pp_wind", "pp_biomass", "pp_solar", "pp_hydropower"]:
    if inv_col(t) in df_base.columns:
        df_base[inv_col(t)] = -999.0

# Para fp_* (fuel production) y storage no tocamos nada.

# Verificacion: suma MSP por año
msp_sum = sum(df_base[msp_col(t)].values for t in ALL_PP)
assert (msp_sum <= 1.0 + 1e-9).all(), f"Σ MSP > 1 en baseline: max={msp_sum.max()}"
print(f"[baseline] Σ MSP por año = {msp_sum[0]:.3f}  (constante)")

df_base.to_csv(OUT_BASE, index=False)
print(f"[baseline] escrito: {OUT_BASE}")

# --- 3. Construir estrategia renovables 2050 ---------------------------------
# Trayectoria: 2015..2029 baseline, 2030..2050 rampa lineal, 2050..2070 plano.
# Mix objetivo 2050 (suma = 0.95 para dejar 5% de holgura al LP):
MSP_2050 = {
    "pp_solar":      0.45,
    "pp_wind":       0.30,
    "pp_hydropower": 0.10,
    "pp_biomass":    0.05,
    "pp_geothermal": 0.05,   # opcional; se anula abajo si max_capacity=0
    "pp_coal":       0.00,
    "pp_gas":        0.00,
    "pp_oil":        0.00,
}

# Comprobar tecnologias deshabilitadas (max_capacity = 0 en todos los años) y mover su MSP_2050 a solar
for t in list(MSP_2050.keys()):
    col = cap_col(t)
    if col in df.columns:
        max_caps = df[col].unique()
        if len(max_caps) == 1 and max_caps[0] == 0.0 and MSP_2050[t] > 0:
            print(f"[renewable] {t} esta deshabilitada (max_capacity=0). Reasignando su MSP_2050 a pp_solar.")
            MSP_2050["pp_solar"] += MSP_2050[t]
            MSP_2050[t] = 0.0

assert abs(sum(MSP_2050.values()) - 0.95) < 1e-6, f"objetivo 2050 suma {sum(MSP_2050.values())}"

df_ren = df_base.copy()

T_START = 15   # 2030
T_TARGET = 35  # 2050
years = np.arange(n)

def ramp(v_base, v_target):
    """Vector de longitud n: baseline hasta T_START, rampa lineal hasta T_TARGET, plano hasta el final."""
    out = np.full(n, v_base, dtype=float)
    for i in range(T_START, T_TARGET + 1):
        w = (i - T_START) / (T_TARGET - T_START)
        out[i] = (1 - w) * v_base + w * v_target
    out[T_TARGET + 1:] = v_target
    return out

for t in ALL_PP:
    v0 = MSP_BASE.get(t, 0.0)
    v1 = MSP_2050.get(t, 0.0)
    df_ren[msp_col(t)] = ramp(v0, v1)

# Verificacion: suma MSP año a año
msp_sum_r = sum(df_ren[msp_col(t)].values for t in ALL_PP)
print(f"[renewable] Σ MSP:  t0={msp_sum_r[0]:.3f}  t15={msp_sum_r[15]:.3f}  t35={msp_sum_r[35]:.3f}  t55={msp_sum_r[55]:.3f}")
assert (msp_sum_r <= 1.0 + 1e-9).all()

# En la estrategia, garantizar que TotalAnnualMaxCapacityInvestment NO bloquee la expansion:
for t in ["pp_solar", "pp_wind", "pp_biomass", "pp_hydropower"]:
    if inv_col(t) in df_ren.columns:
        df_ren[inv_col(t)] = -999.0

# Dejar `max_elec_production_increase_to_satisfy_msp` en -999 para no introducir conflictos
for t in ALL_PP:
    if mpi_col(t) in df_ren.columns:
        df_ren[mpi_col(t)] = -999.0

df_ren.to_csv(OUT_REN, index=False)
print(f"[renewable] escrito: {OUT_REN}")

# --- 4. Resumen mix por tecnologia en años clave -----------------------------
print("\n=== Mix renovable (MSP en años clave) ===")
print(f"{'tech':22s}  2015   2030   2040   2050   2070")
for t in ALL_PP:
    v = df_ren[msp_col(t)].values
    if max(v) > 0:
        print(f"{t:22s}  {v[0]:.2f}   {v[15]:.2f}   {v[25]:.2f}   {v[35]:.2f}   {v[55]:.2f}")

ren_techs = ["pp_solar", "pp_wind", "pp_hydropower", "pp_biomass", "pp_geothermal", "pp_ocean", "pp_biogas"]
ren_share = sum(df_ren[msp_col(t)].values for t in ren_techs)
print(f"\nFraccion renovable (Σ MSP):  2015={ren_share[0]:.2f}  2030={ren_share[15]:.2f}  2050={ren_share[35]:.2f}  2070={ren_share[55]:.2f}")
