# CRA40 Research Diagnostics Design

## Goal

Restore the first layer of legacy-style, research-readable diagnostics for CRA40 single-case runs, starting with `cra40_front2_20170628T18`.

## Scope

The first version only targets CRA40 cases already runnable through `pipeline.runner`. It does not add ERA5 support, continuous-frame animations, or a full legacy product tree.

## Required Figures

- `*_thetae_gradient_mask_overlay.png`: 850 hPa equivalent-potential-temperature gradient background with the manual front mask overlaid.
- `*_precip_mask_overlay.png`: 6-hour CRA40 precipitation background with the manual front mask overlaid.
- `*_subarea_overlay.png`: manual front mask, selected subarea mask, centerline, and all section lines in one map.
- `*_sections_rh.png`, `*_sections_temp.png`, `*_sections_w.png`: all section profiles for each variable as legacy-style panel plots.
- `*_sections_rh_thetae.png`: RH filled contours with theta-e contours for every section.
- `*_sections_w_thetae.png`: W filled contours with theta-e contours for every section.

## Data Flow

`runner` already builds mask, geometry, subarea, profile bundles, and statistics. For CRA40 diagnostics it should additionally pass the target-time 3D field cache and levels to the diagnostics layer. The diagnostics layer computes theta-e from CRA40 temperature and RH fields and reads the matching CRA40 precipitation file.

## Boundaries

The plotting functions consume arrays and metadata. They should not decide case validity, locate manifest files, or change scientific step outputs. If an optional research diagnostic cannot be produced because a required CRA40 variable is missing, the main run should continue with the existing minimal diagnostics.

## Verification

Unit tests should verify that the new diagnostics functions create the expected PNG filenames from synthetic arrays. A real smoke run should verify that `cra40_front2_20170628T18` produces the expanded diagnostics file list and CSV successfully.
