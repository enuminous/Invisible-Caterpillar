# Invisible Caterpillar Records — Album Shelf

A flat, buildless static website for Matthew Chenoweth Wright's public SoundCloud catalog. The snapshot is dated November 4, 2026.

## Included

- `index.html`: all 96 albums, each with an original literary description, cover or labeled fallback, listening link and complete ordered track list; also 14 playlists and an A–Z index.
- `tracks.html`: all 1,392 enuminous uploads, with search, artist filtering, pagination and album connections.
- `styles.css` and `app.js`: responsive design and browser-local controls.
- `catalog.json`: editable metadata, the 96 literary notes, 1,392 uploads and 76 additional recordings referenced by playlists.
- `cover-*.jpg`: 93 local images (81 album covers and 12 labeled track-art fallbacks). Three albums have no public artwork and use text panels.
- `Invisible_Caterpillar_SoundCloud_Catalog_2026-11-04.xlsx`: the catalog spreadsheet, preserved as a dated snapshot.
- `build_site.py`: optional standard-library Python script to regenerate both HTML pages after editing `catalog.json`.
- `favicon.svg`, `.nojekyll` and this README.

Every ZIP entry sits at the root. There is no enclosing directory, nested assets folder, package installation or required build step.

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
python3 build_site.py
```

That command regenerates `index.html` and `tracks.html`; it preserves CSS, JavaScript and images. It does not rescan SoundCloud or update the spreadsheet. If you change data, review dates and counts before publishing. Search and sorting are browser-local and do not alter source files.

## Source and editorial scope

Source profile: https://soundcloud.com/enuminous

Album classification, titles, track order and credits follow public SoundCloud metadata. Track uploads are not a count of distinct compositions. Some albums share recordings. Other uploaders' playlist entries are labeled and excluded from the 1,392-upload catalog and its duration.

Dates distinguish SoundCloud upload dates from supplied release dates. Eyelid/Fetish's original May 28, 2007 release is explicitly stated in its published album notes; its platform date is also retained in the JSON. An album lacking a release date is shown with its upload date. Sorting uses the labeled date shown on each card.

The 96 new literary descriptions are imaginative editorial responses to titles, track lists and published album notes. They are not claims of listening-based review, scientific validation, third-party affiliation or verified historical allegations. Original album descriptions are retained in the JSON as source material and are not automatically rendered as site copy. Catalog names and credits have not been silently corrected.

The collection contains covers and collaborations. A SoundCloud all-rights-reserved setting is not independent proof of complete ownership. The website and its metadata grant no music, image, synchronization, master-use or other third-party rights. Licensing inquiries go to Matthew via @enuminous or enuminous@gmail.com; terms are confirmed per recording.

Repository: https://github.com/enuminous/Invisible-Caterpillar

The catalog files are published at the repository root. GitHub Pages can serve this directory directly.
