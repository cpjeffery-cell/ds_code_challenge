# AI Log

This file records AI-assisted work completed for the City of Cape Town Data Science Unit Code Challenge.

**Token usage:** GitHub Copilot Chat does not expose a per-response token count through any tool or API available to the assistant during this session. The user reports VS Code's own UI showed a figure of approximately 3,776 for this session as a whole; entries below note "Not available" per-entry because no finer-grained breakdown could be obtained by the assistant.

## 2026-08-30 - K-Anonymity Time-Bucket Generalization Fix

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **Issue observed:** After adding cause-code generalization (`cause_code` -> `cause_code_group` -> suppression), 71 of 76 Witsand rows still had to be flagged for manual review, unchanged from before that fix.
- **Diagnosis:** The whole Witsand subsample shares a single `h3_level8_index` value, so location contributes nothing to separating rows; all of the k-anonymity burden falls on `creation_timestamp`. The 6-hour and even 7-day time buckets were too fine for 76 requests spread across a full year: most weeks had fewer than 5 requests, but most months had 5 or more. The configured time-generalization hierarchy stopped at 7 days, one step short of where the data actually clustered.
- **Correction:** Added a 30-day fallback level to `time_generalization_hierarchy` in `config/data_anonymisation_contract.yml`. Verified directly against the real flagged output before changing anything further: an ad hoc 30-day floor rescued 62 of the 71 flagged rows.
- **Outcome:** Re-running the full pipeline confirmed the fix: 62 anonymised rows (up from 5), 14 flagged for manual review (down from 71). The remaining 14 fall in months with only 2-3 requests all year, which cannot be made non-unique even at monthly granularity — that residual is the expected, honest outcome for this sparse subsample, not a flaw in the approach.
- **User-considered and rejected alternative:** A keyed cipher/hash for `notification_number` (to allow reversible re-linkage) was discussed and explicitly rejected: it would address a different problem (protecting a direct identifier while preserving linkage) and does nothing for quasi-identifier uniqueness, which was the actual cause of the high flag rate.
- **Validation:** `python -m unittest discover -s tests` passed (16 tests); confirmed against the real Witsand data (`output/witsand_wind_needs_review.csv`) before and after the fix.

## 2026-08-30 - Step 5.3 Witsand Wind Subsample Anonymisation

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Discuss a strategy for anonymising the Step 5.2 augmented subsample before implementing, following the established class/contract/logging/test/docs/entry-point pattern.
- **Decisions:** `DataAnonymisation` lives in its own file (`scripts/data_anonymisation.py`), with its own new contract (`config/data_anonymisation_contract.yml`), reflecting that it is a materially distinct step from Steps 5.1/5.2. Location precision is achieved by dropping raw `latitude`/`longitude` and keeping only the already-computed `h3_level8_index` (H3 resolution 8, ~461 m average edge, a defensible match for "approximately 500 m") rather than rounding coordinates. Time precision uses 6-hour flooring of both `creation_timestamp` and `completion_timestamp`. `Unnamed: 0`, `notification_number`, and `reference_number` are dropped as direct identifiers. A k-anonymity check (minimum group size 5) over `h3_level8_index` + generalised `creation_timestamp` + `cause_code` splits the data into an anonymised CSV and a "needs review" CSV for a person to anonymise by hand, per the assessment's explicit provision for that case.
- **Privacy consideration raised during design:** The "needs review" file, by definition, contains rows that failed the k-anonymity check and are still re-identifiable. Since the assignment requires the repository to be hosted publicly, both output files are written under a new `output/` directory that is excluded via `.gitignore`, rather than being committed.
- **Work completed:** Added `DataAnonymisation`, its contract, Step 5.3 wiring in `main.py`, focused tests covering identifier/column dropping, 6-hour bucketing, and the k-anonymity split, and documentation of the method and justification.
- **Validation:** `python -m unittest discover -s tests` passed (13 tests).

