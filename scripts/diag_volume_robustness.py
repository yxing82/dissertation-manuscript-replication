"""Volume robustness of the correspondence results (manuscript Sections 3, 4.1, 4.3).

Question: is the weak aggregate correspondence between "Cascade-led" status and
neighbourhood change (Section 4.1), and the selective mechanism-level
correspondence (Section 4.3, Table 5), an artefact of the flow measures being
proportions? A ratio label treats a zone whose cascade-direction moves exceed
counter-direction moves by 20 the same as one where they exceed them by 400.
If neighbourhood change only follows large imbalances, weak cases would dilute
the correspondence.

Net cascade surplus = (IW + OP) - (OW + IP) for a frame. It equals
(2 * Cascade_Dominance - 1) * Cross_Decile_Share * Total_Migration, which lets
it be computed for Frames A, B and C from the EDA 4 regime file.

Sections of the output
  1. Surplus distribution by mechanism profile (Frame C).
  2. Gradient within Cascade-led zones: surplus terciles (Frame C).
  3. Table 4 (Cascade-led x modal gentrification) with low-surplus Cascade-led
     zones dropped, fixed 100 and period-median rules (Frame C).
  4. Table 5 (profile x subtype presence) with low-surplus profile members
     dropped (Frame C).
  5. Threshold sweep, 0-200 moves in steps of 25:
       5a. Cascade-led x modal gentrification, Frames A, B and C.
       5b. Super-gentrification in the outflow-internal-majority profile,
           and every profile x subtype cell, Frame C.
  6. Population shares (needs data/ population files; skipped if absent):
       retained and hierarchy-crossing moves as % of usual residents, net
       surplus as % of residents in Cascade-led zones, and whether
       correspondence depends on that share.

Statistics follow manuscript v14 Section 3.4. Comparisons with IMD change and
the modal label use the Section 4.1 statistics (Spearman's rho; chi-square,
Cramér's V). Comparisons with subtype-presence indicators are descriptive, as
in Table 5: share of zones containing the category against the fixed
London-wide share across all 982 zones, in percentage points. No Fisher, BH or
Mann-Whitney tests (removed 2026-10-25).

Modal label: strict plurality (manuscript Section 3.4), taken from
07_table3_aggregate_correspondence.strict_modal_gen(); 35 zones. The earlier
version of this script (20261020 outputs) used the EDA 12 label (41 zones).
Subtype-presence flags come from EDA 12; they involve no tie rule and are
asserted identical to a fresh derivation in strict_modal_gen().

Inputs
  outputs/msoa_cascade_national_frame_20260625.csv   Frame C flows
  outputs/eda4_results_for_phase3_20260626.csv       Frames A-C regimes and measures
  outputs/eda12_yee_leaf_corroboration_20260705.csv  profiles, subtype presence
  data/yee_LSOA_labels_forMapping.csv                Yee & Dennett LSOA labels (gitignored)
  data/ks101ew_lsoa_2011.csv                         2011 usual residents, LSOA (gitignored)
  data/ts001_msoa_2021.csv                           2021 usual residents, MSOA (gitignored;
                                                     built from data/nomis_2021_ts001.xlsx if absent)
  outputs/lsoa11_to_msoa11.csv, outputs/geo_harmonisation_remap_audit.csv  lookups

Run from the repository root:
    python scripts/diag_volume_robustness.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from manuscript_aggregate_correspondence import strict_modal_gen  # noqa: E402

OUT = ROOT / "outputs"
DATA = ROOT / "data"
FLOWS = OUT / "msoa_cascade_national_frame_20260625.csv"
EDA4 = OUT / "eda4_results_for_phase3_20260626.csv"
YEE = OUT / "eda12_yee_leaf_corroboration_20260705.csv"
LSOA_LOOKUP = OUT / "lsoa11_to_msoa11.csv"
MSOA_REMAP = OUT / "geo_harmonisation_remap_audit.csv"
POP11 = DATA / "ks101ew_lsoa_2011.csv"
POP21 = DATA / "ts001_msoa_2021.csv"
POP21_XLSX = DATA / "nomis_2021_ts001.xlsx"   # Nomis formatted download
STAMP = "20261025"
OUT_CSV = OUT / f"manuscript_volume_robustness_{STAMP}.csv"
OUT_MD = OUT / f"manuscript_volume_robustness_{STAMP}.md"

YEARS = ["2011", "2021"]
FRAMES = ["A", "B", "C"]
SWEEP = list(range(0, 201, 25))
PROFILES = [
    ("inflow-driven", "Inflow-driven, frame-robust"),
    ("frame-sensitive", "Frame-sensitive inflow"),
    ("outflow-internal", "Outflow-internal-majority"),
    ("outflow-external", "Outflow-external-majority"),
]
SUBTYPES = [
    ("any_SupGen", "Super"),
    ("any_MainGen", "Mainstream"),
    ("any_MargGen", "Marginal"),
    ("has_gen", "Any gentrification"),
]


def partial_spearman(x, y, z):
    """Spearman partial correlation of x and y controlling for z."""
    r = pd.DataFrame({"x": x, "y": y, "z": z}).rank().corr().values
    rxy, rxz, ryz = r[0, 1], r[0, 2], r[1, 2]
    return (rxy - rxz * ryz) / np.sqrt((1 - rxz**2) * (1 - ryz**2))


def fmt_p(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def load():
    f = pd.read_csv(FLOWS)
    e = pd.read_csv(EDA4)
    y = pd.read_csv(YEE)
    for c, _ in SUBTYPES:
        y[c] = y[c].astype(str).str.lower() == "true"
    chk, _, _ = strict_modal_gen()
    y["gen_modal"] = chk["gen_strict"].reindex(y["msoa11cd"]).values.astype(bool)
    assert y["gen_modal"].sum() == 35

    keep_e = ["msoa11cd"] + [f"{m}_{fr}_{yr}" for m in ("Dom", "CDS", "Typ")
                             for fr in FRAMES for yr in ("11", "21")]
    keep_y = ["msoa11cd", "leaf_11", "leaf_21", "gen_modal"] + [c for c, _ in SUBTYPES]
    d = f.merge(e[keep_e], on="msoa11cd").merge(y[keep_y], on="msoa11cd")
    assert len(d) == 982
    d = d.copy()
    for yr in YEARS:
        y2 = yr[2:]
        total = {"A": d[f"Total_Migration_{y2}"], "B": d[f"Total_Migration_{y2}"],
                 "C": d[f"Total_Migration_nat_{y2}"]}
        for fr in FRAMES:
            xdec = d[f"CDS_{fr}_{y2}"] * total[fr]
            # Flows are integer counts; round away floating-point error so that a
            # surplus of exactly 100 is not read as 99.999... at the threshold.
            d[f"surplus_{fr}_{yr}"] = ((2 * d[f"Dom_{fr}_{y2}"] - 1) * xdec).round()
            d[f"xdec_{fr}_{yr}"] = xdec.round()
            d[f"cl_{fr}_{yr}"] = d[f"Typ_{fr}_{y2}"] == "Cascade-led"
        d[f"total_C_{yr}"] = total["C"]
        d[f"total_A_{yr}"] = total["A"]
        # Identity check against the raw Frame C flows.
        s = f"nat_{y2}"
        raw = (d[f"Inflow_Wealthier_{s}"] + d[f"Outflow_Poorer_{s}"]
               - d[f"Outflow_Wealthier_{s}"] - d[f"Inflow_Poorer_{s}"])
        assert np.allclose(raw, d[f"surplus_C_{yr}"])
        d[f"leaf_{yr}"] = d[f"leaf_{y2}"]
        # Frame C shorthands used by sections 1-4 and 6.
        d[f"surplus_{yr}"] = d[f"surplus_C_{yr}"]
        d[f"cl_{yr}"] = d[f"cl_C_{yr}"]
    return d


def table4(d, cl_col, mask):
    """Cascade-led x modal gentrification, restricted to rows in mask."""
    s = d[mask]
    a = int((s[cl_col] & s.gen_modal).sum())
    b = int((s[cl_col] & ~s.gen_modal).sum())
    c = int((~s[cl_col] & s.gen_modal).sum())
    e = int((~s[cl_col] & ~s.gen_modal).sum())
    chi2, p, _, _ = chi2_contingency([[a, b], [c, e]], correction=False)
    v = np.sqrt(chi2 / (a + b + c + e))
    return dict(cl_gen=a, cl_not=b, other_gen=c, other_not=e,
                pct_gen_cl=100 * a / (a + b), pct_gen_other=100 * c / (c + e),
                chi2=chi2, p=p, cramers_v=v)


def profile_cells(d, thr_for_year):
    """Profile x subtype presence: share of kept profile zones vs the fixed
    London-wide share (all 982 zones), in percentage points. Descriptive."""
    cells = []
    for col, lab in SUBTYPES:
        pct_london = 100 * d[col].mean()
        for yr in YEARS:
            thr = thr_for_year(yr)
            for key, name in PROFILES:
                in_p = d[f"leaf_{yr}"] == key
                keep = in_p if thr is None else in_p & (d[f"surplus_{yr}"] >= thr)
                n = int(keep.sum())
                k = int((keep & d[col]).sum())
                pct = 100 * k / n if n else np.nan
                cells.append(dict(year=yr, group=name, subtype=lab, n=n, n_label=k,
                                  pct_group=pct, pct_london=pct_london,
                                  pp_diff=pct - pct_london if n else np.nan))
    return cells


def fmt_cell(r, with_n=False):
    if r.n == 0:
        return "–"
    pp = round(r.pp_diff, 1)
    pp_txt = "0.0" if pp == 0 else f"{pp:+.1f}".replace("-", "−")
    lead = f"{r.n_label}/{r.n}" if with_n else f"{r.n_label}"
    return f"{lead} ({r.pct_group:.1f}%, {pp_txt})"


def load_population():
    """Usual residents per 2011 analytical zone for 2011 and 2021, or None."""
    pops = {}
    if POP11.exists():
        ks = pd.read_csv(POP11)
        code = next(c for c in ks.columns
                    if ks[c].astype(str).str.match(r"^[EW]01\d{6}$").mean() > 0.9)
        val = next(c for c in ks.columns if "all usual residents" in c.lower())
        ks = ks[[code, val]].rename(columns={code: "lsoa11cd", val: "pop"})
        ks["pop"] = pd.to_numeric(ks["pop"], errors="coerce")
        lk = pd.read_csv(LSOA_LOOKUP)[["lsoa11cd", "msoa11cd"]].drop_duplicates()
        pops["2011"] = ks.merge(lk, on="lsoa11cd").groupby("msoa11cd")["pop"].sum()
    if not POP21.exists() and POP21_XLSX.exists():
        # Nomis formatted sheet: "E02002483 : Hartlepool 001" | count | %.
        x = pd.read_excel(POP21_XLSX, header=None)
        code = x[0].astype(str).str.extract(r"^([EW]02\d{6})\s*:")[0]
        ts = pd.DataFrame({"msoa21cd": code, "observation": x[1]}).dropna()
        ts.to_csv(POP21, index=False)
    if POP21.exists():
        ts = pd.read_csv(POP21)
        code = next(c for c in ts.columns
                    if ts[c].astype(str).str.match(r"^[EW]02\d{6}$").mean() > 0.9)
        val = next((c for c in ts.columns if "total" in c.lower()
                    or "usual residents" in c.lower()
                    or c.lower() in ("observation", "obs_value")), None)
        assert val is not None, f"population column not found in {POP21.name}"
        ts = ts[[code, val]].rename(columns={code: "msoa21cd", val: "pop"})
        ts["pop"] = pd.to_numeric(ts["pop"], errors="coerce")
        rm = pd.read_csv(MSOA_REMAP)[["msoa21cd", "canonical_msoa11"]]
        m = ts.merge(rm, on="msoa21cd")
        pops["2021"] = m.groupby("canonical_msoa11")["pop"].sum()
    return pops


def pct_range(s, lo=5, hi=95):
    return f"{np.percentile(s, lo):.1f}-{np.percentile(s, hi):.1f}%"


def main():
    d = load()
    rows, md = [], []
    md += ["Modal gentrification label: strict plurality, "
           f"{int(d.gen_modal.sum())} zones. Frame C unless stated.", ""]

    # 1. Surplus by profile
    md += ["## 1. Net cascade surplus by mechanism profile (Frame C)", "",
           "| Profile | Year | Zones | Median surplus | IQR | Min |",
           "| --- | --- | --- | --- | --- | --- |"]
    for key, name in PROFILES:
        for yr in YEARS:
            s = d.loc[d[f"leaf_{yr}"] == key, f"surplus_{yr}"]
            md.append(f"| {name} | {yr} | {len(s)} | {s.median():.0f} | "
                      f"{s.quantile(.25):.0f}-{s.quantile(.75):.0f} | {s.min():.0f} |")
            rows.append(dict(check="1_profile_surplus", year=yr, group=name,
                             n=len(s), median=s.median(), q25=s.quantile(.25),
                             q75=s.quantile(.75), min=s.min()))
    for yr in YEARS:
        s = d.loc[d[f"cl_{yr}"], f"surplus_{yr}"]
        md.append(f"| All Cascade-led | {yr} | {len(s)} | {s.median():.0f} | "
                  f"{s.quantile(.25):.0f}-{s.quantile(.75):.0f} | {s.min():.0f} |")
        rows.append(dict(check="1_profile_surplus", year=yr, group="All Cascade-led",
                         n=len(s), median=s.median(), q25=s.quantile(.25),
                         q75=s.quantile(.75), min=s.min()))

    # 2. Gradient within Cascade-led
    md += ["", "## 2. Gradient within Cascade-led zones (surplus terciles, Frame C)", "",
           "| Year | Tercile | Zones | Surplus range | Modal gentrification | "
           "Any gentrification | Median IMD pctile change |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    notes = []
    for yr in YEARS:
        cl = d[d[f"cl_{yr}"]].copy()
        cl["terc"] = pd.qcut(cl[f"surplus_{yr}"], 3, labels=["Low", "Mid", "High"])
        for tl, g in cl.groupby("terc", observed=True):
            sv = g[f"surplus_{yr}"]
            md.append(f"| {yr} | {tl} | {len(g)} | {sv.min():.0f}-{sv.max():.0f} | "
                      f"{g.gen_modal.sum()} ({100*g.gen_modal.mean():.1f}%) | "
                      f"{g.has_gen.sum()} ({100*g.has_gen.mean():.1f}%) | "
                      f"{g.IMD_Pctile_Change.median():+.3f} |")
            rows.append(dict(check="2_tercile", year=yr, group=str(tl), n=len(g),
                             pct_gen_modal=100 * g.gen_modal.mean(),
                             pct_has_gen=100 * g.has_gen.mean(),
                             median_imd_change=g.IMD_Pctile_Change.median()))
        rho, prho = spearmanr(cl[f"surplus_{yr}"], cl.IMD_Pctile_Change)
        prt = partial_spearman(cl[f"surplus_{yr}"], cl.IMD_Pctile_Change, cl.IMD_2010)
        notes.append(f"- {yr}: Spearman surplus vs IMD change rho = {rho:.3f} "
                     f"(p = {prho:.3f}); partial on IMD 2010 = {prt:.3f}.")
        rows.append(dict(check="2_gradient_tests", year=yr, group="Cascade-led",
                         n=len(cl), spearman_rho=rho, spearman_p=prho, partial_rho=prt))
    md += [""] + notes

    # 3. Table 4 under thresholds
    md += ["", "## 3. Cascade-led x modal gentrification, low-surplus Cascade-led "
           "zones dropped (Frame C)", "",
           "| Year | Rule | Cascade-led kept | CL & gen | Other & gen | "
           "% gen CL | % gen other | Cramér's V | χ² p |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for yr in YEARS:
        med = d.loc[d[f"cl_{yr}"], f"surplus_{yr}"].median()
        for rname, thr in [("All (baseline)", None), ("Surplus ≥ 100", 100),
                           (f"Surplus ≥ median ({med:.0f})", med)]:
            mask = pd.Series(True, index=d.index) if thr is None else \
                (~d[f"cl_{yr}"]) | (d[f"surplus_{yr}"] >= thr)
            r = table4(d, f"cl_{yr}", mask)
            md.append(f"| {yr} | {rname} | {r['cl_gen'] + r['cl_not']} | {r['cl_gen']} | "
                      f"{r['other_gen']} | {r['pct_gen_cl']:.1f}% | "
                      f"{r['pct_gen_other']:.1f}% | {r['cramers_v']:.3f} | "
                      f"{fmt_p(r['p'])} |")
            rows.append(dict(check="3_table4", frame="C", year=yr, group=rname,
                             threshold=thr, **r))

    # 4. Table 5 under thresholds
    md += ["", "## 4. Profile x subtype presence, profile members above threshold "
           "only (Frame C)", "",
           "Cells: zones containing the category (share of the kept profile zones, "
           "percentage-point difference from the fixed London-wide share across all "
           "982 zones). Descriptive, as in Table 5.", ""]
    medians = {yr: d.loc[d[f"cl_{yr}"], f"surplus_{yr}"].median() for yr in YEARS}
    for rule, fn in [("All (baseline)", lambda yr: None),
                     ("Surplus ≥ 100", lambda yr: 100),
                     ("Surplus ≥ period median", lambda yr: medians[yr])]:
        cells = profile_cells(d, fn)
        for x in cells:
            rows.append(dict(check="4_table5", rule=rule, **x))
        cdf = pd.DataFrame(cells)
        md += [f"**{rule}**", "",
               "| Profile | Year | Zones | " + " | ".join(l for _, l in SUBTYPES) + " |",
               "| --- | --- | --- | " + " | ".join("---" for _ in SUBTYPES) + " |"]
        for key, name in PROFILES:
            for yr in YEARS:
                s = cdf[(cdf.group == name) & (cdf.year == yr)].set_index("subtype")
                n = int(s.n.iloc[0])
                md.append(f"| {name} | {yr} | {n} | "
                          + " | ".join(fmt_cell(s.loc[l]) for _, l in SUBTYPES) + " |")
        lw = cdf.drop_duplicates("subtype").set_index("subtype").pct_london
        md += ["| London-wide | – | 982 | "
               + " | ".join(f"{lw[l]:.1f}%" for _, l in SUBTYPES) + " |", ""]

    # 5. Threshold sweep
    md += ["## 5. Threshold sweep (0-200 moves)", "",
           "### 5a. Cascade-led x modal gentrification, all frames", "",
           "Cascade-led zones with surplus below the threshold are dropped; all "
           "other zones are kept.", "",
           "| Frame | Year | Threshold | Cascade-led kept | CL & gen | % gen CL | "
           "% gen other | Cramér's V | χ² p |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for fr in FRAMES:
        for yr in YEARS:
            for thr in SWEEP:
                cl = f"cl_{fr}_{yr}"
                mask = (~d[cl]) | (d[f"surplus_{fr}_{yr}"] >= thr)
                r = table4(d, cl, mask)
                md.append(f"| {fr} | {yr} | {thr} | {r['cl_gen'] + r['cl_not']} | "
                          f"{r['cl_gen']} | {r['pct_gen_cl']:.1f}% | "
                          f"{r['pct_gen_other']:.1f}% | {r['cramers_v']:.3f} | "
                          f"{fmt_p(r['p'])} |")
                rows.append(dict(check="5a_sweep_table4", frame=fr, year=yr,
                                 threshold=thr, **r))
    md += ["", "### 5b. Profile x subtype presence across thresholds (Frame C)", "",
           "Cells: zones containing the category / profile zones kept (share, "
           "percentage-point difference from the fixed London-wide share).", "",
           "| Threshold | Year | " + " | ".join(n for _, n in PROFILES) + " |",
           "| --- | --- | " + " | ".join("---" for _ in PROFILES) + " |"]
    sweep_cells = {}
    for thr in SWEEP:
        cells = profile_cells(d, lambda yr, t=thr: t)
        sweep_cells[thr] = pd.DataFrame(cells)
        for x in cells:
            rows.append(dict(check="5b_sweep_table5", threshold=thr, **x))
    for lab in [l for _, l in SUBTYPES]:
        md += [f"| **{lab}** | | " + " | ".join("" for _ in PROFILES) + " |"]
        for thr in SWEEP:
            c = sweep_cells[thr]
            for yr in YEARS:
                cells = []
                for _, name in PROFILES:
                    r = c[(c.group == name) & (c.year == yr) & (c.subtype == lab)].iloc[0]
                    cells.append(fmt_cell(r, with_n=True))
                md.append(f"| {thr} | {yr} | " + " | ".join(cells) + " |")

    # 6. Population shares
    md += ["", "## 6. Flows relative to usual residents", ""]
    pops = load_population()
    if not pops:
        md.append(f"Skipped: neither {POP11.relative_to(ROOT)} nor "
                  f"{POP21.relative_to(ROOT)} found (data/ is gitignored).")
    else:
        md += ["| Year | Population source | Retained moves, Frame C (P5-P95; min) | "
               "Retained moves, Frame A (P5-P95) | Hierarchy-crossing moves, Frame C "
               "(P5-P95) | Cascade-led net surplus (median; P5-P95; max) |",
               "| --- | --- | --- | --- | --- | --- |"]
        for yr in YEARS:
            src = yr if yr in pops else "2011"
            if src not in pops:
                md.append(f"| {yr} | missing | | | | |")
                continue
            pop = pops[src].reindex(d.msoa11cd).values
            assert np.isfinite(pop).all() and (pop > 0).all(), f"population gaps ({src})"
            d[f"pop_{yr}"] = pop
            ret_c = 100 * d[f"total_C_{yr}"] / pop
            ret_a = 100 * d[f"total_A_{yr}"] / pop
            xdc = 100 * d[f"xdec_C_{yr}"] / pop
            d[f"share_{yr}"] = 100 * d[f"surplus_{yr}"] / pop
            cs = d.loc[d[f"cl_{yr}"], f"share_{yr}"]
            md.append(f"| {yr} | {src} census | {pct_range(ret_c)}; {ret_c.min():.1f}% | "
                      f"{pct_range(ret_a)} | {pct_range(xdc)} | {cs.median():.2f}%; "
                      f"{np.percentile(cs, 5):.2f}-{np.percentile(cs, 95):.2f}%; "
                      f"{cs.max():.1f}% |")
            rows.append(dict(check="6_population_shares", year=yr, group=src,
                             pop_total=float(np.nansum(pop)),
                             retained_C_p5=np.percentile(ret_c, 5),
                             retained_C_p95=np.percentile(ret_c, 95),
                             retained_C_min=ret_c.min(),
                             retained_A_p5=np.percentile(ret_a, 5),
                             retained_A_p95=np.percentile(ret_a, 95),
                             xdec_C_p5=np.percentile(xdc, 5),
                             xdec_C_p95=np.percentile(xdc, 95),
                             cl_share_median=cs.median(),
                             cl_share_p5=np.percentile(cs, 5),
                             cl_share_p95=np.percentile(cs, 95),
                             cl_share_max=cs.max()))
        md += ["", "Does correspondence depend on the net surplus share? "
               "(Cascade-led zones, Frame C)", "",
               "| Year | Label | Share with label (median) | Share without (median) | "
               "Low / Mid / High tercile prevalence | London-wide | "
               "Spearman share vs IMD change (p) |",
               "| --- | --- | --- | --- | --- | --- | --- |"]
        for yr in YEARS:
            if f"share_{yr}" not in d:
                continue
            cl = d[d[f"cl_{yr}"]].copy()
            cl["terc"] = pd.qcut(cl[f"share_{yr}"], 3, labels=["Low", "Mid", "High"])
            rho, prho = spearmanr(cl[f"share_{yr}"], cl.IMD_Pctile_Change)
            for col, lab in [("gen_modal", "Modal gentrification"),
                             ("has_gen", "Any gentrification")]:
                w, wo = cl.loc[cl[col], f"share_{yr}"], cl.loc[~cl[col], f"share_{yr}"]
                terc = " / ".join(f"{100*g[col].mean():.0f}%"
                                  for _, g in cl.groupby("terc", observed=True))
                md.append(f"| {yr} | {lab} | {w.median():.2f}% (n={len(w)}) | "
                          f"{wo.median():.2f}% (n={len(wo)}) | {terc} | "
                          f"{100 * d[col].mean():.1f}% | "
                          f"{rho:.3f} ({fmt_p(prho)}) |")
                rows.append(dict(check="6_share_vs_label", year=yr, group=lab,
                                 n=len(w), median_with=w.median(),
                                 median_without=wo.median(),
                                 spearman_rho=rho, spearman_p=prho))
        if "2021" not in pops:
            md += ["", "2021 shares use 2011 population (2021 file not found)."]

    pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
    OUT_MD.write_text("# Volume robustness check\n\nGenerated by "
                      "`scripts/diag_volume_robustness.py`.\n\n"
                      + "\n".join(md) + "\n")
    print("\n".join(md))
    print(f"\nWrote {OUT_CSV.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
