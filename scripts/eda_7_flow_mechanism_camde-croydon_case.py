"""
Figure 4.6 (two-case version): mechanism case studies for Camden 026 and Croydon 044.
 
Camden 026  : inflow-driven, frame-robust Cascade-led profile (Inner London).
Croydon 044 : outflow-external-majority profile (Outer London).
 
Uses the same colour grammar (flow_yee_palette_v2.ALLUVIAL), input files and
panel geometry as eda_7_v4_case_decomposition_palette_and_westminster_no_kingston.
Can be run as a script (python fig_4_6_mechanism_cases_camden_croydon.py) or
cell by cell in Jupyter / VS Code (the '# %%' markers split it into cells).
"""
 
# %% Imports and paths
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from pyprojroot import here
 
plt.rcParams['font.family'] = 'DejaVu Sans'
 
ROOT = here()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
 
from flow_yee_palette_v2 import ALLUVIAL
 
OUT_DIR = ROOT / 'outputs' / 'case_study' / 'figure_4_6'
NAT     = ROOT / 'outputs' / 'msoa_cascade_national_frame_20260625.csv'
EDA4    = ROOT / 'outputs' / 'eda4_results_for_phase3_20260626.csv'
OUT_DIR.mkdir(parents=True, exist_ok=True)
 
EXT_DECILE = 6        # synthetic external node sits at national D6
YL = 3.05
 
# Shared scale = ribbon widths comparable across both cases (Croydon will look thin
# next to Camden). Set to False to scale each case to its own maximum flow instead.
SHARED_SCALE = True
 
CASES = [
    ('E02000191', 'Camden 026'),    # inflow-driven, frame-robust
    ('E02000237', 'Croydon 044'),   # outflow-external-majority
]
 
OUT_NAME = 'fig_4_6_mechanism_cases_camden_croydon_v6.png'
TITLE    = 'Selected flow decompositions: inflow-driven vs outflow-external mechanisms'
CAPTION  = ('Camden 026 illustrates an inflow-driven, frame-robust Cascade-led profile; '
            'Croydon 044 illustrates an outflow-external-majority profile.')
 
# %% Colours and geometry
C_IN = ALLUVIAL['cascade_in']
C_EX = ALLUVIAL['cascade_ex']
K_IN = ALLUVIAL['counter_in']
K_EX = ALLUVIAL['counter_ex']
BAR  = '#2f2f2f'
ZONE = '#f2f0ec'      # rest-of-England margin shading
BND  = '#8a8a8a'      # boundary dash colour
 
X_EXT_L = -1.05   # external ribbons start here (left)
X_BND_L =  0.30   # London boundary, left
X_ML    =  3.30   # MSOA bar left edge
X_MR    =  3.90   # MSOA bar right edge
X_BND_R =  6.90   # London boundary, right
X_EXT_R =  8.25   # external ribbons end here (right)
 
INNER_LONDON = {
    'Camden', 'City of London', 'Greenwich', 'Hackney', 'Hammersmith and Fulham',
    'Haringey', 'Islington', 'Kensington and Chelsea', 'Lambeth', 'Lewisham',
    'Newham', 'Southwark', 'Tower Hamlets', 'Wandsworth', 'Westminster',
}
 
# %% Data
nat = pd.read_csv(NAT)
e4  = pd.read_csv(EDA4)
 
def row(code):
    return nat.loc[nat['msoa11cd'].eq(code)].iloc[0]
 
def domA(code, yr):
    return e4.loc[e4['msoa11cd'].eq(code), f'Dom_A_{yr}'].iloc[0]
 
# %% Drawing helpers
def _band(ax, x0, x1, lo, hi, color):
    ax.add_patch(mpatches.Rectangle((x0, lo), x1 - x0, hi - lo,
                                    facecolor=color, edgecolor='none',
                                    alpha=0.92, zorder=3))
 
def _chevron(ax, xc, yc, h):
    """White right-pointing chevron centred at (xc, yc); h = band height."""
    s = min(h * 0.55, 0.14)
    if s < 0.045:
        return
    w = s * 0.9
    verts = [(xc - w/2, yc + s), (xc + w/2, yc), (xc - w/2, yc - s),
             (xc - w/2 + w*0.45, yc), (xc - w/2, yc + s)]
    ax.add_patch(PathPatch(Path(verts, closed=True), facecolor='white',
                           edgecolor='none', alpha=0.85, zorder=4))
 
def _lay(segs, gap, scale):
    hs = [(v / scale, c, n, x0, x1) for v, c, n, x0, x1 in segs]
    tot = sum(h for h, *_ in hs) + gap * (sum(1 for _, _, n, _, _ in hs if n) - 1)
    top = tot / 2
    out = []
    for i, (h, c, n, x0, x1) in enumerate(hs):
        if n and i > 0:
            top -= gap
        out.append((top - h, top, c, x0, x1))
        top -= h
    return out
 
