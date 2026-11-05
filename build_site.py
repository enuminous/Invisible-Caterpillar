#!/usr/bin/env python3
"""Regenerate the two static HTML pages from catalog.json. Standard library only."""
import argparse, json, html, pathlib, datetime
from validate_catalog import write_reports

ROOT=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--validate', action='store_true', help='Also write report-only validation and baseline comparison reports')
args=parser.parse_args()
if args.validate:
    write_reports(ROOT/'catalog.json', ROOT/'reports', ROOT/'baselines/catalog-2026-11-04.json',
                  ROOT/'baselines/catalog-2026-11-04.manifest.json')
D=json.loads((ROOT/'catalog.json').read_text())
TRACKS={t['id']:t for t in D['tracks']+D['reference_tracks']}
ALBUMS=sorted([a for a in D['collections'] if a['type']=='album'],key=lambda a:a['date'],reverse=True)
PLAYLISTS=[a for a in D['collections'] if a['type']=='playlist']
ALBUM_MAP={a['id']:a for a in ALBUMS}
UPLOAD_COUNT=len(D['tracks'])
REFERENCE_COUNT=len(D['reference_tracks'])
ALBUM_COUNT=len(ALBUMS)
PLAYLIST_COUNT=len(PLAYLISTS)
UPLOAD_HOURS=sum(t['duration_ms'] for t in D['tracks'] if t['uploader_id']==7380079)/3600000
SNAPSHOT_DATE=datetime.date.fromisoformat(D['snapshot_date']).strftime('%B %d, %Y').replace(' 0', ' ')
XLSX='Invisible_Caterpillar_SoundCloud_Catalog_2026-11-04.xlsx'
e=lambda v:html.escape(str(v),quote=True)

def duration(ms):
    s=round(ms/1000);h,s=divmod(s,3600);m,s=divmod(s,60)
    return f'{h}:{m:02}:{s:02}' if h else f'{m}:{s:02}'

def external(url,label,cls=''):
    return f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer" class="{e(cls)}">{label}</a>'

def count_label(count, singular, plural=None):
    return f'{count} {singular if count==1 else (plural or singular+"s")}'

def header(page,title,description):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{e(description)}"><meta name="theme-color" content="#f4f0e8">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:type" content="website">
<title>{e(title)}</title><link rel="icon" href="favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="styles.css"><script src="app.js" defer></script>
</head><body data-page="{page}"><a class="skip" href="#main">Skip to content</a>
<header class="masthead"><div class="wrap masthead-inner"><a class="brand" href="index.html" aria-label="Invisible Caterpillar Records home"><span class="brand-mark" aria-hidden="true">ic</span><span>Invisible<br>Caterpillar Records</span></a>
<nav class="nav" aria-label="Main navigation"><a class="{'active' if page=='albums' else ''}" href="index.html#albums">Albums</a><a class="{'active' if page=='tracks' else ''}" href="tracks.html">All tracks</a><a href="index.html#about">About</a><a class="external-nav" href="https://soundcloud.com/enuminous" target="_blank" rel="noopener noreferrer">SoundCloud ↗</a></nav></div></header>'''

def footer():
    return f'''<footer class="wrap footer"><span>Invisible Caterpillar Records · Matthew Chenoweth Wright</span><span>Public catalog snapshot · {SNAPSHOT_DATE} · <a href="#top">Back to top ↑</a></span></footer></body></html>'''

def tracklist(a):
    items=[]
    for tid in a['track_ids']:
        t=TRACKS[tid]
        credit=f'<span class="external-credit">Other uploader · {e(t["uploader"])}</span>' if t['uploader_id']!=7380079 else ''
        items.append(f'<li><span>{external(t["url"],e(t["title"]))}{credit}</span><span class="time">{duration(t["duration_ms"])}</span></li>')
    return f'<details class="tracklist"><summary>{count_label(len(items),"track")} · View track list</summary><ol>'+''.join(items)+'</ol></details>'

def album_card(a,i):
    date=datetime.date.fromisoformat(a['date'])
    label='Original release' if a['original_release_date'] else ('Released' if a['release_date'] else 'Uploaded')
    date_label=f'{label} {date.strftime("%b %d, %Y")}'
    top=date_label+(' · '+a['genre'] if a['genre'] else '')
    if a['cover']:
        art=f'<img src="{e(a["cover"])}" width="500" height="500" loading="lazy" decoding="async" alt="{e(a["title"])} — {"album" if a["artwork_source"]=="album_art" else "track"} artwork">'
        art=external(a['url'],art)
        if a['artwork_source']=='track_art':art+='<figcaption class="art-tag">Artwork from an album track</figcaption>'
    else:
        art=f'<div class="type-cover variant-{i%3}"><span class="cover-small">Invisible Caterpillar Records</span><span class="cover-title">{e(a["title"])}</span><span class="cover-small">No published artwork</span></div>'
    credits=' · '.join(a['credits'])
    credit_line=f'<p class="credits">Track credits: {e(credits)}</p>' if credits else ''
    search=' '.join([a['title'],a['literary_note'],a['genre'],credits]+[TRACKS[t]['title'] for t in a['track_ids']])
    return f'''<article class="album-card" id="album-{a['id']}" data-title="{e(a['title'])}" data-date="{a['date']}" data-year="{a['date'][:4]}" data-search="{e(search)}">
