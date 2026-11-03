
"""Manuscript Table 6 (Table 5 before v19): gentrification-subtype presence by
flow mechanism profile.
 
Rebuilds the profile x subtype x year grid for Frame C "Cascade-led" MSOAs from
outputs/eda12_yee_leaf_corroboration_20260705.csv, following manuscript
Section 3.4: for each profile and window, the share of zones containing each
category (any gentrification, super, mainstream, marginal) is compared with
the fixed London-wide share across all 982 zones, and the difference is
reported in percentage points. The comparison is descriptive; no significance
tests are computed (Fisher/BH output was removed on 2026-10-25).
 
Counts, shares and percentage-point differences are checked against
outputs/eda13_proportions_main_20260723.csv.
 
Table 6 (added 2026-11-02) is drawn from the same numbers, nothing
hard-coded. It adds an All "Cascade-led" row (the four profiles together; they
partition the regime, so profile zones sum to it) between the profiles and the
London-wide benchmark. Each Table 6 cell shows the count and the percentage of
the row's zones only (SHOW_PP below). The PNG carries no caption: the caption
lives in the LaTeX source. The CSV/MD outputs below keep their 20261017 names and content,
because scripts/eda_12_v8_comparison_map_marker_marginal_added_20261102.py
reads the CSV.
 
Outputs
  outputs/manuscript_table5_mechanism_subtype_20261017.csv   long-format cells
  outputs/manuscript_table5_mechanism_subtype_20261017.md    Markdown table
  outputs/manuscript_table6_subtype_presence_<STAMP6>.csv    rows as in Table 6
  outputs/Table_6.png                                        Table 6, no caption
 
Run from the repository root:
    python scripts/manuscript_table5_mechanism_subtype.py
"""
 
from pathlib import Path
 
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
 
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "outputs" / "eda12_yee_leaf_corroboration_20260705.csv"
REF = ROOT / "outputs" / "eda13_proportions_main_20260723.csv"
OUT_CSV = ROOT / "outputs" / "manuscript_table5_mechanism_subtype_20261017.csv"
OUT_MD = ROOT / "outputs" / "manuscript_table5_mechanism_subtype_20261017.md"
STAMP6 = "20261102"
OUT6_CSV = ROOT / "outputs" / f"manuscript_table6_subtype_presence_{STAMP6}.csv"
OUT6_PNG = ROOT / "outputs" / "Table_6_manuscript.png"   # no space, so LaTeX can include it
SHOW_PP = False  # Table 6 cells show count (percentage) only; True adds the pp difference
 
PROFILES = [
    ("inflow-driven", "Inflow-driven, frame-robust"),
    ("frame-sensitive", "Frame-sensitive inflow"),
    ("outflow-internal", "Outflow-internal-majority"),
    ("outflow-external", "Outflow-external-majority"),
]
YEARS = [("2011", "leaf_11"), ("2021", "leaf_21")]
SUBTYPES = [
    ("any_SupGen", "Super"),
    ("any_MainGen", "Mainstream"),
    ("any_MargGen", "Marginal"),
    ("has_gen", "Any gentrification"),
]
 
 
# --------------------------------------------------------------------------
# Table 6: rows (profiles, All "Cascade-led", London-wide) and the PNG
# --------------------------------------------------------------------------
MINUS = "−"   # typographic minus
TABLE6_LABELS = {
    "inflow-driven": "Inflow-driven,\nframe-robust",
    "frame-sensitive": "Frame-sensitive\ninflow",
    "outflow-internal": "Outflow-internal-\nmajority",
    "outflow-external": "Outflow-external-\nmajority",
    "all": "All “Cascade-led”",
}
TABLE6_HEADERS = ["Flow mechanism profile", "Year", "Zones", "Super", "Mainstream",
                  "Marginal", "Any subtype"]
 
 