## 2026-08-30 - Wind Augmentation Output Hardening

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Reviewed whether a proposed row-count check after the wind join was necessary and what else was worth considering. The user agreed two of the suggested follow-ups were worth doing (row-order preservation, physical-range sanity checks) and asked for the row-count check to be removed in favour of them.
- **Reasoning:** `pd.merge_asof` structurally cannot duplicate left rows, so a row-count check mostly guarded against a future implementation change rather than a real current failure mode. Two more likely issues were identified instead: (1) sorting the subset by timestamp before the asof join reorders the output relative to the caller's input, and `merge_asof` also drops the original index, so a naive `sort_index()` did not actually restore order; and (2) a column-detection mistake could silently feed physically impossible values (e.g. direction outside 0-360 degrees, negative speed) into the join without being caught.
- **Work completed:** Removed the row-count check. `_join_nearest` now reattaches the sorted-left index to the merge output before sorting it back, so the augmented data preserves the caller's original row order. `_parse_observations` now nulls out direction/speed values outside their physically valid ranges instead of passing them through. Replaced the row-count test with tests for row-order preservation and range nulling.
- **Validation:** `python -m unittest discover -s tests` passed (11 tests).

## 2026-08-30 - Step 5.2 Atlantis Wind Augmentation

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Implement Step 5.2 following the established class, YAML-contract, logging, documentation, test, and entry-point pattern, without hard-coding any of the Step 5.1/5.2 decisions.
- **External dependency investigation:** The README's `.ods` download handler URL returned an HTTP 404 page, and the direct CityApps `.ods` URL failed DNS resolution. The City-owned ArcGIS-hosted `Wind.xlsx` (`arcgis.com/sharing/rest/content/items/31ef242a23484e79bbb19d6b29203179/data`) was confirmed working via metadata inspection and used instead. A WAQI real-time air-quality API was considered and rejected as the wrong data type/timeframe.
- **Correction/improvement by the user:** An earlier notebook draft of the retry logic used placeholder URLs for both "primary" and "fallback" attempts and generated synthetic `np.random` weather data as a last resort. The user flagged this as unacceptable. The implemented approach instead retries the single verified URL a configurable number of times with increasing delay, and raises a clear error if every attempt fails, rather than fabricating data.
- **Decisions:** `WindDataAugmentation` lives in the same file as `FurtherDataTransformation`, and its settings live in a new `wind_augmentation` section of the existing `further_data_transformation_contract.yml` (not a separate config file), per user preference. The nearest-timestamp nature of the hourly wind data with a configurable `max_gap_hours` tolerance, so requests are not misleadingly paired with distant observations.
- **Work completed:** Added `WindDataAugmentation` and `WindAugmentationError`, the `wind_augmentation` contract section, `openpyxl` as a dependency, Step 5.2 wiring in `main.py`, focused tests covering the nearest-join tolerance and retry exhaustion, and documentation of the method.
- **Validation:** `python -m unittest tests.test_wind_data_augmentation` passed.

## 2026-08-30 - Step 5.1 Further Data Transformation

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Implement only Step 5.1 using the same reusable-class, YAML-contract, logging, documentation, test, and entry-point pattern as earlier steps.
- **Decisions:** The selected official planning suburb is `WITSAND`, which yielded 48 requests within the tested 80 m radius. The radius is a documented straight-line approximation of one minute walking. The subset stays in memory for the later Step 5.2 augmentation; no intermediate artifact is written.
- **Work completed:** Added reusable `SpatialData` point construction, refactored Step 2 to use it, and added `FurtherDataTransformation`, its contract, logging, focused tests, documentation, and Step 5.1 entry-point wiring. The official suburb is filtered by the City FeatureServer before it is downloaded. No wind-data or anonymisation work was added.

## 2026-08-30 - Server-Side Suburb Filtering Improvement

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **Correction/improvement by the user:** The initial approach loaded the full Official Suburb layer before filtering for Atlantis. The user asked to filter for Atlantis before loading the data.
- **Change:** The approach uses the City FeatureServer `where` parameter to request only the configured official suburb polygon. This reduces transfer and local processing while preserving the authoritative City source.

## 2026-08-30 - Transformation Threshold Rationale

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Record the reasoning for the selected H3 reference-match and failed-spatial-join thresholds.
- **Work completed:** Added a quantitative threshold-selection section to the transformation validation documentation. It records the observed 29 H3 differences, 3 failed joins, 26 immediate-neighbour assignments, the rejected 99.95% option, and the permitted difference and failed-join counts at the selected 99.99% and 0.01% limits.

## 2026-08-30 - Pipeline Output Labels

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Clearly print the different pipeline steps and identify which pass rates and measurements belong to each step.
- **Work completed:** Added Step 1 and Step 2 headings to the entry-point output. Extraction reports its conformance score, while transformation reports its H3 reference-match rate and failed spatial-join rate with the related counts.

