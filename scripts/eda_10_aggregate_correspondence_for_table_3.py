"""Manuscript Section 4.1: aggregate correspondence with neighbourhood change.
 
Single source for every statistic reported in the aggregate-correspondence
section, following the dissertation design (Section 3.9) with the manuscript's
strict-plurality rule for the modal gentrification label.
 
  1. Spearman rank correlations between IMD percentile change (2010-2019) and
     Cascade_Dominance / Cross_Decile_Share, Frames A, B and C, both windows.
  2. Kruskal-Wallis tests of IMD percentile change across the four regimes,
     with epsilon-squared and regime medians, Frames A, B and C, both windows.
  3. 2x2 cross-tabulation of "Cascade-led" status against modal-gentrification
     status, with chi-square (no continuity correction), Cramer's V and the
     adjusted Rand index, Frames A, B and C, both windows.
  4. Table 3 drawn from 1-3 (nothing hard-coded): rho Cascade_Dominance,
     rho Cross_Decile_Share, Kruskal-Wallis H (epsilon^2), Cramer's V and ARI
     per frame and window, in the same style as Table 4. A dagger marks any
     rho or H with p >= 0.05, and the caption names those cells and their p.
 
Modal rule (manuscript Section 3.4): an MSOA is modal-gentrification only when
its GEN LSOAs strictly outnumber every other class among its constituent LSOAs;
a tie involving GEN is assigned to the non-GEN class.
 
Inputs
  outputs/eda4_results_for_phase3_20260626.csv   regimes, flow measures, IMD change
  data/yee_LSOA_labels_forMapping.csv            Yee & Dennett (2022) LSOA labels
                                                 (gitignored; part 3 is skipped
                                                 with a message if absent)
  outputs/lsoa11_to_msoa11.csv                   LSOA -> MSOA lookup
  outputs/eda12_yee_leaf_corroboration_20260705.csv  earlier labels, for the
                                                 consistency check and to list
                                                 zones changed by the tie rule
 
Outputs
  outputs/manuscript_aggregate_correlations_20261021.csv
  outputs/manuscript_aggregate_kruskal_20261021.csv
  outputs/manuscript_aggregate_crosstab_20261021.csv
  outputs/manuscript_aggregate_correspondence_20261021.md
  outputs/manuscript_table3_20261021.csv          rows as in Table 3
  outputs/Table 3.png                             Table 3 with caption
 
Run from the repository root:
    python scripts/manuscript_aggregate_correspondence.py
"""
 
import textwrap
from pathlib import Path
 
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, kruskal, spearmanr
from sklearn.metrics import adjusted_rand_score
 
ROOT = Path(__file__).resolve().parents[1]
EDA4 = ROOT / "outputs" / "eda4_results_for_phase3_20260626.csv"
YEE = ROOT / "data" / "yee_LSOA_labels_forMapping.csv"
LOOKUP = ROOT / "outputs" / "lsoa11_to_msoa11.csv"
EDA12 = ROOT / "outputs" / "eda12_yee_leaf_corroboration_20260705.csv"
OUT = ROOT / "outputs"
STAMP = "20261021"
 
FRAMES = ["A", "B", "C"]
YEARS = [("11", "2011"), ("21", "2021")]
REGIMES = ["Cascade-led", "Counter-led", "Symmetric", "Lateral"]
 
 
def correlations(d):
    rows = []
    for fr in FRAMES:
        for yr, label in YEARS:
            for name, col in [("Cascade_Dominance", f"Dom_{fr}_{yr}"),
                              ("Cross_Decile_Share", f"CDS_{fr}_{yr}")]:
                rho, p = spearmanr(d[col], d["IMD_Pctile_Change"])
                rows.append(dict(frame=fr, window=label, measure=name,
                                 n=len(d), rho=rho, p=p))
    return pd.DataFrame(rows)
 
 
def kruskal_tests(d):
    rows = []
    for fr in FRAMES:
        for yr, label in YEARS:
            col = f"Typ_{fr}_{yr}"
            groups = [d.loc[d[col] == r, "IMD_Pctile_Change"] for r in REGIMES]
            H, p = kruskal(*groups)
            n, k = len(d), len(REGIMES)
            row = dict(frame=fr, window=label, n=n, H=H, p=p,
                       eps2=(H - k + 1) / (n - k))
            for r, g in zip(REGIMES, groups):
                row[f"n_{r}"] = len(g)
                row[f"median_{r}"] = g.median()
            rows.append(row)
    return pd.DataFrame(rows)
 
 
