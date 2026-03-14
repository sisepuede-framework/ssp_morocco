"""
Morocco SISEPUEDE Calibration Runner

Standalone script to run SISEPUEDE for strategies 0 (baseline) and 6005 (SNBC NDC),
produce emission tables and stacked area plots, and compare against EDGAR targets.

Usage:
    python run_calibration.py
    python run_calibration.py --strategies 0 6005
    python run_calibration.py --strategies 0 1001
    python run_calibration.py --no-energy          # Skip NemoMod (fast, no electricity)
    python run_calibration.py --quick-test          # First 12 periods only
    python run_calibration.py --baseline-only        # Run strategy 0 only

Output:
    - Stacked area emission plots (baseline + transformation)
    - Sector-level emission table at calibration year (t=7, 2022)
    - EDGAR comparison diff report (if targets file available)
    - All saved to ssp_run_output/ with timestamped subfolder
"""

import argparse
import logging
import os
import pathlib
import sys
import time
from typing import Tuple

# Give Julia/NemoMod more heap memory (set before any Julia imports)
os.environ.setdefault("JULIA_HEAP_SIZE_HINT", "8G")

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for script use
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ── SISEPUEDE imports ───────────────────────────────────────────────────────
import sisepuede as si
import sisepuede.core.attribute_table as att
import sisepuede.core.support_classes as sc
import sisepuede.manager.sisepuede_examples as sxl
import sisepuede.manager.sisepuede_file_structure as sfs
import sisepuede.manager.sisepuede_models as sm
import sisepuede.transformers as trf
import sisepuede.utilities._toolbox as sf
import sisepuede.visualization.plots as svp

from ssp_transformations_handler.GeneralUtils import GeneralUtils

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

# ── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SSP_MODELING_DIR = SCRIPT_DIR.parent
PROJECT_DIR = SSP_MODELING_DIR.parent
DATA_DIR = SSP_MODELING_DIR / "input_data"
CONFIG_DIR = SSP_MODELING_DIR / "config_files"
OUTPUT_DIR = SSP_MODELING_DIR / "ssp_run_output"
POSTPROCESSING_DIR = SSP_MODELING_DIR / "output_postprocessing" / "data"

# EDGAR targets file (NIR-sourced crosswalk in invent/ subdirectory)
EDGAR_TARGETS_FILE = POSTPROCESSING_DIR / "invent" / "emission_targets_mar_2022.csv"


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: Configuration
# ═══════════════════════════════════════════════════════════════════════════

def load_config():
    """Load config.yaml and return parameters."""
    g_utils = GeneralUtils()
    yaml_path = CONFIG_DIR / "config.yaml"
    assert yaml_path.exists(), f"Config not found: {yaml_path}"

    config = g_utils.read_yaml(yaml_path)
    country = config["country_name"]
    return {
        "country_name": country,
        "country_code": config.get("country_code", country[:3].upper()),
        "input_file": config["ssp_input_file_name"],
        "transformation_cw": config.get("ssp_transformation_cw"),
        "energy_model_flag": config["energy_model_flag"],
        "lndu_realloc_zero": config.get("set_lndu_reallocation_factor_to_zero", False),
    }


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: File Structure & Input Data
# ═══════════════════════════════════════════════════════════════════════════

def build_file_structure(y0=2015, y1=2070):
    """Create SISEPUEDE file structure and time period attribute table."""
    file_struct = sfs.SISEPUEDEFileStructure(initialize_directories=False)
    key_tp = file_struct.model_attributes.dim_time_period
    key_yr = file_struct.model_attributes.field_dim_year

    years = np.arange(y0, y1 + 1).astype(int)
    attr_tp = att.AttributeTable(
        pd.DataFrame({key_tp: range(len(years)), key_yr: years}),
        key_tp,
    )
    file_struct.model_attributes.update_dimensional_attribute_table(attr_tp)

    return file_struct, attr_tp


