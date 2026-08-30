# Working Instructions

These instructions describe how the user wants this repository work to proceed.

## General Preferences

- Work only in the `ds_code_challenge` repository unless the user explicitly changes this.
- Work through tasks step by step.
- Clarify uncertainty before taking action. Ask focused questions when requirements, scope, or implementation choices are unclear.
- Prefer not adding code over making an uncertain or unnecessary change.
- Keep the implementation as simple as possible.
- Preserve the user's full control over the approach, priorities, and decisions.
- Make the smallest change that addresses the agreed requirement.
- Do not assume an implementation detail when it has a meaningful effect on the result; explain the choice and ask first.
- Validate changes with an appropriate focused check before moving on.
- Keep `AI_log.md` updated whenever AI assistance is used.
- Record important decisions and changes to these instructions as the work progresses.
- Keep explanations concise and simple unless more detail is requested.
- Prefer discussing uncertain design choices before implementing them.
- Treat the notebook as a temporary workspace for experimentation and testing, not as the final product.
- Keep the final deliverable in Python files, using separate reusable classes where appropriate and a separate `main.py` entry point to assemble and execute the workflow.
- Keep credentials out of source code, notebooks, logs, and commits. Fetch or provide them at runtime, and do not print secret values.
- Prefer small, focused classes and functions over large code blocks or broad abstractions.
- Make logging useful for reproducibility: record run timing and validation outcomes without recording secrets.

## Decision Record

- 2026-08-28: Confirmed that all work for this assessment is limited to `ds_code_challenge`.
- 2026-08-28: Confirmed that `AI_log.md` and this `AGENTS.md` file should be created and maintained.
- 2026-08-28: The README is the primary project context and submission guidance.
- 2026-08-29: The Data Engineer track is in scope, including S3 Select extraction, validation against the standalone resolution-8 GeoJSON, and schema conformance documentation.
- 2026-08-29: The notebook is for working and testing only. The final solution should be executable Python with reusable classes and a separate `main.py` entry point.
- 2026-08-29: The extraction validation uses `config/data_extraction_contract.yml` as its machine-readable contract and `docs/data_extraction_validation.md` as its human-readable explanation.
- 2026-08-29: The current extraction class uses S3 Select to filter resolution 8, compares the shared `properties_index`, calculates a contract-based score, and logs each run to `logs/data_extraction.log`.
- 2026-08-29: A below-threshold extraction score stops the pipeline before later transformations. After a passing score, only H3 indices shared with the standalone resolution-8 reference are exposed to downstream steps; mismatches are logged.
- 2026-08-29: On extraction-validation failure, the entry point prints elapsed time, score, and `Passed: False` before exiting with the detailed error message.
- 2026-08-29: Step 2 uses a GeoPandas point-in-polygon join from service-request coordinates to the validated Step 1 H3 polygons. Its contract is `config/data_transformation_contract.yml`; it requires an H3 reference-match rate of at least 99.99% and a valid-coordinate failed-join rate of at most 0.01%.
- 2026-08-29: The 99.99% match threshold permits the investigated, immediate-neighbour boundary cases from exploratory validation. The 0.01% failed-join threshold is separate: it permits a few city-coverage edge cases but detects material spatial-join failures.
- 2026-08-30: The Step 2 YAML contract controls the spatial-join CRS, predicate, latitude/longitude bounds, one-polygon-match rule, source column mappings, and row-order validation assumption, rather than leaving these decisions hard-coded.
- 2026-08-30: Profiling found S3 download and CSV parsing consumed 21.78 seconds of a 24.11-second Step 2 run, compared with 2.15 seconds for the spatial join. Step 2 therefore downloads its two CSV objects concurrently and reads only the H3 index from the validation reference; the worker count and reference columns are contract configuration.
- 2026-08-30: The optimized Step 2 run completed in 21.59 seconds, a 2.52-second (about 10.5%) improvement over the baseline, with the same 99.996920% H3 reference-match rate.
- 2026-08-30: Step 2 reports separate counts for missing or invalid coordinates assigned `"0"`, valid-coordinate failed spatial joins assigned `"0"`, and wrong non-zero H3 assignments. Only the second category contributes to the failed-join threshold; the third contributes to the reference-match rate.
- 2026-08-30: The 99.99% H3 match threshold was selected over 99.95% because it permits at most 94 differences in the observed 941,634-row run, rather than about 470. The 0.01% failed-join threshold permits at most 72 failures among the observed 729,270 valid-coordinate rows, compared with 3 observed failures.
- 2026-08-30: Step 5.1 uses the City of Cape Town Official Suburb FeatureServer and selects the official `WITSAND` polygon because it produced the largest exploratory 80 m-centroid subset (48 requests) among the tested Atlantis-area candidates. It computes the centroid in EPSG:32734 and filters `sr_hex.csv.gz` within an 80 m straight-line distance, the agreed one-minute walking approximation.
- 2026-08-30: `SpatialData` owns reusable coordinate validation and GeoDataFrame point creation for Steps 2 and 5.1. Step 5.1 returns its non-empty subset in memory; Step 5.2 is deliberately not implemented yet.
- 2026-08-29: The current documentation describes only the checks implemented by the extraction class. Additional schema constraints in the YAML are not yet executed by the class.
- 2026-08-29: The current branch is `dev`, synced with the GitHub remote. A prior push was blocked because credentials had been committed to the notebook; the local history was rewritten and the cleaned commit was pushed successfully.
