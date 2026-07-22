# Signed Cross-Front Sections and ERA5 Dynamics Design

## Goal

Upgrade the current single-case diagnostics in two complementary ways:

1. make CRA40 and ERA5 cross-front sections directly comparable by using a signed distance axis in kilometres with a consistent cold-to-warm orientation; and
2. add self-consistent 850 hPa ERA5 dynamical diagnostics using the existing `u / v / q / t / r` fields in `data/raw/era5/201706.nc`.

The first verified target is `era5_front2_20170628T18`. Existing CRA40 research figures and filenames remain unchanged.

## Scope

### Included

- Signed cross-front distance axes for CRA40 and ERA5 section figures.
- Automatic orientation with cold side negative, front centre zero, and warm/moist side positive.
- New signed-distance figures for RH, temperature, vertical velocity, RH plus theta-e, and vertical velocity plus theta-e.
- ERA5 850 hPa maps for theta-e gradient with horizontal wind, divergence/convergence, moisture-flux convergence, and kinematic frontogenesis.
- Explicit units, pressure level, target time, sign conventions, and optional-diagnostic status.
- Synthetic numerical tests and a real ERA5 smoke run.

### Excluded

- Mixing ERA5 wind fields with CRA40 thermodynamic fields.
- Adding CRA40 dynamics before CRA40 `u / v / q` inputs are available.
- Time evolution, animation, composites, significance testing, Q vectors, potential vorticity, or terrain effects.
- Replacing or renaming the existing eleven CRA40 PNG products.

## Existing Data Boundary

The CRA40 directory currently contains RH, temperature, vertical velocity, and precipitation, but no horizontal wind components. Therefore CRA40 receives only the signed-section enhancement in this version.

`data/raw/era5/201706.nc` contains `u`, `v`, `q`, `t`, and `r` on common pressure levels and times. ERA5 dynamics must use these co-located fields from one selected time and 850 hPa level. Dedicated ERA5 RH, temperature, and vertical-velocity files remain the source for the existing profile pipeline unless a later migration deliberately consolidates them.

## Architecture

### 1. Section-coordinate core

Add a small core API that consumes `GeometryResult`, sampled thermodynamic profiles, and latitude/longitude geometry, and returns:

- a distance axis in kilometres for every section;
- an orientation decision for every section;
- oriented profile arrays without mutating the original `ProfileBundle` objects; and
- orientation metadata such as `warm_side_positive`, `geometric_fallback`, or `unresolved`.

Distance is measured along each actual sampling line, relative to its centre point, using physical great-circle or MetPy grid-distance calculations rather than converting degrees with a fixed constant.

### 2. Orientation rule

For every section, interpolate or select theta-e at 850 hPa and compare robust averages near the two section ends.

- If the theta-e contrast exceeds a documented minimum threshold, flip the distance axis and every plotted variable when necessary so that the colder/lower-theta-e side is negative and the warmer/higher-theta-e side is positive.
- If the contrast is too small or the endpoint values are invalid, preserve the geometric order and mark the section as unresolved rather than claiming a cold or warm side.
- The centre sample is always zero kilometres.

The endpoint value is the median of the outermost two samples on each side. The minimum absolute endpoint contrast is `0.5 K`. The threshold is a plot-orientation safeguard, not a new front-identification criterion.

The coordinate origin is the fitted centreline. With the verified odd sample count, the centre sample is exactly zero; if a future manifest uses an even sample count, zero lies between the two central samples rather than being assigned artificially to either one.

### 3. ERA5 dynamics core

Add a dedicated core module that accepts 2-D 850 hPa arrays and coordinates and returns a structured result containing:

- equivalent potential temperature;
- physical theta-e gradient magnitude in `K m-1`;
- horizontal divergence in `s-1`;
- moisture-flux convergence, computed as `-div(q u, q v)`, in `s-1` when specific humidity is treated as `kg kg-1`;
- MetPy kinematic frontogenesis in `K m-1 s-1`; and
- the co-located `u / v` fields for wind vectors.

All horizontal derivatives use latitude/longitude-aware physical spacing from `lat_lon_grid_deltas`. Plot scaling such as `1e5` or `1e9` may be applied only for readable colour-bar labels; the core result retains unscaled physical values.

### 4. ERA5 input adapter

Add a reader that opens the manifest-declared dynamics dataset once, selects the requested `valid_time` and nearest 850 hPa `pressure_level`, and subsets it to the diagnostic domain. It validates that `u`, `v`, `q`, `t`, and `r` are present and share compatible dimensions.

The ERA5 case manifest explicitly declares the dynamics dataset and target pressure level. The runner must not silently locate an unrelated file.