def load_input_data(config, file_struct, input_file_override=None):
    """Load and prepare the input CSV."""
    input_file = input_file_override or config["input_file"]
    input_path = DATA_DIR / input_file
    assert input_path.exists(), f"Input file not found: {input_path}"

    log.info(f"Loading input: {input_file}")
    df = pd.read_csv(input_path)

    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    # Fill missing columns from SISEPUEDEExamples
    examples = sxl.SISEPUEDEExamples()
    df_example = examples("input_data_frame")
    missing = [c for c in df_example.columns if c not in df.columns]
    for col in missing:
        df[col] = 0.0
    log.info(f"  Filled {len(missing)} missing columns with 0")

    # Ensure required columns
    if "time_period" not in df.columns:
        df["time_period"] = range(len(df))
    df["region"] = config["country_name"]
    if "year" not in df.columns:
        df["year"] = df["time_period"] + 2015

    # Set LNDU reallocation factor
    if config["lndu_realloc_zero"]:
        df["lndu_reallocation_factor"] = 0

    log.info(f"  Shape: {df.shape}")
    return df


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: Transformations & Strategies
# ═══════════════════════════════════════════════════════════════════════════

def load_transformations(attr_tp, df_input, tx_dir_name="transformations_ndc"):
    """Load transformations and build strategies."""
    tx_dir = SSP_MODELING_DIR / tx_dir_name
    assert tx_dir.exists(), f"Transformations dir not found: {tx_dir}"

    log.info(f"Loading transformations from: {tx_dir_name}")
    transformations = trf.Transformations(
        tx_dir,
        attr_time_period=attr_tp,
        df_input=df_input,
    )
    log.info(f"  Loaded {len(transformations.attribute_transformation.table)} transformations")

    log.info("Building strategies (prebuild=True)...")
    t0 = time.time()
    strategies = trf.Strategies(
        transformations,
        export_path="transformations",
        prebuild=True,
    )
    log.info(f"  Built {len(strategies.all_strategies)} strategies in {time.time()-t0:.1f}s")
    log.info(f"  Available: {sorted(strategies.all_strategies)}")

    log.info("Regenerating Excel templates from current input data...")
    strategies.build_strategies_to_templates(df_base_trajectories=df_input)
    log.info("  Templates written to disk")

    return transformations, strategies


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: Model Run
# ═══════════════════════════════════════════════════════════════════════════

def run_model(config, strategies, attr_tp, strategies_to_run, energy_flag=None):
    """Initialize SISEPUEDE and run scenarios."""
    if energy_flag is None:
        energy_flag = config["energy_model_flag"]

    country = config["country_name"]

    # Validate strategies exist
    valid = [s for s in strategies_to_run if s in strategies.all_strategies]
    missing = [s for s in strategies_to_run if s not in strategies.all_strategies]
    if missing:
        raise ValueError(
            f"Strategies not found: {missing}. "
            f"Available: {sorted(strategies.all_strategies)}. "
            f"Fix --strategies or check transformations directory."
        )
    if not valid:
        raise ValueError("No valid strategies to run!")

    log.info(f"Initializing SISEPUEDE (energy_model={energy_flag})...")
    t0 = time.time()
    ssp = si.SISEPUEDE(
        "calibrated",
        db_type="csv",
        initialize_as_dummy=not energy_flag,
        regions=[country],
        strategies=strategies,
        attribute_time_period=attr_tp,
    )
    log.info(f"  Initialized in {time.time()-t0:.1f}s (run_id: {ssp.id_fs_safe})")

    # Define scenario combos
    dict_scens = {
        ssp.key_design: [0],
        ssp.key_future: [0],
        ssp.key_strategy: valid,
    }

    n_total = len(valid)
    log.info(f"\nRunning {n_total} scenarios: {valid}")
    log.info("This may take several minutes. Progress will be logged below.\n")

    t0 = time.time()
    ssp.project_scenarios(
        dict_scens,
        save_inputs=True,
        include_electricity_in_energy=energy_flag,
        check_results=False,
        dict_optimizer_attributes={"time_limit": 1800.0},  # removed user_bound_scale=-7 which caused 128x phantom scaling of NemoMod outputs
    )
    elapsed = time.time() - t0
    log.info(f"\nAll scenarios complete in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")

    # Read outputs
    df_out = ssp.read_output(None)
    df_in = ssp.read_input(None)

    log.info(f"Output shape: {df_out.shape}")
    log.info(f"Input shape:  {df_in.shape}")

    # Print fuel production for FGTV diagnosis
    tp7_out = df_out[(df_out.get('time_period', pd.Series()) == 7)]
    if len(tp7_out) > 0:
        log.info("\n=== FGTV DIAGNOSIS: Fuel Production / Imports / Demand at tp=7 ===")
        for pattern in ['prod_enfu_', 'imports_enfu_pj', 'energy_demand_enfu_total',
                        'energy_demand_by_fuel_total', 'totalvalue_enfu']:
            cols = [c for c in df_out.columns if pattern in c]
            if cols:
                log.info(f"  [{pattern}] ({len(cols)} cols):")
                for col in sorted(cols):
                    val = tp7_out[col].values[0]
                    if abs(val) > 0.001:
                        log.info(f"    {col}: {val:.4f}")

    return ssp, df_out, df_in


