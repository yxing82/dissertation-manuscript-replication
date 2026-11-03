"""
flow_yee_palette.py — chapter-wide colour grammar (v2, 2026-07-29)
======================================================================
One hue family per classification system, fixed across every Results
figure:

  WARM REDS  = flow-CASCADE mechanism leaves (this study, EDA 9 tree)
  GOLD       = frame-sensitive residual (reported, not narrated)
  COOL BLUE  = flow-COUNTER regime (replaces the old #6a51a3 purple,
               which collided with the conventional gentrification
               purple and with Yee's own GEN colour #762a83)
  PURPLE     = Yee & Dennett (2022) ATTRIBUTE labels, exclusively
  GREEN      = agreement of the two lenses (divergence map only)
  GREY       = Symmetric / Lateral background fabric

Import from any EDA notebook (ROOT is already on sys.path):

    from flow_yee_palette import FLOW_FILL, FLOW_ALPHA, YEE, DIVERGENCE

Change history vs the EDA 10/12-v3 hexes:
  counter          #6a51a3 -> COUNTER blue  (de-purpled)
  outflow-internal #fcbba1 -> #fc9272       (one ColorBrewer-Reds step
                                             darker: separates from the
                                             #e9e7e2 background grey)
  Yee markers      black   -> #762a83       (markers now visually
                                             'belong' to the attribute
                                             lens)
All other flow hexes are unchanged from EDA 10, so the mechanism-
geography maps stay recognisable.
"""

# ── flow side (this study) ──────────────────────────────────────────────
FLOW_FILL = {
    'inflow-driven':    '#99000d',   # deep red   — gentrification-candidate arm
    'frame-sensitive':  '#e6ab02',   # ochre/gold — residual
    'outflow-external': '#e64a2e',   # deepened (was #ef6548) — exodus signature
    'outflow-internal': '#f8875f',   # salmon, darkened again (#fcbba1→#fc9272→#f8875f)
    'counter':          '#9db8ce',   # light grey-blue (was #4d88b5): context, not signal
    'other':            '#e9e7e2',   # grey fabric — Symmetric / Lateral
}
FLOW_ALPHA = {
    'inflow-driven': 0.95, 'frame-sensitive': 0.90,
    'outflow-external': 0.95, 'outflow-internal': 0.95,
    'counter': 0.85, 'other': 1.00,
}
# bottom -> top draw order (most salient last)
FLOW_DRAW_ORDER = ('other', 'counter', 'outflow-internal',
                   'outflow-external', 'frame-sensitive', 'inflow-driven')

FLOW_LABEL = {
    'inflow-driven':    'Inflow-driven cascade — frame-robust, inflow-led',
    'frame-sensitive':  'Frame-sensitive inflow — residual',
    'outflow-external': 'Outflow cascade — external-majority',
    'outflow-internal': 'Outflow cascade — internal-majority',
    'counter':          'Counter-led',
    'other':            'Symmetric / Lateral',
}

# ── attribute side (Yee & Dennett 2022) — purple owns this system ───────
YEE = {
    'GEN':   '#762a83',   # matches Yee's own published GEN purple
    'IUP':   '#af8dc3',
    'NRW':   '#7fbf7b',
    'DEC':   '#1b7837',
    'STB':   '#e7e7e7',
    'marker': '#762a83',  # SupGen / MainGen map markers
}

# ── divergence map (Fig 4.21) — recoloured to obey the grammar ──────────
# red = flow-only, purple = Yee-only, green = agreement, grey = neither
DIVERGENCE = {
    'Flow-only: cascade, no Yee-GEN': '#c0392b',   # was blue #4575b4
    'Gap: Yee-GEN, non-cascade flow': '#762a83',   # was red  #d73027
    'Agree: GEN & cascade':           '#1a9850',   # unchanged
    'Neither':                        '#e0e0e0',   # unchanged
}

# ── alluvial arms (EDA 11) — counter arms follow the de-purpling ────────
ALLUVIAL = {
    'cascade_in':  '#c0392b', 'cascade_ex': '#e8a7a0',
    'counter_in':  '#5d8fb5', 'counter_ex': '#aec8dd',   # were #6a51a3 / #bcaede
}

# ── marker styling (v2.1): tag, not cover ───────────────────────────────
# Shrunk ~20% linear from v2 (circles a touch more than triangles) so the
# underlying fill colour stays visible; halo thinned but KEPT, purple
# stroke kept strong. The marker's job: (1) flag subtype presence,
# (2) let the reader see which mechanism fill it sits on.
#   path_effects=[pe.withStroke(linewidth=MARKER_STYLE['halo_lw'], foreground='white')]
# MARKER_STYLE = dict(
#     supgen=dict(s=19, facecolors='none', edgecolors=YEE['marker'], linewidths=1.4),   # was s=30, lw=1.6
#     maingen=dict(s=26, marker='^', facecolors=YEE['marker'], edgecolors='white', linewidths=0.6),  # was s=36, lw=0.7
#     halo_lw=2.4,                                                                       # was 3.0
#     legend=dict(supgen_ms=5.6, supgen_mew=1.4, maingen_ms=6.6, maingen_mew=0.6),
# )
SUBTYPE_MARKER = '#111111'

MARKER_STYLE = dict(
    supgen=dict(
        s=19,
        facecolors='none',
        edgecolors=SUBTYPE_MARKER,
        linewidths=1.4
    ),
    maingen=dict(
        s=26,
        marker='^',
        facecolors=SUBTYPE_MARKER,
        edgecolors='white',
        linewidths=0.6
    ),
    halo_lw=2.4,
    legend=dict(
        supgen_ms=5.6,
        supgen_mew=1.4,
        maingen_ms=6.6,
        maingen_mew=0.6
    ),
)