def strict_modal_gen():
    """Binary modal-gentrification status per MSOA under strict plurality."""
    yee = pd.read_csv(YEE).rename(columns={"LSOA_Code": "lsoa11cd"})
    lk = pd.read_csv(LOOKUP)[["lsoa11cd", "msoa11cd"]].drop_duplicates().dropna()
    yg = yee.merge(lk, on="lsoa11cd", how="inner")
    counts = pd.crosstab(yg["msoa11cd"], yg["Class_2_status"])
    other = counts.drop(columns="GEN").max(axis=1)
    out = pd.DataFrame({
        "gen_strict": counts["GEN"] > other,
        "gen_tied": (counts["GEN"] == other) & (counts["GEN"] > 0),
        "n_gen_lsoa": counts["GEN"],
        "n_lsoa": counts.sum(axis=1),
    })
    # Consistency with the earlier pipeline: the any-LSOA flags involve no tie
    # rule, so they must match EDA 12 exactly.
    ref = pd.read_csv(EDA12).set_index("msoa11cd")
    ref_has_gen = ref["has_gen"].astype(str).str.lower() == "true"
    chk = out.reindex(ref.index)
    assert chk["n_lsoa"].notna().all(), "frame MSOAs missing from Yee labels"
    assert ((chk["n_gen_lsoa"] > 0) == ref_has_gen).all(), "any-GEN flags differ from EDA 12"
    ref_modal = ref["gen_modal"].astype(str).str.lower() == "true"
    changed = chk.index[chk["gen_strict"] != ref_modal]
    return chk, ref_modal, list(changed)
 
 
def crosstabs(d, gen):
    rows = []
    for fr in FRAMES:
        for yr, label in YEARS:
            casc = d[f"Typ_{fr}_{yr}"].eq("Cascade-led").values
            g = gen.reindex(d["msoa11cd"]).values.astype(bool)
            t = np.array([[np.sum(casc & g), np.sum(casc & ~g)],
                          [np.sum(~casc & g), np.sum(~casc & ~g)]])
            chi2, p, _, _ = chi2_contingency(t, correction=False)
            rows.append(dict(frame=fr, window=label,
                             cascade_gen=t[0, 0], cascade_not_gen=t[0, 1],
                             other_gen=t[1, 0], other_not_gen=t[1, 1],
                             chi2=chi2, p=p, cramers_v=np.sqrt(chi2 / t.sum()),
                             ari=adjusted_rand_score(casc, g)))
    return pd.DataFrame(rows)
 
 
