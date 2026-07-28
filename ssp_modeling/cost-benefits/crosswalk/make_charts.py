"""Generate the Task 4 chart PNGs embedded in the workbook (reproducible)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from task4_data import vehicles, elec_production_pj, FUEL_ORDER

HERE = os.path.dirname(os.path.abspath(__file__))
STRATS = ["Business as Usual - CDN", "Baseline Scenario - SNBC", "LTS"]
FCOL = {"electricity": "#F5A623", "gasoline": "#7FC7BF", "diesel": "#6B8FB5",
        "hydrocarbon_gas_liquids": "#8FBF6B", "hydrogen": "#E0798C",
        "biofuels": "#B0A0D0", "natural_gas": "#C9A05A"}
ECOL = {"coal": "#E8963A", "coal_ccs": "#F0C08A", "gas": "#5FA55A", "gas_ccs": "#A9D4A0",
        "oil": "#D9737A", "solar": "#F2A9BC", "wind": "#B8B8B8", "hydropower": "#F0D264",
        "nuclear": "#4C9C93", "biogas": "#5A7DB0", "biomass": "#A9C7E8", "ocean": "#8FD0CE",
        "waste_incineration": "#9A9A9A", "geothermal": "#B8A94C"}


def _veh_panel(v, mode, unit, title, fname):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
    for ax, st in zip(axes, STRATS):
        sub = v[(v["mode"] == mode) & (v.strategy == st)]
        piv = sub.pivot_table(index="Year", columns="fuel", values="vehicles", aggfunc="sum").fillna(0)
        fuels = [f for f in FUEL_ORDER if f in piv.columns and piv[f].abs().sum() > 0]
        ax.stackplot(piv.index, [piv[f] / unit for f in fuels],
                     labels=[f.replace("_", " ").title() for f in fuels],
                     colors=[FCOL.get(f, "#ccc") for f in fuels], alpha=0.9)
        ax.set_title(st, fontsize=11); ax.set_xlabel("Year"); ax.margins(x=0)
        ax.axvline(2030, color="grey", lw=0.6); ax.axvline(2040, color="grey", lw=0.6)
    axes[0].set_ylabel(title.split("—")[1].strip())
    axes[-1].legend(loc="upper left", fontsize=9, frameon=False)
    fig.suptitle(title, fontsize=13, y=1.02); plt.tight_layout()
    plt.savefig(os.path.join(HERE, fname), dpi=130, bbox_inches="tight"); plt.close(fig)


def main():
    v = vehicles()
    _veh_panel(v, "road_light", 1e6,
               "Task 4 — Private light vehicles (road_light) by fuel = VKM / 12,000  [millions]",
               "T4_EVs_private.png")
    # public + heavy in one 2-row figure
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), sharex=True)
    for ri, mode in enumerate(["public", "road_heavy_freight"]):
        for ci, st in enumerate(STRATS):
            ax = axes[ri][ci]
            sub = v[(v["mode"] == mode) & (v.strategy == st)]
            piv = sub.pivot_table(index="Year", columns="fuel", values="vehicles", aggfunc="sum").fillna(0)
            fuels = [f for f in FUEL_ORDER if f in piv.columns and piv[f].abs().sum() > 0]
            ax.stackplot(piv.index, [piv[f] / 1e3 for f in fuels],
                         labels=[f.replace("_", " ").title() for f in fuels],
                         colors=[FCOL.get(f, "#ccc") for f in fuels], alpha=0.9)
            if ri == 0:
                ax.set_title(st, fontsize=11)
            if ci == 0:
                ax.set_ylabel(f"{mode}\nvehicles (thousands)")
            ax.margins(x=0); ax.axvline(2030, color="grey", lw=0.5); ax.axvline(2040, color="grey", lw=0.5)
    axes[0][-1].legend(loc="upper left", fontsize=8, frameon=False)
    fig.suptitle("Task 4 — Public transport and Heavy freight trucks by fuel (both = VKM / 60,000)", fontsize=13, y=1.0)
    plt.tight_layout(); plt.savefig(os.path.join(HERE, "T4_EVs_public_heavy.png"), dpi=125, bbox_inches="tight"); plt.close(fig)

    # electricity mix % of total
    elec, etech = elec_production_pj()
    fig, axes = plt.subplots(1, 3, figsize=(17, 6), sharey=True)
    for ax, st in zip(axes, STRATS):
        piv = elec[st]; share = piv.div(piv.sum(axis=1), axis=0) * 100
        techs = [t for t in etech if share[t].abs().sum() > 0]
        ax.stackplot(share.index, [share[t] for t in techs], labels=[("pp_" + t) for t in techs],
                     colors=[ECOL.get(t, "#ccc") for t in techs], alpha=0.9)
        ax.set_title(st, fontsize=11); ax.set_xlabel("Year"); ax.margins(x=0, y=0); ax.set_ylim(0, 100)
        ax.axvline(2030, color="grey", lw=0.5); ax.axvline(2040, color="grey", lw=0.5)
    axes[0].set_ylabel("Electricity production by technology (% of total)")
    axes[-1].legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False)
    fig.suptitle("Task 4 — Electricity Generation by Source (% of total), from raw NEMOMOD production by technology", fontsize=13, y=1.0)
    plt.tight_layout(); plt.savefig(os.path.join(HERE, "T4_elec_mix.png"), dpi=125, bbox_inches="tight"); plt.close(fig)
    print("charts generated")


if __name__ == "__main__":
    main()
