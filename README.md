# Invisible Caterpillar Records — Album Shelf

A flat, buildless static website for Matthew Chenoweth Wright's public SoundCloud catalog. The snapshot is dated November 4, 2026.

## Included

- `index.html`: all 96 albums, each with an original literary description, cover or labeled fallback, listening link and complete ordered track list; also 14 playlists and an A–Z index.
- `tracks.html`: all 1,392 enuminous uploads, with search, artist filtering, pagination and album connections.
- `styles.css` and `app.js`: responsive design and browser-local controls.
- `catalog.json`: editable metadata, the 96 literary notes, 1,392 uploads and 76 additional recordings referenced by playlists.
- `cover-*.jpg`: 93 local images (81 album covers and 12 labeled track-art fallbacks). Three albums have no public artwork and use text panels.
- `Invisible_Caterpillar_SoundCloud_Catalog_2026-11-04.xlsx`: the catalog spreadsheet, preserved as a dated snapshot.
- `build_site.py`: standard-library Python script to regenerate both HTML pages; `--validate` also regenerates the catalog reports. Counts and the snapshot date are read from the catalog.
- `validate_catalog.py`: offline report-only completeness checks and identity-based snapshot comparisons.
- `baselines/`: byte-preserved November 4 JSON and provenance/checksum manifest.
- `reports/`: machine-readable findings, human-readable issue report and snapshot comparison.
- `tests/` and `.github/workflows/catalog-validation.yml`: regression tests and CI artifact generation.
- `favicon.svg`, `.nojekyll` and this README.

The original site assets remain at the repository root. Validation support lives in `baselines/`, `reports/`, `tests/` and `.github/workflows/`. No package installation is required.

## Open locally

Extract the ZIP and open `index.html` in a browser. Artwork, literary notes, track lists, search and filters work locally. SoundCloud listening and external contact links require internet access. Audio recordings are not included. No external scripts, fonts or embeds are loaded.

## Put it on GitHub Pages

1. Create or open your GitHub repository.
2. Upload the extracted files to the repository root, so `index.html` is at the top level. Upload the contents, not the ZIP itself.
3. Commit them to your publishing branch (commonly `main`).
4. In **Settings → Pages → Build and deployment**, choose **Deploy from a branch**.
5. Select that branch and **/(root)**, then **Save**. GitHub will show the site's URL after deployment.

All local links are relative, so the site works at both a domain root and a GitHub project path. No custom domain or repository name is hardcoded.

GitHub's instructions: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site

## Edit the catalog

The simplest text edit is directly in `index.html`. For consistent regenerated pages, edit each collection's `literary_note` or other fields in `catalog.json`, then run:

```bash
python3 build_site.py --validate
```

That command regenerates `index.html`, `tracks.html` and `reports/`; it preserves source metadata, CSS, JavaScript and images. It does not rescan SoundCloud or update the spreadsheet. If you change data, review dates and counts before publishing. Search and sorting are browser-local and do not alter source files.

## Source and editorial scope

Source profile: https://soundcloud.com/enuminous

Album classification, titles, track order and credits follow public SoundCloud metadata. Track uploads are not a count of distinct compositions. Some albums share recordings. Other uploaders' playlist entries are labeled and excluded from the 1,392-upload catalog and its duration.

Dates distinguish SoundCloud upload dates from supplied release dates. Eyelid/Fetish's original May 28, 2007 release is explicitly stated in its published album notes; its platform date is also retained in the JSON. An album lacking a release date is shown with its upload date. Sorting uses the labeled date shown on each card.

The 96 new literary descriptions are imaginative editorial responses to titles, track lists and published album notes. They are not claims of listening-based review, scientific validation, third-party affiliation or verified historical allegations. Original album descriptions are retained in the JSON as source material and are not automatically rendered as site copy. Catalog names and credits have not been silently corrected.

The collection contains covers and collaborations. A SoundCloud all-rights-reserved setting is not independent proof of complete ownership. The website and its metadata grant no music, image, synchronization, master-use or other third-party rights. Licensing inquiries go to Matthew via @enuminous or enuminous@gmail.com; terms are confirmed per recording.

No website has been deployed by preparing this archive.

## Report-only completeness validation

Run offline with Python 3.11 or newer, from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 validate_catalog.py catalog.json \
  --baseline baselines/catalog-2026-11-04.json \
  --baseline-manifest baselines/catalog-2026-11-04.manifest.json \
  --output-dir reports
python3 build_site.py
```

See [VALIDATION.md](VALIDATION.md) for the schema, checks, interpretation, baseline provenance and future-snapshot workflow.

- [Execution summary](reports/summary.md): every executed check, scope and result.
- [Human-readable issue report](reports/issues.md): review findings and all affected missing-field entities.
- [Machine-readable validation](reports/validation.json): full findings, source-field states, coverage and entity/membership index.
- [Snapshot change report](reports/changes.md) and [machine-readable changes](reports/changes.json).

The November 5 implementation ran all 11 check groups against the November 4 snapshot: **0 verified schema/internal-consistency errors, 7,106 missing-source field findings and 827 review findings**. These are field-level counts, not counts of distinct recordings. The 1,392 uploads and 76 other-uploader references remain separate, and upload duration recomputes to **132.51778694 hours**. The unchanged snapshot compares identically to the frozen baseline.

The validator returns exit code 0 when reports are produced, including when they contain findings. Exit code 2 indicates execution/input failure (for example unreadable JSON or baseline checksum failure). It never repairs metadata or fails CI merely because a recording lacks credits, ISRCs or engagement. The test and site-build steps can still fail for software regressions or unrenderable inputs. CI runs on pushes to main, pull requests and manual dispatch, writes a job summary and uploads fresh reports as an artifact. Committed reports describe their recorded input hash; regenerate them after a catalog update. No recurring external SoundCloud scan or separate Sites application is created.
