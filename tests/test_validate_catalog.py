import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import validate_catalog as v

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'baselines/catalog-2026-11-04.json'
MANIFEST = ROOT / 'baselines/catalog-2026-11-04.manifest.json'
BASELINE_SHA256 = '7f635b87508e2d808d74a5d4d7f8ae12ff6c021efefe6916071b669bd04f0b01'


def fixture():
    track = dict(id=1, title='Track', artist='Artist', uploader='Uploader', uploader_id=v.OWNER_ID,
                 url='https://soundcloud.com/enuminous/track', duration_ms=1000, genre='',
                 uploaded_at='2026-01-01T00:00:00Z', release_date='2025-12-01', isrc='USABC2600001',
                 composer='Composer', publisher='Publisher', label='Label', license='all-rights-reserved',
                 tags='', plays=12, likes=2, album_ids=[10])
    album = dict(id=10, title='Album', type='album', genre='', url='https://soundcloud.com/enuminous/sets/album',
                 uploaded_at='2026-01-01T00:00:00Z', release_date='2025-12-01', original_release_date=None,
                 date='2025-12-01', date_kind='Release date', duration_ms=1000, track_count=1,
                 track_ids=[1], credits=['Artist'], cover=None, artwork_source=None, artwork_source_url=None,
                 literary_note='An editorial note.', source_description='')
    return dict(snapshot_date='2026-11-04', tracks=[track], reference_tracks=[], collections=[album])


