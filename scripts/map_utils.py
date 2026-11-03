"""
map_utils.py — Shared choropleth mapping utility for London MSOA analysis.

All EDA notebooks import this for consistent map styling. Provides:
  - load_london_msoa(): loads and reprojects the MSOA boundary GeoJSON
  - plot_london_choropleth(): produces a styled choropleth of any numeric column
  - plot_london_categorical(): produces a styled categorical map

Usage:
    from map_utils import load_london_msoa, plot_london_choropleth
    gdf = load_london_msoa('path/to/london_msoa_2011.geojson', df)
    fig, ax = plot_london_choropleth(gdf, column='CFI_Churn_21', title='...')
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np


# ── Default style constants ─────────────────────────────────────────────────
BG_COLOR = '#fafafa'
EDGE_COLOR = '#cccccc'
EDGE_LW = 0.15
BOROUGH_EDGE_COLOR = '#666666'
BOROUGH_EDGE_LW = 0.6
FIGSIZE = (12, 10)
TARGET_CRS = 'EPSG:27700'  # British National Grid — appropriate for London maps


def load_london_msoa(geojson_path, df=None, msoa_col='msoa11cd'):
    """
    Load London MSOA boundaries and optionally merge with a DataFrame.

    Parameters
    ----------
    geojson_path : str
        Path to the London MSOA GeoJSON file.
    df : pd.DataFrame, optional
        Data to merge (must contain `msoa_col`).
    msoa_col : str
        Column name in df for MSOA codes (default: 'msoa11cd').

    Returns
    -------
    gpd.GeoDataFrame
        Reprojected to British National Grid with data merged if provided.
    """
    gdf = gpd.read_file(geojson_path)
    gdf = gdf.to_crs(TARGET_CRS)

    if df is not None:
        gdf = gdf.merge(df, left_on='MSOA11CD', right_on=msoa_col, how='left')

    return gdf


def _add_borough_boundaries(ax, gdf):
    """Overlay dissolved borough boundaries for spatial context."""
    if 'ladnm' in gdf.columns:
        boroughs = gdf.dissolve(by='ladnm')
        boroughs.boundary.plot(
            ax=ax, color=BOROUGH_EDGE_COLOR, linewidth=BOROUGH_EDGE_LW
        )


def plot_london_choropleth(
    gdf, column, title='', cmap='RdYlBu_r', figsize=FIGSIZE,
    legend_label=None, vmin=None, vmax=None, vcenter=None,
    show_boroughs=True, ax=None, missing_color='#d9d9d9'
):
    """
    Produce a styled choropleth map of London MSOAs.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Must contain 'geometry' and `column`.
    column : str
        Numeric column to map.
    title : str
        Map title.
    cmap : str
        Matplotlib colormap name.
    figsize : tuple
        Figure size (ignored if ax is provided).
    legend_label : str
        Label for the colorbar.
    vmin, vmax : float
        Colorbar limits (auto-detected if None).
    vcenter : float
        Centre value for diverging colormaps (creates TwoSlopeNorm).
    show_boroughs : bool
        Whether to overlay borough boundaries.
    ax : matplotlib.axes.Axes
        Existing axes to plot on (creates new figure if None).
    missing_color : str
        Colour for MSOAs with NaN values.

    Returns
    -------
    fig, ax
    """
    return_fig = ax is None
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    else:
        fig = ax.get_figure()

    ax.set_facecolor(BG_COLOR)
    fig.patch.set_facecolor(BG_COLOR)

    # Handle colour normalisation
    norm = None
    if vcenter is not None:
        v0 = vmin if vmin is not None else gdf[column].min()
        v1 = vmax if vmax is not None else gdf[column].max()
        norm = mcolors.TwoSlopeNorm(vmin=v0, vcenter=vcenter, vmax=v1)

    plot_kwargs = dict(
        column=column, cmap=cmap, linewidth=EDGE_LW, edgecolor=EDGE_COLOR,
        legend=True, missing_kwds={'color': missing_color, 'label': 'No data'},
        legend_kwds={
            'label': legend_label or column,
            'shrink': 0.6, 'aspect': 25, 'pad': 0.02
        },
        ax=ax,
    )
    if norm is not None:
        plot_kwargs['norm'] = norm
    else:
        if vmin is not None:
            plot_kwargs['vmin'] = vmin
        if vmax is not None:
            plot_kwargs['vmax'] = vmax

    gdf.plot(**plot_kwargs)

    if show_boroughs:
        _add_borough_boundaries(ax, gdf)

    ax.set_axis_off()
    ax.set_title(title, fontsize=13, fontweight='bold', pad=12)

    if return_fig:
        fig.tight_layout()
        return fig, ax
    return fig, ax


def plot_london_categorical(
    gdf, column, title='', color_dict=None, figsize=FIGSIZE,
    show_boroughs=True, ax=None, missing_color='#d9d9d9'
):
    """
    Produce a styled categorical map of London MSOAs.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Must contain 'geometry' and `column` (categorical).
    column : str
        Categorical column to map.
    title : str
        Map title.
    color_dict : dict
        Mapping from category values to colours.
    show_boroughs : bool
        Whether to overlay borough boundaries.

    Returns
    -------
    fig, ax
    """
    return_fig = ax is None
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    else:
        fig = ax.get_figure()

    ax.set_facecolor(BG_COLOR)
    fig.patch.set_facecolor(BG_COLOR)

    categories = gdf[column].dropna().unique()

    if color_dict is None:
        default_colors = plt.cm.Set2.colors
        color_dict = {cat: default_colors[i % len(default_colors)]
                      for i, cat in enumerate(sorted(categories))}

    # Plot each category separately for legend control
    for cat in sorted(categories):
        subset = gdf[gdf[column] == cat]
        subset.plot(
            ax=ax, color=color_dict.get(cat, '#999999'),
            linewidth=EDGE_LW, edgecolor=EDGE_COLOR, label=str(cat)
        )

    # Missing values
    missing = gdf[gdf[column].isna()]
    if len(missing) > 0:
        missing.plot(ax=ax, color=missing_color, linewidth=EDGE_LW,
                     edgecolor=EDGE_COLOR, label='No data')

    if show_boroughs:
        _add_borough_boundaries(ax, gdf)

    ax.set_axis_off()
    ax.set_title(title, fontsize=13, fontweight='bold', pad=12)
    ax.legend(loc='lower left', fontsize=9, framealpha=0.9, title=column)

    if return_fig:
        fig.tight_layout()
        return fig, ax
    return fig, ax
