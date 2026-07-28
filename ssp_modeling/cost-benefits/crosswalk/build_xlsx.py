"""Assemble the master crosswalk workbook (Tasks 1 & 2 so far)."""
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from assemble import (build_model, SAM, AGENTS)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "morocco_crosswalk_deliverable.xlsx")
inv_rows, inv_cum, years, COST_VECTORS, AGENT_SHARES, gw = build_model()

# investment sectors in file order
SECTORS = list(inv_rows.keys())
# SAM destination order (as in SAM dict = file order, imports last)
DEST = list(SAM.keys())

FN = "Arial"
BLUE = Font(name=FN, color="0000FF")          # editable input
BLACK = Font(name=FN, color="000000")         # formula
GREEN = Font(name=FN, color="008000")         # link/source-derived
BOLD = Font(name=FN, bold=True)
HEADF = Font(name=FN, bold=True, color="FFFFFF")
HEAD = PatternFill("solid", fgColor="305496")
YELLOW = PatternFill("solid", fgColor="FFF2CC")
GREYF = PatternFill("solid", fgColor="D9D9D9")
WRAP = Alignment(wrap_text=True, vertical="top")
CTR = Alignment(horizontal="center")
thin = Side(style="thin", color="BFBFBF")
BORD = Border(left=thin, right=thin, top=thin, bottom=thin)
PCT = "0.0%"; BN = "#,##0.00;(#,##0.00);-"

wb = Workbook()

def style_header(ws, row, ncols, start=1):
    for c in range(start, start+ncols):
        cell = ws.cell(row, c); cell.fill = HEAD; cell.font = HEADF
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        cell.border = BORD

# ---------------- README ----------------
ws = wb.active; ws.title = "README"
ws.column_dimensions["A"].width = 118
lines = [
 ("Morocco investment & benefits crosswalk", True),
 ("Units: billion 2019 USD, cumulative 2023-2050 unless noted. Source run: LEDS (LTS) vs BASE (no-action).", False),
 ("", False),
 ("STRUCTURE — each investment path is decomposed two independent ways, each summing to 100%:", True),
 ("  (A) AGENT split  : who finances it — government / firms / households (depends on financing judgment).", False),
 ("  (B) COST VECTOR  : what it buys — a vector across SAM sectors + IMPORTS (supply chain; independent of financing).", False),
 ("Final SAM allocation = investment(sector) x cost-vector(sector).  Final agent allocation = investment(sector) x agent-share(sector).", False),
 ("", False),
 ("IMPORTS is a synthetic destination inside the 100% (the SAM has no imports row). Solar modules, wind turbines,", False),
 ("EV drivetrains and heat pumps are largely imported; allocating them domestically would overstate domestic activity.", False),
 ("'territorial correction' (SAM row 43) is excluded — it is a balancing item, not a sector.", False),
 ("", False),
 ("TABS", True),
 ("  T1_agent_split   : investment x {gov, firms, hh} shares + applied bn + documented source per sector.", False),
 ("  T1_cost_vectors  : share matrix, SAM destination x investment sector (blue = editable inputs; each column sums to 1).", False),
 ("  T1_applied_SAM   : applied bn = cost-vector share x sector investment total (formulas).", False),
 ("  T2_fuel_savings  : power-sector fuel COST savings by generation technology (from NEMOMOD).", False),
 ("  T2_capex_by_tech : generation capital expenditure by technology (from NEMOMOD).", False),
 ("  T2_note          : why these differ from the CB 'Fuel cost savings (power sector)' row. READ THIS.", False),
 ("  T3_agent_split / T3_cost_vectors / T3_applied_SAM : benefits crosswalk (12 categories, 826.1 bn; 4 non-market", False),
 ("                     categories excluded; food savings -> households/food retail; livestock value stays negative).", False),
 ("  T4_vehicles      : number of vehicles by fuel x strategy = VKM / Tableau divisor (road_light /12,000, public /60,000).", False),
 ("  T4_elec_generation / T4_energy_by_fuel : energy mix exported from the Tableau 'drivers' datasource.", False),
 ("  T5_ecosystem_split : evidence-based split of the $500/ha forest value (de Groot 2012 / Costanza 2014; food+carbon", False),
 ("                     stripped and renormalised; tourism = the cultural/recreation subset, not a parallel category).", False),
 ("  T5_memo          : answers to Moulaye's two disaggregation questions (food-by-product is mostly not feasible).", False),
 ("  T7_pct_change    : (LTS-SNBC)/SNBC. FINDING: reused BAU ~ no-action, so the % denominator collapses (see tab).", False),
 ("", False),
 ("RECONCILIATION", True),
 (f"  Investment total (10 paths)            = {sum(inv_cum.values()):.2f} bn", False),
 (f"  Agent split total                      = {sum(inv_cum[k]*AGENT_SHARES[k][0] for k in SECTORS)+sum(inv_cum[k]*AGENT_SHARES[k][1] for k in SECTORS)+sum(inv_cum[k]*AGENT_SHARES[k][2] for k in SECTORS):.2f} bn (ties to investment total)", False),
 ("  Of the SAM allocation, IMPORTS captures ~22% (turbines, modules, EV drivetrains, heat pumps).", False),
 ("", False),
 ("LEGEND: blue = editable input (share/assumption) · black = formula · yellow = key assumption to review.", False),
]
for i, (t, b) in enumerate(lines, 1):
    c = ws.cell(i, 1, t); c.font = BOLD if b else Font(name=FN)
    c.alignment = WRAP

# ---------------- T1_agent_split ----------------
ws = wb.create_sheet("T1_agent_split")
hdr = ["Investment sector", "Investment (bn)", "Gov %", "Firms %", "HH %",
       "Gov (bn)", "Firms (bn)", "HH (bn)", "Row check", "Source (documented judgment)"]
ws.append(hdr); style_header(ws, 1, len(hdr))
widths = [30, 14, 9, 9, 9, 11, 11, 11, 10, 90]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
r = 2
for s in SECTORS:
    g, f, h, src = AGENT_SHARES[s]
    ws.cell(r, 1, s).font = Font(name=FN)
    ws.cell(r, 2, round(inv_cum[s], 4)).font = BLUE
    ws.cell(r, 3, g).font = BLUE; ws.cell(r, 4, f).font = BLUE; ws.cell(r, 5, h).font = BLUE
    ws.cell(r, 6, f"=$B{r}*C{r}").font = BLACK
    ws.cell(r, 7, f"=$B{r}*D{r}").font = BLACK
    ws.cell(r, 8, f"=$B{r}*E{r}").font = BLACK
    ws.cell(r, 9, f"=C{r}+D{r}+E{r}").font = BLACK
    sc = ws.cell(r, 10, src); sc.font = Font(name=FN, size=9); sc.alignment = WRAP
    for col in (3, 4, 5, 9):
        ws.cell(r, col).number_format = PCT
    for col in (2, 6, 7, 8):
        ws.cell(r, col).number_format = BN
    r += 1
