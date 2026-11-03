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

Run from the repository root:
    python scripts/manuscript_aggregate_correspondence.py
"""

from pathlib import Path

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
    else:
        md.append(f"Skipped: {YEE.relative_to(ROOT)} not found (gitignored). "
                  "Place the file and rerun.")

    text = "\n".join(md) + "\n"
    (OUT / f"manuscript_aggregate_correspondence_{STAMP}.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