## 2026-08-28

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Read the repository README for context; create this AI log; create an agent-instruction Markdown file describing the user's preferred way of working; keep both files updated as work continues.
- **Repository scope:** `ds_code_challenge` only.
- **Work completed:** Read `README.md`; confirmed the assessment's requirement for an `AI_log.md`; created `AI_log.md` and `AGENTS.md`.
- **Corrections or improvements by the user:** None yet.
- **Decisions recorded:** Work step by step, clarify uncertainty before implementation, prefer no code over uncertain code, keep the solution simple, and preserve the user's control over the approach.

## 2026-08-28 - S3 Connectivity Implementation

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User prompt:** Start implementation of the agreed first phase for Data Extraction: connect to the challenge S3 data using Python and `boto3`, then load or inspect the data before planning validation.
- **Work requested:** Check Python dependencies; install `boto3` after user approval; create a read-only connectivity check for the two GeoJSON objects; do not implement validation yet.
- **Work completed:** Confirmed Python 3.12.10; installed `boto3`; added `scripts/check_s3_connection.py`. The script reads AWS credentials from runtime environment variables, checks object metadata, reads only a 2 KB bounded preview, and does not log credential values.
- **Validation:** The script passed `py_compile`. The live S3 check is pending runtime credentials being entered directly by the user in the terminal.
- **Corrections or improvements by the user:** None yet.

## 2026-08-29 - Validation Approach

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **Approach:** Loaded the multi-resolution GeoJSON and the standalone resolution-8 GeoJSON into pandas for comparison.
- **Correction/improvement:** The initial validation was too strict because it expected identical columns and used the wrong index name. The revised approach compares the shared `properties_index` values, row counts, index uniqueness, missing indexes, and unexpected indexes. This is appropriate because the multi-resolution source contains the additional `properties_resolution` field.

## 2026-08-29 - Extraction Contract

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **Approach:** Added `config/data_extraction_contract.yml` to define the shared index column, expected resolution, allowed extra extraction column, validation checks, score weights, and the non-binary minimum score.
- **Scope:** The contract intentionally does not require identical schemas because the multi-resolution source includes `properties_resolution`.

## 2026-08-29 - Schema and Scoring Documentation

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **Approach:** Extended the YAML contract with the expected schema, field types, constraints, score components, weights, formula, and pass threshold. Added `docs/data_extraction_validation.md` as a concise human-readable explanation.
- **Validation:** The executable YAML parse check is pending because `PyYAML` is not currently installed. No additional package was installed without user approval.

## 2026-08-29 - Data Extraction Class

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **Approach:** Moved the S3 Select extraction and contract-based comparison into `scripts/data_extraction.py` as a `DataExtraction` class. The class receives an S3 client from the caller, keeps credentials outside the class, and returns only elapsed time, score, and pass/fail.
- **Validation:** The new Python file passed compilation.

## 2026-08-29 - Run Logging

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **Approach:** Added standard file logging to `DataExtraction`. Each run appends the validation component results, row counts, elapsed time, score, threshold, and pass/fail result to `logs/data_extraction.log`. Added comments explaining how the YAML contract controls the checks and how S3 Select reduces local processing.
- **Validation:** Python compilation and `git diff --check` passed.

## 2026-08-29 - Final Structure Specification

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User specification:** The notebook is for working and testing only, not the final product. The final deliverable should be Python files containing separate reusable general-purpose classes, with a separate `main.py` entry point that imports the classes and executes the workflow. The notebook may remain during development; its final submission status will be decided later.

## 2026-08-29 - Documentation Correction

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **Correction:** Updated `docs/data_extraction_validation.md` to describe only the checks currently implemented by `DataExtraction`: shared columns, row count, index coverage, and index uniqueness. Removed claims about data types, geometry constraints, and resolution checks that are defined in the YAML but not yet executed by the class.

## 2026-08-29 - Handoff Instructions

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Update `AGENTS.md` with relevant working preferences, task decisions, and implementation context so the next chat can continue with the next step.
- **Work completed:** Added concise communication preferences, notebook and final-deliverable boundaries, credential-handling guidance, current extraction architecture, validation-contract references, logging details, Git branch status, and the known credential-removal history.

