"""
Sensitivity of the mechanism-profile findings to the cascade-inflow-share
threshold (INFLOW_MIN = 0.25).

The 0.25 cut lies in an interval that is empty among frame-robust Frame C
"Cascade-led" zones in both windows, but it is applied to all Frame C
"Cascade-led" zones, some of which (all frame-sensitive) fall inside that
interval. This script rebuilds the mechanism tree with the cut at the lower
edge, at 0.25 and at the upper edge of the interval, and reports the profile
counts and the subtype comparisons reported in Section 4.3 (Table 6).

Inputs (run after eda_6 and eda_14):
  outputs/eda9_mechanism_tree_20260705.csv          tree inputs and leaves (eda_6)
  outputs/eda12_yee_leaf_corroboration_20260705.csv subtype presence flags (eda_14)

Outputs:
  outputs/diagnostics_inflow_threshold_sensitivity.csv
  outputs/diagnostics_inflow_threshold_sensitivity.md

Run from the repository root:
  python scripts/diag_inflow_threshold.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
EDA9 = OUT / "eda9_mechanism_tree_20260705.csv"
EDA12 = OUT / "eda12_yee_leaf_corroboration_20260705.csv"
OUT_CSV = OUT / "diagnostics_inflow_threshold_sensitivity.csv"
OUT_MD = OUT / "diagnostics_inflow_threshold_sensitivity.md"

INFLOW_MIN, EXT_MAJ = 0.25, 0.50          # as in eda_6
YEARS = ("11", "21")
LEAVES = ["inflow-driven", "frame-sensitive inflow",
          "outflow: internal-majority", "outflow: external-majority"]
FLAGS = {"any_SupGen": "super", "any_MainGen": "mainstream",
         "any_MargGen": "marginal", "has_gen": "any"}


def leaf(row, yr, cut):
    """Same rule as mechanism() in eda_6, with the inflow cut as a parameter."""
    if row[f"Typ_C_{yr}"] != "Cascade-led":
        return None
    if row[f"Casc_Inflow_Share_{yr}"] >= cut:
        return "inflow-driven" if row[f"Typ_A_{yr}"] == "Cascade-led" else "frame-sensitive inflow"
    if row[f"Ext_Arm_Share_{yr}"] >= EXT_MAJ:
        return "outflow: external-majority"
    return "outflow: internal-majority"


def as_bool(s):
    return s if s.dtype == bool else s.astype(str).str.lower().eq("true")


def main():
    tree = pd.read_csv(EDA9)
    flags = pd.read_csv(EDA12)[["msoa11cd", *FLAGS]]
    for c in FLAGS:
        flags[c] = as_bool(flags[c])
    d = tree.merge(flags, on="msoa11cd", how="left", validate="1:1")
    assert len(d) == 982 and d[list(FLAGS)].notna().all().all()

    # Guard: at the adopted cut the rebuilt tree must equal the eda_6 export.
    for yr in YEARS:
        rebuilt = d.apply(leaf, axis=1, yr=yr, cut=INFLOW_MIN).fillna("none")
        assert (rebuilt.values == d[f"leaf_{yr}"].fillna("none").values).all(), \
            f"rebuilt leaf_{yr} differs from eda9 export"

    # Interval empty among frame-robust Cascade-led zones in BOTH windows.
    lo_edges, hi_edges = [], []
    for yr in YEARS:
        robust = d[(d[f"Typ_C_{yr}"] == "Cascade-led") & (d[f"Typ_A_{yr}"] == "Cascade-led")]
        s = robust[f"Casc_Inflow_Share_{yr}"]
        lo_edges.append(s[s < INFLOW_MIN].max())
        hi_edges.append(s[s >= INFLOW_MIN].min())
    band_lo, band_hi = max(lo_edges), min(hi_edges)
    assert band_lo < INFLOW_MIN < band_hi, "0.25 no longer lies inside the frame-robust gap"

    lines = [f"Interval empty among frame-robust Frame C Cascade-led zones: "
             f"({band_lo:.3f}, {band_hi:.3f})", ""]
    for yr in YEARS:
        casc = d[d[f"Typ_C_{yr}"] == "Cascade-led"]
        s = casc[f"Casc_Inflow_Share_{yr}"]
        inside = casc[(s > band_lo) & (s < band_hi)]
        lines.append(f"20{yr}: {len(inside)} of {len(casc)} Frame C Cascade-led zones inside the "
                     f"interval ({(inside[f'Typ_A_{yr}'] == 'Cascade-led').sum()} frame-robust)")

    london = {name: d[c].mean() for c, name in FLAGS.items()}
    rows = []
    for label, cut in (("lower edge", band_lo + 1e-9), ("adopted", INFLOW_MIN), ("upper edge", band_hi)):
        for yr in YEARS:
            lf = d.apply(leaf, axis=1, yr=yr, cut=cut)
            for prof in LEAVES:
                sub = d[lf == prof]
                row = {"cut": round(cut, 3), "cut_label": label, "year": f"20{yr}",
                       "profile": prof, "zones": len(sub)}
                for c, name in FLAGS.items():
                    share = sub[c].mean() if len(sub) else float("nan")
                    row[f"{name}_share"] = round(share * 100, 1)
                    row[f"{name}_pp_vs_london"] = round((share - london[name]) * 100, 1)
                rows.append(row)
    res = pd.DataFrame(rows)
    res.to_csv(OUT_CSV, index=False)

    lines += ["", "London-wide shares: " + ", ".join(f"{k} {v:.1%}" for k, v in london.items()), ""]
    for yr in YEARS:
        piv = res[res.year == f"20{yr}"].pivot_table(
            index="profile", columns="cut_label",
            values=["zones", "super_share", "mainstream_share", "any_share"], aggfunc="first")
        piv = piv.reindex(LEAVES)[[(v, c) for v in ("zones", "super_share", "mainstream_share", "any_share")
                                   for c in ("lower edge", "adopted", "upper edge")]]
        lines += [f"20{yr} (zones; % containing super / mainstream / any gentrification):",
                  piv.to_string(), ""]
    text = "\n".join(lines)
    OUT_MD.write_text("```\n" + text + "\n```\n")
    print(text)
    print(f"Written {OUT_CSV.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