def arms_split(r, yr):
    d = r['Wealth_Decile_National']
    ei, eo = r[f'Ext_Inflow_nat_{yr}'], r[f'Ext_Outflow_nat_{yr}']
    iw, op = r[f'Inflow_Wealthier_nat_{yr}'], r[f'Outflow_Poorer_nat_{yr}']
    ip, ow = r[f'Inflow_Poorer_nat_{yr}'], r[f'Outflow_Wealthier_nat_{yr}']
    e_iw = ei if d < EXT_DECILE else 0
    e_ip = ei if d > EXT_DECILE else 0
    e_ow = eo if d < EXT_DECILE else 0
    e_op = eo if d > EXT_DECILE else 0
    return dict(iw=iw, op=op, ip=ip, ow=ow,
                iw_e=e_iw, op_e=e_op, ip_e=e_ip, ow_e=e_ow,
                iw_i=iw - e_iw, op_i=op - e_op, ip_i=ip - e_ip, ow_i=ow - e_ow)
 
def case_scale(cases):
    m = 0
    for c, _ in cases:
        r = row(c)
        for yr in ['11', '21']:
            a = arms_split(r, yr)
            m = max(m, a['iw'] + a['ip'], a['ow'] + a['op'])
    return m / 3.0
 
# %% Panel
def panel(ax, r, yr, scale, title, dom_lon, show_headers=True):
    a = arms_split(r, yr)
    gap = 0.30
 
    # background: rest-of-England margins + boundary dashes
    ax.add_patch(mpatches.Rectangle((X_EXT_L - 0.55, -YL), X_BND_L - (X_EXT_L - 0.55), 2*YL,
                                    facecolor=ZONE, edgecolor='none', zorder=0))
    ax.add_patch(mpatches.Rectangle((X_BND_R, -YL), (X_EXT_R + 0.55) - X_BND_R, 2*YL,
                                    facecolor=ZONE, edgecolor='none', zorder=0))
    for xb in (X_BND_L, X_BND_R):
        ax.plot([xb, xb], [-YL*0.88, YL*0.80], ls=(0, (4, 3)), lw=0.9, color=BND, zorder=1)
        ax.text(xb, -YL*0.96, 'London boundary', ha='center', va='top', fontsize=5.8, color=BND)
    ax.text((X_EXT_L - 0.55 + X_BND_L)/2, -YL*0.80, 'rest of\nEngland', ha='center',
            va='center', fontsize=5.8, color='#9a9a9a', style='italic')
    ax.text((X_BND_R + X_EXT_R + 0.55)/2, -YL*0.80, 'rest of\nEngland', ha='center',
            va='center', fontsize=5.8, color='#9a9a9a', style='italic')
 
    # internal segments stop at the boundary, external ones cross it
    Lsegs = [(a['iw_i'], C_IN, True,  X_BND_L, X_ML),
             (a['iw_e'], C_EX, False, X_EXT_L, X_ML),
             (a['ip_i'], K_IN, True,  X_BND_L, X_ML),
             (a['ip_e'], K_EX, False, X_EXT_L, X_ML)]
    Rsegs = [(a['ow_i'], K_IN, True,  X_MR, X_BND_R),
             (a['ow_e'], K_EX, False, X_MR, X_EXT_R),
             (a['op_i'], C_IN, True,  X_MR, X_BND_R),
             (a['op_e'], C_EX, False, X_MR, X_EXT_R)]
    L, R = _lay(Lsegs, gap, scale), _lay(Rsegs, gap, scale)
 
    for lo, hi, c, x0, x1 in L:
        _band(ax, x0, x1, lo, hi, c)
        _chevron(ax, X_ML - 0.55, (lo + hi)/2, hi - lo)
    for lo, hi, c, x0, x1 in R:
        _band(ax, x0, x1, lo, hi, c)
        _chevron(ax, x1 - 0.45, (lo + hi)/2, hi - lo)
 
    bar_lo, bar_hi = min(L[-1][0], R[-1][0]), max(L[0][1], R[0][1])
    ax.add_patch(mpatches.Rectangle((X_ML, bar_lo), X_MR - X_ML, bar_hi - bar_lo,
                                    facecolor=BAR, edgecolor='none', zorder=5))
 
    # arm labels + counts at the outer end of each arm
    iw_c = (L[0][0] + L[1][1])/2; ip_c = (L[2][0] + L[3][1])/2
    ow_c = (R[0][0] + R[1][1])/2; op_c = (R[2][0] + R[3][1])/2
 
    def lab(x, y, name, tot, ext, c, ha):
        if tot / scale < 0.03:
            return
        ax.text(x, y + 0.085, name, ha=ha, va='bottom', fontsize=6.4, color=c, fontweight='bold')
        ax.text(x, y - 0.075, f'{int(tot)}' + (f' (ext {int(ext)})' if ext > 0.5 else ''),
                ha=ha, va='top', fontsize=6.8, color=c)
 
    lab(X_EXT_L - 0.68, iw_c, 'from wealthier', a['iw'], a['iw_e'], C_IN, 'right')
    lab(X_EXT_L - 0.68, ip_c, 'from poorer',    a['ip'], a['ip_e'], K_IN, 'right')
    lab(X_EXT_R + 0.68, ow_c, 'to wealthier',   a['ow'], a['ow_e'], K_IN, 'left')
    lab(X_EXT_R + 0.68, op_c, 'to poorer',      a['op'], a['op_e'], C_IN, 'left')
 
    if show_headers:
        ax.text((X_EXT_L + X_ML)/2, YL*0.90, 'I N F L O W S  \u25b6',
                ha='center', va='center', fontsize=7.6, color='#555', fontweight='bold')
        ax.text((X_MR + X_EXT_R)/2, YL*0.90, '\u25b6  O U T F L O W S',
                ha='center', va='center', fontsize=7.6, color='#555', fontweight='bold')
 
    ring = 'Inner' if r['ladnm'] in INNER_LONDON else 'Outer'
    ax.text(0.99, 0.985, f"{ring} London \u00b7 nat D{int(r['Wealth_Decile_National'])}",
            transform=ax.transAxes, ha='right', va='top', fontsize=6.6, color='#444',
            bbox=dict(boxstyle='round,pad=0.32', fc='white', ec='#cfcfcf', lw=0.7))
 
    casc, cnt = a['iw'] + a['op'], a['ip'] + a['ow']
    dom = casc / (casc + cnt)
    infl = a['iw'] / (a['iw'] + a['op']) if (a['iw'] + a['op']) else np.nan
    ext_sh = (a['iw_e'] + a['ip_e'] + a['ow_e'] + a['op_e']) / (casc + cnt) if (casc + cnt) else 0
    ax.text(0.5, -0.045,
            f'dominance(nat) {dom:.2f}   inflow share {infl:.2f}   '
            f'external(cross-decile) {ext_sh:.0%}   \u00b7   dominance(London) {dom_lon:.2f}',
            transform=ax.transAxes, ha='center', va='top', fontsize=8,
            color=C_IN if dom >= 0.5 else K_IN, fontweight='bold')
    ax.text(0.5, 1.0, title, transform=ax.transAxes, ha='center', va='bottom',
            fontsize=10, fontweight='bold')
    ax.set_xlim(X_EXT_L - 2.55, X_EXT_R + 2.55)
    ax.set_ylim(-YL, YL)
    ax.set_axis_off()
 
