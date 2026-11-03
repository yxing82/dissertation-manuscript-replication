"""Manuscript figure: flow mechanisms x all three gentrification subtypes.

Redraw of EDA 12 v7 (fig_eda12_yee_subtype_mechanism_map_v7_20260729.png) with
the marginal-gentrification (MargGen) marker added, so the map covers the same
three subtypes as Table 5 (scripts/manuscript_table5_mechanism_subtype.py).

Inputs (all tracked in the repository, no data/ folder needed):
  outputs/eda12_yee_leaf_corroboration_20260705.csv  mechanism leaves + subtype flags
                                                     (same source as Table 5)
  outputs/eda4_results_for_phase3_20260626.csv       Typ_C_11 / Typ_C_21 for the
                                                     Counter-led vs Symmetric/Lateral fill
  MSOA_Dec_2011_Boundaries_..._BGC_EW_V3_2022_*.zip  ONS MSOA 2011 boundaries (BGC)
  flow_yee_palette_v2.py                             colour grammar

Changes vs v7:
  * MargGen marker added (black X, white halo), legend entry with n.
  * Where one MSOA carries more than one subtype, its markers are spread a few
    hundred metres apart around the MSOA point so none hides another
    (v7 drew SupGen and MainGen on the same point).
  * Boundaries read from the ONS BGC shapefile in the repo root instead of the
    untracked data/london_msoa_2011.geojson.
  Fills, palette, titles, annotations and legends are otherwise as in v7.

Run from the repository root:
    python scripts/manuscript_fig_subtype_mechanism_map.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flow_yee_palette_v2 import (FLOW_ALPHA, FLOW_DRAW_ORDER, FLOW_FILL,  # noqa: E402
                                 FLOW_LABEL, MARKER_STYLE, SUBTYPE_MARKER)

SRC = ROOT / "outputs" / "eda12_yee_leaf_corroboration_20260705.csv"
EDA4 = ROOT / "outputs" / "eda4_results_for_phase3_20260626.csv"
TAB5 = ROOT / "outputs" / "manuscript_table5_mechanism_subtype_20261017.csv"
BND = next(ROOT.glob("MSOA_Dec_2011_Boundaries_Generalised_Clipped_BGC_EW_V3_2022_*.zip"))
FIG_DIR = ROOT / "outputs" / "comparison_figs"
OUT_PNG = FIG_DIR / "fig_manuscript_subtype_mechanism_map_3subtypes_20261102.png"
OUT_PDF = OUT_PNG.with_suffix(".pdf")

SUBS = ["SupGen", "MainGen", "MargGen"]
FLAGS = [f"any_{s}" for s in SUBS]

# MargGen: filled X, same black as the other subtype markers, white halo.
MARGEN_STYLE = dict(s=24, marker="X", facecolors=SUBTYPE_MARKER,
                    edgecolors="white", linewidths=0.5)
OFFSET_M = 330  # spacing between markers that share one MSOA (metres, EPSG:27700)

LONDON_LADS = {
    "City of London", "Barking and Dagenham", "Barnet", "Bexley", "Brent", "Bromley",
    "Camden", "Croydon", "Ealing", "Enfield", "Greenwich", "Hackney",
    "Hammersmith and Fulham", "Haringey", "Harrow", "Havering", "Hillingdon",
    "Hounslow", "Islington", "Kensington and Chelsea", "Kingston upon Thames",
    "Lambeth", "Lewisham", "Merton", "Newham", "Redbridge", "Richmond upon Thames",
    "Southwark", "Sutton", "Tower Hamlets", "Waltham Forest", "Wandsworth",
    "Westminster",
}


def load():
    d = pd.read_csv(SRC)
    for c in FLAGS:
        d[c] = d[c].astype(str).str.lower() == "true"
    typ = pd.read_csv(EDA4)[["msoa11cd", "Typ_C_11", "Typ_C_21"]]
    d = d.merge(typ, on="msoa11cd", how="left", validate="1:1")
    assert d[["Typ_C_11", "Typ_C_21"]].notna().all().all()

    # Guards: must reproduce EDA 9 leaf counts and the EDA 12 subtype counts.
    assert d["leaf_11"].value_counts().to_dict() == {
        "outflow-internal": 81, "frame-sensitive": 57, "inflow-driven": 56,
        "outflow-external": 19}
    assert d["leaf_21"].value_counts().to_dict() == {
        "outflow-internal": 90, "outflow-external": 78, "frame-sensitive": 14,
        "inflow-driven": 13}
    assert [int(d[c].sum()) for c in FLAGS] == [94, 39, 101]

    for yr in ("11", "21"):
        d[f"map_class_{yr}"] = np.where(
            d[f"leaf_{yr}"].notna(), d[f"leaf_{yr}"],
            np.where(d[f"Typ_C_{yr}"] == "Counter-led", "counter", "other"))
    return d


def geometry(d):
    g = gpd.read_file(f"zip://{BND}")
    g = g.rename(columns={c: c.lower() for c in g.columns if c.lower() == "msoa11cd"})
    lad = g["MSOA11NM"].str.rsplit(" ", n=1).str[0]
    g = g[lad.isin(LONDON_LADS)].copy()
    assert len(g) == 983, f"expected 983 London MSOAs, got {len(g)}"
    if g.crs is None or g.crs.to_epsg() != 27700:
        g = g.to_crs(27700)
    missing = set(g["msoa11cd"]) - set(d["msoa11cd"])
    assert missing == {"E02000190"}, missing
    g = g[["msoa11cd", "geometry"]].merge(d, on="msoa11cd", how="left")

    # Camden 024/025 merge: E02000190 inherits E02000189's fill, no markers
    # (same convention as EDA 10 / EDA 12).
    m = g["msoa11cd"] == "E02000190"
    donor = g.loc[g["msoa11cd"] == "E02000189"].iloc[0]
    for c in d.columns:
        if c != "msoa11cd":
            g.loc[m, c] = donor[c]
    g.loc[m, FLAGS] = False
    for c in FLAGS:
        g[c] = g[c].astype(bool)
    return g


def marker_positions(g):
    """One (x, y) per subtype flag; spread when an MSOA carries several."""
    pts = g.geometry.representative_point()
    pos = {s: ([], []) for s in SUBS}
    layouts = {1: [(0, 0)],
               2: [(-0.5, 0), (0.5, 0)],
               3: [(-0.5, -0.29), (0.5, -0.29), (0, 0.58)]}
    for i, row in g.iterrows():
        present = [s for s in SUBS if row[f"any_{s}"]]
        for (dx, dy), s in zip(layouts.get(len(present), []), present):
            pos[s][0].append(pts[i].x + dx * 2 * OFFSET_M)
            pos[s][1].append(pts[i].y + dy * 2 * OFFSET_M)
    return pos


# def caption_stats():
#     t = pd.read_csv(TAB5)
#     t["year"] = t["year"].astype(str)
#     lines = []
#     for sub in ["Super", "Mainstream", "Marginal"]:
#         for yr in ("2011", "2021"):
#             for _, r in t[(t.subtype == sub) & (t.year == yr)].iterrows():
#                 if r.fisher_p < 0.05:
#                     lines.append(f"  {sub} x {r.profile} ({yr}): {r.n_label}/{r.n} "
#                                  f"({r.pct_group:.1f}% vs {r.pct_london:.1f}% London), "
#                                  f"p = {r.fisher_p:.2g}, BH q = {r.bh_q:.2g}")
#     return lines


def main():
    d = load()
    g = geometry(d)
    pos = marker_positions(g)

    outer_outline = g.dissolve()
    inner = g[g["Ring"] == "Inner"].dissolve()
    inner.geometry = inner.buffer(25).buffer(-25)

    TITLES = {"11": ("2011 Migration Window",
                     "Yee labels describe change during 2001–2011"),
              "21": ("2021 Migration Window",
                     "compared with the same earlier gentrification geography")}
    ANNOT = {"11": "MainGen concentrates in inflow-driven profiles · "
                   "SupGen in outflow-internal profiles",
             "21": "SupGen enrichment in outflow-internal persists"}
    HALO = [pe.withStroke(linewidth=MARKER_STYLE["halo_lw"], foreground="white")]

    fig, axes = plt.subplots(1, 2, figsize=(15.6, 8.3))
    for ax, yr in zip(axes, ("11", "21")):
        for cls in FLOW_DRAW_ORDER:
            sub = g[g[f"map_class_{yr}"] == cls]
            if len(sub):
                sub.plot(ax=ax, color=FLOW_FILL[cls], alpha=FLOW_ALPHA[cls],
                         edgecolor="none")
        outer_outline.boundary.plot(ax=ax, color="#999999", linewidth=0.8, zorder=4)
        inner.boundary.plot(ax=ax, color="black", linewidth=1.2,
                            linestyle=(0, (6, 3)), zorder=5)
        ax.scatter(*pos["MargGen"], zorder=6, path_effects=HALO, **MARGEN_STYLE)
        ax.scatter(*pos["SupGen"], zorder=7, path_effects=HALO, **MARKER_STYLE["supgen"])
        ax.scatter(*pos["MainGen"], zorder=8, path_effects=HALO, **MARKER_STYLE["maingen"])
        t, s = TITLES[yr]
        ax.set_title(t + "\n", fontsize=12.8, fontweight="bold", pad=10)
        ax.text(0.5, 1.035, s, transform=ax.transAxes, ha="center", fontsize=10,
                style="italic", color="#555555")
        ax.set_axis_off()

    fig.text(0.28, 0.165, ANNOT["11"], ha="center", fontsize=9.3, color="#444444")
    fig.text(0.755, 0.165, ANNOT["21"], ha="center", fontsize=9.3, color="#444444")

    # fill_handles = [mpatches.Patch(fc=FLOW_FILL[c], alpha=FLOW_ALPHA[c], label=FLOW_LABEL[c])
    #                 for c in ("inflow-driven", "frame-sensitive", "outflow-external",
    #                           "outflow-internal", "counter", "other")]
        # Legend wording only: rename "Counter-led" to "Escalator-led".
    # Classification, data and the shared palette are unchanged.
    legend_label = dict(FLOW_LABEL)
    assert "Counter-led" in legend_label["counter"], legend_label["counter"]
    legend_label["counter"] = legend_label["counter"].replace("Counter-led", "Escalator-led")

    fill_handles = [mpatches.Patch(fc=FLOW_FILL[c], alpha=FLOW_ALPHA[c], label=legend_label[c])
                    for c in ("inflow-driven", "frame-sensitive", "outflow-external",
                              "outflow-internal", "counter", "other")]
    
    LG = MARKER_STYLE["legend"]
    yee_handles = [
        Line2D([0], [0], marker="o", ls="", mfc="none", mec=SUBTYPE_MARKER,
               mew=LG["supgen_mew"], markersize=LG["supgen_ms"], path_effects=HALO,
               label=f"≥ 1 SupGen LSOA (n = {int(d.any_SupGen.sum())})"),
        Line2D([0], [0], marker="^", ls="", mfc=SUBTYPE_MARKER, mec="white",
               mew=LG["maingen_mew"], markersize=LG["maingen_ms"], path_effects=HALO,
               label=f"≥ 1 MainGen LSOA (n = {int(d.any_MainGen.sum())})"),
        Line2D([0], [0], marker="X", ls="", mfc=SUBTYPE_MARKER, mec="white",
               mew=0.5, markersize=6.2, path_effects=HALO,
               label=f"≥ 1 MargGen LSOA (n = {int(d.any_MargGen.sum())})"),
    ]
    bnd_handles = [
        Line2D([0], [0], color="black", lw=1.2, ls=(0, (6, 3)),
               label="Inner London (statutory)"),
        Line2D([0], [0], color="#999999", lw=0.8, label="Greater London"),
    ]
    l1 = fig.legend(handles=fill_handles, loc="lower left", bbox_to_anchor=(0.04, 0.005),
                    ncol=2, frameon=False, fontsize=8.6, alignment="left",
                    title="Area fill — flow mechanism classification (this study)")
    l2 = fig.legend(handles=yee_handles, loc="lower left", bbox_to_anchor=(0.555, 0.005),
                    ncol=1, frameon=False, fontsize=8.6, alignment="left",
                    title="Markers — Yee & Dennett (2022)\noverlapping subtype indicators")
    l3 = fig.legend(handles=bnd_handles, loc="lower left", bbox_to_anchor=(0.80, 0.005),
                    ncol=1, frameon=False, fontsize=8.6, alignment="left",
                    title="Boundaries")
    for lg in (l1, l2, l3):
        lg.get_title().set_fontweight("bold")
        lg.get_title().set_fontsize(9.2)

    fig.suptitle("Correspondence between flow mechanisms and "
                 "attribute-defined gentrification subtypes",
                 fontsize=14, fontweight="bold", y=0.99)
    fig.text(0.5, 0.945, "Area fills show this study’s independently derived flow "
             "mechanisms; black markers show Yee & Dennett (2022) subtype locations.",
             ha="center", fontsize=10.5, style="italic", color="#444444")

    plt.tight_layout(rect=[0, 0.185, 1, 0.90])
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for out in (OUT_PNG, OUT_PDF):
        fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"Saved {OUT_PNG.relative_to(ROOT)} and {OUT_PDF.name}")

    # Marker counts per fill class, checked against Table 5 for the cascade leaves.
    t5 = pd.read_csv(TAB5)
    t5["year"] = t5["year"].astype(str)
    for yr in ("11", "21"):
        counts = d.groupby(f"map_class_{yr}")[FLAGS].sum()
        print(f"\n20{yr} markers per fill class:\n{counts.to_string()}")
        for _, r in t5[t5.year == f"20{yr}"].iterrows():
            if r.flag_col in FLAGS:
                assert counts.loc[r.profile_key, r.flag_col] == r.n_label
    print("\nCascade-leaf marker counts match Table 5.")
    # print("\nSignificant cells for the caption (Table 5, p < 0.05):")
    # print("\n".join(caption_stats()))


if __name__ == "__main__":
    main()
