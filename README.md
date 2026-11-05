# Cascade migration and gentrification in London: replication code

Code for a manuscript, in preparation, that compares migration across the
neighbourhood deprivation hierarchy in London (2011 and 2021 Census
origin-destination data) with deprivation change over 2010–2019 and Yee and
Dennett's (2022) gentrification classification. Section and table numbers
below refer to the manuscript and its Supporting Information (SI).

## Repository layout

```
scripts/       analysis notebooks and scripts, numbered in run order
outputs.zip    every intermediate file and the files behind each table and figure
data/          raw inputs (not included; see "Data")
```

Unzip `outputs.zip` in the repository root to create `outputs/`. Every script
reads from and writes to `data/` and `outputs/` relative to the repository
root, so it can be run from any working directory.

## Data

The raw inputs are not redistributed. Place them in `data/` under these names.

| File in `data/` | Contents | Source | Used by |
| --- | --- | --- | --- |
| `census_od_2011_oa.csv` | 2011 Census migration flows, table MF01EW, Output Area level | WICID (UK Data Service); safeguarded, registration required | 01, 03 |
| `census_od_2021_msoa.csv` | 2021 Census migration flows, table ODMG01EW, MSOA level | Nomis | 01, 03 |
| `imd_2010.xls` | English indices of deprivation 2010 (2001 LSOAs) | DCLG (2011) | 01, 03 |
| `imd_2019.csv` | English indices of deprivation 2019, with mid-2015 population | MHCLG (2019) | 01 |
| `LSOA01_LSOA11_LAD11_EW_LU.csv` | LSOA (2001) to LSOA (2011) lookup, for the IMD 2010 recast | ONS Open Geography Portal | 01, 03 |
| `NSPCL_NOV22_UK_LU.csv` | Postcode to OA (2011) to LSOA to MSOA lookup, November 2022 | ONS Open Geography Portal | 01, 03 |
| `msoa_2011_to_2021_lookup.csv`, `MSOA_2011_to_2021_lookup_for_identification.csv` | MSOA (2011) to MSOA (2021) lookup | ONS Open Geography Portal | 01, 03, 06, 12 |
| `ks101ew_lsoa_2011.csv`, `ks101ew_lsoa_2011_allengland.csv` | 2011 Census usual residents (KS101EW) by LSOA, London and all England | Nomis | 01, 03 |
| `yee_LSOA_labels_forMapping.csv` | LSOA neighbourhood-change classification | Yee and Dennett (2022) | 06, 07, 08 |
| `london_msoa_2011.geojson` | London MSOA (2011) boundaries | ONS Open Geography Portal | 02, 03, 04 |
| `MSOA_Dec_2011_Boundaries_Generalised_Clipped_BGC_EW_V3_2022_*.zip` | MSOA (2011) boundaries | ONS Open Geography Portal | 11 |
| `ts001_msoa_2021.csv` or `nomis_2021_ts001.xlsx` | 2021 Census usual residents (TS001) by MSOA | Nomis | `diag_volume_robustness.py` only, optional |

`outputs.zip` holds results aggregated to the 982 analytical zones. It does
not contain the Output Area flows.

## Run order

Steps 01–06 build the analysis files from `data/`. Steps 07–12 produce the
manuscript's tables and figures from `outputs/`. "Needs `data/`" lists the raw
files a step still needs once `outputs.zip` is unzipped.

| Step | Script | What it does | Main files written to `outputs/` | Manuscript | Needs `data/` |
| --- | --- | --- | --- | --- | --- |
| 01 | `01_preprocess_london.ipynb` | Harmonises 2011 and 2021 flows to 982 zones; recasts and aggregates IMD 2010 and 2019; builds London-internal (Frame A) flows | `msoa_cascade_features_20260625.csv`, `lsoa11_to_msoa11.csv`, `exclusion_*.csv` | §3.1; SI S1.1, Tables S1–S3 | yes |
| 02 | `02_flow_measures.ipynb` | Derives the flow measures, including `Cascade_Dominance` and `Cross_Decile_Share` | `msoa_cascade_features_enriched_20260625.csv` | §3.3 | `london_msoa_2011.geojson` |
| 03 | `03_preprocess_national.ipynb` | England-wide ladder and the rest-of-England external node (Frames B and C) | `msoa_cascade_national_frame_20260625.csv` | §3.2; SI S1.2, Tables S4–S6 | yes |
| 04 | `04_flow_regimes_by_frame.ipynb` | Assigns flow regimes under Frames A, B and C in both windows | `eda4_results_for_phase3_20260626.csv` | Table 2; SI Table S8 | `london_msoa_2011.geojson` |
| 05 | `05_mechanism_profiles.ipynb` | Decision tree for Frame C "Cascade-led" zones and its thresholds | `eda9_mechanism_tree_20260705.csv`, `manuscript_table5_profile_composition.csv`, `case_study/fig01_*.png`, `case_study/fig02_*.png` | Table 5; SI Figures S1–S2, Tables S9–S10 | no |
| 06 | `06_gentrification_labels.ipynb` | Attaches Yee and Dennett (2022) subtype flags to each zone | `eda12_yee_leaf_corroboration_20260705.csv` | input to steps 07–11 | yes |
| 07 | `07_table3_aggregate_correspondence.py` | Spearman's rho, Kruskal–Wallis, Cramér's V and ARI | `manuscript_table3_20261021.csv`, `manuscript_aggregate_*` | Table 3, §4.1 | Yee labels |
| 08 | `08_table4_cascade_label.py` | "Cascade-led" membership against the modal gentrification label | `manuscript_cascade_label_table_20261027.*` | Table 4 | Yee labels |
| 09 | `09_table6_subtype_presence.py` | Subtype presence by mechanism profile | `manuscript_table6_subtype_presence_20261102.csv` | Table 6, §4.3 | no |
| 10 | `10_figure4_cases.py` | Flow decompositions of Camden 026 and Croydon 044 | `case_study/mechanism_cases_camden_croydon.png` | Figure 4 | no |
| 11 | `11_figure5_map.py` | Map of mechanism profiles and gentrification subtypes | `comparison_figs/fig_manuscript_subtype_mechanism_map_3subtypes_20261102.*` | Figure 5 | MSOA boundary zip |
| 12 | `12_figureS3_further_cases.ipynb` | Flow decompositions of Tower Hamlets 010, Westminster 019 and Harrow 008 | `case_study/si_appendix_s2/si_further_flow_decompositions.png` | SI Figure S3 | MSOA lookup |