<figure class="album-art">{art}</figure><div class="album-topline">{e(top)}</div>
<h3><a href="#album-{a['id']}">{e(a['title'])}</a></h3><p class="literary">{e(a['literary_note'])}</p>{credit_line}
<div class="album-actions">{external(a['url'],'Listen on SoundCloud ↗')}<span>{count_label(a['track_count'],'track')} · {duration(a['duration_ms'])}</span></div>{tracklist(a)}</article>'''

def about():
    return f'''<section class="about" id="about"><div><div class="eyebrow">The label</div><h2>Many names.<br>One improbable record shelf.</h2>
<p>Invisible Caterpillar Records is the musical world of Matthew Chenoweth Wright: eNuminous &amp; Archimedes, Millie Sievert and The Radioactive Five, Faust Jones and The Chronologically Impaired, and a growing cast of collaborators and invented ensembles.</p>
<p>Explore the albums, follow a title into unfamiliar territory, or browse every public upload in the <a href="tracks.html">track catalog</a>.</p></div>
<div><div class="eyebrow">Inquiries &amp; licensing</div><p>Have a project in mind? Name the recording and tell us how you would like to use it. Availability and rights are confirmed for each recording.</p><p class="contact"><a href="https://x.com/enuminous" target="_blank" rel="noopener noreferrer">@enuminous ↗</a></p><p><a href="mailto:enuminous@gmail.com">enuminous@gmail.com</a></p>
<div class="downloads"><a href="{XLSX}" download>Download spreadsheet ↓</a><a href="catalog.json" download>Catalog data ↓</a><a href="reports/validation.json" download>Validation data ↓</a><a href="reports/issues.md" download>Issue report ↓</a></div>
<details><summary>About the catalog &amp; literary notes</summary><p>These original literary notes respond to album titles, track lists and published album notes. They are imaginative editorial descriptions, not audio-listening reviews. Album labels and artist credits follow SoundCloud metadata; upload and release dates are distinguished. Eyelid/Fetish's original 2007 date comes from its album notes.</p><p>The {UPLOAD_COUNT:,} uploads are those on the enuminous account. Playlists also reference {REFERENCE_COUNT} distinct recordings from other uploaders, labeled in their track lists and excluded from the upload total. Covers and collaborations retain their published titles and credits; catalog inclusion is not a grant of rights.</p><p>Most illustrations are album covers. Where an album has no cover, a track image is labeled as such; {sum(not a['cover'] for a in ALBUMS)} albums use text panels. Public metadata was collected {SNAPSHOT_DATE}. <a href="https://soundcloud.com/enuminous" target="_blank" rel="noopener noreferrer">Original SoundCloud catalog ↗</a></p></details></div></section>'''

