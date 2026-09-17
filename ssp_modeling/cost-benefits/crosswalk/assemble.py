"""Compose power cost-vector from Task 2 shares, validate all share tables, print applied."""
import pandas as pd, openpyxl
from crosswalk_data import (SAM, AGENTS, AGENT_SHARES, COST_VECTORS,
                            CV_POWER, CV_POWER_SRC, POWER_GEN_SHARE, POWER_TRN_SHARE)

INV = "/Users/fabianfuentes/Downloads/investment_requirements_morocco_2026_07_19.xlsx"
import os
_HERE = os.path.dirname(os.path.abspath(__file__))


def build_model():
    """Return (inv_rows, inv_cum, years, COST_VECTORS, AGENT_SHARES, gw)."""
    wb = openpyxl.load_workbook(INV); ws = wb["Sheet 1"]
    years = [ws.cell(2, c).value for c in range(2, ws.max_column+1)]
    inv_rows = {}
    for r in range(3, ws.max_row+1):
        name = ws.cell(r, 1).value
        if not name or "units" in str(name).lower():
            continue
        vals = [ws.cell(r, c).value or 0 for c in range(2, ws.max_column+1)]
        inv_rows[name] = dict(zip(years, vals))
    inv_cum = {k: sum(v.values()) for k, v in inv_rows.items()}

    cx = pd.read_csv(os.path.join(_HERE, "task2_capex.csv"))
    pos = cx[cx.capex_incremental_musd > 0].groupby("technology")["capex_incremental_musd"].sum()
    gen_share = (pos / pos.sum())
    GEN_MAP = {"pp_wind": "wind", "pp_solar": "solar", "pp_biogas": "biogas", "pp_nuclear": "nuclear"}
    gw = {GEN_MAP[t]: s for t, s in gen_share.items() if t in GEN_MAP}
    gwsum = sum(gw.values()); gw = {k: v/gwsum for k, v in gw.items()}

    def blend(vectors_weights):
        out = {}
        for vec, w in vectors_weights:
            for k, v in vec.items():
                out[k] = out.get(k, 0) + v*w
        return out
    power_parts = [(CV_POWER[tech], POWER_GEN_SHARE*w) for tech, w in gw.items()]
    power_parts.append((CV_POWER["transmission"], POWER_TRN_SHARE))
    COST_VECTORS["EN - Power Industry"] = (blend(power_parts), CV_POWER_SRC)
    return inv_rows, inv_cum, years, COST_VECTORS, AGENT_SHARES, gw


inv_rows, inv_cum, years, COST_VECTORS, AGENT_SHARES, gw = build_model()
power_vec = COST_VECTORS["EN - Power Industry"][0]

# ---- VALIDATE sums ----
print("=== validation: agent shares sum to 1 ===")
for k, (g, f, h, _) in AGENT_SHARES.items():
    assert abs(g+f+h-1) < 1e-9, (k, g+f+h)
print("  all agent rows OK")
print("=== validation: cost vectors sum to 1 ===")
for k, (vec, _) in COST_VECTORS.items():
    s = sum(vec.values())
    assert abs(s-1) < 1e-9, (k, s)
    for dest in vec:
        assert dest in SAM, (k, dest, "unknown SAM key")
print("  all cost vectors OK")

# ---- APPLIED cumulative allocations ----
print("\n=== gen-block tech weights (renormalised) ===", {k: round(v,3) for k,v in gw.items()})
print("\n=== EN - Power Industry composed cost vector ===")
for k, v in sorted(power_vec.items(), key=lambda x:-x[1]):
    print(f"  {SAM[k]:45s} {v*100:5.1f}%")

print("\n=== APPLIED: cumulative investment by AGENT (bn USD) ===")
agent_tot = {a: 0 for a in AGENTS}
for k, (g, f, h, _) in AGENT_SHARES.items():
    T = inv_cum.get(k, 0)
    agent_tot["government"] += T*g; agent_tot["firms"] += T*f; agent_tot["households"] += T*h
for a in AGENTS:
    print(f"  {a:12s} {agent_tot[a]:7.2f}")
print(f"  {'TOTAL':12s} {sum(agent_tot.values()):7.2f}  (investment file total = {sum(inv_cum.values()):.2f})")

print("\n=== APPLIED: cumulative investment by SAM destination (bn USD), top 15 ===")
sam_tot = {}
for k, (vec, _) in COST_VECTORS.items():
    T = inv_cum.get(k, 0)
    for dest, sh in vec.items():
        sam_tot[dest] = sam_tot.get(dest, 0) + T*sh
for dest, v in sorted(sam_tot.items(), key=lambda x:-x[1])[:15]:
    print(f"  {SAM[dest]:45s} {v:7.2f}")
print(f"  {'--- of which IMPORTS':45s} {sam_tot.get('imports',0):7.2f}")
print(f"  {'TOTAL':45s} {sum(sam_tot.values()):7.2f}")
