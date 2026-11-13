"""Manuscript figure: flow mechanisms x all three gentrification subtypes.

Inputs (all tracked in the repository, no data/ folder needed):
  outputs/eda12_yee_leaf_corroboration_20260705.csv  mechanism leaves + subtype flags
                                                     (same source as Table 5)
  outputs/eda4_results_for_phase3_20260626.csv       Typ_C_11 / Typ_C_21 for the
                                                     Counter-led vs Symmetric/Lateral fill
  MSOA_Dec_2011_Boundaries_..._BGC_EW_V3_2022_*.zip  ONS MSOA 2011 boundaries (BGC)
  flow_yee_palette_v2.py                             colour grammar


Run from the repository root:
    python scripts/11_figure5_map.py
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

BND = next((ROOT / "data").glob("MSOA_Dec_2011_Boundaries_Generalised_Clipped_BGC_EW_V3_2022_*.zip"))

EDA9 = ROOT / "outputs" / "eda9_mechanism_tree_20260705.csv"
FIG_DIR = ROOT / "outputs" / "comparison_figs"
OUT_PNG = FIG_DIR / "fig_manuscript_subtype_mechanism_map_3subtypes_stacked.png"
OUT_PDF = OUT_PNG.with_suffix(".pdf")

SUBS = ["SupGen", "MainGen", "MargGen"]
FLAGS = [f"any_{s}" for s in SUBS]

# MargGen: filled X, same black as the other subtype markers, white halo.
MARGEN_STYLE = dict(s=24, marker="X", facecolors=SUBTYPE_MARKER,
                    edgecolors="white", linewidths=0.5)
OFFSET_M = 380  # spacing between markers that share one MSOA (metres, EPSG:27700);
                # was 330, widened because markers are relatively larger on the 11.5 cm map

# Print-size layout (cm). FIG_W_CM = A4 text width with 2.54 cm margins.
CM = 1 / 2.54
FIG_W_CM = 15.9   # full figure width
MAP_W_CM = 12.0   # width of each stacked map; the rest is the legend column
GAP_CM = 0.3      # vertical gap between the 2011 and 2021 maps
LEGEND_GAP_CM = 0.3   # space between the three legend blocks
FONT_PT = 7       # base text size at print size
TITLE_PT = 7      # legend block titles (bold)
LABEL_PT = 6.5    # legend entries; keep >= 6 pt, the usual journal minimum
YEAR_PT = 8.5
# Marker sizes for an 11.5 cm map (s is in points squared).
MAP_MARKERS = {
    "SupGen":  dict(s=13, facecolors="none", edgecolors=SUBTYPE_MARKER, linewidths=0.9),
    "MainGen": dict(s=17, marker="^", facecolors=SUBTYPE_MARKER, edgecolors="white",
                    linewidths=0.4),
    "MargGen": dict(s=15, marker="X", facecolors=SUBTYPE_MARKER, edgecolors="white",
                    linewidths=0.35),
}

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

        # Guard: leaves must match the EDA 6 tree zone by zone.
    ref = pd.read_csv(EDA9).set_index("msoa11cd")
    short = {"inflow-driven": "inflow-driven", "frame-sensitive inflow": "frame-sensitive",
             "outflow: external-majority": "outflow-external",
             "outflow: internal-majority": "outflow-internal"}
    for yr in ("11", "21"):
        expected = ref[f"leaf_{yr}"].map(short).reindex(d["msoa11cd"]).fillna("none").values
        assert (d[f"leaf_{yr}"].fillna("none").values == expected).all(), f"leaf_{yr} differs from EDA 6"
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

    # ---- Layout: two maps stacked, one shared legend on the right ----------
    # Drawn at the size it is printed (A4 text width), so point sizes are real.
    xmin, ymin, xmax, ymax = outer_outline.total_bounds
    map_h_cm = MAP_W_CM * (ymax - ymin) / (xmax - xmin)
    fig_h_cm = 2 * map_h_cm + GAP_CM
    plt.rcParams.update({"font.size": FONT_PT})
    fig = plt.figure(figsize=(FIG_W_CM * CM, fig_h_cm * CM))
    HALO = [pe.withStroke(linewidth=1.5, foreground="white")]

    for i, yr in enumerate(("11", "21")):
        bottom = fig_h_cm - (i + 1) * map_h_cm - i * GAP_CM
        ax = fig.add_axes([0, bottom / fig_h_cm, MAP_W_CM / FIG_W_CM, map_h_cm / fig_h_cm])
        for cls in FLOW_DRAW_ORDER:
            sub = g[g[f"map_class_{yr}"] == cls]
            if len(sub):
                sub.plot(ax=ax, color=FLOW_FILL[cls], alpha=FLOW_ALPHA[cls],
                         edgecolor="none")
        outer_outline.boundary.plot(ax=ax, color="#999999", linewidth=0.5, zorder=4)
        inner.boundary.plot(ax=ax, color="black", linewidth=0.8,
                            linestyle=(0, (6, 3)), zorder=5)
        ax.scatter(*pos["MargGen"], zorder=6, path_effects=HALO, **MAP_MARKERS["MargGen"])
        ax.scatter(*pos["SupGen"], zorder=7, path_effects=HALO, **MAP_MARKERS["SupGen"])
        ax.scatter(*pos["MainGen"], zorder=8, path_effects=HALO, **MAP_MARKERS["MainGen"])
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal")
        # Year label in the empty north-west corner instead of a title above the map.
        ax.text(0.0, 1.0, f"20{yr}", transform=ax.transAxes, ha="left", va="top",
                fontsize=YEAR_PT, fontweight="bold")
        ax.set_axis_off()

    # Legend wording in the article's terms (classification and colours unchanged).
    legend_label = {
        "inflow-driven":    "Inflow-driven, frame-robust",
        "frame-sensitive":  "Frame-sensitive inflow",
        "outflow-external": "Outflow-external-majority",
        "outflow-internal": "Outflow-internal-majority",
        "counter":          "Escalator-led",
        "other":            "Symmetric or Lateral",
    }
    fill_handles = [mpatches.Patch(fc=FLOW_FILL[c], alpha=FLOW_ALPHA[c], label=legend_label[c])
                    for c in ("inflow-driven", "frame-sensitive", "outflow-external",
                              "outflow-internal", "counter", "other")]
    yee_handles = [
        Line2D([0], [0], marker="o", ls="", mfc="none", mec=SUBTYPE_MARKER,
               mew=0.8, markersize=4.0, path_effects=HALO,
               label=f"SupGen (n = {int(d.any_SupGen.sum())})"),
        Line2D([0], [0], marker="^", ls="", mfc=SUBTYPE_MARKER, mec="white",
               mew=0.4, markersize=4.5, path_effects=HALO,
               label=f"MainGen (n = {int(d.any_MainGen.sum())})"),
        Line2D([0], [0], marker="X", ls="", mfc=SUBTYPE_MARKER, mec="white",
               mew=0.35, markersize=4.2, path_effects=HALO,
               label=f"MargGen (n = {int(d.any_MargGen.sum())})"),
    ]
    bnd_handles = [
        Line2D([0], [0], color="black", lw=0.8, ls=(0, (6, 3)), label="Inner London (statutory)"),
        Line2D([0], [0], color="#999999", lw=0.5, label="Greater London"),
    ]

    # Legend column to the right of the maps, centred on the gap between them.
    lax = fig.add_axes([(MAP_W_CM + 0.25) / FIG_W_CM, 0,
                        (FIG_W_CM - MAP_W_CM - 0.25) / FIG_W_CM, 1])
    lax.set_axis_off()
    blocks = [
        (fill_handles, "Flow mechanism profile\nor flow regime (Frame C)", 1.2),
        (yee_handles, "Gentrification subtype\n(Yee & Dennett, 2022)", 1.2),
        (bnd_handles, "Boundaries", 2.0),   # longer sample so a full dash shows
    ]
    # Stack the three legend blocks by their measured heights, then centre the
    # column vertically on the gap between the maps.
    renderer = fig.canvas.get_renderer()
    to_fig = fig.transFigure.inverted()
    lx = lax.get_position().x0
    legends, y = [], 1.0
    for handles, title, hlen in blocks:
        lg = lax.legend(handles=handles, title=title, loc="upper left",
                        bbox_to_anchor=(lx, y), bbox_transform=fig.transFigure,
                        frameon=False, fontsize=LABEL_PT, title_fontsize=TITLE_PT,
                        alignment="left", borderaxespad=0, borderpad=0,
                        handlelength=hlen, handleheight=0.6, handletextpad=0.5,
                        labelspacing=0.3)
        lg.get_title().set_fontweight("bold")
        lax.add_artist(lg)
        legends.append((lg, y))
        y = lg.get_window_extent(renderer).transformed(to_fig).y0 - LEGEND_GAP_CM / fig_h_cm
    used = 1.0 - (y + LEGEND_GAP_CM / fig_h_cm)
    shift = (1.0 - used) / 2
    for lg, y0 in legends:
        lg.set_bbox_to_anchor((lx, y0 - shift), transform=fig.transFigure)

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for out in (OUT_PNG, OUT_PDF):
        # No bbox_inches="tight": keep the exact print size so Word inserts it at 100%.
        fig.savefig(out, dpi=600, facecolor="white")
    print(f"Saved {OUT_PNG.name} and {OUT_PDF.name} "
          f"({FIG_W_CM:.1f} x {fig_h_cm:.1f} cm; insert at 100% in Word)")
 
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


if __name__ == "__main__":
    main()
