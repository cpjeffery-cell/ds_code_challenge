# AI Log

This file records AI-assisted work completed for the City of Cape Town Data Science Unit Code Challenge.

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
