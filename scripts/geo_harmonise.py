"""
geo_harmonise.py  —  Single source of truth for 2011<->2021 MSOA geography harmonisation.

Both preprocessing notebooks (London-only 0615 and national-frame 0622) import this so the
two panels are guaranteed to sit on the *same* 982-MSOA, 2011-based geography.

Policy
------
- Unchanged (U): 2021 code maps to the identical 2011 code.
- Split (S): each 2021 child maps up to its single 2011 parent (exact aggregation).
- Merge (M): the 2011 parents that fuse into one 2021 code are collapsed into a single
  "best-fit" combined zone, keyed by the LOWEST member 2011 code (kept as a real code so it
  still joins to the IMD table and the 2011 geojson). The combined zone carries the
  population-weighted IMD of its members (handled in each notebook by relabelling the
  LSOA->MSOA mapping before aggregation), and is treated as ONE unit in both census years.
"""
from dataclasses import dataclass
import pandas as pd


@dataclass
class Harmonisation:
    remap_2021: dict       # 2021 MSOA code -> canonical 2011 code (London-relevant codes only)
    collapse_2011: dict     # 2011 parent code -> canonical code (merge collapse; non-identity only)
    merge_groups: dict      # canonical code -> [member 2011 parent codes] (only true merges)
    frame: set              # the canonical 2011 codes that define the balanced panel (982)


def build_harmonisation(lookup_id, london_msoa11,
                        code11_col='MSOA11CD', code21_col='MSOA21CD', chng_col='CHNGIND'):
    """
    lookup_id     : the ONS change lookup (MSOA_2011_to_2021_lookup_for_identification.csv)
    london_msoa11 : iterable of London 2011 MSOA codes (983 original OR 982 post-fix; either works)
    """
    lk = lookup_id[[code11_col, code21_col, chng_col]].dropna().astype(str).copy()
    london = set(map(str, london_msoa11))

    # --- detect merges from the FULL lookup: a 2021 code fed by >1 distinct 2011 parent ---
    parents_per_child = lk.groupby(code21_col)[code11_col].nunique()
    merge_children = set(parents_per_child[parents_per_child > 1].index)

    parent_to_canon = {}          # 2011 parent -> canonical (only differs for merged parents)
    for ch in merge_children:
        members = sorted(lk.loc[lk[code21_col] == ch, code11_col].unique())
        canon = members[0]        # lowest code is the surviving combined-zone key
        for m in members:
            parent_to_canon[m] = canon

    def canon(p):
        return parent_to_canon.get(p, p)

    # --- which 2011 parents are London-relevant (member or canonical lands in London) ---
    def is_london(p):
        return (p in london) or (canon(p) in london) or any(
            m in london for m, c in parent_to_canon.items() if c == canon(p))

    remap_2021 = {}
    for _, r in lk.iterrows():
        p, ch = r[code11_col], r[code21_col]
        if is_london(p):
            remap_2021[ch] = canon(p)

    frame = {canon(p) for p in {row for row in lk[code11_col]} if is_london(p)}
    collapse_2011 = {p: canon(p) for p in parent_to_canon if is_london(p) and p != canon(p)}

    merge_groups = {}
    for p, c in parent_to_canon.items():
        if is_london(p):
            merge_groups.setdefault(c, []).append(p)
    merge_groups = {c: sorted(set(m)) for c, m in merge_groups.items()}

    return Harmonisation(remap_2021, collapse_2011, merge_groups, frame)


def export_remap_table(h, path):
    """Write an auditable long-form table of the harmonisation for the methodology appendix."""
    rows = [{'msoa21cd': k, 'canonical_msoa11': v,
             'relation': 'merge' if v in h.merge_groups else ('unchanged' if k == v else 'split')}
            for k, v in sorted(h.remap_2021.items())]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def build_full_remap(lookup_id,
                     code11_col='MSOA11CD', code21_col='MSOA21CD'):
    """
    England-wide 2021 MSOA code -> canonical 2011 code (every code, not just London).

    Needed by the national-frame notebook: external (non-London) origins/destinations
    must keep a *real* 2011 code so their national deprivation decile can be looked up
    (e.g. the flow-weighted external-decile diagnostic). Merges collapse to the lowest
    member 2011 code, exactly as in build_harmonisation, so London stays consistent.
    """
    lk = lookup_id[[code11_col, code21_col]].dropna().astype(str)
    parents_per_child = lk.groupby(code21_col)[code11_col].nunique()
    merge_children = set(parents_per_child[parents_per_child > 1].index)
    parent_to_canon = {}
    for ch in merge_children:
        members = sorted(lk.loc[lk[code21_col] == ch, code11_col].unique())
        for m in members:
            parent_to_canon[m] = members[0]
    return {r[code21_col]: parent_to_canon.get(r[code11_col], r[code11_col])
            for _, r in lk.iterrows()}