hero_ids=[aid for aid in [1036118158,2204001416,2116330169] if aid in ALBUM_MAP and ALBUM_MAP[aid]['cover']]
sleeves=''.join(f'<a class="sleeve" href="#album-{aid}" aria-label="Explore {e(ALBUM_MAP[aid]["title"])}"><img src="{e(ALBUM_MAP[aid]["cover"])}" width="500" height="500" alt="{e(ALBUM_MAP[aid]["title"])}"></a>' for aid in hero_ids)
years=sorted({a['date'][:4] for a in ALBUMS},reverse=True)
year_options=''.join(f'<option value="{y}">{y}</option>' for y in years)
index_links=''.join(f'<a href="#album-{a["id"]}">{e(a["title"])}</a>' for a in sorted(ALBUMS,key=lambda a:a['title'].casefold()))
cards=''.join(album_card(a,i) for i,a in enumerate(ALBUMS))
playlist_cards=''.join(f'<article class="playlist" id="playlist-{a["id"]}"><h3>{external(a["url"],e(a["title"])+" ↗")}</h3><p>{count_label(a["track_count"],"entry","entries")} · {duration(a["duration_ms"])} · SoundCloud playlist</p>{tracklist(a)}</article>' for a in PLAYLISTS)
index=header('albums','Invisible Caterpillar Records — The Album Shelf',f'Explore {ALBUM_COUNT} albums with literary notes, artwork and complete track lists from Invisible Caterpillar Records.')+f'''
<main class="wrap" id="main"><section class="hero" id="top"><div><div class="eyebrow">An independent universe in sound</div><h1>A record shelf<br>for the <em>improbable.</em></h1><p class="hero-copy">Time-traveling chanteuses. Circuit collaborators. Mathematics at the dinner table. {ALBUM_COUNT} albums, and many ways to get lost.</p><p class="byline">The musical worlds of Matthew Chenoweth Wright.</p><a class="hero-action" href="#albums">Explore the album shelf ↓</a></div><div class="sleeves">{sleeves}<span class="sleeve-label">A few doors into the collection</span></div></section>
<section class="stats" aria-label="Catalog totals"><div class="stat"><strong>{ALBUM_COUNT}</strong><span>Albums</span></div><div class="stat"><strong>{UPLOAD_COUNT:,}</strong><span>Track uploads</span></div><div class="stat"><strong>{UPLOAD_HOURS:.1f}</strong><span>Hours of recordings</span></div><div class="stat"><strong>{PLAYLIST_COUNT}</strong><span>Playlists</span></div></section>
<section id="albums" aria-labelledby="albums-heading"><div class="section-head"><h2 id="albums-heading">The album shelf.</h2><p>Literary notes, cover art &amp; every track in order.</p></div>
<div class="controls"><div class="control search-control"><label for="album-search">Search the shelf</label><input type="search" id="album-search" placeholder="Album, track, artist or phrase…" autocomplete="off"></div><div class="control"><label for="album-year">Catalog year</label><select id="album-year"><option value="">All years</option>{year_options}</select></div><div class="control"><label for="album-sort">Order</label><select id="album-sort"><option value="newest">Newest date first</option><option value="oldest">Oldest date first</option><option value="az">A–Z by title</option></select></div><button class="reset" id="reset-albums" type="button">Clear filters</button></div>
<div class="browse-meta"><span id="album-count" role="status" aria-live="polite">{ALBUM_COUNT} of {ALBUM_COUNT} albums</span><a href="#playlists">Go to playlists ↓</a></div>
<details class="index-jump" id="alphabetical-index"><summary>Open the A–Z album index</summary><nav class="jump-links" aria-label="Alphabetical album index">{index_links}</nav></details>
<noscript>All albums and track lists are available below. Search and sorting require JavaScript.</noscript><p class="empty-state" id="no-albums" hidden>No albums match. Try another title, artist or phrase.</p><div class="album-grid" id="album-grid">{cards}</div></section>
<section id="playlists" aria-labelledby="playlists-heading"><div class="section-head"><h2 id="playlists-heading">The mixtape shelf.</h2><p>{PLAYLIST_COUNT} playlists. Other uploaders are identified in the track lists.</p></div><div class="playlist-grid">{playlist_cards}</div></section>{about()}</main>'''+footer()
(ROOT/'index.html').write_text(index,encoding='utf8')