def table6_data(d, res):
    """One row per profile-window, then All "Cascade-led" per window, then London."""
    rows = []
    for key, name in PROFILES:
        for year, _ in YEARS:
            sub = res[(res.profile_key == key) & (res.year == year)].set_index("flag_col")
            row = dict(profile_key=key, profile=name, year=year, n=int(sub["n"].iloc[0]))
            for col, _ in SUBTYPES:
                row[f"{col}_n"] = int(sub.loc[col, "n_label"])
            rows.append(row)
 
    # All "Cascade-led": every zone with a Frame C profile in that window,
    # computed from the zones, then checked against the profile sums.
    keys = [k for k, _ in PROFILES]
    for year, leaf_col in YEARS:
        in_regime = d[leaf_col].isin(keys)
        row = dict(profile_key="all", profile='All "Cascade-led"', year=year,
                   n=int(in_regime.sum()))
        for col, _ in SUBTYPES:
            row[f"{col}_n"] = int((in_regime & d[col]).sum())
        parts = [r for r in rows if r["year"] == year and r["profile_key"] in keys]
        assert row["n"] == sum(r["n"] for r in parts), "profiles do not sum to the regime"
        for col, _ in SUBTYPES:
            assert row[f"{col}_n"] == sum(r[f"{col}_n"] for r in parts)
        rows.append(row)
 
    london = dict(profile_key="london", profile="London-wide benchmark", year="",
                  n=len(d))
    for col, _ in SUBTYPES:
        london[f"{col}_n"] = int(d[col].sum())
    rows.append(london)
 
    t = pd.DataFrame(rows)
    for col, _ in SUBTYPES:
        pct_london = 100 * d[col].mean()
        t[f"{col}_pct"] = 100 * t[f"{col}_n"] / t["n"]
        t[f"{col}_pp"] = t[f"{col}_pct"] - pct_london
        t.loc[t.profile_key == "london", f"{col}_pp"] = np.nan
    return t
 
 
def _pp_text(pp):
    pp = round(pp, 1)
    return "0.0" if pp == 0 else f"{pp:+.1f}".replace("-", MINUS)
 
 
def table6_cells(t):
    out = []
    for r in t.itertuples():
        cells = []
        for col, _ in SUBTYPES:
            n, pct, pp = getattr(r, f"{col}_n"), getattr(r, f"{col}_pct"), getattr(r, f"{col}_pp")
            if SHOW_PP and not np.isnan(pp):
                cells.append(f"{n} ({pct:.1f}%, {_pp_text(pp)})")
            else:
                cells.append(f"{n} ({pct:.1f}%)")
        out.append(dict(key=r.profile_key, year=r.year, n=r.n, cells=cells))
    return out
 
 
def render_table6(t, path):
    plt.rcParams["font.family"] = "STIXGeneral"
    plt.rcParams["mathtext.fontset"] = "stix"
    FS = 11
 
    # Everything in inches: x across the page, y up from the bottom.
    W = 9.6
    X_LABEL = 0.08                                      # profile names, left-aligned
    X = [2.42, 3.02, 4.22, 5.70, 7.10, 8.62]            # centres: Year .. Any subtype
    ROW = 0.33                                          # height of one data row
    HEAD = 0.52
    rows = table6_cells(t)
    n_body = len(rows)
    H = 0.10 + HEAD + n_body * ROW + 0.16
 
    fig = plt.figure(figsize=(W, H), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
 
    def hline(y, lw=0.8, color="black"):
        ax.plot([0.02, W - 0.02], [y, y], color=color, lw=lw, solid_capstyle="butt")
 
    def txt(x, y, s, ha="center", **kw):
        ax.text(x, y, s, ha=ha, va="center", fontsize=FS, **kw)
 
    y_top = H - 0.10
    hline(y_top, lw=1.2)
    y_head = y_top - HEAD / 2
    txt(X_LABEL, y_head, TABLE6_HEADERS[0], ha="left", fontweight="bold")
    for x, s in zip(X, TABLE6_HEADERS[1:]):
        txt(x, y_head, s, fontweight="bold")
    y = y_top - HEAD
    hline(y, lw=0.8)
 
    # Body: rows come in pairs (2011, 2021) per profile, then the London row.
    i = 0
    while i < n_body:
        r = rows[i]
        if r["key"] == "london":
            hline(y, lw=0.8)
            yc = y - ROW / 2
            txt(X_LABEL, yc, "London-wide benchmark", ha="left", fontweight="bold")
            for x, v in zip(X, ["—", str(r["n"]), *r["cells"]]):
                txt(x, yc, v, fontweight="bold")
            y -= ROW
            i += 1
            continue
        pair = rows[i:i + 2]
        if r["key"] == "all":
            hline(y, lw=0.6)                         # subtotal: thin black rule
        elif i > 0:
            hline(y, lw=0.5, color="#bbbbbb")        # between profiles: light rule
        txt(X_LABEL, y - ROW, TABLE6_LABELS[r["key"]], ha="left", linespacing=1.15)
        for p in pair:
            yc = y - ROW / 2
            for x, v in zip(X, [p["year"], str(p["n"]), *p["cells"]]):
                txt(x, yc, v)
            y -= ROW
        i += 2
 
    hline(y, lw=1.2)
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.06, facecolor="white")
    plt.close(fig)
 
 
