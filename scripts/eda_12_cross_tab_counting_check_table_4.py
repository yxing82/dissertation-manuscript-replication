"""Manuscript Section 4.1: "Cascade-led" status x modal gentrification label.
 
Builds the separate cross-tabulation table (TABLE_NAME below) that reports, for
each reference frame (A, B, C) and migration window (2011, 2021), the four cells
of the 2 x 2 table under explicit names:
 
  "Cascade-led" zones, labelled       ("Cascade-led" and gentrification)
  "Cascade-led" zones, not labelled   ("Cascade-led", no gentrification label)
  Other zones, labelled               (gentrification label, not "Cascade-led")
  Other zones, not labelled           (neither)
 
"Labelled" means the zone carries the modal gentrification label. Percentages
are shares of the zones in each group, and the last column gives the share of
all labelled zones that fall outside the "Cascade-led" regime. Descriptive only:
no significance tests. Cramer's V and the ARI stay in Table 3.
 
Modal rule (manuscript Section 3.4): an MSOA is modal-gentrification only when
its GEN LSOAs strictly outnumber every other Class 2 category among its
constituent LSOAs. A tie involving GEN is assigned to non-gentrification.
This is the same rule as scripts/manuscript_cross_tab_counting_check.py.
 
Inputs
  outputs/eda4_results_for_phase3_20260626.csv   flow regimes (Typ_*)
  data/yee_LSOA_labels_forMapping.csv            Yee & Dennett (2022) LSOA labels
                                                 (gitignored, place locally)
  outputs/lsoa11_to_msoa11.csv                   LSOA -> MSOA lookup
  outputs/manuscript_modal_cascade_crosstab_20261026.csv
  outputs/manuscript_modal_by_regime_20261026.csv
                                                 optional: outputs of the Table 3
                                                 script, used only to confirm the
                                                 counts match
 
Outputs
  outputs/manuscript_cascade_label_table_<STAMP>.csv
  outputs/manuscript_cascade_label_table_<STAMP>.md
  outputs/<TABLE_NAME>.png                     no caption: it lives in the manuscript source
 
Run from the repository root:
    python scripts/manuscript_cascade_label_table.py
"""
 
from pathlib import Path
 
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
import numpy as np
import pandas as pd
 
ROOT = Path(__file__).resolve().parents[1]
EDA4 = ROOT / "outputs" / "eda4_results_for_phase3_20260626.csv"
YEE = ROOT / "data" / "yee_LSOA_labels_forMapping.csv"
LOOKUP = ROOT / "outputs" / "lsoa11_to_msoa11.csv"
PREV_CROSSTAB = ROOT / "outputs" / "manuscript_modal_cascade_crosstab_20261026.csv"
PREV_BY_REGIME = ROOT / "outputs" / "manuscript_modal_by_regime_20261026.csv"
OUT = ROOT / "outputs"
STAMP = "20261027"
 
# Table numbers: change here if the order of tables changes.
# This table replaces the earlier by-regime Table 4 and takes its number.
TABLE_NAME = "Table 4"
TABLE_PNG = OUT / f"{TABLE_NAME}.png"
 
FRAMES = ["A", "B", "C"]
YEARS = [("11", "2011"), ("21", "2021")]
 
 
# --------------------------------------------------------------------------
# Modal gentrification label (strict plurality)
# --------------------------------------------------------------------------
def strict_modal_gen(msoa_codes):
    """Return a boolean Series (index msoa11cd): True = modal gentrification."""
    yee = pd.read_csv(YEE).rename(columns={"LSOA_Code": "lsoa11cd"})
    lk = pd.read_csv(LOOKUP)[["lsoa11cd", "msoa11cd"]].drop_duplicates().dropna()
    yg = yee.merge(lk, on="lsoa11cd", how="inner")
 
    # Number of LSOAs in each Class 2 category, per MSOA
    counts = pd.crosstab(yg["msoa11cd"], yg["Class_2_status"])
    n_gen = counts["GEN"]
    n_top_other = counts.drop(columns="GEN").max(axis=1)
 
    gen = (n_gen > n_top_other).rename("modal_gen")   # ties -> not GEN
    gen = gen.reindex(msoa_codes)
    assert gen.notna().all(), "some analytical zones have no Yee labels"
    return gen.astype(bool)
 
 
