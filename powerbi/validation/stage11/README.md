# Stage 11 validation evidence

The existing PBIP was actually opened and refreshed in Power BI Desktop
2.157.1354.0. These artifacts distinguish native results from static checks.

## Final page captures

| Page | Screenshot |
|---|---|
| Executive Overview, filters cleared after interaction test | [executive_overview_cleared.png](executive_overview_cleared.png) |
| Market Trends | [market_trends.png](market_trends.png) |
| Area Intelligence | [area_intelligence.png](area_intelligence.png) |
| Property & Pricing | [property_pricing.png](property_pricing.png) |

[slicer_interaction.png](slicer_interaction.png) shows the native Ready selection:
38,042 sales records and 100% Ready Share. It was cleared before the final default
state was saved. The earlier valid `executive_overview.png` is preserved as an
initial render capture. The `*_ui.json` snapshots are supplemental accessibility
observations, not substitutes for the final inspected screenshots.
`desktop_window_final.png` is the earlier startup diagnostic of the empty window
encountered before the cache compatibility issue was resolved; despite that old
filename, it is not a final page capture. It is retained as recovery history.

## Results

- `recovery_baseline.json`: original clean-tree baseline and 114 protection hashes.
- `continuation_checkpoint.json`: state after the repeated recovery request;
  distinguishes complete components from remaining finalization work.
- `native_model_validation.json`: Desktop's native TMDL parser, model columns,
  measure names and active single-direction date relationship.
- `desktop_refresh.json`: real full refresh against the Desktop-owned engine;
  both imported partitions reached Ready. The recorded process has since closed.
- `live_dax_validation.json`: all 21 measures and Ready/September filter contexts.
- `live_segment_validation.json`: actual native area, band and bedroom aggregates.
- `segment_reconciliation.json`: exact case-sensitive area/source reconciliation,
  band ordering and bedroom count checks.
- `stage11_validation.json`: final source recalculation, JSON/schema checks, measure
  preservation, field references, visual counts and baseline protection checks.
- `desktop_render_validation.json`: reviewed screenshots, navigation and interaction
  results with explicit test scope.
- `protection_audit.json`: final strict allowed-path audit and source before/after SHA.
- `file_manifest.json`: exact created/modified paths, plus the final file hashes.
- `git_status_final.txt`: final uncommitted working-tree status on main.

Public visualContainer 2.12 schemas were unavailable (HTTP 404). Actual native
opening, refresh, DAX and rendering supplement the schemas that were available.
At the machine's 1024 × 768 resolution, some chart/table contents require scrolling.
No Service deployment or exhaustive slicer-combination test is claimed.

The scripts here operate on local Stage 11 evidence only. `build_missing_stage11.py`
records the initial missing-component build and refuses to overwrite existing new
pages; it is not a command to rebuild completed work. Point-capture helpers are
specific to the observed Desktop window and selection state and should not be run
blindly against another window. Validation evidence from Stage 10 is untouched.
