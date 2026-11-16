# Evidence format and corrections

All four starting histories are synthetic. They cover 2024 term 2 through 2026 term 1, with two assessments per term and skill. Learner C has only two terms. Learner A has an uncertain handwritten score and an observation recorded late. The fictional thresholds in `reference/policy.json` require at least three terms and three reliable assessments for a sustained pattern.

## Import JSON

Create a separate learner through the interface, then choose **Import evidence**. Use a JSON array or an object whose `records` value is that array. `data/import-example.json` is a complete, working synthetic example. No learner identifier is included in each row: the authenticated request binds every record to the selected learner.

| Field | Format |
| --- | --- |
| `id` | Stable unique source ID, 1–160 characters. Never reuse it for a different assessment. |
| `kind` | `assessment`, `observation` or `attendance` |
| `skill` | `reading_comprehension`, `spatial_reasoning`, `numeracy`, `scientific_reasoning` or `writing` |
| `academic_year` | Integer, 2000–2100 |
| `term` | Integer 1, 2 or 3 |
| `observed_at` | Assessment/observation date, ISO `YYYY-MM-DD` |
| `recorded_at` | Entry date, on/after observation date. Neither date may be in the future. |
| `title` | Short description, up to 300 characters |
| `score`, `maximum` | JSON numbers with `0 <= score <= maximum`, maximum positive; both `null` for context or unscored records |
| `note` | Up to 2,000 characters of source context |
| `source` | Non-empty original-record pointer, up to 500 characters |
| `reliable` | JSON `true` or `false`; uncertain scores use `false` |

Every row must contain exactly these fields. Stable IDs and unchanged content make repeat imports idempotent. Imports are transactional: a malformed record rolls back the entire batch. A successful addition increments the learner's evidence revision and makes earlier profiles ineligible for release or download.

Calculation: each assessment becomes `100 * score / maximum`. A term average is the unweighted mean of reliable scored assessments with the same skill tag. Terms are ordered by academic year and term. High/low sustained-result checks use every term average. A trajectory observation compares the first and last average and displays all intermediate averages. This is descriptive arithmetic; it does not equate difficulty or validate the skill tag. Context notes remain visible to the teacher and do not become inferred traits.

## Correct an existing record

Do not add a second ID for a corrected version of the same quiz. That would count the assessment twice. Save the corrected row using the same `id` to a JSON file and, with `.venv` activated, run:

```bash
python -m scripts.manage correct L001 data/correction-example.json --reason "Rechecked the synthetic source scan"
```

The supplied correction example applies to a synthetic L001 record. The helper asks for the current teacher password, displays the proposed change, and requires an explicit confirmation. The server checks the learner assignment and evidence revision, validates the replacement, preserves the before/after data and correction reason in its audit, and invalidates older profiles. A concurrent change is rejected for a fresh review.

## Command-line imports

```bash
python -m scripts.manage list
python -m scripts.manage import L001 data/import-example.json
```

For real records, replace `L001` with the separate learner ID created in your workspace. Use pseudonyms and keep identity mappings in your school's existing approved system. Audit records contain source data, so protect the entire database and its backups. This demonstration has no automatic retention/deletion policy or administrative consent-withdrawal interface. Those are required operational decisions for a school pilot.

## Backups and recovery

Stop the application before copying the database directory, or use SQLite's online backup API. The default native database is `data/studio.sqlite3`; Docker uses the `studio-data` volume. Preserve the whole data directory if WAL files exist. On restart, interrupted runs become failed with a recorded explanation. The teacher starts a fresh run; any prior completed draft remains available as history.
