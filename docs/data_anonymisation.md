# Data Anonymisation

## Step 5.3: Witsand Wind Subsample Anonymisation

The anonymisation takes the Step 5.2 augmented subsample and produces two outputs: an anonymised CSV suitable for release, and a "needs review" CSV containing rows that are still re-identifiable, intended for a person to review and generalise by hand. Neither file is committed to the repository, because the review file specifically retains fine-grained quasi-identifiers that the anonymisation step is meant to remove.

**Direct identifiers.** `Unnamed: 0` (a leftover export row index), `notification_number`, and `reference_number` are dropped outright. The latter two are per-request tracking numbers that residents can use to look up the status of their own request, making them a direct path back to a specific person.

**Location, to within approximately 500 m.** Rather than rounding latitude/longitude (which does not map predictably to a metre distance), the raw `latitude`/`longitude` columns are dropped and only the existing `h3_level8_index` is kept. H3 resolution 8 hexagons have an average edge length of about 461 m, which is a close, defensible match for "approximately 500 m" and was already computed and validated in Step 2.

**Time, to within 6 hours.** `creation_timestamp` and `completion_timestamp` are floored to 6-hour buckets (`00:00`, `06:00`, `12:00`, `18:00`), so the exact time of day is no longer recoverable, only the block it fell in.

**Residual re-identification risk.** Even after the above, a rare combination of hexagon, time bucket, and `cause_code` could still uniquely identify a single request. Because the whole Witsand subsample falls inside a single H3 cell, `h3_level8_index` alone cannot separate any two records — all of the anonymity burden falls on `creation_timestamp` and `cause_code`. To handle this, rows are grouped by `h3_level8_index`, `creation_timestamp`, and `cause_code`; a group below a minimum size of 5 is not released as-is. Rather than flagging every such row immediately, generalization is attempted first, from finest to coarsest:

1. Replace `cause_code` with the broader `cause_code_group`, and re-check the group size.
2. If still below 5, suppress the cause entirely (`"REDACTED"`) and check by location/time alone.
3. If still below 5, widen the time bucket from 6 hours to 1 day, then 7 days, then 30 days, repeating steps 1-2 at each coarser time window.

Only rows that remain below 5 even at the coarsest (30-day) window are excluded from the anonymised output and written to the review file instead. On the real Witsand subsample (76 rows), this brought the flagged count down from 71 (using only the 6-hour bucket) to 14 — most months had 5 or more requests even though most weeks did not, so the 30-day level did the majority of the rescuing. The remaining 14 rows are spread across months with only 2-3 requests all year, so even monthly generalisation cannot make them non-unique; that residual set is the expected, honest outcome for a subsample this sparse, and is exactly the provision the assessment asks for: a smaller, flagged set for a person to anonymise by hand rather than releasing it automatically.