def fmt_p(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"
 
 
# --------------------------------------------------------------------------
# Table 3: rho, H (epsilon^2), Cramer's V and ARI, in the Table 4 style
# --------------------------------------------------------------------------
# Table numbers: change here if the order of tables changes.
TABLE_NAME = "Table 3"
TABLE4_NAME = "Table 4"   # the cross-tabulation behind Cramer's V and the ARI
TABLE_PNG = OUT / f"{TABLE_NAME}.png"
TABLE_CSV = OUT / f"manuscript_table3_{STAMP}.csv"
SHOW_CAPTION = True       # False leaves the caption to the manuscript source
ALPHA = 0.05
DAGGER = "†"
MINUS = "−"               # typographic minus
NB = " "             # non-breaking space, keeps "n = 982" on one line
 
 
def table3_data(corr, kw, ct):
    """One row per frame and window, taken from the three result tables."""
    rows = []
    for fr in FRAMES:
        for _, w in YEARS:
            s = corr[(corr.frame == fr) & (corr.window == w)].set_index("measure")
            k = kw[(kw.frame == fr) & (kw.window == w)].iloc[0]
            x = ct[(ct.frame == fr) & (ct.window == w)].iloc[0]
            rows.append(dict(
                frame=fr, window=w,
                rho_dom=s.loc["Cascade_Dominance", "rho"],
                p_dom=s.loc["Cascade_Dominance", "p"],
                rho_cds=s.loc["Cross_Decile_Share", "rho"],
                p_cds=s.loc["Cross_Decile_Share", "p"],
                H=k.H, p_H=k.p, eps2=k.eps2,
                cramers_v=x.cramers_v, ari=x.ari))
    return pd.DataFrame(rows)
 
 
def _num(v, dp):
    return f"{v:.{dp}f}".replace("-", MINUS)
 
 
def _flag(p):
    return DAGGER if p >= ALPHA else ""
 
 
def table3_rows(t):
    return [[r.frame, r.window,
             _num(r.rho_dom, 3) + _flag(r.p_dom),
             _num(r.rho_cds, 3) + _flag(r.p_cds),
             f"{_num(r.H, 1)} ({_num(r.eps2, 3)}){_flag(r.p_H)}",
             _num(r.cramers_v, 3),
             _num(r.ari, 3)] for r in t.itertuples()]
 
 
def _p_text(p):
    return f"{p:.2g}"
 
 
def _all_below(ps, what):
    if (ps < 0.001).all():
        return f"all {what} have p{NB}<{NB}0.001"
    if (ps < ALPHA).all():
        return f"all {what} have p{NB}<{NB}0.05"
    return None
 
 
def table3_caption(t, n_zones, n_gen):
    flagged = []
    for r in t.itertuples():
        for p, what in [(r.p_dom, "ρ Cascade_Dominance"),
                        (r.p_cds, "ρ Cross_Decile_Share"),
                        (r.p_H, "H")]:
            if p >= ALPHA:
                flagged.append(f"{what}, Frame{NB}{r.frame} {r.window} "
                               f"(p{NB}={NB}{_p_text(p)})")
    if flagged:
        sig = (f"{DAGGER} Not significant at the 5% level: " + "; ".join(flagged)
               + ". All other ρ and H have p" + NB + "<" + NB + "0.05")
    else:
        sig = "All ρ and H have p" + NB + "<" + NB + "0.05"
    extra = [s for s in (_all_below(t.p_cds, "ρ Cross_Decile_Share"),
                         _all_below(t.p_H, "H")) if s and "0.001" in s]
    sig += ("; " + " and ".join(extra) if extra else "") + "."
 
    return (
        f"{TABLE_NAME}. Aggregate correspondence between flow measures, flow "
        "regimes and neighbourhood change, by reference frame and migration window "
        f"(n{NB}={NB}{n_zones} zones). Spearman’s ρ is calculated between each flow "
        "measure and IMD percentile change, 2010–2019; positive values indicate "
        "movement towards a less deprived relative position. Kruskal–Wallis H "
        "compares IMD percentile change across the four flow regimes, with "
        f"ε²{NB}={NB}(H{NB}−{NB}k{NB}+{NB}1)/(n{NB}−{NB}k) in brackets. "
        f"Cramér’s V (equal to |φ| for a 2{NB}×{NB}2 table) and the adjusted Rand "
        "index (ARI) compare “Cascade-led” membership with the modal gentrification "
        f"label ({n_gen} zones; strict plurality of Yee and Dennett’s (2022) Class 2 "
        "categories, ties not labelled); they are descriptive, and the underlying "
        f"cross-tabulation is reported in {TABLE4_NAME}. " + sig
    )
 
 
def render_table3(rows, caption, path):
    plt.rcParams["font.family"] = "STIXGeneral"
    plt.rcParams["mathtext.fontset"] = "stix"
 
    # column centres in axes units (0..1)
    X = [0.04, 0.115, 0.255, 0.415, 0.585, 0.765, 0.905]
    FS = 10.5
 
    fig = plt.figure(figsize=(10.5, 4.0 if caption else 3.0), dpi=300)
    ax = fig.add_axes([0.02, 0.0, 0.96, 1.0])
    ax.patch.set_visible(False)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
 
    # vertical layout in axes units, scaled so the body is the same with or
    # without the caption
    sy = 1.0 if caption else 4.0 / 3.0
 
    def Y(v):
        return 1 - (1 - v) * sy
 
    def hline(y, x0=0.0, x1=1.0, lw=0.8, color="black"):
        ax.plot([x0, x1], [y, y], color=color, lw=lw, solid_capstyle="butt")
 
    def txt(x, y, s, **kw):
        ax.text(x, y, s, ha="center", va="center", fontsize=FS, **kw)
 
    hline(Y(0.965), lw=1.1)
 
    # spanning headers: what each block of columns is compared with
    y_grp = Y(0.925)
    txt((X[2] + X[4]) / 2, y_grp, "IMD percentile change, 2010–2019")
    hline(Y(0.895), X[2] - 0.075, X[4] + 0.085, lw=0.6)
    txt((X[5] + X[6]) / 2, y_grp, "Modal gentrification label")
    hline(Y(0.895), X[5] - 0.07, X[6] + 0.06, lw=0.6)
 
    # column headers
    yh = Y(0.835)
    for x, s in [(X[0], "Frame"), (X[1], "Window"),
                 (X[2], "Spearman’s ρ\nCascade_Dominance"),
                 (X[3], "Spearman’s ρ\nCross_Decile_Share"),
                 (X[4], "Kruskal–Wallis\nH (ε²)"),
                 (X[5], "Cramér’s V"), (X[6], "ARI")]:
        txt(x, yh, s, linespacing=1.15)
 
    y_mid = Y(0.77)
    hline(y_mid, lw=0.6)
 
    # body, with light rules between rows
    row_h = 0.062 * sy
    y = y_mid - 0.04 * sy
    for i, r in enumerate(rows):
        for x, v in zip(X, r):
            txt(x, y, str(v))
        if i < len(rows) - 1:
            hline(y - row_h / 2, lw=0.4, color="#bbbbbb")
        y -= row_h
 
    y_bot = y + row_h - 0.035 * sy
    hline(y_bot, lw=1.1)
 
    if caption:
        ax.text(0.0, y_bot - 0.03, textwrap.fill(caption, width=172),
                ha="left", va="top", fontsize=9.2, style="italic", linespacing=1.35)
 
    # Crop to the drawn rules and text, so no empty band is left below the table.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    content = Bbox.union([a.get_window_extent(renderer) for a in [*ax.texts, *ax.lines]])
    content = content.transformed(fig.dpi_scale_trans.inverted()).padded(0.08)
    fig.savefig(path, dpi=300, bbox_inches=content, facecolor="white")
    plt.close(fig)
 
 
def write_table3(corr, kw, ct, n_zones, n_gen):
    t = table3_data(corr, kw, ct)
    t.to_csv(TABLE_CSV, index=False)
    caption = table3_caption(t, n_zones, n_gen) if SHOW_CAPTION else None
    render_table3(table3_rows(t), caption, TABLE_PNG)
    return t
 
 
def main():
    d = pd.read_csv(EDA4)
    assert len(d) == 982 and d["IMD_Pctile_Change"].notna().all()
 
    corr = correlations(d)
    kw = kruskal_tests(d)
    corr.to_csv(OUT / f"manuscript_aggregate_correlations_{STAMP}.csv", index=False)
    kw.to_csv(OUT / f"manuscript_aggregate_kruskal_{STAMP}.csv", index=False)
 
    md = ["# Aggregate correspondence (manuscript Section 4.1)", "",
          "Generated by `scripts/manuscript_aggregate_correspondence.py`. n = 982 zones.", "",
          "## 1. Spearman correlations with IMD percentile change, 2010-2019", "",
          "| Frame | Window | Cascade_Dominance rho (p) | Cross_Decile_Share rho (p) |",
          "| --- | --- | --- | --- |"]
    for fr in FRAMES:
        for _, label in YEARS:
            s = corr[(corr.frame == fr) & (corr.window == label)].set_index("measure")
            md.append(f"| {fr} | {label} | "
                      + " | ".join(f"{s.loc[m, 'rho']:.3f} ({fmt_p(s.loc[m, 'p'])})"
                                   for m in ["Cascade_Dominance", "Cross_Decile_Share"]) + " |")
    md += ["", "## 2. Kruskal-Wallis tests of IMD percentile change across regimes", "",
           "| Frame | Window | H | p | epsilon^2 | "
           + " | ".join(f"Median {r} (n)" for r in REGIMES) + " |",
           "| --- | --- | --- | --- | --- | " + " | ".join("---" for _ in REGIMES) + " |"]
    for _, r in kw.iterrows():
        md.append(f"| {r.frame} | {r.window} | {r.H:.1f} | {fmt_p(r.p)} | {r.eps2:.3f} | "
                  + " | ".join(f"{r[f'median_{g}']:+.3f} ({r[f'n_{g}']})" for g in REGIMES)
                  + " |")
 
    md += ["", "## 3. Cascade-led status x modal gentrification (strict plurality)", ""]
    if YEE.exists():
        chk, ref_modal, changed = strict_modal_gen()
        gen = chk["gen_strict"]
        ct = crosstabs(d, gen)
        ct.to_csv(OUT / f"manuscript_aggregate_crosstab_{STAMP}.csv", index=False)
        md += [f"Modal-gentrification zones: {int(gen.sum())} under strict plurality "
               f"({int(ref_modal.sum())} in the earlier EDA 12 output). "
               f"GEN tied for the top count in {int(chk['gen_tied'].sum())} zones.", "",
               "| Frame | Window | Cascade-led & GEN | Cascade-led only | GEN only | Neither "
               "| chi2 | p | Cramer's V | ARI |",
               "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for _, r in ct.iterrows():
            md.append(f"| {r.frame} | {r.window} | {r.cascade_gen} | {r.cascade_not_gen} | "
                      f"{r.other_gen} | {r.other_not_gen} | {r.chi2:.2f} | {fmt_p(r.p)} | "
                      f"{r.cramers_v:.3f} | {r.ari:.3f} |")
        md += ["", "Zones whose modal-gentrification status differs from EDA 12: "
               + (", ".join(changed) if changed else "none") + ".",
               "Chi-square without continuity correction; Cramer's V = sqrt(chi2 / n)."]
 
        write_table3(corr, kw, ct, len(d), int(gen.sum()))
        md += ["", f"{TABLE_NAME} written to `{TABLE_PNG.relative_to(ROOT)}` "
               f"(rows in `{TABLE_CSV.relative_to(ROOT)}`)."]
    else:
        md.append(f"Skipped: {YEE.relative_to(ROOT)} not found (gitignored). "
                  "Place the file and rerun.")
 
    text = "\n".join(md) + "\n"
    (OUT / f"manuscript_aggregate_correspondence_{STAMP}.md").write_text(text)
    print(text)
 
 
if __name__ == "__main__":
    main()
 