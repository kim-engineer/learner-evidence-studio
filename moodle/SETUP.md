# Moodle connection

This is an optional **external REST importer**, not a Moodle plugin. It requires no changes to Moodle core, the earlier `local_aichat` plugin, PHP settings or the Moodle database schema. Gemini is configured on the Studio server, not through Azure.

## Compatibility evidence

The original Microsoft repository specifies Moodle 4.2+ and identifies 4.5 as its tested version. This rebuild reads the existing `gradereport_user_get_grade_items` service. The service implementation and returned fields were checked in Moodle's official `MOODLE_402_STABLE` and `MOODLE_405_STABLE` source. A mocked HTTP contract test covers mapping and numeric grades. No live Moodle server, token or course was supplied, so live 4.2/4.5 integration is not claimed as passed. Moodle versions after 4.5 are not certified by this package.

## Configure the service

1. On your Moodle instance, enable web services and the REST protocol through Site administration.
2. Create a restricted external service with only `gradereport_user_get_grade_items`. Authorise a dedicated teacher/service user for the intended course, and create its token.
3. That user needs web-service access, `gradereport/user:view`, and `moodle/grade:viewall` in the relevant course to read another learner's report. Course/group visibility restrictions still apply. Do not use a site-administrator token as a shortcut.
4. In the Studio `.env`, set `MOODLE_URL` to the HTTPS root URL of your Moodle installation, including its subdirectory if any, and set `MOODLE_TOKEN`. Restart Studio. Credentials are server-side and are excluded from submitted traces.
5. Create a separate pseudonymous learner in Studio. Keep the identity mapping to the Moodle user ID within your school.

## Map assessments explicitly

Edit a copy of `moodle/import-map.example.json` using your real **numeric Moodle user, course and grade-item IDs**. These are deployment inputs, not missing program code. A grade-item ID is not a course-module ID. Inspect the user grade report through your Moodle service's API documentation/test client to obtain the item IDs.

For each item choose a reviewed skill tag and its actual assessment date. Set the academic year and term for that batch. Import different terms as separate batches. The importer does not infer a learning skill from a course name or mistake the current import date for the assessment date.

With the Studio running and its Python environment activated:

```bash
python -m scripts.manage list
python -m scripts.manage moodle L001 moodle/import-map.example.json
```

Use your newly created learner ID instead of `L001` for real records. The helper signs into Studio, shows the proposed mappings and requests confirmation of consent before importing. The example IDs are fictional and are not expected to exist on your Moodle site.

Only explicit, visible, current activity grades with numeric ranges are accepted. Course/category totals are excluded to avoid double counting. Ordinal scales, ungraded items, hidden grades and grades needing recalculation are rejected. Scores with a nonzero minimum are normalised to `graderaw - grademin`, with maximum `grademax - grademin`. The graded timestamp is retained as the recorded date, bounded below by the teacher-supplied assessment date.

Each source ID includes a hash of the configured Moodle root plus course, user and grade-item IDs. Re-importing identical data does not duplicate it. A changed grade is rejected as a conflicting existing source; use the documented correction operation after reviewing the change. Never create a new source ID merely to bypass that check.

## Validation before a pilot

Use a synthetic/test learner on your own Moodle version first. Compare imported values against its gradebook, confirm permissions and course/group restrictions, verify the dates and mappings with a teacher, repeat the import to confirm idempotency, and test a changed-grade correction. This package never writes grades back to Moodle.
