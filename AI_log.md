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