# totals
ws.cell(r, 1, "TOTAL").font = BOLD
for col, L in [(2, "B"), (6, "F"), (7, "G"), (8, "H")]:
    ws.cell(r, col, f"=SUM({L}2:{L}{r-1})").font = BOLD
    ws.cell(r, col).number_format = BN
for c in range(1, 11):
    ws.cell(r, c).fill = GREYF
ws.freeze_panes = "A2"

# ---------------- T1_cost_vectors (share matrix) ----------------
ws = wb.create_sheet("T1_cost_vectors")
# row1 header: sector columns; row2: investment totals; rows: destinations
ws.cell(1, 1, "SAM destination").fill = HEAD; ws.cell(1, 1).font = HEADF
for j, s in enumerate(SECTORS, 2):
    ws.cell(1, j, s)
style_header(ws, 1, len(SECTORS)+1)
ws.cell(2, 1, "Investment (bn) ->").font = BOLD
for j, s in enumerate(SECTORS, 2):
    ws.cell(2, j, round(inv_cum[s], 4)).font = BLUE
    ws.cell(2, j).number_format = BN; ws.cell(2, j).fill = YELLOW
ws.column_dimensions["A"].width = 52
for j in range(2, len(SECTORS)+2):
    ws.column_dimensions[get_column_letter(j)].width = 13
r0 = 3
for i, d in enumerate(DEST):
    r = r0 + i
    lab = ws.cell(r, 1, SAM[d]); lab.font = Font(name=FN)
    if d == "imports":
        lab.font = Font(name=FN, bold=True, color="C00000")
    for j, s in enumerate(SECTORS, 2):
        vec = COST_VECTORS[s][0]
        v = vec.get(d, 0)
        cell = ws.cell(r, j, round(v, 4) if v else 0)
        cell.font = BLUE if v else Font(name=FN, color="BFBFBF")
        cell.number_format = PCT
rsum = r0 + len(DEST)
ws.cell(rsum, 1, "SUM (must = 100%)").font = BOLD
for j in range(2, len(SECTORS)+2):
    L = get_column_letter(j)
    ws.cell(rsum, j, f"=SUM({L}{r0}:{L}{rsum-1})").font = BOLD
    ws.cell(rsum, j).number_format = PCT; ws.cell(rsum, j).fill = GREYF
ws.freeze_panes = "B3"

# ---------------- T1_applied_SAM (formulas) ----------------
ws = wb.create_sheet("T1_applied_SAM")
ws.cell(1, 1, "SAM destination (bn 2019 USD)").fill = HEAD; ws.cell(1, 1).font = HEADF
for j, s in enumerate(SECTORS, 2):
    ws.cell(1, j, s)
ws.cell(1, len(SECTORS)+2, "TOTAL")
style_header(ws, 1, len(SECTORS)+2)
ws.column_dimensions["A"].width = 52
for j in range(2, len(SECTORS)+3):
    ws.column_dimensions[get_column_letter(j)].width = 13
for i, d in enumerate(DEST):
    r = 2 + i; cvr = r0 + i    # matching row in T1_cost_vectors
    lab = ws.cell(r, 1, SAM[d]); lab.font = Font(name=FN)
    if d == "imports":
        lab.font = Font(name=FN, bold=True, color="C00000")
    for j, s in enumerate(SECTORS, 2):
        L = get_column_letter(j)
        ws.cell(r, j, f"=T1_cost_vectors!{L}{cvr}*T1_cost_vectors!{L}$2").font = BLACK
        ws.cell(r, j).number_format = BN
    tl = get_column_letter(len(SECTORS)+2)
    ws.cell(r, len(SECTORS)+2, f"=SUM(B{r}:{get_column_letter(len(SECTORS)+1)}{r})").font = BOLD
    ws.cell(r, len(SECTORS)+2).number_format = BN
rtot = 2 + len(DEST)
ws.cell(rtot, 1, "TOTAL").font = BOLD
for j in range(2, len(SECTORS)+3):
    L = get_column_letter(j)
    ws.cell(rtot, j, f"=SUM({L}2:{L}{rtot-1})").font = BOLD
    ws.cell(rtot, j).number_format = BN; ws.cell(rtot, j).fill = GREYF
ws.freeze_panes = "B2"