def run_quick_test(file_struct, df_input, n_periods=12):
    """Run a fast trajectory test (no strategies, first N periods)."""
    matt = file_struct.model_attributes
    models = sm.SISEPUEDEModels(
        matt,
        fp_julia=file_struct.dir_jl,
        fp_nemomod_reference_files=file_struct.dir_ref_nemo,
    )

    log.info(f"Running quick test ({n_periods} periods)...")
    t0 = time.time()
    df_test = models(df_input, time_periods_base=list(range(n_periods)))
    log.info(f"  Complete in {time.time()-t0:.1f}s, shape: {df_test.shape}")

    return df_test


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: Analysis & Plotting
# ═══════════════════════════════════════════════════════════════════════════

SUBSECTOR_COLS = [
    "emission_co2e_subsector_total_agrc",
    "emission_co2e_subsector_total_ccsq",
    "emission_co2e_subsector_total_entc",
    "emission_co2e_subsector_total_fgtv",
    "emission_co2e_subsector_total_frst",
    "emission_co2e_subsector_total_inen",
    "emission_co2e_subsector_total_ippu",
    "emission_co2e_subsector_total_lndu",
    "emission_co2e_subsector_total_lsmm",
    "emission_co2e_subsector_total_lvst",
    "emission_co2e_subsector_total_scoe",
    "emission_co2e_subsector_total_soil",
    "emission_co2e_subsector_total_trns",
    "emission_co2e_subsector_total_trww",
    "emission_co2e_subsector_total_waso",
]


def get_subsector_emissions(df_out, ssp_obj):
    """Extract subsector emission columns from output, compute if missing."""
    existing = [c for c in SUBSECTOR_COLS if c in df_out.columns]

    if len(existing) >= 10:
        return existing

    # If not, aggregate from detailed emission columns
    log.info("Subsector total columns not found. Aggregating from detailed columns...")
    emission_cols = [c for c in df_out.columns if c.startswith("emission_co2e")]

    subsector_map = {
        "agrc": [], "ccsq": [], "entc": [], "fgtv": [], "frst": [],
        "inen": [], "ippu": [], "lndu": [], "lsmm": [], "lvst": [],
        "scoe": [], "soil": [], "trns": [], "trww": [], "waso": [],
    }

    for col in emission_cols:
        for sub in subsector_map:
            if f"_{sub}_" in col or col.endswith(f"_{sub}"):
                subsector_map[sub].append(col)
                break

    created = []
    for sub, cols in subsector_map.items():
        total_col = f"emission_co2e_subsector_total_{sub}"
        if cols:
            df_out[total_col] = df_out[cols].sum(axis=1)
            created.append(total_col)

    log.info(f"  Created {len(created)} subsector total columns")
    return created


