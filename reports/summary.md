# Catalog completeness report

Snapshot: 2026-11-04. Validator: 1.0.0. Execution: completed.

**Report-only. Successful execution is not a completeness or licensing certificate.**

Uploads: 1392; other-uploader reference section: 76; albums: 96; other playlists: 14; ordered entries: 1754.

enuminous upload duration: 132.51778694 hours (1392 records).

| Finding category | Count |
| --- | ---: |
| verified_error | 0 |
| missing_source | 7106 |
| review | 827 |

## Checks executed

Counts are records examined, not individual assertions. Skips are dependent operations whose inputs were unavailable or ambiguous.

| Check | Records | Skipped operations | Findings | Outcome |
| --- | ---: | ---: | ---: | --- |
| schema — Object/list shape, field types, titles and source URLs | 1579 | 0 | 0 | no_findings |
| identity — Positive integer IDs and duplicate identities across source sections | 1578 | 0 | 0 | no_findings |
| uploader_scope — enuminous uploads versus other uploaders by numeric account ID | 1468 | 0 | 0 | no_findings |
| isrc — Missing ISRC, syntax, presentation and potential cross-record inconsistencies | 1468 | 0 | 1092 | findings |
| credits — Artist/composer information and collection credits | 1578 | 0 | 1778 | findings |
| rights — Available license, publisher and label metadata (not ownership verification) | 1468 | 0 | 2907 | findings |
| membership — Resolvable collection references and reciprocal album membership | 1578 | 0 | 239 | findings |
| ordering — Ordered track ID arrays, entry counts and repeated entries | 110 | 0 | 0 | no_findings |
| dates — Date syntax, release-date gaps and display-date provenance | 1579 | 0 | 1329 | findings |
| duration — Nonnegative durations, upload totals and collection duration discrepancies | 1578 | 0 | 105 | findings |
| engagement — Missing/invalid counters, low plays and likes exceeding plays | 1468 | 0 | 483 | findings |

## Finding meanings

Counts below are field-level findings, not counts of distinct recordings.

| Category / code | Count | Interpretation |
| --- | ---: | --- |
| missing\_source / missing\_source | 7106 | Source field is absent, null or empty; no replacement inferred. |
| review / collection\_duration\_discrepancy | 105 | Collection duration differs from the sum of listed tracks; rounding, source timing or unavailable entries may explain it. |
| review / likes\_exceed\_plays | 21 | Counter discrepancy for review; platform counters need not be synchronized. |
| review / low\_plays | 462 | Below the configured review threshold; low play counts may be accurate. |
| review / no\_collection | 239 | No listed collection contains this upload; it may be a standalone recording. |

## Interpretation and limits

- Only supplied JSON is inspected; no live SoundCloud rescan, audio analysis or registry lookup.
- Missing_source means absent, null or empty in this export; the original platform may have more information.
- Verified_error means a schema/format violation or internal contradiction, not a verified fact about a recording.
- Review findings are heuristics or discrepancies; low plays, repeated entries and shared ISRCs can be legitimate.
- ISRC syntax does not verify assignment. SoundCloud track IDs identify uploads, not necessarily unique masters or compositions.
- Collection order is the supplied track_ids array (positions start at 1); actual SoundCloud order is not independently verified.
- Artists, composers and uploader names are separate roles. Missing artists are never replaced with the uploader.
- The snapshot has no dedicated performer/producer, master-owner, permission, contract or clearance fields. Free text is not treated as verified evidence.
- Catalog inclusion, ISRCs, uploader identity and SoundCloud rights settings do not independently establish ownership or grant licensing rights.
- No source fields are changed, guessed or filled. Report completion and CI success do not certify catalog completeness or rights.

## Source-field coverage

An absent key differs from an explicit null or empty value. All source fields and per-entity findings are in validation.json.