# ---------------- T2 tabs (transparent: raw BASE + raw LEDS + formula) ----------------
def t2_transparent(sheet, detail_csv, title, method_lines, calc_label, minuend, subtrahend,
                   collabel):
    """Stack three Year x category blocks: raw BASE, raw LEDS, and the difference as live
    formulas (minuend - subtrahend). Every raw number names its NEMOMOD source column."""
    d = pd.read_csv(os.path.join(HERE, detail_csv))
    d["cat"] = d["technology"] if "fuel" not in d.columns else (
        d["fuel"] + " (" + d["technology"] + ")")
    base = d.pivot_table(index="Year", columns="cat", values="base_musd", aggfunc="sum").fillna(0) / 1000.0
    leds = d.pivot_table(index="Year", columns="cat", values="leds_musd", aggfunc="sum").fillna(0) / 1000.0
    calc = (base - leds) if (minuend == "BASE") else (leds - base)
    order = calc.sum().sort_values(key=lambda s: -s.abs()).index.tolist()
    base, leds = base[order], leds[order]
    src = {c: d.loc[d["cat"] == c, "source_var"].iloc[0] for c in order}
    yrs = list(base.index)

    ws = wb.create_sheet(sheet)
    ws.column_dimensions["A"].width = 12
    for j in range(2, len(order)+2):
        ws.column_dimensions[get_column_letter(j)].width = 17
    ws.cell(1, 1, title).font = BOLD
    r = 2
    for ln in method_lines:
        ws.cell(r, 1, ln).font = Font(name=FN, size=9, italic=True); ws.cell(r, 1).alignment = WRAP
        r += 1
    r += 1

    def block(startr, header, values_getter, is_formula=False, base_row0=None, leds_row0=None):
        ws.cell(startr, 1, header).font = BOLD
        for c in range(1, len(order)+2):
            ws.cell(startr, c).fill = GREYF
        hr = startr + 1
        ws.cell(hr, 1, "Year")
        for j, cat in enumerate(order, 2):
            ws.cell(hr, j, cat)
        style_header(ws, hr, len(order)+1)
        for i, y in enumerate(yrs):
            rr = hr + 1 + i
            ws.cell(rr, 1, int(y)).font = Font(name=FN)
            for j, cat in enumerate(order, 2):
                if is_formula:
                    L = get_column_letter(j)
                    ws.cell(rr, j, f"={L}{base_row0+i}-{L}{leds_row0+i}" if minuend == "BASE"
                            else f"={L}{leds_row0+i}-{L}{base_row0+i}").font = BLACK
                else:
                    ws.cell(rr, j, round(float(values_getter.loc[y, cat]), 4)).font = BLUE
                ws.cell(rr, j).number_format = BN
        # source-variable row under each raw block
        return hr + 1  # first data row

    # BASE block
    r_base_hdr = r
    base_row0 = block(r, f"RAW — {collabel} in BASE / no-action (bn)", base)
    r = base_row0 + len(yrs) + 1
    ws.cell(r-1, 1, "source: " + ", ".join(f"{c}={src[c]}" for c in order[:2]) + " ...").font = Font(name=FN, size=8, color="808080")
    r += 1
    # LEDS block
    leds_row0 = block(r, f"RAW — {collabel} in LEDS / LTS (bn)", leds)
    r = leds_row0 + len(yrs) + 2
    # CALC block (formulas)
    calc_row0 = block(r, f"CALC — {calc_label} (bn)  [each cell = a raw-BASE cell minus the raw-LEDS cell above]",
                      None, is_formula=True, base_row0=base_row0, leds_row0=leds_row0)
    rc = calc_row0 + len(yrs)
    ws.cell(rc, 1, "CUMULATIVE").font = BOLD
    for j in range(2, len(order)+2):
        L = get_column_letter(j)
        ws.cell(rc, j, f"=SUM({L}{calc_row0}:{L}{rc-1})").font = BOLD
        ws.cell(rc, j).number_format = BN; ws.cell(rc, j).fill = GREYF
    ws.freeze_panes = "B2"
    return calc_row0, rc

fs_method = [
 "HOW THIS WAS COMPUTED (fuel cost savings by generation technology):",
 "1. Raw data: for each fuel, the value of fuel consumed by the power sector, per scenario and year, straight",
 "   from NEMOMOD column  totalvalue_enfu_fuel_consumed_entc_fuel_<fuel>  (= physical consumption x fuel price).",
 "2. Two raw blocks below show that variable in BASE (no-action) and in LEDS (LTS), in bn 2019 USD.",
 "3. Saving = BASE minus LEDS (the CALC block; every cell is a live formula subtracting the two raw cells).",
 "4. Each fuel is mapped 1:1 to the plant that burns it (coal->pp_coal, natural gas->pp_gas, oil->pp_oil, ...).",
 "   Renewables (solar/wind/hydro) burn no fuel -> no row here -> zero saving (correct: the saving is the",
 "   avoided coal/oil/gas purchase). This is NOT the CB 'Fuel cost savings (power sector)' row (a residual).",
]
t2_transparent("T2_fuel_savings", "task2_fuel_detail.csv",
               "Task 2 — Power-sector FUEL COST SAVINGS by generation technology",
               fs_method, "Fuel saving = BASE minus LEDS", "BASE", "LEDS", "fuel value")

cx_method = [
 "HOW THIS WAS COMPUTED (generation capex by technology):",
 "1. Raw data: discounted capital investment by plant technology, per scenario and year, straight from NEMOMOD",
 "   column  nemomod_entc_discounted_capital_investment_pp_<tech>, in bn 2019 USD.",
 "2. Two raw blocks below show that variable in BASE (no-action) and in LEDS (LTS).",
 "3. Incremental capex = LEDS minus BASE (the CALC block; every cell is a live formula). Positive = extra build",
 "   in the LTS; negative = fossil capex avoided. Gross positive additions drive the per-technology power cost",
 "   vector in Task 1 (T1_cost_vectors). Net (all techs) = 55.8 bn = the generation part of the 65.5 bn power path.",
]
t2_transparent("T2_capex_by_tech", "task2_capex_detail.csv",
               "Task 2 — Generation CAPEX by technology (discounted)",
               cx_method, "Incremental capex = LEDS minus BASE", "LEDS", "BASE", "capex")

# ---------------- T2_note ----------------
ws = wb.create_sheet("T2_note")
ws.column_dimensions["A"].width = 118
note = [
 ("Task 2 note — fuel savings & capex by generation technology (for Moulaye)", True),
 ("", False),
 ("WHY THIS DOES NOT MATCH THE 'Fuel cost savings (power sector)' ROW IN THE COST-BENEFIT FILE", True),
 ("That CB row (cb_type = 'savings_opex') sums to 9.76 bn cumulative. Despite its name it is a RESIDUAL", False),
 ("bucket: it aggregates demand-side, sector-level fuel expenditures and electricity costs allocated to", False),
 ("each demand sector from NEMOMOD. It is NOT generation fuel expenditure.", False),
 ("", False),
 ("The series here are computed straight from NEMOMOD:", True),
 ("  Fuel savings by tech = change in ENTC fuel consumption value (BASE - LEDS), by fuel, mapped to the", False),
 ("  plant that burns it (coal->pp_coal, natural gas->pp_gas, oil->pp_oil, ...). Source column:", False),
 ("  totalvalue_enfu_fuel_consumed_entc_fuel_<fuel>  (= consumption x fuel price, model-consistent).", False),
 ("  Cumulative: coal 52.95, oil 9.53, gas 6.47, biomass 0.59, biogas -2.27 -> ~67 bn total.", False),
 ("", False),
 ("RENEWABLES RECEIVE ZERO FUEL SAVINGS — THIS IS CORRECT, NOT A BUG.", True),
 ("Solar, wind, hydro burn no fuel, so they carry no fuel expenditure and no saving. The saving from", False),
 ("decarbonisation shows up as REDUCED FUEL PURCHASE by the coal, oil and gas plants they displace.", False),
 ("A capex weighting would (wrongly) put the savings on solar/wind, which have no fuel — so we do NOT", False),
 ("allocate fuel savings by capex.", False),
 ("", False),
 ("CAPEX by technology (incremental LEDS - BASE, discounted):", True),
 ("  Positive builds: wind 49.5, solar 20.6, biogas 4.4 bn; avoided fossil capex: coal -16.1, gas -1.2, oil -0.7.", False),
 ("  Net 55.8 bn generation capex; the EN - Power Industry investment path (65.5 bn) = this + transmission + O&M.", False),
 ("  Gross-addition shares (wind 66%, solar 26%, biogas 6%, nuclear 2%) drive the per-technology power cost", False),
 ("  vectors in Task 1 (T1_cost_vectors), replacing one generic vector for the whole power sector.", False),
 ("", False),
 ("WHICH SIDE OF THE SAVING IS RECORDED: the fuel saving here is the BUYER's cost reduction (the power", True),
 ("plant spends less on fuel). The mirror image — reduced demand for the coking/refining & gas sectors —", False),
 ("is NOT in this table; add it on the demand side of the SAM if you want the refinery output effect.", False),
]
for i, (t, b) in enumerate(note, 1):
    c = ws.cell(i, 1, t); c.font = BOLD if b else Font(name=FN); c.alignment = WRAP