# --------------------------------------------------------------------------
# The four cells, group totals and percentages
# --------------------------------------------------------------------------
def cascade_label_table(d, gen):
    g = gen.reindex(d["msoa11cd"]).values.astype(bool)
    rows = []
    for fr in FRAMES:
        for yr, label in YEARS:
            cl = d[f"Typ_{fr}_{yr}"].eq("Cascade-led").values
            rows.append(dict(
                frame=fr, window=label,
                cl_labelled=int(np.sum(cl & g)),        # "Cascade-led" and labelled
                cl_not_labelled=int(np.sum(cl & ~g)),   # "Cascade-led", no label
                oth_labelled=int(np.sum(~cl & g)),      # labelled, not "Cascade-led"
                oth_not_labelled=int(np.sum(~cl & ~g)), # neither
            ))
    t = pd.DataFrame(rows)
    t["cl_total"] = t.cl_labelled + t.cl_not_labelled
    t["oth_total"] = t.oth_labelled + t.oth_not_labelled
    t["n_labelled"] = t.cl_labelled + t.oth_labelled
 
    # Shares within each group (so labelled + not labelled = 100% per group)
    t["pct_cl_labelled"] = 100 * t.cl_labelled / t.cl_total
    t["pct_cl_not_labelled"] = 100 * t.cl_not_labelled / t.cl_total
    t["pct_oth_labelled"] = 100 * t.oth_labelled / t.oth_total
    t["pct_oth_not_labelled"] = 100 * t.oth_not_labelled / t.oth_total
    # Share of all labelled zones that are not "Cascade-led"
    t["pct_labelled_outside_cl"] = 100 * t.oth_labelled / t.n_labelled
 
    # The four cells partition the zones; the label total never changes
    assert (t.cl_total + t.oth_total == len(d)).all(), "cells do not sum to n"
    assert (t.n_labelled == int(g.sum())).all(), "labelled total varies"
    return t
 
 
# --------------------------------------------------------------------------
# Optional check against the Table 3 / Table 4 outputs
# --------------------------------------------------------------------------
def _read_prev(path):
    return pd.read_csv(path, dtype={"frame": str, "window": str})
 
 
def compare_with_previous(t):
    lines = []
    if PREV_CROSSTAB.exists():
        m = t.merge(_read_prev(PREV_CROSSTAB), on=["frame", "window"])
        ok = len(m) == len(t) and (
            (m.cl_labelled == m.both) & (m.cl_not_labelled == m.cascade_only)
            & (m.oth_labelled == m.gen_only) & (m.oth_not_labelled == m.neither)
        ).all()
        lines.append(f"- Counts identical to {PREV_CROSSTAB.name}: {bool(ok)}")
    if PREV_BY_REGIME.exists():
        p = _read_prev(PREV_BY_REGIME)
        p = (p[p.regime == "Cascade-led"]
             .rename(columns={"n_labelled": "t4_labelled", "n_zones": "t4_zones"}))
        m = t.merge(p[["frame", "window", "t4_labelled", "t4_zones"]],
                    on=["frame", "window"])
        ok = len(m) == len(t) and (
            (m.cl_labelled == m.t4_labelled) & (m.cl_total == m.t4_zones)
        ).all()
        lines.append('- "Cascade-led" counts identical to '
                     f"{PREV_BY_REGIME.name}: {bool(ok)}")
    if not lines:
        return ["Earlier outputs not found; consistency check skipped."]
    return ["## Consistency with the Table 3 script outputs", ""] + lines
 
 
# --------------------------------------------------------------------------
# Table rows
# --------------------------------------------------------------------------
def _cell(n, pct):
    return f"{n} ({pct:.1f}%)"
 
 
def table_rows(t):
    rows = []
    for r in t.itertuples():
        rows.append([
            r.frame, r.window,
            _cell(r.cl_labelled, r.pct_cl_labelled),
            _cell(r.cl_not_labelled, r.pct_cl_not_labelled),
            str(r.cl_total),
            _cell(r.oth_labelled, r.pct_oth_labelled),
            _cell(r.oth_not_labelled, r.pct_oth_not_labelled),
            str(r.oth_total),
            f"{r.pct_labelled_outside_cl:.1f}",
        ])
    return rows
 
 
# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def render_table(rows, n_gen, path):
    plt.rcParams["font.family"] = "STIXGeneral"
    plt.rcParams["mathtext.fontset"] = "stix"
 
    # column centres in axes units (0..1)
    X = [0.035, 0.10, 0.21, 0.315, 0.40, 0.505, 0.61, 0.695, 0.865]
    FS = 10.5
 
    fig = plt.figure(figsize=(10.5, 4.3), dpi=300)
    ax = fig.add_axes([0.02, 0.0, 0.96, 1.0])
    ax.patch.set_visible(False)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
 
    def hline(y, x0=0.0, x1=1.0, lw=0.8, color="black"):
        ax.plot([x0, x1], [y, y], color=color, lw=lw, solid_capstyle="butt")
 
    def txt(x, y, s, **kw):
        ax.text(x, y, s, ha="center", va="center", fontsize=FS, **kw)
 
    hline(0.965, lw=1.1)
 
    # spanning header 1: what "Labelled" means
    left, right = X[2] - 0.06, X[8] + 0.08
    txt((left + right) / 2, 0.925,
        "Labelled = zone carries the modal gentrification label "
        "(Yee & Dennett, 2022)")
    hline(0.895, left, right, lw=0.6)
 
    # spanning header 2: the two groups of zones
    y_grp = 0.86
    txt((X[2] + X[4]) / 2, y_grp, "“Cascade-led” zones")
    hline(y_grp - 0.03, X[2] - 0.06, X[4] + 0.03, lw=0.6)
    txt((X[5] + X[7]) / 2, y_grp, "Other zones")
    hline(y_grp - 0.03, X[5] - 0.06, X[7] + 0.03, lw=0.6)
 
    # column headers
    yh = 0.785
    for x, s in [(X[0], "Frame"), (X[1], "Window"),
                 (X[2], "Labelled"), (X[3], "Not labelled"), (X[4], "Total"),
                 (X[5], "Labelled"), (X[6], "Not labelled"), (X[7], "Total")]:
        txt(x, yh, s)
    txt(X[8], 0.81, f"Labelled zones outside\n“Cascade-led” (% of {n_gen})",
        linespacing=1.15)
 
    y_mid = 0.745
    hline(y_mid, lw=0.6)
 
    # body, with light rules between rows
    row_h = 0.062
    y = y_mid - 0.04
    for i, r in enumerate(rows):
        for x, v in zip(X, r):
            txt(x, y, str(v))
        if i < len(rows) - 1:
            hline(y - row_h / 2, lw=0.4, color="#bbbbbb")
        y -= row_h
 
    y_bot = y + row_h - 0.035
    hline(y_bot, lw=1.1)
 
    # Crop to the drawn rules and text, so no empty band is left below the table.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    content = Bbox.union([a.get_window_extent(renderer) for a in [*ax.texts, *ax.lines]])
    content = content.transformed(fig.dpi_scale_trans.inverted()).padded(0.08)
    fig.savefig(path, dpi=300, bbox_inches=content, facecolor="white")
    plt.close(fig)
 
 
# --------------------------------------------------------------------------
def main():
    d = pd.read_csv(EDA4)
    assert len(d) == 982, f"expected 982 analytical zones, found {len(d)}"
 
    if not YEE.exists():
        raise SystemExit(f"{YEE.relative_to(ROOT)} not found (gitignored). "
                         "Place the Yee & Dennett LSOA labels there and rerun.")
 
    gen = strict_modal_gen(d["msoa11cd"])
    n_gen = int(gen.sum())
    t = cascade_label_table(d, gen)
    t.to_csv(OUT / f"manuscript_cascade_label_table_{STAMP}.csv", index=False)
 
    md = [
        f'# {TABLE_NAME}: "Cascade-led" status x modal gentrification label', "",
        "Generated by `scripts/manuscript_cascade_label_table.py`. "
        f"n = {len(d)} zones; {n_gen} labelled zones (modal gentrification, "
        "strict plurality). Descriptive only: no significance tests.", "",
        "Labelled = zone carries the modal gentrification label. Percentages are "
        "shares of the zones in each group.", "",
        '| Frame | Window | "Cascade-led": labelled | "Cascade-led": not labelled '
        '| "Cascade-led": total | Other: labelled | Other: not labelled '
        f'| Other: total | Labelled zones outside "Cascade-led" (% of {n_gen}) |',
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in table_rows(t):
        md.append("| " + " | ".join(row) + " |")
    md += ["", *compare_with_previous(t)]
 
    render_table(table_rows(t), n_gen, TABLE_PNG)
    md += ["", f"{TABLE_NAME} written to `{TABLE_PNG.relative_to(ROOT)}`."]
 
    text = "\n".join(md) + "\n"
    (OUT / f"manuscript_cascade_label_table_{STAMP}.md").write_text(text)
    print(text)
 
 
if __name__ == "__main__":
    main()