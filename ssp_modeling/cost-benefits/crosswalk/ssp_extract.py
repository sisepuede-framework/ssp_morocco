"""Shared loader for the Morocco SISEPUEDE run used by the crosswalk deliverables.

Run: 2026-07-16T18;06;11.475894  (the run behind the 2026-07-19 investment/CB files)
Scenarios (primary_id): BASE=0 (no-action), BAU=72072 (SNBC ref), LEDS=73073 (LTS)
time_period t -> Year = t + 2015 ; deliverable horizon = 2023..2050 (t=8..35)
Monetary NEMOMOD/ENFU-totalvalue columns are in MILLIONS of 2019 USD.
"""
import pandas as pd
import functools

SSP = "/Users/fabianfuentes/git/ssp_morocco/ssp_modeling"
RUN = "sisepuede_results_sisepuede_run_2026-07-16T18;06;11.475894"
WIDE = f"{SSP}/ssp_run_output/{RUN}/{RUN}_WIDE_INPUTS_OUTPUTS.csv"

BASE, BAU, LEDS = 0, 72072, 73073
YEARS = list(range(2023, 2051))   # deliverable horizon

@functools.lru_cache(maxsize=1)
def load():
    df = pd.read_csv(WIDE)
    df["Year"] = df["time_period"] + 2015
    return df

def series(col, pid):
    """Year-indexed series for one column and one scenario."""
    df = load()
    return df[df.primary_id == pid].set_index("Year")[col]

def cumdiff(col, pid_hi, pid_lo, years=YEARS):
    """Cumulative (hi - lo) over the horizon for one column."""
    return (series(col, pid_hi).loc[years] - series(col, pid_lo).loc[years]).sum()

def cols_with_prefix(prefix):
    return [c for c in load().columns if c.startswith(prefix)]