# %% Build figure
LEG = [
    mpatches.Patch(color=C_IN, label='Cascade direction · within London'),
    mpatches.Patch(color=C_EX, label='Cascade direction · crossing London boundary'),
    mpatches.Patch(color=K_IN, label='Escalator direction · within London'),
    mpatches.Patch(color=K_EX, label='Escalator direction · crossing London boundary'),
]
 
def build(title, cases, fname, caption='', figsize_per_row=3.25, dpi=180):
    shared = case_scale(cases)
    nr = len(cases)
    fig, axes = plt.subplots(nr, 2, figsize=(14, figsize_per_row * nr + 1.5), squeeze=False)
    for i, (code, name) in enumerate(cases):
        sc = shared if SHARED_SCALE else case_scale([(code, name)])
        panel(axes[i, 0], row(code), '11', sc, f'{name}  ·  2011', domA(code, '11'), show_headers=(i == 0))
        panel(axes[i, 1], row(code), '21', sc, f'{name}  ·  2021', domA(code, '21'), show_headers=(i == 0))
 
    fig.suptitle(title, fontsize=13.5, fontweight='bold', y=0.995)
    fig.legend(handles=LEG, loc='lower center', ncol=2, frameon=False,
               fontsize=8.2, bbox_to_anchor=(0.5, 0.0))
    if caption:
        fig.text(0.5, 0.075, caption, ha='center', va='bottom', fontsize=8.1,
                 style='italic', color='#333333', wrap=True)
    plt.tight_layout(rect=[0, 0.11 if caption else 0.07, 1, 0.965])
    out = OUT_DIR / fname
    plt.savefig(out, dpi=dpi, bbox_inches='tight')
    print(f'Saved {out}')
    plt.show()
 
 
if __name__ == '__main__' or 'ipykernel' in sys.modules:
    build(TITLE, CASES, OUT_NAME, caption=CAPTION)
 