## 2026-08-29 - Extraction Pipeline Gate

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Stop the pipeline when the resolution-8 extraction score is below its configured minimum and, after a successful score, use only H3 indices shared with the standalone resolution-8 reference.
- **Work completed:** Added an `ExtractionValidationError` for a below-threshold score; the entry point now exits with a clear error before downstream work can begin. The extraction result exposes only shared-index features after passing and logs missing and unexpected index counts. Updated the validation documentation and decision record.
- **Validation:** `python -m py_compile scripts\\data_extraction.py scripts\\main.py` and `python -m unittest tests\\test_data_extraction.py` passed.

## 2026-08-29 - Failure Result Output

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Print the elapsed time, score, and failed result before the program exits for a failed extraction validation.
- **Work completed:** Added elapsed time and score attributes to `ExtractionValidationError`. The entry point now prints `Time`, `Score`, and `Passed: False` before the detailed exit message. Added a unit-test assertion for the failure metrics.
- **Validation:** `python -m unittest tests\\test_data_extraction.py` passed.

## 2026-08-29 - Initial Data Transformation

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Move the explored spatial join into the final Python pipeline, using the prior pattern of a reusable class, YAML contract, logging, documentation, main entry-point wiring, and tests. The H3 reference-match rate must be in YAML.
- **Work completed:** Added `InitialDataTransformation`, which reads `sr.csv.gz`, assigns each valid coordinate to a validated Step 1 resolution-8 polygon, preserves missing or invalid coordinates as `"0"`, and validates against `sr_hex.csv.gz`. Added a YAML contract with `minimum_h3_match_rate: 99.99` and `maximum_failed_join_rate: 0.01`, logging, dependency declarations, focused tests, README run instructions, and validation documentation.
- **Decision:** The two thresholds measure different risks. The H3 reference-match rate permits the investigated immediate-neighbour boundary cases. The failed-join rate measures valid coordinates with no polygon match and remains tighter to detect spatial-join faults.
- **Validation:** `python -m py_compile scripts\\initial_data_transformation.py scripts\\main.py` and `python -m unittest discover -s tests` passed.

## 2026-08-30 - Repeatable Transformation Contract

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Make the Step 2 YAML contract more repeatable and record an instance where AI work was corrected or improved by the user.
- **Correction/improvement by the user:** The initial AI-generated contract included input names and validation thresholds, but left reproducibility-critical spatial settings hard-coded in Python. The user identified this gap and requested that these settings be made part of the contract.
- **Work completed:** Added executable YAML settings for the polygon-coordinate column, coordinate reference system, spatial predicate, valid coordinate ranges, one-polygon-match rule, comparison method, and failed-join counting rule. Updated the transformation class to read those settings and documented them.
- **Validation:** `python -m unittest tests\\test_initial_data_transformation.py` passed.

## 2026-08-30 - Measured Transformation Optimization

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User-provided result:** The optimized notebook profiling run completed in 21.59 seconds: 19.09 seconds for concurrent S3 download and CSV parsing, 2.33 seconds for point creation and spatial join, and 0.17 seconds for reference validation.
- **Outcome:** This is a 2.52-second, approximately 10.5% reduction from the 24.11-second baseline. The H3 reference-match rate remained 99.996920%, confirming that the optimization did not change the assignment result.

## 2026-08-30 - Transformation Performance Optimization

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Optimise the observed 24.11-second initial-transformation run using minimal reference columns and concurrent downloads.
- **Evidence:** Notebook profiling measured 21.78 seconds for S3 download and CSV parsing, 2.15 seconds for point creation and spatial join, and 0.18 seconds for validation. The H3 match rate remained 99.996920%.
- **Work completed:** The transformation now downloads `sr.csv.gz` and `sr_hex.csv.gz` concurrently using two configured workers. It reads all source-request fields but only `h3_level8_index` from the validation reference. The input-load duration is recorded in the transformation log.
- **Validation:** `python -m unittest tests\\test_initial_data_transformation.py` passed.

## 2026-08-30 - Transformation Outcome Reporting

- **AI/model:** GitHub Copilot
- **Token count:** Not available from the editor session.
- **User request:** Print the number of failed spatial joins and distinguish intentional `"0"` assignments for missing or invalid coordinates from failed joins and wrong non-zero H3 assignments.
- **Work completed:** The transformation result, failure exception, terminal output, and log now report separate counts for missing or invalid coordinates, failed spatial joins, and wrong H3 assignments. Documentation explains which counts affect the join-failure and H3-reference-match thresholds.
- **Validation:** `python -m unittest tests\\test_initial_data_transformation.py` passed.
