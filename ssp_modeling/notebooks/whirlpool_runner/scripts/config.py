"""
config.py  (whirlpool — Morocco)
--------------------------------
All configuration constants for the whirlpool experiment.
Edit RUN_ID / TORNADO_RUN_ID (or leave them as None to auto-detect) and the
experiment parameters here; everything else is derived.

Whirlpool design
----------------
Each strategy is the FULL portfolio minus ONE transformation
(strategy_code = 'WHIRLPOOL_PFLO_LEDS:TX:<SECTOR>:<NAME>'), so the reference for
emissions and costs in the MAC is the complete portfolio — 'PFLO:LEDS' for
Morocco (it was 'PFLO:CONDITIONAL' for Libya).

Cost-benefits still runs against 'BASE': CostBenefits produces costs relative to
BASE and mac_pipeline then re-bases them on the portfolio by subtracting the
portfolio's own technical cost.

Morocco vs Libya (what changed)
-------------------------------
  - ISO_CODE3 / REGION   : MAR / morocco      (was LBY / libya)
  - YEAR_REF             : 2018               (was 2023) — Morocco NIR reference
  - YEAR_END             : 2050 (sim_end_year) (was 2070)
  - Portfolio baseline   : PFLO:LEDS          (was PFLO:CONDITIONAL)
  - TARGETS_PATH         : emission_targets_mar_2018.csv
  - INVENT_HISTORIC_PATH : invent_historic_mar.csv
  - TABLEAU_DIR          : ssp_modeling/tableau/data (same dir the WB manager writes)
  - REGION / YEAR_END are read from notebooks/config_files/config.yaml so this
    file never drifts from the run configuration.
"""

import pathlib

import pandas as _pd
import yaml as _yaml

# ── Directory layout (derived from this file's location) ─────────────────────
SCRIPTS_DIR       = pathlib.Path(__file__).parent.resolve()
RUNNER_DIR        = SCRIPTS_DIR.parent                      # whirlpool_runner/
NOTEBOOKS_DIR     = RUNNER_DIR.parent                       # notebooks/
SSP_MODELING_DIR  = NOTEBOOKS_DIR.parent                    # ssp_modeling/
PROJECT_DIR       = SSP_MODELING_DIR.parent                 # repo root

DATA_DIR          = SSP_MODELING_DIR / "input_data"
RUN_OUTPUT_DIR    = SSP_MODELING_DIR / "ssp_run_output"
CONFIG_DIR        = NOTEBOOKS_DIR / "config_files"

# ── Run configuration (single source of truth: notebooks/config_files/config.yaml)
with open(CONFIG_DIR / "config.yaml", "r") as _f:
    _CONFIG = _yaml.safe_load(_f)

REGION       = _CONFIG["country_name"]                      # "morocco"
ISO_CODE3    = _CONFIG.get("country_code", "MAR")           # "MAR"

# ── Model time range ──────────────────────────────────────────────────────────
YEAR_START = 2015
YEAR_END   = _CONFIG.get("sim_end_year", 2050)              # Morocco runs to 2050

# ── Post-processing parameters ────────────────────────────────────────────────
YEAR_REF     = 2018                                         # Morocco NIR reference year
INVENT_DIR   = SSP_MODELING_DIR / "output_postprocessing" / "data" / "invent"
TARGETS_PATH = INVENT_DIR / f"emission_targets_{ISO_CODE3.lower()}_{YEAR_REF}.csv"
INVENT_HISTORIC_PATH = INVENT_DIR / f"invent_historic_{ISO_CODE3.lower()}.csv"

# primary_id suffix of the baseline scenario inside the decomposition.
# Morocco's BASE strategy (strategy_id 0) maps to primary_id 0.
INITIAL_CONDITIONS_ID = "_0"

# ── Runs to analyze ───────────────────────────────────────────────────────────
# Set these explicitly to pin runs; leave None to auto-detect:
#   RUN_ID         → most recent run dir holding a *_WIDE_INPUTS_OUTPUTS.csv
#   TORNADO_RUN_ID → most recent run dir holding marginal_abatement_costs_tornado.csv
RUN_ID: str | None         = "sisepuede_results_sisepuede_run_2026-09-17T17;28;54.353650"   # whirlpool Morocco, 44 primaries
# Pinned on purpose: the whirlpool run dir also holds a stray
# marginal_abatement_costs_tornado.csv (tornado runner once pointed at it), so the
# auto-detect would pick the whirlpool run itself as the tornado reference.
TORNADO_RUN_ID: str | None = "sisepuede_results_sisepuede_run_2026-09-17T16;54;17.970763"   # tornado Morocco, 44 primaries