def plot_emissions_stack(df_scenario, matt, title, output_path, subsector_cols):
    """Create stacked area emission plot for one scenario."""
    fig, ax = plt.subplots(figsize=(14, 8))

    available = [c for c in subsector_cols if c in df_scenario.columns]
    if not available:
        log.warning(f"No subsector columns found for {title}")
        return

    tp = df_scenario["time_period"].values
    data = df_scenario[available].values

    labels = [c.replace("emission_co2e_subsector_total_", "") for c in available]

    try:
        svp.plot_emissions_stack(df_scenario, matt)
        plt.title(title)
    except Exception:
        colors = plt.cm.tab20(np.linspace(0, 1, len(available)))
        ax.stackplot(tp, data.T, labels=labels, colors=colors, alpha=0.8)
        ax.set_xlabel("Time Period")
        ax.set_ylabel("Emissions (MtCO2e)")
        ax.set_title(title)
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {output_path.name}")


def build_emission_table(df_scenario, subsector_cols, ref_period=7):
    """Build emission summary table at calibration year."""
    ref = df_scenario[df_scenario["time_period"] == ref_period]

    rows = []
    for col in subsector_cols:
        if col in ref.columns:
            val = ref[col].values[0]
            sub = col.replace("emission_co2e_subsector_total_", "")
            rows.append({"subsector": sub, "emissions_MtCO2e": round(val, 3)})

    df_table = pd.DataFrame(rows)
    df_table = df_table.sort_values("emissions_MtCO2e", ascending=False)
    df_table.loc[len(df_table)] = {"subsector": "TOTAL", "emissions_MtCO2e": round(df_table["emissions_MtCO2e"].sum(), 3)}
    return df_table


def compare_edgar(df_scenario, subsector_cols, ssp_obj, ref_period=7):
    """Compare model emissions against EDGAR targets at calibration year.

    Uses the Vars column (colon-separated emission variable names) from the
    EDGAR targets file to sum the matching columns from the SSP output.
    """
    if not EDGAR_TARGETS_FILE.exists():
        log.warning(f"EDGAR targets not found: {EDGAR_TARGETS_FILE}")
        return None

    targets = pd.read_csv(EDGAR_TARGETS_FILE)
    ref = df_scenario[df_scenario["time_period"] == ref_period]

    rows = []
    for _, t_row in targets.iterrows():
        subsector = t_row.get("Subsector", "")
        category = t_row.get("id", "")
        vars_str = str(t_row.get("Vars", ""))
        edgar_val = t_row.get("MAR", np.nan)

        if pd.isna(vars_str) or vars_str.strip() == "":
            continue

        # Parse variable list (colon-separated)
        vars_list = [v.strip() for v in vars_str.split(":") if v.strip()]
        valid_vars = [v for v in vars_list if v in ref.columns]

        if valid_vars:
            ssp_val = ref[valid_vars].sum(axis=1).values[0]
        else:
            ssp_val = np.nan

        epsilon = 1e-8
        if not pd.isna(ssp_val) and not pd.isna(edgar_val):
            error = abs(ssp_val - edgar_val) / (abs(edgar_val) + epsilon)
        else:
            error = np.nan

        rows.append({
            "subsector": subsector,
            "category": category,
            "edgar_MtCO2e": round(edgar_val, 6),
            "ssp_MtCO2e": round(ssp_val, 6) if not pd.isna(ssp_val) else np.nan,
            "diff_MtCO2e": round(ssp_val - edgar_val, 3) if not pd.isna(ssp_val) else np.nan,
            "error_pct": round(error * 100, 1) if not np.isnan(error) else np.nan,
            "n_vars_matched": len(valid_vars),
            "n_vars_missing": len(vars_list) - len(valid_vars),
        })

    if rows:
        return pd.DataFrame(rows).sort_values("error_pct", ascending=False, na_position="last")
    return None