# ================= TASK 3 — BENEFITS CROSSWALK =================
from task3_data import BENEFITS, EXCLUDE_NONMARKET, EXCLUDE_INVESTMENT
import openpyxl as _oxl
_cbws = _oxl.load_workbook("/Users/fabianfuentes/Downloads/cost_benefits_morocco_2026_07_19.xlsx")["Sheet 1"]
cb_cum = {}
for _r in range(3, _cbws.max_row+1):
    _n = _cbws.cell(_r, 1).value
    if not _n or "units" in str(_n).lower():
        continue
    cb_cum[_n] = sum(_cbws.cell(_r, _c).value or 0 for _c in range(2, _cbws.max_column+1))
BCATS = list(BENEFITS.keys())            # 12 crosswalked categories
BDEST = list(SAM.keys())

# ---- T3_agent_split ----
ws = wb.create_sheet("T3_agent_split")
hdr = ["Benefit category", "Value (bn)", "Gov %", "Firms %", "HH %",
       "Gov (bn)", "Firms (bn)", "HH (bn)", "Row check", "Side recorded", "Source"]
ws.append(hdr); style_header(ws, 1, len(hdr))
for i, w in enumerate([34, 12, 8, 8, 8, 11, 11, 11, 9, 60, 70], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
r = 2
for k in BCATS:
    (g, f, h), cv, side, src = BENEFITS[k]
    ws.cell(r, 1, k).font = Font(name=FN)
    ws.cell(r, 2, round(cb_cum[k], 4)).font = BLUE
    ws.cell(r, 3, g).font = BLUE; ws.cell(r, 4, f).font = BLUE; ws.cell(r, 5, h).font = BLUE
    ws.cell(r, 6, f"=$B{r}*C{r}").font = BLACK
    ws.cell(r, 7, f"=$B{r}*D{r}").font = BLACK
    ws.cell(r, 8, f"=$B{r}*E{r}").font = BLACK
    ws.cell(r, 9, f"=C{r}+D{r}+E{r}").font = BLACK
    ws.cell(r, 10, side).font = Font(name=FN, size=9); ws.cell(r, 10).alignment = WRAP
    ws.cell(r, 11, src).font = Font(name=FN, size=9); ws.cell(r, 11).alignment = WRAP
    for col in (3, 4, 5, 9):
        ws.cell(r, col).number_format = PCT
    for col in (2, 6, 7, 8):
        ws.cell(r, col).number_format = BN
    r += 1
ws.cell(r, 1, "TOTAL (crosswalked)").font = BOLD
for col, L in [(2, "B"), (6, "F"), (7, "G"), (8, "H")]:
    ws.cell(r, col, f"=SUM({L}2:{L}{r-1})").font = BOLD
    ws.cell(r, col).number_format = BN
for c in range(1, 12):
    ws.cell(r, c).fill = GREYF
# exclusions note rows
r += 2
ws.cell(r, 1, "EXCLUDED from crosswalk:").font = BOLD
r += 1
ws.cell(r, 1, "  Net Reduction in Capital Costs — covered by the investment file (Task 1).").font = Font(name=FN, size=9)
r += 1
for k in EXCLUDE_NONMARKET:
    ws.cell(r, 1, f"  {k} = {cb_cum.get(k,0):.2f} bn — non-market welfare value, no agent/transaction.").font = Font(name=FN, size=9)
    r += 1
ws.cell(r, 1, f"  (4 non-market categories = {sum(cb_cum[k] for k in EXCLUDE_NONMARKET):.2f} bn.) "
              f"Crosswalked 826.10 + excluded 30.40 = 856.51 bn (16-category total).").font = Font(name=FN, size=9, italic=True)
ws.freeze_panes = "A2"

# ---- T3_cost_vectors ----
ws = wb.create_sheet("T3_cost_vectors")
ws.cell(1, 1, "SAM destination").fill = HEAD; ws.cell(1, 1).font = HEADF
for j, k in enumerate(BCATS, 2):
    ws.cell(1, j, k)
style_header(ws, 1, len(BCATS)+1)
ws.cell(2, 1, "Value (bn) ->").font = BOLD
for j, k in enumerate(BCATS, 2):
    ws.cell(2, j, round(cb_cum[k], 4)).font = BLUE
    ws.cell(2, j).number_format = BN; ws.cell(2, j).fill = YELLOW
ws.column_dimensions["A"].width = 52
for j in range(2, len(BCATS)+2):
    ws.column_dimensions[get_column_letter(j)].width = 14
b_r0 = 3
for i, d in enumerate(BDEST):
    r = b_r0 + i
    lab = ws.cell(r, 1, SAM[d]); lab.font = Font(name=FN, bold=True, color="C00000") if d == "imports" else Font(name=FN)
    for j, k in enumerate(BCATS, 2):
        v = BENEFITS[k][1].get(d, 0)
        cell = ws.cell(r, j, round(v, 4) if v else 0)
        cell.font = BLUE if v else Font(name=FN, color="BFBFBF")
        cell.number_format = PCT
b_rsum = b_r0 + len(BDEST)
ws.cell(b_rsum, 1, "SUM (must = 100%)").font = BOLD
for j in range(2, len(BCATS)+2):
    L = get_column_letter(j)
    ws.cell(b_rsum, j, f"=SUM({L}{b_r0}:{L}{b_rsum-1})").font = BOLD
    ws.cell(b_rsum, j).number_format = PCT; ws.cell(b_rsum, j).fill = GREYF
ws.freeze_panes = "B3"

# ---- T3_applied_SAM ----
ws = wb.create_sheet("T3_applied_SAM")
ws.cell(1, 1, "SAM destination (bn 2019 USD)").fill = HEAD; ws.cell(1, 1).font = HEADF
for j, k in enumerate(BCATS, 2):
    ws.cell(1, j, k)
ws.cell(1, len(BCATS)+2, "TOTAL")
style_header(ws, 1, len(BCATS)+2)
ws.column_dimensions["A"].width = 52
for j in range(2, len(BCATS)+3):
    ws.column_dimensions[get_column_letter(j)].width = 14
for i, d in enumerate(BDEST):
    r = 2 + i; cvr = b_r0 + i
    lab = ws.cell(r, 1, SAM[d]); lab.font = Font(name=FN, bold=True, color="C00000") if d == "imports" else Font(name=FN)
    for j, k in enumerate(BCATS, 2):
        L = get_column_letter(j)
        ws.cell(r, j, f"=T3_cost_vectors!{L}{cvr}*T3_cost_vectors!{L}$2").font = BLACK
        ws.cell(r, j).number_format = BN
    ws.cell(r, len(BCATS)+2, f"=SUM(B{r}:{get_column_letter(len(BCATS)+1)}{r})").font = BOLD
    ws.cell(r, len(BCATS)+2).number_format = BN
b_rtot = 2 + len(BDEST)
ws.cell(b_rtot, 1, "TOTAL").font = BOLD
for j in range(2, len(BCATS)+3):
    L = get_column_letter(j)
    ws.cell(b_rtot, j, f"=SUM({L}2:{L}{b_rtot-1})").font = BOLD
    ws.cell(b_rtot, j).number_format = BN; ws.cell(b_rtot, j).fill = GREYF
ws.freeze_panes = "B2"

# ================= TASK 4 — ENERGY MIX & VEHICLES =================
import task4_data as t4

def write_pivot(sheet, piv, title, subtitle, valfmt="#,##0", cum_row=False, index_name="Year"):
    ws = wb.create_sheet(sheet)
    ws.cell(1, 1, title).font = BOLD
    ws.cell(2, 1, subtitle).font = Font(name=FN, size=9, italic=True)
    hrow = 3
    ws.cell(hrow, 1, index_name)
    cols = list(piv.columns)
    for j, c in enumerate(cols, 2):
        ws.cell(hrow, j, str(c))
    style_header(ws, hrow, len(cols)+1)
    ws.column_dimensions["A"].width = 12
    for j in range(2, len(cols)+2):
        ws.column_dimensions[get_column_letter(j)].width = 15
    for i, idx in enumerate(piv.index):
        r = hrow+1+i
        ws.cell(r, 1, int(idx) if str(idx).isdigit() or isinstance(idx, (int, float)) else str(idx)).font = Font(name=FN)
        for j, c in enumerate(cols, 2):
            ws.cell(r, j, round(float(piv.loc[idx, c]), 3)).font = BLACK
            ws.cell(r, j).number_format = valfmt
    ws.freeze_panes = "B4"
    return ws

# ---- vehicles (reconstructed with the Tableau divisor logic) ----
veh = t4.vehicles()
STRAT_ORDER = ["Business as Usual - CDN", "Baseline Scenario - SNBC", "LTS"]
ws = wb.create_sheet("T4_vehicles")
ws.column_dimensions["A"].width = 13
for j in range(2, 10):
    ws.column_dimensions[get_column_letter(j)].width = 16
ws.cell(1, 1, "Task 4 — Number of vehicles, reconstructed from the Tableau logic").font = BOLD
method = [
 "HOW THIS WAS COMPUTED (matches the Tableau sheet 'EVs-Private'):",
 "  vehicles = VKM / divisor, where VKM = vehicle_distance_traveled_trns_<mode>_<fuel> (vehicle-km, per fuel),",
 "  and the divisor is the km/vehicle/year set in Tableau: road_light = 12,000 (field Value_road_ligth = [value]/12000),",
 "  public = 60,000 (field Value_public = [value]/60000). Only these two modes have a Tableau divisor.",
 "  Strategy labels (Tableau aliases): BASE = 'Business as Usual - CDN', bau = 'Baseline Scenario - SNBC', LEDS = 'LTS'.",
 "  Below, each strategy shows the RAW VKM by fuel and the vehicles = VKM/divisor as a live formula (blue = raw model output).",
]
r = 2
for ln in method:
    ws.cell(r, 1, ln).font = Font(name=FN, size=9, italic=True); ws.cell(r, 1).alignment = WRAP
    r += 1
r += 1

def veh_section(mode, divisor):
    """T2-style layout: ALL raw VKM blocks first, THEN all vehicle-estimation blocks
    (formulas referencing the raw blocks above)."""
    global r
    fuels = [f for f in t4.FUEL_ORDER
             if ((veh["mode"] == mode) & (veh.fuel == f)).any()
             and veh[(veh["mode"] == mode) & (veh.fuel == f)]["vkm"].abs().sum() > 0]
    ws.cell(r, 1, f"{mode.upper()}  —  divisor {divisor:,} km/veh/yr").font = Font(name=FN, bold=True, size=12)
    r += 2

    # ---------- RAW SECTION (all strategies) ----------
    ws.cell(r, 1, f"RAW DATA — VKM (vehicle-km) by fuel; source: vehicle_distance_traveled_trns_{mode}_<fuel>").font = BOLD
    r += 1
    raw_start = {}
    yrs_ref = None
    for strat in STRAT_ORDER:
        vp = (veh[(veh["mode"] == mode) & (veh.strategy == strat)]
              .pivot_table(index="Year", columns="fuel", values="vkm", aggfunc="sum")
              .fillna(0).reindex(columns=fuels).fillna(0))
        yrs = list(vp.index); yrs_ref = yrs
        ws.cell(r, 1, f"RAW VKM — {strat}").font = BOLD
        for c in range(1, len(fuels)+2):
            ws.cell(r, c).fill = GREYF
        hr = r + 1
        ws.cell(hr, 1, "Year")
        for j, f in enumerate(fuels, 2):
            ws.cell(hr, j, f)
        style_header(ws, hr, len(fuels)+1)
        d0 = hr + 1
        for i, y in enumerate(yrs):
            rr = d0 + i
            ws.cell(rr, 1, int(y)).font = Font(name=FN)
            for j, f in enumerate(fuels, 2):
                ws.cell(rr, j, round(float(vp.loc[y, f]), 1)).font = BLUE
                ws.cell(rr, j).number_format = "#,##0"
        raw_start[strat] = d0
        r = d0 + len(yrs) + 1

    # ---------- ESTIMATION SECTION (all strategies) ----------
    r += 1
    ws.cell(r, 1, f"ESTIMATION — vehicles = VKM / {divisor:,}  (each cell = the RAW cell above divided by {divisor:,})").font = BOLD
    r += 1
    for strat in STRAT_ORDER:
        raw0 = raw_start[strat]
        ws.cell(r, 1, f"VEHICLES — {strat}").font = BOLD
        for c in range(1, len(fuels)+3):
            ws.cell(r, c).fill = GREYF
        hr = r + 1
        ws.cell(hr, 1, "Year")
        for j, f in enumerate(fuels, 2):
            ws.cell(hr, j, f)
        ws.cell(hr, len(fuels)+2, "TOTAL")
        style_header(ws, hr, len(fuels)+2)
        d0 = hr + 1
        for i, y in enumerate(yrs_ref):
            rr = d0 + i
            ws.cell(rr, 1, int(y)).font = Font(name=FN)
            for j, f in enumerate(fuels, 2):
                L = get_column_letter(j)
                ws.cell(rr, j, f"={L}{raw0+i}/{divisor}").font = BLACK
                ws.cell(rr, j).number_format = "#,##0"
            ws.cell(rr, len(fuels)+2, f"=SUM(B{rr}:{get_column_letter(len(fuels)+1)}{rr})").font = BOLD
            ws.cell(rr, len(fuels)+2).number_format = "#,##0"
        EST_BLOCKS.append({"mode": mode, "strat": strat, "hdr": hr, "d0": d0,
                           "dn": d0 + len(yrs_ref) - 1, "nfuel": len(fuels)})
        r = d0 + len(yrs_ref) + 2

EST_BLOCKS = []
veh_section("road_light", 12000)
veh_section("public", 60000)
veh_section("road_heavy_freight", 60000)
ws.freeze_panes = "B2"

# ---- charts: final output of Task 4 (stacked area, vehicles by fuel, per strategy) ----
from openpyxl.chart import AreaChart, Reference
from openpyxl.drawing.image import Image as XLImage

def embed_png(sheet, fname, anchor, width=1000):
    """Embed a PNG (scaled to `width` px, aspect preserved) if it exists. Renders in every
    Excel (unlike native openpyxl charts, which can show blank in Excel for Mac)."""
    path = os.path.join(HERE, fname)
    if not os.path.exists(path):
        return
    img = XLImage(path)
    if img.width:
        img.height = int(img.height * width / img.width); img.width = width
    img.anchor = anchor
    wb[sheet].add_image(img)

cws = wb.create_sheet("T4_EVs_chart")
cws.cell(1, 1, "Task 4 — Number of vehicles by fuel, per strategy").font = BOLD
cws.cell(2, 1, "Vehicles = VKM / divisor (road_light /12,000; public and road_heavy_freight /60,000), by fuel and "
              "scenario. Under LTS: road_light -> Electricity, road_heavy_freight -> Hydrogen.").font = Font(name=FN, size=9, italic=True)
embed_png("T4_EVs_chart", "T4_EVs_private.png", "A4", width=1040)
embed_png("T4_EVs_chart", "T4_EVs_public_heavy.png", "A28", width=1040)

# ---- electricity generation: RAW PJ + % of total, per scenario, from the raw run ----
elec, etech = t4.elec_production_pj()
STRAT_ORDER3 = ["Business as Usual - CDN", "Baseline Scenario - SNBC", "LTS"]
ncol = len(etech)
yrs_e = list(elec[STRAT_ORDER3[0]].index)
egs = wb.create_sheet("T4_elec_generation")
egs.column_dimensions["A"].width = 12
for j in range(2, ncol + 3):
    egs.column_dimensions[get_column_letter(j)].width = 12
egs.cell(1, 1, "Task 4 — Electricity production by technology: PJ (raw) and % of total, per scenario").font = BOLD
enote = [
 "HOW THIS WAS COMPUTED (electricity generation mix), all straight from the raw run:",
 "  RAW: electricity produced by each generation technology, per scenario and year, from the raw wide-output",
 "  column  nemomod_entc_annual_production_by_technology_pp_<tech>  (PJ).",
 "  Below each raw block: SHARE OF TOTAL = technology PJ / that year's total PJ (live formula). Reproduces the",
 "  Tableau 'Electricity Generation by Source' view. Scenarios: BASE = 'Business as Usual - CDN',",
 "  bau = 'Baseline Scenario - SNBC', LEDS = 'LTS'.",
]
r = 2
for ln in enote:
    egs.cell(r, 1, ln).font = Font(name=FN, size=9, italic=True); egs.cell(r, 1).alignment = WRAP
    r += 1
r += 1
# --- RAW PJ section (all scenarios) ---
egs.cell(r, 1, "RAW — electricity production (PJ) by technology; source: nemomod_entc_annual_production_by_technology_pp_<tech>").font = BOLD
r += 1
raw_pos = {}
for st in STRAT_ORDER3:
    piv = elec[st]
    egs.cell(r, 1, f"RAW PJ — {st}").font = BOLD
    for c in range(1, ncol + 3):
        egs.cell(r, c).fill = GREYF
    hr = r + 1
    egs.cell(hr, 1, "Year")
    for j, t in enumerate(etech, 2):
        egs.cell(hr, j, t)
    egs.cell(hr, ncol + 2, "TOTAL")
    style_header(egs, hr, ncol + 2)
    d0 = hr + 1
    for i, y in enumerate(yrs_e):
        rr = d0 + i
        egs.cell(rr, 1, int(y)).font = Font(name=FN)
        for j, t in enumerate(etech, 2):
            egs.cell(rr, j, round(float(piv.loc[y, t]), 3)).font = BLUE
            egs.cell(rr, j).number_format = "#,##0.0"
        egs.cell(rr, ncol + 2, f"=SUM(B{rr}:{get_column_letter(ncol+1)}{rr})").font = BOLD
        egs.cell(rr, ncol + 2).number_format = "#,##0.0"
    raw_pos[st] = {"d0": d0, "totcol": get_column_letter(ncol + 2)}
    r = d0 + len(yrs_e) + 1
# --- % OF TOTAL section (formulas referencing raw) ---
r += 1
egs.cell(r, 1, "SHARE OF TOTAL — % = technology PJ / total PJ  (formula referencing the RAW block above)").font = BOLD
r += 1
pct_pos = {}
for st in STRAT_ORDER3:
    rp = raw_pos[st]; d0r = rp["d0"]; totL = rp["totcol"]
    egs.cell(r, 1, f"% OF TOTAL — {st}").font = BOLD
    for c in range(1, ncol + 2):
        egs.cell(r, c).fill = GREYF
    hr = r + 1
    egs.cell(hr, 1, "Year")
    for j, t in enumerate(etech, 2):
        egs.cell(hr, j, t)
    style_header(egs, hr, ncol + 1)
    d0 = hr + 1
    for i, y in enumerate(yrs_e):
        rr = d0 + i
        egs.cell(rr, 1, int(y)).font = Font(name=FN)
        for j, t in enumerate(etech, 2):
            L = get_column_letter(j)
            egs.cell(rr, j, f"={L}{d0r+i}/{totL}{d0r+i}").font = BLACK
            egs.cell(rr, j).number_format = "0.0%"
    pct_pos[st] = {"hdr": hr, "d0": d0, "dn": d0 + len(yrs_e) - 1}
    r = d0 + len(yrs_e) + 2
egs.freeze_panes = "B2"

# --- electricity mix chart (% of total), reproduces 'Electricity Generation by Source' ---
ecws = wb.create_sheet("T4_elec_chart")
ecws.cell(1, 1, "Task 4 — Electricity generation by source (% of total), per scenario").font = BOLD
ecws.cell(2, 1, "Share of total electricity production by technology, computed in T4_elec_generation. Reproduces the "
              "Tableau 'Electricity Generation by Source Morocco'.").font = Font(name=FN, size=9, italic=True)
embed_png("T4_elec_chart", "T4_elec_mix.png", "A4", width=1150)

gen, totf, secs, gunits = t4.energy_mix()
write_pivot("T4_energy_by_fuel", totf,
            "Task 4 — Total final energy demand by fuel (LEDS)",
            "Total Energy Demand by Fuel, from the Tableau 'drivers' datasource. Per-sector splits "
            "(Transport, Buildings/SCOE, Industry) available in the drivers data on request.",
            valfmt="#,##0.0")

# ================= TASK 5 — ECOSYSTEM & FOOD DISAGGREGATION =================
# de Groot et al. (2012) Table 2, temperate forest (Int$/ha/yr, 2007) — basis of Costanza (2014).
DG_TEMPERATE = {  # service -> value; the $500/ha is already NET of food + climate(carbon)
    "Provisioning (non-food: water, raw materials, genetic)": 671 - 299,  # 372
    "Regulating (non-climate: water flow, waste treatment, erosion, nutrient, pollination, bio-control)": 491 - 152,  # 339
    "Habitat / biodiversity (nursery, genetic diversity)": 862,
    "Cultural (recreation/TOURISM, aesthetic, inspiration)": 990,
}
DG_STRIPPED = {"Food (provisioning)": 299, "Climate regulation (carbon)": 152}
dg_base = sum(DG_TEMPERATE.values())   # 2562 after stripping food + carbon
NET_HA = 500.0                          # primary forest $/ha/yr, already net of food+carbon

ws = wb.create_sheet("T5_ecosystem_split")
ws.column_dimensions["A"].width = 66
for i, w in enumerate([66, 16, 14, 16], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.cell(1, 1, "Task 5 — Ecosystem services: evidence-based split of the $500/ha/yr forest value").font = BOLD
ws.cell(2, 1, "Source: de Groot et al. (2012) Table 2, temperate forest (Int$/ha/yr, 2007) — the unit-value basis of "
              "Costanza (2014). Morocco-specific refinement: Taye (2021).").font = Font(name=FN, size=9, italic=True)
ws.cell(3, 1, "The $500/ha is ALREADY NET of food provisioning and carbon (climate regulation); those two services "
              "are stripped below and the remainder renormalised, so there is NO double-count against crop value.").font = Font(name=FN, size=9, italic=True)
hr = 5
for j, h in enumerate(["Ecosystem service (grouped)", "de Groot Int$/ha", "Share of net", "Applied $/ha (of 500)"], 1):
    ws.cell(hr, j, h)
style_header(ws, hr, 4)
r = hr + 1
for svc, val in DG_TEMPERATE.items():
    ws.cell(r, 1, svc).font = Font(name=FN)
    ws.cell(r, 2, val).font = BLUE
    ws.cell(r, 3, f"=B{r}/B${hr+len(DG_TEMPERATE)+1}").font = BLACK; ws.cell(r, 3).number_format = PCT
    ws.cell(r, 4, f"=C{r}*{NET_HA}").font = BLACK; ws.cell(r, 4).number_format = "$#,##0"
    r += 1
ws.cell(r, 1, "NET BASE (food + carbon excluded)").font = BOLD
ws.cell(r, 2, f"=SUM(B{hr+1}:B{r-1})").font = BOLD
ws.cell(r, 4, f"=SUM(D{hr+1}:D{r-1})").font = BOLD; ws.cell(r, 4).number_format = "$#,##0"
for c in range(1, 5):
    ws.cell(r, c).fill = GREYF
r += 2
ws.cell(r, 1, "STRIPPED before renormalisation (already counted elsewhere):").font = BOLD
r += 1
for svc, val in DG_STRIPPED.items():
    ws.cell(r, 1, f"  {svc}").font = Font(name=FN)
    ws.cell(r, 2, val).font = Font(name=FN, color="C00000")
    ws.cell(r, 3, "excluded").font = Font(name=FN, color="C00000", size=9)
    r += 1
r += 1
for line in [
    "KEY POINT for Moulaye: TOURISM is a SUBSET of ecosystem-service value — it is the cultural (recreation)",
    "service line above (~$192 of the $500/ha, since recreation is ~989/990 of the cultural total). It is NOT a",
    "parallel category alongside 'environment'. The split must be a partition of ONE total, not two overlapping ones.",
    "",
    "Do NOT re-add food or carbon: the $500 figure already excludes them. Pulling the full Costanza/de Groot",
    "breakdown without stripping food + climate would double-count against Crop value (food) and the carbon benefit.",
]:
    ws.cell(r, 1, line).font = Font(name=FN, size=9, italic=("KEY POINT" not in line))
    if "KEY POINT" in line:
        ws.cell(r, 1).font = Font(name=FN, size=9, bold=True)
    r += 1

# ---- T5_memo (food savings feasibility + summary) ----
ws = wb.create_sheet("T5_memo")
ws.column_dimensions["A"].width = 118
memo = [
 ("Task 5 — answers to Moulaye's two disaggregation questions", True),
 ("", False),
 ("Q1. ECOSYSTEM SERVICES — can the value be split by service type?  YES, evidence-based (see T5_ecosystem_split).", True),
 ("  - Factors come from Costanza (2014), whose unit values are de Groot et al. (2012) Table 2. Both break value", False),
 ("    down by service type, so we use their temperate-forest breakdown rather than inventing percentages.", False),
 ("  - CRITICAL: the $500/ha (primary) and $300/ha (secondary) figures are ALREADY NET of food provisioning and", False),
 ("    carbon. We strip those two services out of the de Groot breakdown and renormalise the rest to 100% before", False),
 ("    applying to $500/ha. Skipping this step would reintroduce double-counting against Crop value and the carbon benefit.", False),
 ("  - TOURISM is a cultural (recreation) service — a SUBSET of the ecosystem-service total, not a separate category", False),
 ("    parallel to 'environment'. Present the split as a partition of one total. Recreation is ~$192 of the $500/ha.", False),
 ("  - Taye (2021) gives Morocco/Mediterranean-specific values that can refine the shares; the method is unchanged.", False),
 ("", False),
 ("Q2. FOOD CONSUMER SAVINGS by product — mostly NOT FEASIBLE. Say this early rather than inventing detail.", True),
 ("  Food consumer savings (64.76 bn cumulative) is built from three components, ALL using flat factors with no", False),
 ("  product dimension:", False),
 ("    1. Dietary shift  — $385/person/year x urban population adopting improved diets  (per-capita, flat).", False),
 ("    2. Consumer food-waste reduction — $350/tonne of food waste avoided  (per-tonne, flat).", False),
 ("    3. Conservation agriculture — $350/ha of improved cropland  (per-hectare, flat).", False),
 ("  Because each factor is flat, the calculation carries NO by-product resolution.", False),
 ("    - Component 1 (dietary) COULD be split by product using an external diet-composition assumption (e.g.", False),
 ("      Springmann et al. dietary shares) — but that is an ADDED assumption, not something in the model.", False),
 ("    - Components 2 and 3 (waste, conservation ag) cannot be split by product at all.", False),
 ("  Recommendation: report the dietary component optionally split via Springmann (flagged as an assumption), and", False),
 ("  state plainly that the waste and conservation-agriculture components are not decomposable by product.", False),
]
for i, (t, b) in enumerate(memo, 1):
    c = ws.cell(i, 1, t); c.font = BOLD if b else Font(name=FN); c.alignment = WRAP

# ================= TASK 7 — PERCENTAGE CHANGE =================
t7 = pd.read_csv(os.path.join(HERE, "task7_result.csv"))
ws = wb.create_sheet("T7_pct_change")
ws.column_dimensions["A"].width = 52
for i, w in enumerate([52, 13, 13, 15, 12, 58], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.cell(1, 1, "Task 7 — (LTS - SNBC) / SNBC, both vs a common no-action (BASE) reference. Cumulative 2023-2050, bn 2019 USD.").font = BOLD
ws.cell(2, 1, "SNBC = PFLO:BAU minus BASE.  LTS = PFLO:LEDS minus BASE.  numerator = LTS - SNBC (= plain LTS-SNBC).").font = Font(name=FN, size=9, italic=True)
ws.cell(3, 1, "FINDING: in the reused runs, PFLO:BAU is ~identical to BASE (BAU-BASE ~ 0 for almost every category), so the "
              "SNBC denominator collapses and the % is structurally undefined. A meaningful % needs a DISTINCT SNBC-ambition run.").font = Font(name=FN, size=9, color="C00000", bold=True)
hr = 5
for j, h in enumerate(["Benefit category", "SNBC (bn)", "LTS (bn)", "numerator (bn)", "% change", "Reason / flag"], 1):
    ws.cell(hr, j, h)
style_header(ws, hr, 6)
r = hr + 1
for _, row in t7.iterrows():
    ws.cell(r, 1, row["category"]).font = Font(name=FN)
    ws.cell(r, 2, round(row["SNBC_bn"], 3)).font = BLACK
    ws.cell(r, 3, round(row["LTS_bn"], 3)).font = BLACK
    ws.cell(r, 4, round(row["numerator_bn"], 3)).font = BLACK
    if pd.notna(row["pct"]):
        ws.cell(r, 5, round(row["pct"], 4)).font = BLACK
        ws.cell(r, 5).number_format = PCT
    else:
        ws.cell(r, 5, "—").font = Font(name=FN, color="808080"); ws.cell(r, 5).alignment = CTR
    for col in (2, 3, 4):
        ws.cell(r, col).number_format = BN
    rc = ws.cell(r, 6, row["reason"]); rc.font = Font(name=FN, size=9); rc.alignment = WRAP
    if "DROPPED" in str(row["reason"]) or "SUPPRESSED" in str(row["reason"]):
        rc.font = Font(name=FN, size=9, color="C00000")
    r += 1
r += 1
for line in [
    "Rules applied (per the task):",
    "  - Fertilizer DROPPED — within $2.7m of zero in all 28 years.",
    "  - Sign-change categories SUPPRESSED (a % across a sign change is meaningless): crop value, both fuel-savings rows,",
    "    air-quality health, water pollution — plus any other whose SNBC increment crosses zero over the horizon.",
    "  - Near-zero SNBC denominator SUPPRESSED; O&M-type near-zero denominators flagged.",
    "  - Absolute values (SNBC, LTS, numerator) shown next to every % so nothing is hidden by suppression.",
    "  - Validation PASSED: sum(numerator) = sum(LTS) - sum(SNBC), and the LTS column reproduces the cost-benefit file.",
    "",
    "Because BAU ~ BASE here, the numerator (LTS - SNBC) essentially equals LTS-vs-no-action and IS delivered; only the",
    "percentages are undefined. To get real percentages, run a distinct SNBC-ambition scenario (the 'new SNBC run' option).",
]:
    ws.cell(r, 1, line).font = Font(name=FN, size=9, bold=line.startswith("Rules"))
    r += 1

wb.save(OUT)
print("saved", OUT)
