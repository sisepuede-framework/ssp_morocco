"""
config.py  (tornado — Morocco)
------------------------------
All configuration constants for the tornado experiment.
Edit RUN_ID (or leave it as None to auto-detect the latest run) and the
experiment parameters here; everything else is derived.

Tornado design
--------------
Each strategy adds ONE transformation on top of TX:BASE
(strategy_code = 'TORNADO_BASE:TX:<SECTOR>:<NAME>'), so 'BASE' is the reference
for BOTH emissions and costs.

Key differences vs whirlpool:
  - STRATEGY_CODE_BASE  : 'BASE'  (emission AND cost baseline in MAC)
  - Output suffix       : _tornado

Morocco vs Libya (what changed)
-------------------------------
  - ISO_CODE3 / REGION  : MAR / morocco      (was LBY / libya)
  - YEAR_REF            : 2018               (was 2023) — Morocco NIR reference
  - YEAR_END            : 2050 (sim_end_year) (was 2070)
  - TARGETS_PATH        : emission_targets_mar_2018.csv
  - INVENT_HISTORIC_PATH: invent_historic_mar.csv
  - TABLEAU_DIR         : ssp_modeling/tableau/data (same dir the WB manager writes)
  - REGION / YEAR_END are read from notebooks/config_files/config.yaml so this
    file never drifts from the run configuration.
"""

import pathlib

import pandas as _pd
import yaml as _yaml

# ── Directory layout (derived from this file's location) ─────────────────────
SCRIPTS_DIR       = pathlib.Path(__file__).parent.resolve()
RUNNER_DIR        = SCRIPTS_DIR.parent                      # tornado_runner/
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

# ── Run to analyze ────────────────────────────────────────────────────────────
# Set RUN_ID explicitly to pin a run; leave None to pick the most recent run
# directory that contains a *_WIDE_INPUTS_OUTPUTS.csv file.
RUN_ID: str | None = None


def _latest_run_id() -> str:
    """Most recently modified run dir holding a wide-format export."""
    candidates = [
        d for d in RUN_OUTPUT_DIR.iterdir()
        if d.is_dir() and any(d.glob("*_WIDE_INPUTS_OUTPUTS.csv"))
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No run directory with a *_WIDE_INPUTS_OUTPUTS.csv found under {RUN_OUTPUT_DIR}. "
            "Run the tornado manager notebook first, or set RUN_ID explicitly."
        )
    return max(candidates, key=lambda d: d.stat().st_mtime).name


RUN_ID            = RUN_ID or _latest_run_id()
RUN_ID_OUTPUT_DIR = RUN_OUTPUT_DIR / RUN_ID

# ── Output paths for intermediate results ─────────────────────────────────────
OUTPUT_DECOMPOSED = RUN_ID_OUTPUT_DIR / "decomposed_ssp_output_tornado.csv"
OUTPUT_CB_DATA    = RUN_ID_OUTPUT_DIR / "cost_benefits_data_tornado.csv"
OUTPUT_MAC        = RUN_ID_OUTPUT_DIR / "marginal_abatement_costs_tornado.csv"

# ── Tableau output ────────────────────────────────────────────────────────────
# Same directory the WB manager notebook writes to (ssp_modeling/tableau/data).
TABLEAU_DIR            = SSP_MODELING_DIR / "tableau" / "data"
OUTPUT_TABLEAU_TORNADO = TABLEAU_DIR / "tableau_tornado.csv"

# ── Cost-benefits parameters ──────────────────────────────────────────────────
CB_CONFIG_PATH = SSP_MODELING_DIR / "cost-benefits" / "cb_config_files" / "cb_config_params.xlsx"
CB_OUTPUT_PATH = SSP_MODELING_DIR / "cost-benefits" / "out"

# ── Strategy codes ────────────────────────────────────────────────────────────
# In tornado, 'BASE' is the reference for both emissions AND costs in MAC.
STRATEGY_CODE_BASE     = "BASE"
STRATEGY_CODE_BASELINE = "BASE"   # alias used by mac_pipeline

# ── MAC cumulative window ─────────────────────────────────────────────────────
# First year included when cumulating emissions/costs for the MAC ratio.
# None  → falls back to the last year of the historical inventory (2018 for MAR;
#         this reproduces the Libya behaviour, where that year was 2023).
# Set to 2025 to cumulate only over the policy horizon.
YEAR_CUMUL_START: int | None = None

# ── Primary IDs to analyze (tornado strategy set) ─────────────────────────────
PRIMARY_IDS_FILTER = sorted(
    _pd.read_csv(RUN_ID_OUTPUT_DIR / "ATTRIBUTE_PRIMARY.csv")["primary_id"].tolist()
)
