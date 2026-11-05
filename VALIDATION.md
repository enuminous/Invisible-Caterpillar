# Reproducible catalog completeness validation

This is an offline, report-only extension to the existing catalog and Python site generator. It uses no external dependencies, modifies no source metadata, and does not implement or replace a Sites application. Python 3.11+ is supported.

## Source and immutable baseline

The actual input is `catalog.json`, not the spreadsheet or rendered HTML. Its top-level fields are `title`, `creator`, `source`, `snapshot_date`, `literary_note_basis`, `tracks`, `reference_tracks` and `collections`.

`baselines/catalog-2026-11-04.json` preserves the exact original bytes from [commit 4744f491a98099c58b0c18e47834f1de17cfcc8f](https://github.com/enuminous/Invisible-Caterpillar/commit/4744f491a98099c58b0c18e47834f1de17cfcc8f). Git blob: `b928ce82451af93caddab5214435b4b9d3b7b0c3`. SHA-256: `7f635b87508e2d808d74a5d4d7f8ae12ff6c021efefe6916071b669bd04f0b01`.

The adjacent manifest records the source repository, commit, blob, byte count and checksum. The tests independently pin the baseline hash and original totals. Do not overwrite this baseline when updating the active catalog. The original dated XLSX also remains unchanged.

| Input section | Meaning | November 4 rows |
| --- | --- | ---: |
| `tracks` | Uploads on account ID 7380079 (enuminous) | 1,392 |
| `reference_tracks` | Other uploaders' recordings referenced by collections | 76 |
| `collections` | 96 albums and 14 other playlists | 110 |
| `collections[].track_ids` | Ordered entries, with repetition preserved | 1,754 |

Tracks contain `id`, `title`, `artist`, `uploader`, `uploader_id`, `url`, `duration_ms`, `genre`, `uploaded_at`, `release_date`, `isrc`, `composer`, `publisher`, `label`, `license`, `tags`, `plays`, `likes` and `album_ids`. Collection credits are an unstructured list of names; they do not specify performer/producer roles. Collections retain ordered IDs, count, duration, upload/release/original dates, display-date provenance, artwork, literary notes and source descriptions.

The validator never equates account ownership with music rights. It never substitutes the uploader for an absent artist. Record identity is the numeric SoundCloud upload ID, not title text, ISRC or artist name. These IDs do not prove that two uploads contain different audio.

## Categories and successful execution

| Category | Meaning | Example |
| --- | --- | --- |
| `missing_source` | Key absent, explicit null, or empty field in the supplied export | Composer is blank; release date is null |
| `verified_error` | A schema/format violation or internal contradiction that the input itself establishes | Invalid calendar date; dangling track ID; album membership disagreement |
| `review` | An observable discrepancy or configurable heuristic requiring interpretation | Fewer than 10 plays; differing aggregate duration; shared ISRC |

Null metadata remains unknown. It is not simultaneously classified as a type error. Supplied values with incompatible types are errors. Source states `absent`, `null`, `empty` and `present` remain distinct in the JSON evidence and snapshot changes.

Exit **0** means the reports were produced; it does not mean that all fields are complete, all findings are resolved, or rights are verified. Exit **2** means execution could not finish, such as invalid JSON, duplicate JSON keys, unreadable files, invalid options or a baseline checksum mismatch. Malformed but parseable catalog structures are reported where possible. Dependent operations that lack adequate inputs are counted as skipped. Inputs and outputs may not alias one another, including through symlinks/hardlinks.

## Checks

| Check group | Executed rules | Interpretation boundary |
| --- | --- | --- |
| `schema` | Root/section/record shape; types of known fields; missing title/URL; absolute URL syntax | Coverage also records unrecognized fields; no live URL requests |
| `identity` | Positive integer IDs; duplicates within and across both track pools; duplicate collection IDs | Ambiguous identities are not silently overwritten |
| `uploader_scope` | Required uploader name/ID and agreement with the track pool | Numeric ID 7380079 determines account scope, never licensing |
| `isrc` | Missing ISRC; 12-character syntax; presentation forms; shared ISRCs; same title/artist/exact duration with different ISRCs | Normalization is for comparison only; shared audio may legitimately occur on multiple uploads; no registry or audio verification |
| `credits` | Missing artist/composer/collection credits; invalid collection credit entries; differing artist/composer metadata on a shared ISRC | Composer is not a substitute for a performer or producer; aliases are not guessed |
| `rights` | Missing license/publisher/label; type checks; differing supplied rights fields on shared ISRCs | Existing rights settings and credits are not proof of ownership or clearance |
| `membership` | Track references resolve uniquely; album references point to albums; reciprocal membership; repeated album IDs; standalone uploads | A track need not belong to a collection; playlist membership is derived from collection lists, not `album_ids` |
| `ordering` | `track_ids` array and positive IDs; `track_count` equals array length; repeated entries | Array position is the only order supplied; duplicates may be intentional; no invented positions or platform-order verification |
| `dates` | Real ISO dates/timestamps; missing release/upload/display dates; future dates; original/release/upload fallback and `date_kind` agreement | Upload date does not become an inferred release date; original release from album notes remains attributed source information |
| `duration` | Nonnegative integer milliseconds; own-upload total; declared collection duration versus all ordered entries | Every discrepancy is review-only, including small rounding differences; no tolerance silently hides source differences |
| `engagement` | Missing/invalid plays/likes; nonnegative integers; plays below configurable threshold; likes greater than plays | Low values may be accurate; counters may update at different times; zero is known data, not missing data |

ISRC syntax follows [IFPI's code structure](https://isrc.ifpi.org/isrc-standard/isrc-structure): two letters, three alphanumeric characters and seven digits. Optional printed `ISRC` prefix, spaces, hyphens and case are normalized only in a temporary comparison value. The [IFPI Handbook](https://isrc.ifpi.org/images/downloads/ISRC_Handbook.pdf) explains why the assignment year is not necessarily the release year and why a prefix does not establish the current rights owner. The validator does not check agency allocation ranges or ownership.

The report records eleven check groups with execution state, number of records examined, skipped dependent operations, finding count and outcome (`no_findings`, `findings` or `not_applicable`). A group may execute successfully while finding gaps. No finding means only that the implemented checks found none in the supplied data.

## Reproduce the current results

```bash
python3 -m unittest discover -s tests -v
python3 build_site.py --validate
```

The optional `--validate` integrates the reports into the existing generator. For inspection of incomplete or unrenderable data, run the validator separately:

```bash
python3 validate_catalog.py catalog.json \
  --baseline baselines/catalog-2026-11-04.json \
  --baseline-manifest baselines/catalog-2026-11-04.manifest.json \
  --output-dir reports
```

| Output | Contents |
| --- | --- |
| `reports/validation.json` | Versioned report, hashes, check ledger, complete findings/evidence, field coverage, entity identities and ordered collection membership |
| `reports/summary.md` | Compact execution record and coverage summary |
| `reports/issues.md` | All verified/review findings with evidence and every affected missing-field entity grouped by field/state |
| `reports/changes.json` | Identity-based comparison including raw before/after values, additions, removals, membership and order changes |
| `reports/changes.md` | Human-readable summary and complete change evidence |

JSON keys, findings and comparison identities are sorted deterministically. No clock time, local absolute path or changing network response is embedded. Same input bytes, options and validator version produce identical output bytes. Input SHA-256 hashes identify exactly which snapshots were compared; cosmetic JSON changes can change those hashes without creating semantic record changes.

`--low-plays 10` is the default: 0–9 plays generate review flags. `--low-plays 0` disables this heuristic; it does not suppress missing or invalid counters. The threshold is recorded in the result. There is no inference about expected audience, fraud, recording quality or missing plays.

## Future snapshots and ongoing comparisons

1. Obtain a new authorized source export separately. The validator does not scrape SoundCloud.
2. Keep all original field states and the separation between own uploads and other-uploaders' references. Update `snapshot_date` to the actual capture date; never use an upload date as the capture date.
3. Compare the new file with the preserved baseline (or another explicitly selected snapshot):

```bash
python3 validate_catalog.py catalog-next.json \
  --baseline baselines/catalog-2026-11-04.json \
  --baseline-manifest baselines/catalog-2026-11-04.manifest.json \
  --output-dir reports-next
```

4. Inspect `changes.md` and `issues.md`. A field changing is not a verified correction. Added or removed records describe the supplied snapshots, not confirmed publication/deletion events on SoundCloud.
5. If adopting the new snapshot, replace active `catalog.json` with that exact export and run `python3 build_site.py --validate`. Commit the active catalog, regenerated reports and HTML together. Keep the November 4 baseline and XLSX intact. The generator now reads counts and display snapshot date dynamically; it still requires renderable source metadata and album literary notes.

Comparisons join tracks across both pools by numeric ID, so a change of source pool is reported as a change rather than removal plus addition. All supplied fields, including previously unknown fields, are compared recursively. Root array ordering is ignored for identity matching. Collection `track_ids` order and multiplicity remain significant. Membership differences count occurrences, and the relative order of retained occurrences is compared separately from inserted/removed entries.

Duplicate or invalid IDs are explicitly listed as unresolved. Duplicate IDs on either side are excluded from inferred changes/additions/removals. A missing/malformed section suppresses additions/removals for that entity domain. The summary must be read alongside the unresolved lists, not as a claim of complete comparison.

## Initial execution, November 5, 2026

All eleven groups executed against the original snapshot with **zero dependent operations skipped**. Totals recompute to 1,392 uploads, 76 other-uploader references, 96 albums, 14 playlists, 1,754 entries and **132.51778694 upload hours**. Self-comparison reports zero additions, removals or changed fields.

| Result | Count |
| --- | ---: |
| Verified schema/internal-consistency errors | 0 |
| Missing-source field findings | 7,106 |
| Review findings | 827 |
| Missing ISRC fields across both track pools | 1,092 |
| Distinct syntactically valid supplied ISRCs | 376 |
| Own uploads with fewer than 10 plays | 462 |
| Records with more likes than plays | 21 |
| Uploads with no collection membership | 239 |
| Collection-duration discrepancies | 105 |

Review categories can overlap. No play counts or durations were changed. There are no supplied duplicate ISRCs or malformed ISRCs in this baseline, but both behaviors are tested with synthetic mutations. Dates without source release metadata remain unknown; artist aliases, performer credits, rights ownership and clearance cannot be established from this export.

Regression tests exercise malformed inputs; missing/null/empty distinctions; uploader identity; ISRC syntax and ambiguous reuse; credits and rights conflicts; references, counts, repeats and order; dates; duration and engagement; deterministic read-only output; baseline integrity; report-only exit behavior; comparison changes and unresolved identities; and the existing site's integration with future catalog counts.

CI executes on `push` to `main`, `pull_request` and manual `workflow_dispatch`. It uses read-only repository permissions, executes tests, generates fresh reports in the runner's temporary directory, appends the summary, checks that regenerated HTML matches the committed pages, and uploads all five reports as a commit-labeled artifact. It does not commit fixes, create GitHub issues, scan SoundCloud, send messages or schedule a separate service. CI findings do not fail the validator; failures in software tests, input decoding or site reproducibility still fail the workflow.

The existing README warning remains in force: catalog inclusion and SoundCloud rights settings do not independently establish ownership or grant licensing rights.