### 5. Plotting layer

The plotting layer consumes oriented profiles or a dynamics result and writes figures without performing file discovery or case validation.

New section products:

- `*_sections_rh_signed_km.png`
- `*_sections_temp_signed_km.png`
- `*_sections_w_signed_km.png`
- `*_sections_rh_thetae_signed_km.png`
- `*_sections_w_thetae_signed_km.png`

New ERA5 dynamics products:

- `*_850_thetae_gradient_wind.png`
- `*_850_divergence.png`
- `*_850_moisture_flux_convergence.png`
- `*_850_frontogenesis.png`

Every dynamics map overlays the front mask. Titles include dataset, case time, and `850 hPa`. Section panels label the x-axis as signed distance from the front centre in kilometres and state that negative is cold side and positive is warm side. Unresolved sections receive a visible `orientation unresolved` annotation.

## Runner and Manifest Integration

The runner keeps the current base chain intact. When diagnostics are enabled:

1. existing minimal and CRA40 research figures are generated as before;
2. signed-section figures are generated whenever RH and temperature profiles are available to determine orientation;
3. ERA5 dynamics are generated only when the case is ERA5 and a dynamics input is declared;
4. statistics CSV generation remains unchanged in this version.

The ERA5 `2017-06-28T18` manifest gains an explicit dynamics input and a diagnostics parameter selecting `850 hPa`.

The top-level diagnostics summary keeps its existing `enabled`, `status`, and `files` keys and adds a backward-compatible `components` mapping and `warnings` list:

- `completed`: all requested base, signed-section, and ERA5 dynamics products were produced;
- `partial`: the base diagnostics completed but one optional component was skipped;
- `skipped`: diagnostics were disabled.

Missing or invalid optional dynamics input must not abort a scientifically unrelated CRA40 run. For an ERA5 manifest that explicitly requests dynamics, the summary records a component-level failure reason and becomes `partial`; it must not report a false `completed` state.

## Error Handling

- Missing required profile variables for signed orientation: skip signed-section figures and record the reason.
- Weak or invalid endpoint theta-e contrast: retain geometric orientation, annotate unresolved sections, and continue.
- Missing ERA5 dynamics variables, time, or pressure level: preserve base diagnostics, mark dynamics failed/partial, and report the exact reason.
- Shape or coordinate mismatches: reject the dynamics component with an explicit validation error rather than resizing arrays implicitly.
- Numerical NaNs: propagate through calculations and mask invalid plotting regions; do not replace them with zero.

## Testing

### Section-coordinate tests

- Physical distance is monotonic, centred at zero, and stable across latitude-aware geometry.
- A synthetic theta-e field with the warm side initially on the left flips the distance and all profile variables.
- A field already oriented cold-to-warm remains unchanged.
- Weak or all-NaN endpoint contrast yields unresolved metadata without inventing a direction.

### Dynamics numerical tests

- Uniform wind produces near-zero divergence.
- A known linear divergent wind field produces the expected divergence sign and magnitude.
- A known `q u / q v` field produces the expected moisture-flux convergence sign.
- A synthetic deformation and thermal-gradient field produces a finite frontogenesis field with the expected sign pattern.
- Changing grid resolution does not change the physical derivative solely because sample spacing changed.

### Plot and runner tests

- Synthetic inputs create all five signed-section filenames.
- Synthetic ERA5 dynamics create all four expected map filenames.
- Existing CRA40 filenames and tests remain valid.
- A real `era5_front2_20170628T18` run produces the five signed-section figures, four dynamics maps, and the existing base diagnostics.
- A missing optional dynamics input produces `partial` with a concrete warning rather than a false success.

## Verification and Success Criteria

- The full existing test suite passes.
- The new numerical tests pass without relying only on file existence.
- `cra40_front2_20170628T18` still generates its existing research product set.
- `era5_front2_20170628T18` generates five signed-section figures and four 850 hPa dynamics maps.
- Visual QA confirms readable units, pressure labels, time labels, masks, wind vectors, signed-distance axes, and orientation annotations.
- No computation combines CRA40 thermodynamics with ERA5 dynamics.

## Expected Scientific Gain

The signed sections make different frontal segments directly comparable and expose cross-front tilt, moisture asymmetry, and ascent placement in a physically interpretable coordinate. ERA5 dynamics then add the first self-consistent evidence for convergence, moisture-flux forcing, deformation-driven frontogenesis, and their spatial relationship with the manually identified front.

The result supports stronger single-case mechanism discussion, while still not claiming temporal causality, climatological representativeness, or statistical significance.