def findings(data, code=None):
    fs = v.validate(data)['findings']
    return [f for f in fs if code is None or f['code'] == code]


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.d = fixture()
        self.t = self.d['tracks'][0]
        self.a = self.d['collections'][0]

    def test_complete_fixture_has_no_findings(self):
        self.assertEqual(findings(self.d), [])
        self.assertEqual(set(v.CHECKS), {c['id'] for c in v.validate(self.d)['checks']})

    def test_missing_absent_null_empty_are_distinct_and_not_errors(self):
        del self.t['artist']
        self.t['composer'] = None
        self.t['publisher'] = ' '
        fs = findings(self.d, 'missing_source')
        states = {f['field']: f['evidence']['state'] for f in fs}
        self.assertEqual({k: states[k] for k in ('artist', 'composer', 'publisher')},
                         dict(artist='absent', composer='null', publisher='empty'))
        # Null is missing information, not automatically a contradictory source value.
        self.assertFalse(any(f['category'] == 'verified_error' for f in fs))

    def test_missing_artist_is_not_inferred_from_uploader(self):
        self.t['artist'] = ''
        before = copy.deepcopy(self.d)
        r = v.validate(self.d)
        self.assertTrue(any(f['field'] == 'artist' for f in r['findings']))
        self.assertEqual(self.d, before)

    def test_all_null_source_metadata_remains_missing_not_type_error(self):
        for field in ('artist', 'isrc', 'composer', 'publisher', 'label', 'license', 'plays', 'likes'):
            self.t[field] = None
        self.assertFalse(any(f['category'] == 'verified_error' for f in findings(self.d)))

    def test_empty_counter_or_membership_cell_is_missing_not_verified_error(self):
        self.t.update(plays='', album_ids='')
        fs = findings(self.d)
        self.assertFalse(any(f['category'] == 'verified_error' for f in fs))
        self.assertEqual({f['field'] for f in fs if f['category'] == 'missing_source'}, {'plays', 'album_ids'})

    def test_isrc_syntax_and_presentation(self):
        self.t['isrc'] = 'ISRC us-abc-26-00001'
        self.assertEqual(v.normalized_isrc(self.t['isrc']), 'USABC2600001')
        self.assertEqual(len(findings(self.d, 'isrc_presentation')), 1)
        self.assertFalse(findings(self.d, 'invalid_isrc'))
        self.t['isrc'] = 'USABC26000!1'
        self.assertEqual(len(findings(self.d, 'invalid_isrc')), 1)

    def test_isrc_year_is_not_release_year(self):
        self.t['isrc'] = 'USABC9900001'
        self.assertFalse(findings(self.d))

    def test_shared_isrc_and_conflicting_rights_are_review_only(self):
        other = copy.deepcopy(self.t)
        other.update(id=2, uploader_id=55, artist='Another artist', license='cc-by', album_ids=[])
        self.d['reference_tracks'].append(other)
        fs = findings(self.d)
        self.assertTrue(any(f['code'] == 'shared_isrc' for f in fs))
        self.assertEqual({f['field'] for f in fs if f['code'] == 'shared_isrc_metadata_conflict'}, {'artist', 'license'})
        self.assertFalse(any(f['category'] == 'verified_error' for f in fs))

    def test_matching_metadata_different_isrc_is_not_proof_of_duplicate_audio(self):
        other = copy.deepcopy(self.t)
        other.update(id=2, isrc='USABC2600002', album_ids=[])
        self.d['tracks'].append(other)
        self.assertEqual(findings(self.d, 'potential_isrc_conflict')[0]['category'], 'review')

    def test_partition_uses_numeric_uploader_not_display_name_or_artist(self):
        self.t.update(uploader_id=55, uploader='Matthew', artist='Matthew')
        r = v.validate(self.d)
        self.assertEqual(r['entities']['tracks:1']['uploader_scope'], 'other_uploader')
        self.assertEqual(r['summary']['enuminous_duration_ms'], 0)
        self.assertEqual(len(findings(self.d, 'uploader_section_conflict')), 1)

    def test_missing_uploader_does_not_become_other_uploader(self):
        del self.t['uploader_id']
        self.assertEqual(v.validate(self.d)['entities']['tracks:1']['uploader_scope'], 'unknown_uploader')
        self.assertFalse(findings(self.d, 'uploader_section_conflict'))

    def test_duplicate_ids_across_sections_do_not_silently_overwrite(self):
        other = copy.deepcopy(self.t)
        other['uploader_id'] = 55
        self.d['reference_tracks'].append(other)
        self.assertEqual(len(findings(self.d, 'duplicate_id')), 1)
        self.assertEqual(len(v.validate(self.d)['entities']), 3)
        self.assertTrue(findings(self.d, 'unresolved_track_reference'))

    def test_dangling_reference_and_reciprocal_album_membership(self):
        self.a['track_ids'] = [999]
        self.assertTrue(findings(self.d, 'unresolved_track_reference'))
        self.assertTrue(findings(self.d, 'album_membership_mismatch'))
        self.t['album_ids'] = [777]
        self.assertTrue(findings(self.d, 'invalid_album_reference'))

    def test_playlists_do_not_have_to_appear_in_album_ids(self):
        self.a['type'] = 'playlist'
        self.t['album_ids'] = []
        self.assertFalse(findings(self.d))

    def test_standalone_upload_is_review_not_error(self):
        self.d['collections'] = []
        self.t['album_ids'] = []
        self.assertEqual(findings(self.d, 'no_collection')[0]['category'], 'review')
        self.assertFalse(any(f['category'] == 'verified_error' for f in findings(self.d)))

    def test_missing_collections_cannot_establish_nonmembership(self):
        del self.d['collections']
        self.assertFalse(findings(self.d, 'no_collection'))
        self.assertFalse(findings(self.d, 'album_membership_mismatch'))

    def test_repeated_entries_are_preserved_count_mismatch_is_error(self):
        self.a.update(track_ids=[1, 1], track_count=2, duration_ms=2000)
        self.assertEqual(findings(self.d, 'repeated_entry')[0]['category'], 'review')
        self.assertFalse(findings(self.d, 'entry_count_mismatch'))
        self.a['track_count'] = 1
        self.assertEqual(findings(self.d, 'entry_count_mismatch')[0]['category'], 'verified_error')

    def test_dates_calendar_and_timezone(self):
        for value in ('2026-02-30', 'yesterday', '2026-02-03T10:00:00'):
            with self.subTest(value=value):
                self.t['release_date'] = value
                self.assertTrue(findings(self.d, 'invalid_date'))
        self.t['release_date'] = '2026-02-03T10:00:00+01:00'
        self.assertFalse(findings(self.d, 'invalid_date'))

    def test_upload_date_is_not_assumed_release_date(self):
        self.t['release_date'] = None
        self.a.update(release_date=None, date='2026-01-01', date_kind='SoundCloud upload')
        self.assertEqual(len([f for f in findings(self.d, 'missing_source') if f['field'] == 'release_date']), 2)
        self.assertFalse(findings(self.d, 'display_date_mismatch'))

    def test_original_release_overrides_platform_release_only_with_correct_label(self):
        self.a.update(original_release_date='2007-05-28', date='2007-05-28',
                      date_kind='Original release (album notes)', source_description='Released in 2007.')
        self.assertFalse(findings(self.d))
        self.a['date_kind'] = 'Release date'
        self.assertTrue(findings(self.d, 'date_kind_mismatch'))

    def test_future_date_and_duration_difference_are_review_only(self):
        self.t['release_date'] = '2027-01-01'
        self.a['duration_ms'] += 1
        self.assertEqual(findings(self.d, 'date_after_snapshot')[0]['category'], 'review')
        self.assertEqual(findings(self.d, 'collection_duration_discrepancy')[0]['category'], 'review')

    def test_missing_negative_boolean_and_low_engagement(self):
        self.t.update(plays=0, likes=1)
        r = v.validate(self.d)
        self.assertEqual(len(findings(self.d, 'low_plays')), 1)
        self.assertEqual(len(findings(self.d, 'likes_exceed_plays')), 1)
        self.assertEqual(r['summary']['findings_by_category']['verified_error'], 0)
        self.assertFalse(any(f['code'] == 'low_plays' for f in v.validate(self.d, 0)['findings']))
        for value in (-1, True, 1.5):
            self.t['plays'] = value
            self.assertTrue(findings(self.d, 'invalid_nonnegative_integer'))
        del self.t['plays']
        self.assertFalse(findings(self.d, 'low_plays'))
        self.assertTrue(any(f['field'] == 'plays' for f in findings(self.d, 'missing_source')))

    def test_empty_and_malformed_input_reports_without_crashing(self):
        for data in (None, [], {}, {'tracks': 'bad'}, {'tracks': [None, [], {'id': {}}]},
                     {'collections': [{'id': 1, 'track_ids': [{}, True], 'credits': [None]}]}):
            with self.subTest(data=data):
                r = v.validate(data)
                self.assertEqual(r['execution'], 'completed')
                self.assertTrue(r['findings'])
                json.dumps(r, allow_nan=False)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.before = fixture()
        self.after = copy.deepcopy(self.before)

    def test_identity_comparison_not_array_position(self):
        other = copy.deepcopy(self.before['tracks'][0])
        other['id'] = 2
        self.before['tracks'].append(other)
        self.after = copy.deepcopy(self.before)
        self.after['tracks'].reverse()
        self.assertEqual(v.compare(self.before, self.after)['summary']['tracks_changed'], 0)

    def test_added_removed_changed_and_unknown_fields(self):
        self.after['tracks'][0].update(plays=99, artist='', unknown_future_field={'role': 'Producer'})
        self.after['collections'] = []
        other = copy.deepcopy(self.after['tracks'][0]); other['id'] = 2
        self.after['tracks'].append(other)
        result = v.compare(self.before, self.after)
        self.assertEqual(result['summary']['tracks_added'], 1)
        self.assertEqual(result['summary']['tracks_changed'], 1)
        self.assertEqual(result['summary']['collections_removed'], 1)
        self.assertIn('/record/unknown_future_field', [x['field'] for x in result['tracks']['changed'][0]['changes']])

    def test_null_empty_and_absent_are_not_coalesced(self):
        self.before['tracks'][0]['artist'] = None
        del self.after['tracks'][0]['artist']
        c = v.compare(self.before, self.after)['tracks']['changed'][0]['changes'][0]
        self.assertEqual(c['before'], {'state': 'null', 'value': None})
        self.assertEqual(c['after'], {'state': 'absent'})
        self.after['tracks'][0]['artist'] = ''
        c = v.compare(self.before, self.after)['tracks']['changed'][0]['changes'][0]
        self.assertEqual(c['after'], {'state': 'empty', 'value': ''})

    def test_uploader_pool_move_is_change_not_add_remove(self):
        self.after['reference_tracks'] = self.after['tracks']
        self.after['tracks'] = []
        result = v.compare(self.before, self.after)
        self.assertEqual(result['summary']['tracks_changed'], 1)
        self.assertEqual(result['summary']['tracks_added'], 0)
        self.assertEqual(result['summary']['tracks_removed'], 0)

    def test_order_and_duplicate_multiplicity(self):
        self.before['collections'][0]['track_ids'] = [1, 2, 1, 3]
        self.after['collections'][0]['track_ids'] = [2, 1, 3, 4]
        c = v.compare(self.before, self.after)['collections']['changed'][0]['membership_and_order']
        self.assertTrue(c['retained_relative_order_changed'])
        self.assertEqual(c['removed_occurrences'], [{'track_id': 1, 'count': 1}])
        self.assertEqual(c['added_occurrences'], [{'track_id': 4, 'count': 1}])
        self.assertFalse(v.order_change([1, 2], [3, 1, 2])['retained_relative_order_changed'])

    def test_ambiguous_id_is_unresolved_instead_of_guessed(self):
        self.after['reference_tracks'] = copy.deepcopy(self.after['tracks'])
        r = v.compare(self.before, self.after)
        self.assertEqual(r['execution'], 'completed_with_unresolved_identities')
        self.assertEqual(r['summary']['tracks_removed'], 0)
        self.assertEqual(r['summary']['tracks_changed'], 0)
        self.assertEqual(r['tracks']['unresolved_after'][0]['id'], 1)

    def test_missing_section_does_not_imply_removal(self):
        del self.after['tracks']
        r = v.compare(self.before, self.after)
        self.assertEqual(r['tracks']['presence_comparison'], 'unresolved')
        self.assertEqual(r['summary']['tracks_removed'], 0)