def check_nemomod_status(df_out, ssp_obj):
    """Check if NemoMod returned OPTIMAL or INFEASIBLE by examining ENTC emissions."""
    primary_ids = sorted(df_out[ssp_obj.key_primary].unique())
    results = {}

    for pid in primary_ids:
        df_s = df_out[df_out[ssp_obj.key_primary] == pid]
        entc_cols = [c for c in df_out.columns if "entc" in c and c.startswith("emission_co2e")]

        if not entc_cols:
            log.error(f"  Strategy {pid}: NEMOMOD_STATUS=CRASHED — no ENTC emission columns")
            results[pid] = {
                "status": "CRASHED",
                "zero_periods": -1,
                "total_periods": len(df_s),
                "block1_zero": -1,
                "block2_zero": -1,
            }
            continue

        entc_per_period = df_s[entc_cols].sum(axis=1)
        n_zero_periods = (entc_per_period == 0).sum()
        total_periods = len(df_s)

        tp_col = "time_period"
        block1 = df_s[df_s[tp_col] <= 12] if tp_col in df_s.columns else df_s.iloc[:13]
        block2 = df_s[df_s[tp_col] >= 13] if tp_col in df_s.columns else df_s.iloc[13:]

        b1_zero = (block1[entc_cols].sum(axis=1) == 0).sum() if len(block1) > 0 else 0
        b2_zero = (block2[entc_cols].sum(axis=1) == 0).sum() if len(block2) > 0 else 0

        if n_zero_periods > total_periods * 0.5:
            status = "INFEASIBLE"
            block_info = f"Block1={len(block1)-b1_zero}/{len(block1)} OK, Block2={len(block2)-b2_zero}/{len(block2)} OK"
            log.warning(f"  Strategy {pid}: NEMOMOD_STATUS=INFEASIBLE — ENTC=0 for {n_zero_periods}/{total_periods} periods ({block_info})")
        else:
            status = "OPTIMAL"
            log.info(f"  Strategy {pid}: NEMOMOD_STATUS=OPTIMAL — ENTC non-zero for {total_periods-n_zero_periods}/{total_periods} periods")

        results[pid] = {
            "status": status,
            "zero_periods": int(n_zero_periods),
            "total_periods": int(total_periods),
            "block1_zero": int(b1_zero),
            "block2_zero": int(b2_zero),
        }

    return results


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Morocco SISEPUEDE Calibration Runner")
    parser.add_argument("--strategies", nargs="+", type=int, default=[0, 6005],
                        help="Strategy IDs to run (default: 0 6005)")
    parser.add_argument("--no-energy", action="store_true",
                        help="Disable NemoMod energy optimization (faster)")
    parser.add_argument("--quick-test", action="store_true",
                        help="Run quick test only (12 periods, no strategies)")
    parser.add_argument("--baseline-only", action="store_true",
                        help="Run strategy 0 only (baseline)")
    parser.add_argument("--tx-dir", type=str, default="transformations_ndc",
                        help="Transformations directory name (default: transformations_ndc)")
    parser.add_argument("--input-file", type=str, default=None,
                        help="Override input CSV filename (from input_data/)")
    parser.add_argument("--end-year", type=int, default=2070,
                        help="End year for simulation (default: 2070, use 2050 for faster runs)")
    parser.add_argument("--show", action="store_true",
                        help="Show plots interactively instead of saving")
    args = parser.parse_args()

    if args.baseline_only:
        args.strategies = [0]

    if args.show:
        matplotlib.use("TkAgg")

    # ── Load config ─────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("MOROCCO SISEPUEDE CALIBRATION RUNNER")
    log.info("=" * 60)

    config = load_config()
    log.info(f"Country:      {config['country_name']}")
    log.info(f"Input file:   {args.input_file or config['input_file']}")
    log.info(f"Energy model: {config['energy_model_flag']}")
    log.info(f"TX dir:       {args.tx_dir}")

    # ── Build file structure ────────────────────────────────────────────
    file_struct, attr_tp = build_file_structure(y1=args.end_year)
    n_tp = args.end_year - 2015 + 1
    log.info(f"End year:     {args.end_year} ({n_tp} time periods)")
    matt = file_struct.model_attributes

    # ── Load input data ─────────────────────────────────────────────────
    df_input = load_input_data(config, file_struct, input_file_override=args.input_file)

    # Truncate input to match time horizon
    if len(df_input) > n_tp:
        log.info(f"  Truncating input from {len(df_input)} to {n_tp} rows (end year {args.end_year})")
        df_input = df_input.iloc[:n_tp].reset_index(drop=True)

    # ── Quick test mode ─────────────────────────────────────────────────
    if args.quick_test:
        df_test = run_quick_test(file_struct, df_input)
        subsector_cols = get_subsector_emissions(df_test, None)

        OUTPUT_DIR.mkdir(exist_ok=True)
        out_path = OUTPUT_DIR / "quick_test_emissions.png"

        fig, ax = plt.subplots(figsize=(14, 8))
        try:
            svp.plot_emissions_stack(df_test, matt)
            plt.title(f"{config['country_name'].upper()} Quick Test: Baseline Emissions")
        except Exception as e:
            log.warning(f"svp.plot_emissions_stack failed: {e}. Using fallback.")
            available = [c for c in subsector_cols if c in df_test.columns]
            tp = df_test["time_period"].values
            data = df_test[available].values
            labels = [c.replace("emission_co2e_subsector_total_", "") for c in available]
            colors = plt.cm.tab20(np.linspace(0, 1, len(available)))
            ax.stackplot(tp, data.T, labels=labels, colors=colors, alpha=0.8)
            ax.set_xlabel("Time Period")
            ax.set_ylabel("Emissions (MtCO2e)")
            ax.set_title(f"{config['country_name'].upper()} Quick Test")
            ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)

        plt.tight_layout()
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        if args.show:
            plt.show()
        plt.close()
        log.info(f"Quick test plot saved: {out_path}")

        table = build_emission_table(df_test, subsector_cols)
        print("\n" + table.to_string(index=False))
        return 0

    # ── Load transformations ────────────────────────────────────────────
    transformations, strategies = load_transformations(
        attr_tp, df_input, tx_dir_name=args.tx_dir
    )

    # ── Run model ───────────────────────────────────────────────────────
    energy_flag = False if args.no_energy else config["energy_model_flag"]
    ssp, df_out, df_in = run_model(
        config, strategies, attr_tp,
        strategies_to_run=args.strategies,
        energy_flag=energy_flag,
    )

    # ── Check NemoMod status ────────────────────────────────────────────
    log.info("\nNemoMod status check:")
    nemo_results = check_nemomod_status(df_out, ssp)
    all_optimal = all(r["status"] == "OPTIMAL" for r in nemo_results.values())
    print(f"\nNEMOMOD_ALL_OPTIMAL={'YES' if all_optimal else 'NO'}")
    for pid, r in nemo_results.items():
        print(f"  NEMOMOD_STATUS strategy={pid} status={r['status']} zero_periods={r['zero_periods']}/{r['total_periods']} block1_zero={r['block1_zero']} block2_zero={r['block2_zero']}")

    # ── Get primary IDs and subsector columns ───────────────────────────
    primary_ids = sorted(df_out[ssp.key_primary].unique())
    subsector_cols = get_subsector_emissions(df_out, ssp)
    log.info(f"Primary IDs: {primary_ids}")
    log.info(f"Subsector columns: {len(subsector_cols)}")

    # Read strategy mapping
    try:
        run_dir = ssp.file_struct.dir_out / ssp.id_fs_safe
        attr_file = run_dir / f"{ssp.id_fs_safe}_output_database" / "ATTRIBUTE_PRIMARY.csv"
        if attr_file.exists():
            attr_primary = pd.read_csv(attr_file)
            log.info("Strategy mapping:")
            for _, row in attr_primary.iterrows():
                log.info(f"  primary_id={int(row['primary_id'])} -> strategy_id={int(row['strategy_id'])}")
    except Exception:
        pass

    # ── Create output directory ─────────────────────────────────────────
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_output_dir = OUTPUT_DIR / f"calibration_{timestamp}"
    run_output_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"\nOutput directory: {run_output_dir}")

    # ── Save WIDE_INPUTS_OUTPUTS (following morocco_manager_wb.ipynb logic) ──
    try:
        df_wide = pd.merge(df_out, df_in, how="left")
        wide_path = run_output_dir / f"WIDE_INPUTS_OUTPUTS.csv"
        df_wide.to_csv(wide_path, index=False, encoding="UTF-8")
        log.info(f"WIDE output saved: {wide_path} ({df_wide.shape[1]} columns)")
    except Exception as e:
        log.warning(f"Could not save WIDE output: {e}")

    # ── Plot and table for each scenario ────────────────────────────────
    for i, pid in enumerate(primary_ids):
        df_s = df_out[df_out[ssp.key_primary] == pid].copy()
        label = "Baseline" if i == 0 else f"Strategy (ID {pid})"

        log.info(f"\nPlotting: {label}")
        plot_path = run_output_dir / f"emissions_stack_{label.lower().replace(' ', '_')}.png"

        fig, ax = plt.subplots(figsize=(14, 8))
        try:
            svp.plot_emissions_stack(df_s, matt)
            plt.title(f"Emissions Stack - {label}")
        except Exception as e:
            log.warning(f"svp failed: {e}. Using fallback plot.")
            available = [c for c in subsector_cols if c in df_s.columns]
            tp = df_s["time_period"].values
            data = df_s[available].values
            labels_list = [c.replace("emission_co2e_subsector_total_", "") for c in available]
            colors = plt.cm.tab20(np.linspace(0, 1, len(available)))
            ax.stackplot(tp, data.T, labels=labels_list, colors=colors, alpha=0.8)
            ax.set_xlabel("Time Period")
            ax.set_ylabel("Emissions (MtCO2e)")
            ax.set_title(f"Emissions Stack - {label}")
            ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)

        plt.tight_layout()
        plt.savefig(plot_path, dpi=150, bbox_inches="tight")
        if args.show:
            plt.show()
        plt.close()

        # Emission table
        table = build_emission_table(df_s, subsector_cols)
        table_path = run_output_dir / f"emissions_table_{label.lower().replace(' ', '_')}.csv"
        table.to_csv(table_path, index=False)

        print(f"\n{'='*60}")
        print(f"  {label} — Emissions at t=7 (2022)")
        print(f"{'='*60}")
        print(table.to_string(index=False))

    # ── NIR inventory comparison (replaces old EDGAR+NDC approach) ──────
    # Uses emission_targets_mar_2022.csv crosswalk with NIR Tableau 19/83/126 values
    nir_targets = POSTPROCESSING_DIR / "invent" / "emission_targets_mar_2022.csv"
    wide_path = run_output_dir / "WIDE_INPUTS_OUTPUTS.csv"

    if nir_targets.exists() and wide_path.exists():
        import subprocess
        diag_script = SCRIPT_DIR.parent / "output_postprocessing" / "scripts" / "compare_to_inventory.py"
        if diag_script.exists():
            cmd = [
                sys.executable, str(diag_script),
                "--targets", str(nir_targets),
                "--output", str(wide_path),
                "--tp", "7",
                "--threshold", "0.15",
            ]
            log.info(f"Running inventory comparison: {diag_script.name}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            print(result.stdout)
            if result.stderr:
                log.warning(result.stderr[:500])
        else:
            log.warning(f"Diagnostic script not found: {diag_script}")
    else:
        log.warning(f"NIR targets or WIDE output not found, skipping inventory comparison")

    # ── Summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  RUN SUMMARY")
    print(f"{'='*60}")
    print(f"  Input:        {args.input_file or config['input_file']}")
    print(f"  TX dir:       {args.tx_dir}")
    print(f"  Strategies:   {args.strategies}")
    print(f"  Energy model: {energy_flag}")
    print(f"  NemoMod:      {'ALL OPTIMAL' if all_optimal else 'INFEASIBLE — see above'}")
    print(f"  Output:       {run_output_dir}")
    print(f"  Plots:        {len(primary_ids)} saved")
    print(f"  Run ID:       {ssp.id_fs_safe}")
    print(f"{'='*60}")

    return 0 if all_optimal else 1


if __name__ == "__main__":
    sys.exit(main())