| Section | Field | Absent | Null | Empty | Present |
| --- | --- | ---: | ---: | ---: | ---: |
| tracks | album_ids | 0 | 0 | 321 | 1071 |
| tracks | artist | 0 | 0 | 469 | 923 |
| tracks | composer | 0 | 0 | 1199 | 193 |
| tracks | duration_ms | 0 | 0 | 0 | 1392 |
| tracks | genre | 0 | 0 | 61 | 1331 |
| tracks | id | 0 | 0 | 0 | 1392 |
| tracks | isrc | 0 | 0 | 1039 | 353 |
| tracks | label | 0 | 0 | 1391 | 1 |
| tracks | license | 0 | 0 | 0 | 1392 |
| tracks | likes | 0 | 0 | 0 | 1392 |
| tracks | plays | 0 | 0 | 0 | 1392 |
| tracks | publisher | 0 | 0 | 1391 | 1 |
| tracks | release_date | 0 | 1223 | 0 | 169 |
| tracks | tags | 0 | 0 | 1279 | 113 |
| tracks | title | 0 | 0 | 0 | 1392 |
| tracks | uploaded_at | 0 | 0 | 0 | 1392 |
| tracks | uploader | 0 | 0 | 0 | 1392 |
| tracks | uploader_id | 0 | 0 | 0 | 1392 |
| tracks | url | 0 | 0 | 0 | 1392 |
| reference_tracks | album_ids | 0 | 0 | 76 | 0 |
| reference_tracks | artist | 0 | 0 | 41 | 35 |
| reference_tracks | composer | 0 | 0 | 55 | 21 |
| reference_tracks | duration_ms | 0 | 0 | 0 | 76 |
| reference_tracks | genre | 0 | 0 | 7 | 69 |
| reference_tracks | id | 0 | 0 | 0 | 76 |
| reference_tracks | isrc | 0 | 0 | 53 | 23 |
| reference_tracks | label | 0 | 0 | 62 | 14 |
| reference_tracks | license | 0 | 0 | 0 | 76 |
| reference_tracks | likes | 0 | 0 | 0 | 76 |
| reference_tracks | plays | 0 | 0 | 0 | 76 |
| reference_tracks | publisher | 0 | 0 | 63 | 13 |
| reference_tracks | release_date | 0 | 56 | 0 | 20 |
| reference_tracks | tags | 0 | 0 | 26 | 50 |
| reference_tracks | title | 0 | 0 | 0 | 76 |
| reference_tracks | uploaded_at | 0 | 0 | 0 | 76 |
| reference_tracks | uploader | 0 | 0 | 0 | 76 |
| reference_tracks | uploader_id | 0 | 0 | 0 | 76 |
| reference_tracks | url | 0 | 0 | 0 | 76 |
| collections | artwork_source | 0 | 17 | 0 | 93 |
| collections | artwork_source_url | 0 | 17 | 0 | 93 |
| collections | cover | 0 | 17 | 0 | 93 |
| collections | credits | 0 | 0 | 14 | 96 |
| collections | date | 0 | 0 | 0 | 110 |
| collections | date_kind | 0 | 0 | 0 | 110 |
| collections | duration_ms | 0 | 0 | 0 | 110 |
| collections | genre | 0 | 0 | 15 | 95 |
| collections | id | 0 | 0 | 0 | 110 |
| collections | literary_note | 0 | 0 | 14 | 96 |
| collections | original_release_date | 0 | 109 | 0 | 1 |
| collections | release_date | 0 | 50 | 0 | 60 |
| collections | source_description | 0 | 0 | 65 | 45 |
| collections | title | 0 | 0 | 0 | 110 |
| collections | track_count | 0 | 0 | 0 | 110 |
| collections | track_ids | 0 | 0 | 0 | 110 |
| collections | type | 0 | 0 | 0 | 110 |
| collections | uploaded_at | 0 | 0 | 0 | 110 |
| collections | url | 0 | 0 | 0 | 110 |

## Provenance

```json
{
  "baseline_manifest_verified": true,
  "baseline_sha256": "7f635b87508e2d808d74a5d4d7f8ae12ff6c021efefe6916071b669bd04f0b01",
  "baseline_source_commit": "4744f491a98099c58b0c18e47834f1de17cfcc8f",
  "catalog_sha256": "7f635b87508e2d808d74a5d4d7f8ae12ff6c021efefe6916071b669bd04f0b01"
}
```