class ExecutionTests(unittest.TestCase):
    def test_existing_generator_handles_future_counts_and_validation_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('build_site.py', 'validate_catalog.py'):
                (root / name).write_bytes((ROOT / name).read_bytes())
            d = fixture()
            (root / 'catalog.json').write_text(json.dumps(d))
            (root / 'baselines').mkdir()
            baseline = root / 'baselines/catalog-2026-11-04.json'
            baseline.write_bytes((root / 'catalog.json').read_bytes())
            (root / 'baselines/catalog-2026-11-04.manifest.json').write_text(json.dumps({
                'sha256': hashlib.sha256(baseline.read_bytes()).hexdigest(), 'source_commit': 'test-fixture'}))
            proc = subprocess.run([sys.executable, str(root / 'build_site.py'), '--validate'], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            page = (root / 'index.html').read_text()
            self.assertIn('1 of 1 albums', page)
            self.assertIn('reports/validation.json', page)
            self.assertIn('catalog inclusion is not a grant of rights', page)
            self.assertIn('1 of 1 tracks', (root / 'tracks.html').read_text())
            self.assertEqual(json.loads((root / 'reports/validation.json').read_text())['summary']['total_findings'], 0)

    def test_site_artist_sort_is_stable_across_process_hash_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('build_site.py', 'validate_catalog.py'):
                (root / name).write_bytes((ROOT / name).read_bytes())
            d = fixture()
            for i, artist in enumerate(('Artist', 'artist', 'ARTIST'), 1):
                track = copy.deepcopy(d['tracks'][0])
                track.update(id=i, artist=artist, album_ids=[])
                if i == 1:
                    d['tracks'] = [track]
                else:
                    d['tracks'].append(track)
            d['collections'] = []
            (root / 'catalog.json').write_text(json.dumps(d))
            outputs = []
            for seed in ('1', '2', '42'):
                proc = subprocess.run([sys.executable, str(root / 'build_site.py')],
                                      env={**os.environ, 'PYTHONHASHSEED': seed}, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                outputs.append((root / 'tracks.html').read_text())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], outputs[2])
            self.assertLess(outputs[0].index('value="ARTIST"'), outputs[0].index('value="Artist"'))
            self.assertLess(outputs[0].index('value="Artist"'), outputs[0].index('value="artist"'))

    def test_baseline_bytes_counts_partition_and_duration(self):
        self.assertEqual(hashlib.sha256(BASELINE.read_bytes()).hexdigest(), BASELINE_SHA256)
        d, _ = v.load_json(BASELINE)
        r = v.validate(d)
        s = r['summary']
        self.assertEqual(s['source_section_counts'], dict(tracks=1392, reference_tracks=76, collections=110))
        self.assertEqual((s['albums'], s['other_playlists'], s['ordered_entries']), (96, 14, 1754))
        self.assertEqual(s['uploader_scopes'], dict(enuminous_upload=1392, other_uploader=76))
        self.assertAlmostEqual(s['enuminous_duration_hours'], 132.51778694444445, places=7)
        self.assertEqual(s['findings_by_category']['verified_error'], 0)
        self.assertTrue(all(c['execution'] == 'completed' for c in r['checks']))
        self.assertTrue(all(c['dependent_operations_skipped'] == 0 for c in r['checks']))
        self.assertFalse(any(v.compare(d, d)['summary'].values()))

    def test_reports_are_deterministic_and_source_unchanged(self):
        original = BASELINE.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a', Path(tmp) / 'b'
            v.write_reports(BASELINE, a, BASELINE, MANIFEST)
            v.write_reports(BASELINE, b, BASELINE, MANIFEST)
            self.assertEqual({p.name: p.read_bytes() for p in a.iterdir()}, {p.name: p.read_bytes() for p in b.iterdir()})
        self.assertEqual(BASELINE.read_bytes(), original)

    def test_baseline_tamper_fails_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'baseline.json'; bad.write_text('{}')
            out = Path(tmp) / 'out'
            with self.assertRaisesRegex(ValueError, 'checksum'):
                v.write_reports(BASELINE, out, bad, MANIFEST)
            self.assertFalse(out.exists())

    def test_no_output_input_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'validation.json'; p.write_text(json.dumps(fixture()))
            old = p.read_bytes()
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                v.write_reports(p, tmp)
            self.assertEqual(p.read_bytes(), old)

    def test_symlink_collision_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'source.json'; p.write_text(json.dumps(fixture()))
            (Path(tmp) / 'validation.json').symlink_to(p)
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                v.write_reports(p, tmp)

    def test_duplicate_json_keys_and_nonstandard_numbers_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bad.json'
            for bad in ('{"id":1,"id":2}', '{"plays":NaN}', '{"plays":Infinity}'):
                p.write_text(bad)
                with self.assertRaises(ValueError):
                    v.load_json(p)

    def test_report_only_cli_succeeds_with_findings_invalid_json_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'input.json'
            p.write_text('{"tracks":[{"id":false}]}')
            command = [sys.executable, str(ROOT / 'validate_catalog.py'), str(p), '--output-dir', str(Path(tmp) / 'out')]
            process = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            report = json.loads((Path(tmp) / 'out/validation.json').read_text())
            self.assertGreater(report['summary']['findings_by_category']['verified_error'], 0)
            p.write_text('{broken')
            process = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(process.returncode, 2)
            self.assertIn('could not execute', process.stderr)

    def test_report_escapes_untrusted_titles_and_evidence(self):
        d = fixture(); d['tracks'][0].update(title='<script>bad()</script>\n|text|', plays=0)
        rendered = v.render_report(v.validate(d))
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn('\\|text\\|', rendered)

    def test_no_baseline_does_not_leave_stale_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            v.write_reports(BASELINE, tmp, BASELINE)
            v.write_reports(BASELINE, tmp)
            self.assertEqual(json.loads((Path(tmp) / 'changes.json').read_text())['execution'], 'not_requested')


if __name__ == '__main__':
    unittest.main()