def _latest_run_id(marker: str = "*_WIDE_INPUTS_OUTPUTS.csv", what: str = "wide-format export") -> str:
    """Most recently modified run dir containing a file matching *marker*."""
    candidates = [
        d for d in RUN_OUTPUT_DIR.iterdir()
        if d.is_dir() and any(d.glob(marker))
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No run directory with a {what} ({marker}) found under {RUN_OUTPUT_DIR}. "
            "Run the corresponding notebook first, or set the RUN_ID explicitly."
        )
    return max(candidates, key=lambda d: d.stat().st_mtime).name


RUN_ID            = RUN_ID or _latest_run_id()
RUN_ID_OUTPUT_DIR = RUN_OUTPUT_DIR / RUN_ID

# ── Tornado run reference (for the tornado vs whirlpool comparison) ───────────
# Produced by tornado_runner/run_experiment.ipynb.
# Not fatal at import time: steps 1-4 do not need the tornado run, so a missing
# tornado MAC only blocks the comparison steps (5-6), which assert on their own.
if TORNADO_RUN_ID is None:
    try:
        TORNADO_RUN_ID = _latest_run_id(
            "marginal_abatement_costs_tornado.csv", "tornado MAC export"
        )
    except FileNotFoundError:
        print(
            "[config] WARNING: no tornado MAC found under ssp_run_output/. "
            "Run tornado_runner/run_experiment.ipynb first — steps 5 and 6 "
            "(Tableau whirlpool + tornado comparison) will fail until then."
        )

TORNADO_RUN_DIR      = RUN_OUTPUT_DIR / TORNADO_RUN_ID if TORNADO_RUN_ID else None
TORNADO_MAC_PATH     = TORNADO_RUN_DIR / "marginal_abatement_costs_tornado.csv" if TORNADO_RUN_DIR else None
TORNADO_ATT_MAP_PATH = TORNADO_RUN_DIR / "ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv" if TORNADO_RUN_DIR else None

# ── Output paths for intermediate results ─────────────────────────────────────
OUTPUT_DECOMPOSED = RUN_ID_OUTPUT_DIR / "decomposed_ssp_output_whirlpool.csv"
OUTPUT_CB_DATA    = RUN_ID_OUTPUT_DIR / "cost_benefits_data_whirlpool.csv"
OUTPUT_MAC        = RUN_ID_OUTPUT_DIR / "marginal_abatement_costs_whirlpool.csv"

# ── Tableau output ────────────────────────────────────────────────────────────
# Same directory the WB manager notebook writes to (ssp_modeling/tableau/data).
TABLEAU_DIR                     = SSP_MODELING_DIR / "tableau" / "data"
OUTPUT_TABLEAU_WHIRLPOOL        = TABLEAU_DIR / "tableau_whirlpool.csv"
OUTPUT_MAC_TORNADO_TO_WHIRLPOOL = TABLEAU_DIR / "mac_tornado_to_whirlpool.csv"

# ── Cost-benefits parameters ──────────────────────────────────────────────────
CB_CONFIG_PATH = SSP_MODELING_DIR / "cost-benefits" / "cb_config_files" / "cb_config_params.xlsx"
CB_OUTPUT_PATH = SSP_MODELING_DIR / "cost-benefits" / "out"

# ── Strategy codes ────────────────────────────────────────────────────────────
STRATEGY_CODE_BASE      = "BASE"        # reference used by CostBenefits
STRATEGY_CODE_PORTFOLIO = "PFLO:LEDS"   # full portfolio — MAC baseline (was PFLO:CONDITIONAL in Libya)

# ── MAC cumulative window ─────────────────────────────────────────────────────
# First year included when cumulating emissions/costs for the MAC ratio.
# None  → falls back to the last year of the historical inventory (2018 for MAR;
#         this reproduces the Libya behaviour, where that year was 2023).
# Set to 2025 to cumulate only over the policy horizon.
# Keep this IDENTICAL to the tornado config, or the two MACs are not comparable.
YEAR_CUMUL_START: int | None = None

# ── Primary IDs to analyze (whirlpool strategy set) ───────────────────────────
PRIMARY_IDS_FILTER = sorted(
    _pd.read_csv(RUN_ID_OUTPUT_DIR / "ATTRIBUTE_PRIMARY.csv")["primary_id"].tolist()
)
