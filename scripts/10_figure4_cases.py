"""
(two-case version): mechanism case studies for Camden 026 and Croydon 044.
 
Camden 026  : inflow-driven, frame-robust Cascade-led profile (Inner London).
Croydon 044 : outflow-external-majority profile (Outer London).
 
Uses the same colour grammar (flow_yee_palette_v2.ALLUVIAL), input files and
panel geometry as scripts/12_figureS3_further_cases.ipynb.
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
 
OUT_DIR = ROOT / 'outputs' / 'case_study' 
NAT     = ROOT / 'outputs' / 'msoa_cascade_national_frame_20260625.csv'
EDA4    = ROOT / 'outputs' / 'eda4_results_for_phase3_20260626.csv'
OUT_DIR.mkdir(parents=True, exist_ok=True)
 
EXT_DECILE = 6        # synthetic external node sits at national D6
YL = 3.05

# ---- Print size -------------------------------------------------------------
# 2 x 2 grid (one row per case, 2011 | 2021) drawn at the size it is printed: a
# full portrait A4 page above the caption. FIG_W_CM is the LaTeX \textwidth
# (A4, 2.5 cm margins) and FIG_H_CM the most the page holds with the caption
# (footnotesize) below it. Font sizes below are therefore the sizes on the page.
CM = 1 / 2.54
FIG_W_CM = 16.0
FIG_H_CM = 20.4
COL_GAP_CM = 0.5      # gap between the 2011 and 2021 panels
LABEL_CM = 2.0        # room for the arm labels on each side of a panel
FS = dict(title=9, header=7, label=6.5, note=6, box=6.5, metric=6.5, legend=7.5)
 
# Shared scale = ribbon widths comparable across both cases (Croydon will look thin
# next to Camden). Set to False to scale each case to its own maximum flow instead.
SHARED_SCALE = True
 
CASES = [
    ('E02000191', 'Camden 026'),    # inflow-driven, frame-robust
    ('E02000237', 'Croydon 044'),   # outflow-external-majority
]
 
OUT_NAME = 'mechanism_cases_camden_croydon.png'
TITLE    = ''
 
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
def panel(ax, r, yr, scale, title, dom_lon, show_headers=True, pad=2.55, label_gap=0.80):
    """One half-width panel. pad: room outside the rest-of-England margins for
    the arm labels, in data units; label_gap: smallest vertical distance between
    the two labels on one side (build() sets both from cm)."""
    a = arms_split(r, yr)
    gap = 0.30
 
    # background: rest-of-England margins + boundary dashes
    ax.add_patch(mpatches.Rectangle((X_EXT_L - 0.55, -YL), X_BND_L - (X_EXT_L - 0.55), 2*YL,
                                    facecolor=ZONE, edgecolor='none', zorder=0))
    ax.add_patch(mpatches.Rectangle((X_BND_R, -YL), (X_EXT_R + 0.55) - X_BND_R, 2*YL,
                                    facecolor=ZONE, edgecolor='none', zorder=0))
    for xb in (X_BND_L, X_BND_R):
        ax.plot([xb, xb], [-YL*0.88, YL*0.80], ls=(0, (4, 3)), lw=0.7, color=BND, zorder=1)
        ax.text(xb, -YL*0.96, 'London boundary', ha='center', va='top', fontsize=FS['note'], color=BND)
    # "rest of England" runs up each shaded strip, which is too narrow for it across
    for xz in ((X_EXT_L - 0.55 + X_BND_L)/2, (X_BND_R + X_EXT_R + 0.55)/2):
        ax.text(xz, -YL*0.55, 'rest of England', ha='center', va='center', rotation=90,
                fontsize=FS['note'], color='#9a9a9a', style='italic')
 
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

    # keep the two labels on each side apart when their arms are thin
    def spread(y_top, y_bot, gap=label_gap):
        if y_top - y_bot < gap:
            mid = (y_top + y_bot) / 2
            return mid + gap / 2, mid - gap / 2
        return y_top, y_bot
    iw_c, ip_c = spread(iw_c, ip_c)
    ow_c, op_c = spread(ow_c, op_c)
 
    def lab(x, y, name, tot, ext, c, ha):
        if tot / scale < 0.03:
            return
        ax.text(x, y + 0.085, name, ha=ha, va='bottom', fontsize=FS['label'], color=c, fontweight='bold')
        ax.text(x, y - 0.075, f'{int(tot)}' + (f' (ext {int(ext)})' if ext > 0.5 else ''),
                ha=ha, va='top', fontsize=FS['label'], color=c)
 
    lab(X_EXT_L - 0.68, iw_c, 'from wealthier', a['iw'], a['iw_e'], C_IN, 'right')
    lab(X_EXT_L - 0.68, ip_c, 'from poorer',    a['ip'], a['ip_e'], K_IN, 'right')
    lab(X_EXT_R + 0.68, ow_c, 'to wealthier',   a['ow'], a['ow_e'], K_IN, 'left')
    lab(X_EXT_R + 0.68, op_c, 'to poorer',      a['op'], a['op_e'], C_IN, 'left')
 
    if show_headers:
        ax.text((X_BND_L + X_ML)/2, YL*0.90, 'Inflows  \u25b6',
                ha='center', va='center', fontsize=FS['header'], color='#555', fontweight='bold')
        ax.text((X_MR + X_BND_R)/2, YL*0.90, '\u25b6  Outflows',
                ha='center', va='center', fontsize=FS['header'], color='#555', fontweight='bold')
 
    ring = 'Inner' if r['ladnm'] in INNER_LONDON else 'Outer'
    loc = f"{ring} London \u00b7 nat D{int(r['Wealth_Decile_National'])}"
    box = dict(boxstyle='round,pad=0.32', fc='white', ec='#cfcfcf', lw=0.5)
    # Title on the left and location box on the right, both above the panel
    ax.text(0.0, 1.02, title, transform=ax.transAxes, ha='left', va='bottom',
            fontsize=FS['title'], fontweight='bold')
    ax.text(0.985, 1.02, loc, transform=ax.transAxes, ha='right', va='bottom',   # box border stays inside
            fontsize=FS['box'], color='#444', bbox=box)
 
    casc, cnt = a['iw'] + a['op'], a['ip'] + a['ow']
    dom = casc / (casc + cnt)
    infl = a['iw'] / (a['iw'] + a['op']) if (a['iw'] + a['op']) else np.nan
    ext_sh = (a['iw_e'] + a['ip_e'] + a['ow_e'] + a['op_e']) / (casc + cnt) if (casc + cnt) else 0
    # two lines, so the measures fit under a half-width panel
    measures = (f'dominance(nat) {dom:.2f}   \u00b7   dominance(London) {dom_lon:.2f}\n'
                f'inflow share {infl:.2f}   \u00b7   external(cross-decile) {ext_sh:.0%}')
    ax.text(0.5, -0.04, measures, transform=ax.transAxes, ha='center', va='top',
            fontsize=FS['metric'], linespacing=1.3,
            color=C_IN if dom >= 0.5 else K_IN, fontweight='bold')
    ax.set_xlim(X_EXT_L - 0.55 - pad, X_EXT_R + 0.55 + pad)
    ax.set_ylim(-YL, YL)
    ax.set_axis_off()
 
# %% Build figure
LEG = [
    mpatches.Patch(color=C_IN, label='Cascade direction · within London'),
    mpatches.Patch(color=C_EX, label='Cascade direction · crossing London boundary'),
    mpatches.Patch(color=K_IN, label='Escalator direction · within London'),
    mpatches.Patch(color=K_EX, label='Escalator direction · crossing London boundary'),
]
 
def build(title, cases, fname, dpi=600):
    """2 x 2 grid filling FIG_W_CM x FIG_H_CM: one row per case, 2011 | 2021."""
    shared = case_scale(cases)
    nr = len(cases)

    # Vertical layout in cm; the panels take whatever height FIG_H_CM leaves.
    TOP, TITLE_BAND, METRIC, ROW_GAP, LEGEND = 0.05, 0.5, 0.85, 0.3, 1.2
    panel_h = (FIG_H_CM - TOP - (nr - 1) * ROW_GAP - LEGEND) / nr - TITLE_BAND - METRIC
    row_h = TITLE_BAND + panel_h + METRIC
    panel_w = (FIG_W_CM - COL_GAP_CM) / 2
    fig = plt.figure(figsize=(FIG_W_CM * CM, FIG_H_CM * CM))

    core_units = (X_EXT_R + 0.55) - (X_EXT_L - 0.55)
    pad = LABEL_CM * core_units / (panel_w - 2 * LABEL_CM)    # LABEL_CM in data units
    label_gap = max(0.80, 0.65 * 2 * YL / panel_h)            # two-line labels need 0.65 cm

    for i, (code, name) in enumerate(cases):
        sc = shared if SHARED_SCALE else case_scale([(code, name)])
        top = TOP + i * (row_h + ROW_GAP) + TITLE_BAND
        bottom = FIG_H_CM - top - panel_h
        for j, yr in enumerate(['11', '21']):
            left = j * (panel_w + COL_GAP_CM)
            ax = fig.add_axes([left / FIG_W_CM, bottom / FIG_H_CM,
                               panel_w / FIG_W_CM, panel_h / FIG_H_CM])
            panel(ax, row(code), yr, sc, f'{name}  \u00b7  20{yr}', domA(code, yr),
                  show_headers=(i == 0), pad=pad, label_gap=label_gap)

    if title:
        fig.suptitle(title, fontsize=FS['title'] + 1, fontweight='bold')
    fig.legend(handles=LEG, loc='lower center', ncol=2, frameon=False,
               fontsize=FS['legend'], columnspacing=2.0, bbox_to_anchor=(0.5, 0.0))

    out = OUT_DIR / fname
    for o in (out, out.with_suffix('.pdf')):
        # No bbox_inches='tight': keep the exact print size.
        plt.savefig(o, dpi=dpi, facecolor='white')
    print(f'Saved {out.name} and {out.with_suffix(".pdf").name} in {OUT_DIR} '
          f'({FIG_W_CM:.1f} x {FIG_H_CM:.1f} cm; panels {panel_w:.1f} x {panel_h:.1f} cm)')
    plt.show()
 
 
if __name__ == '__main__' or 'ipykernel' in sys.modules:
    build(TITLE, CASES, OUT_NAME)
 