Diagnostics:

| Script | What it checks | Manuscript | Needs `data/` |
| --- | --- | --- | --- |
| `diag_same_decile_definition.ipynb` | Treatment of same-decile moves (strict, asymmetric and symmetric) | SI S1.2.4, Table S7 | no |
| `diag_inflow_threshold.py` | Moving the 0.25 "cascade-inflow-share" threshold to either end of its empty interval | SI S1.3.2 | no |
| `diag_volume_robustness.py` | Whether the results depend on migration volume rather than proportions | not reported | Yee labels; population files optional |

Helper modules: `geo_harmonise.py` (2011–2021 MSOA harmonisation), `map_utils.py`
(choropleth maps) and `flow_yee_palette_v2.py` (figure colours).

Run notebooks with Jupyter and scripts with `python scripts/<name>.py`.
Figures 1–3 and Tables 1–2 are explanatory diagrams and method tables.

## Code terms and article terms

The code was written before some terms in the article were settled. In
particular, the code calls the escalator direction "counter".

| In the code | In the article |
| --- | --- |
| `Counter`, counter-cascade, `Counter-led` | escalator direction, "Escalator-led" |
| `Inflow_Wealthier`, `Outflow_Poorer` | IW and OP, which together form the cascade direction |
| `Outflow_Wealthier`, `Inflow_Poorer` | OW and IP, which together form the escalator direction |
| `CFI_Churn` | cascade-direction flows, IW + OP |
| `Counter_Churn` | escalator-direction flows, OW + IP |
| `Dom_A`, `Dom_B`, `Dom_C` | "Cascade_Dominance" under Frames A, B and C |
| `CDS_A`, `CDS_B`, `CDS_C` | "Cross_Decile_Share" under Frames A, B and C |
| `Typ_A`, `Typ_B`, `Typ_C` | flow regime under Frames A, B and C |
| no suffix / `_nat` suffix in `msoa_cascade_national_frame` | Frame A / Frame C measures |
| `_11`, `_21` | 2011 and 2021 migration windows |
| `Wealth_Decile` | London-relative IMD 2010 decile (1 = most deprived) |
| `Wealth_Decile_National` | England-wide IMD 2010 decile |
| `IMD_Pctile_Change` | IMD percentile change, 2010–2019 |
| `Casc_Inflow_Share`, `INFLOW_MIN = 0.25` | "cascade-inflow-share" and its threshold |
| `Ext_Arm_Share`, `EXT_MAJ = 0.5` | "external-arm-share" and its threshold |
| `leaf_11`, `leaf_21` | flow mechanism profile |
| `inflow-driven` | "inflow-driven, frame-robust" |
| `frame-sensitive`, `frame-sensitive inflow` | "frame-sensitive inflow" |
| `outflow-internal`, `outflow: internal-majority` | "outflow-internal-majority" |
| `outflow-external`, `outflow: external-majority` | "outflow-external-majority" |
| `any_SupGen`, `any_MainGen`, `any_MargGen`, `has_gen` | zone contains at least one LSOA with super-, mainstream, marginal or any gentrification |
| `Class_2_status`: `GEN`, `IUP`, `NRW`, `DEC`, `STB` | Yee and Dennett's broad classes: gentrifying, incumbent upgrading, new-build re-urbanisation, declining, stable |
| `strict_modal_gen()` in steps 07 and 08 | "modal gentrification" label (35 zones) |
| `gen_modal`, `yee_modal` in the `eda12` file | an earlier modal rule (41 zones), not used for the manuscript's tables |
| `Ring` | inner or outer London |
| external node, "+1" node | rest of England, at national Decile 6 |

Labels such as `eda4`, `eda9`, `eda12` and `phase3`, and the dates in output
file names, are fixed names from development. They do not refer to sections of
the manuscript.

## Software

Developed with Python 3.11. Packages are listed in `requirements.txt`.