artist_options=''.join(f'<option value="{e(a)}">{e(a)}</option>' for a in sorted({t['artist'] for t in D['tracks'] if t['artist']},key=lambda value:(value.casefold(), value)))
rows=[]
for t in D['tracks']:
    albums=[ALBUM_MAP[a] for a in t['album_ids']]
    album_links=''.join(f'<a href="index.html#album-{a["id"]}">{e(a["title"])}</a>' for a in albums) or 'No album listed'
    search=' '.join([t['title'],t['artist'],t['genre'],t['isrc']]+[a['title'] for a in albums])
    rows.append(f'''<tr data-title="{e(t['title'])}" data-artist="{e(t['artist'])}" data-date="{e(t['uploaded_at'])}" data-search="{e(search)}"><td>{external(t['url'],e(t['title']),'song-title')}<span class="genre">{e(t['genre'] or 'Genre not supplied')}</span></td><td class="artist" data-label="Artist">{e(t['artist'] or 'Not supplied')}</td><td class="duration" data-label="Duration">{duration(t['duration_ms'])}</td><td data-label="Uploaded">{e(t['uploaded_at'][:10])}</td><td class="album-links" data-label="Albums">{album_links}</td></tr>''')
tracks_page=header('tracks','All Tracks — Invisible Caterpillar Records',f'Search all {UPLOAD_COUNT:,} public uploads by title, artist, album, genre or ISRC.')+f'''
<main class="wrap" id="main"><section class="tracks-hero" id="top"><div class="eyebrow">The complete upload catalog</div><h1>Every strange thread.</h1><p>All {UPLOAD_COUNT:,} public uploads from the enuminous account, with album connections and direct listening links. Search by title, artist, genre, album or ISRC.</p></section>
<div class="controls track-controls" id="tracks-start"><div class="control search-control"><label for="track-search">Search all tracks</label><input type="search" id="track-search" placeholder="A title, an artist, a fragment…" autocomplete="off"></div><div class="control"><label for="track-artist">Published artist credit</label><select id="track-artist"><option value="">All artist credits</option><option value="__blank__">Not supplied</option>{artist_options}</select></div><div class="control"><label for="track-sort">Order</label><select id="track-sort"><option value="newest">Newest upload first</option><option value="az">A–Z by title</option></select></div><button class="reset" type="button" id="reset-tracks">Clear filters</button></div>
<div class="browse-meta"><span role="status" aria-live="polite" id="track-count">{UPLOAD_COUNT:,} of {UPLOAD_COUNT:,} tracks</span><a href="{XLSX}" download>Download spreadsheet ↓</a></div><noscript>All {UPLOAD_COUNT:,} tracks are listed below. Search, artist filtering and pagination require JavaScript.</noscript>
<p class="empty-state" id="no-tracks" hidden>No tracks match. Try another phrase or clear the artist filter.</p><table class="track-table"><thead><tr><th scope="col">Track</th><th scope="col">Artist metadata</th><th scope="col">Duration</th><th scope="col">Uploaded (UTC)</th><th scope="col">Album membership</th></tr></thead><tbody id="track-body">{''.join(rows)}</tbody></table>
<nav class="pager" aria-label="Track pages"><button type="button" id="previous-page">← Previous</button><span id="page-number" role="status">All tracks</span><button type="button" id="next-page">Next →</button></nav></main>'''+footer()
(ROOT/'tracks.html').write_text(tracks_page,encoding='utf8')
assert all(a['literary_note'] for a in ALBUMS)
print(f'Built index.html with {ALBUM_COUNT} literary descriptions and tracks.html with {UPLOAD_COUNT} uploads.')