def write_table6(d, res):
    t = table6_data(d, res)
    t.to_csv(OUT6_CSV, index=False)
    render_table6(t, OUT6_PNG)
    print(f"Table 6 written to {OUT6_PNG.relative_to(ROOT)} "
          f"(rows in {OUT6_CSV.relative_to(ROOT)}).")
    return t
 
 
def main():
    d = pd.read_csv(SRC)
    for col, _ in SUBTYPES:
        d[col] = d[col].astype(str).str.lower() == "true"
    assert len(d) == 982
 
    rows = []
    for col, label in SUBTYPES:
        pct_london = 100 * d[col].mean()
        for year, leaf_col in YEARS:
            for key, name in PROFILES:
                in_g = d[leaf_col] == key
                n = int(in_g.sum())
                k = int((in_g & d[col]).sum())
                pct = 100 * k / n
                rows.append(dict(subtype=label, flag_col=col, year=year,
                                 profile_key=key, profile=name, n=n, n_label=k,
                                 pct_group=pct, pct_london=pct_london,
                                 pp_diff=pct - pct_london))
    res = pd.DataFrame(rows)
    res.to_csv(OUT_CSV, index=False)
 
    # Check against the existing eda13 output.
    ref = pd.read_csv(REF)
    ref["year"] = ref["year"].astype(str)
    merged = res.merge(ref, left_on=["flag_col", "year", "profile_key"],
                       right_on=["flag_col", "year", "group"],
                       suffixes=("", "_ref"))
    assert len(merged) == len(res), "Missing rows when matching eda13 output"
    assert (merged["n"] == merged["n_ref"]).all()
    assert (merged["n_label"] == merged["n_label_ref"]).all()
    assert np.allclose(merged["pct_group"].round(1), merged["pct_group_ref"])
    assert np.allclose(merged["pp_diff"].round(1), merged["pp_diff_ref"])
    print(f"All {len(res)} cells match {REF.name}.")
 
    # Manuscript-formatted table: count (share, pp difference from London-wide).
    def fmt(r):
        pp = round(r.pp_diff, 1)
        pp_txt = "0.0" if pp == 0 else f"{pp:+.1f}".replace("-", "−")
        return f"{r.n_label} ({r.pct_group:.1f}%, {pp_txt})"
 
    lines = ["| Mechanism profile | Window | Zones | "
             + " | ".join(lbl for _, lbl in SUBTYPES) + " |",
             "| --- | --- | --- | " + " | ".join("---" for _ in SUBTYPES) + " |"]
    for key, name in PROFILES:
        for year, _ in YEARS:
            sub = res[(res.profile_key == key) & (res.year == year)].set_index("flag_col")
            n = int(sub["n"].iloc[0])
            lines.append(f"| {name} | {year} | {n} | "
                         + " | ".join(fmt(sub.loc[c]) for c, _ in SUBTYPES) + " |")
    london = res.drop_duplicates("flag_col").set_index("flag_col")
    lines.append(f"| London-wide | – | {len(d)} | "
                 + " | ".join(f"{int(round(london.loc[c, 'pct_london'] * len(d) / 100))} "
                              f"({london.loc[c, 'pct_london']:.1f}%)" for c, _ in SUBTYPES) + " |")
    lines.append("")
    lines.append("Cells: zones containing the category (share of the profile's zones, "
                 "percentage-point difference from the London-wide share across all 982 zones). "
                 "Descriptive comparison; no significance tests.")
    OUT_MD.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
 
    write_table6(d, res)
 
 
if __name__ == "__main__":
    main()