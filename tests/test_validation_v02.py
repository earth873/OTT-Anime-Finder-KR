import copy
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from matching import assess_identity, choose_candidate, normalize_title
from validate_v02 import read_csv, revalidate_snapshot, refresh_live
from validate_ott_episodes import validate_row
from validate_tmdb import choose
from validate_tmdb import get
from validate_v02 import main


class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = json.loads((ROOT / 'data/identity_rules_v0_2.json').read_text(encoding='utf-8'))
        cls.baseline = read_csv(ROOT / 'data/tmdb_results.csv')

    def test_korean_brackets_and_cross(self):
        self.assertEqual(normalize_title('【최애의 아이】'), normalize_title('최애의 아이'))
        self.assertEqual(normalize_title('헌터×헌터'), normalize_title('헌터x헌터'))

    def test_wrong_spinoff_rejected(self):
        old = next(r for r in self.baseline if r['query'] == '코노스바')
        self.assertEqual(assess_identity(old, self.rules['코노스바']), ('review_required', 'tmdb_id_conflict'))

    def test_identity_requires_all_signals(self):
        rule = self.rules['최애의 아이']
        row = dict(id=203737, original_name='【推しの子】', first_air_date='2023-04-12')
        self.assertEqual(assess_identity(row, rule)[0], 'identity_verified')
        for field, wrong in [('id', 1), ('original_name', '違う'), ('first_air_date', '2024-01-01')]:
            changed = dict(row, **{field: wrong})
            self.assertEqual(assess_identity(changed, rule)[0], 'review_required')

    def test_hunter_edition_remains_unresolved(self):
        old = next(r for r in self.baseline if r['query'] == '헌터×헌터')
        self.assertEqual(assess_identity(old, self.rules['헌터×헌터'])[1], 'edition_not_specified_1999_or_2011')
        old = dict(old, first_air_date='1999-10-16')
        self.assertEqual(assess_identity(old, self.rules['헌터×헌터'])[1], 'production_year_conflict')

    def test_no_first_result_fallback_or_title_confirmation(self):
        results = [dict(id=1, name='Other', original_name='Other')]
        self.assertIsNone(choose(results, 'Wanted')[0])
        results.append(dict(id=2, name='Wanted', original_name='Wanted'))
        self.assertEqual(choose(results, 'Wanted')[1], 'review_required')
        results.append(dict(id=3, name='Wanted', original_name='Wanted'))
        self.assertIsNone(choose_candidate(results, None, ['Wanted'])[0])

    def test_all_30_and_no_spinoff_metadata_leak(self):
        rows = revalidate_snapshot(self.baseline, self.rules, '2026-10-11T00:00:00+00:00')
        self.assertEqual(len(rows), 30)
        row = next(r for r in rows if r['query'] == '코노스바')
        self.assertEqual(row['tmdb_id'], '65844')
        for key in ['official_episode_count', 'season_count', 'providers_kr_subscription', 'checked_at_utc']:
            self.assertEqual(row[key], '')
        self.assertTrue(all(not r['ott_latest_episode'] for r in rows))
        other = rows[0]
        self.assertEqual(other['checked_at_utc'], self.baseline[0]['checked_at_utc'])
        self.assertEqual(other['match_status'], 'review_required')

    def test_code_geass_original_and_year(self):
        old = next(r for r in self.baseline if r['query'] == '코드 기아스')
        self.assertEqual(assess_identity(old, self.rules['코드 기아스'])[0], 'identity_verified')

    def test_live_api_and_seasons_do_not_become_ott_episodes(self):
        details = dict(id=203737, original_name='【推しの子】', name='【최애의 아이】',
                       first_air_date='2023-04-12', number_of_episodes=35, number_of_seasons=1,
                       seasons=[dict(id=99, season_number=1, episode_count=35, name='S1')])
        providers = {'results': {'KR': {'flatrate': [{'provider_name': 'Netflix'}], 'link': 'https://example.org'}}}
        with patch('validate_v02.get', side_effect=[details, providers]):
            rows, seasons = refresh_live([dict(title_ko='최애의 아이', search_title_en='Oshi No Ko')], [], self.rules, 'fake-test-token', 0)
        self.assertEqual(rows[0]['match_status'], 'identity_verified')
        self.assertEqual(rows[0]['ott_latest_episode'], '')
        self.assertEqual(seasons[0]['scope'], 'TMDB_METADATA_NOT_OTT_UPLOAD')

    def test_api_errors_are_visible_and_no_secrets_logged(self):
        with patch('validate_v02.get', side_effect=TimeoutError('secret')):
            rows, _ = refresh_live([dict(title_ko='최애의 아이', search_title_en='Oshi No Ko')], [], self.rules, 'fake', 0)
        self.assertEqual(rows[0]['error_type'], 'TimeoutError')
        self.assertNotIn('secret', str(rows))

    def test_provider_failure_preserves_identity_but_reports_error(self):
        details = dict(id=203737, original_name='【推しの子】', name='【최애의 아이】', first_air_date='2023-04-12')
        with patch('validate_v02.get', side_effect=[details, TimeoutError('hidden')]):
            rows, _ = refresh_live([dict(title_ko='최애의 아이', search_title_en='Oshi No Ko')], [], self.rules, 'fake', 0)
        self.assertEqual(rows[0]['match_status'], 'identity_verified')
        self.assertEqual(rows[0]['error_stage'], 'providers')
        self.assertEqual(rows[0]['provider_verification_status'], 'error')

    def test_transient_http_retry_after_non_numeric(self):
        error = urllib.error.HTTPError('https://example.org', 429, 'rate', {'Retry-After': 'invalid'}, None)
        with patch('urllib.request.urlopen', side_effect=[error, io.BytesIO(b'{"results": []}')]) as request, patch('time.sleep') as sleep:
            self.assertEqual(get('/search/tv', {}, 'fake'), {'results': []})
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_auth_failure_does_not_retry(self):
        error = urllib.error.HTTPError('https://example.org', 401, 'unauthorized', {}, None)
        with patch('urllib.request.urlopen', side_effect=error) as request, patch('time.sleep') as sleep:
            with self.assertRaises(urllib.error.HTTPError):
                get('/search/tv', {}, 'fake')
        self.assertEqual(request.call_count, 1)
        sleep.assert_not_called()


class ArtifactTests(unittest.TestCase):
    def test_missing_token_leaves_existing_output_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'result.csv'
            path.write_text('sentinel', encoding='utf-8')
            with patch.dict(os.environ, {'TMDB_READ_ACCESS_TOKEN': ''}), patch.object(sys, 'argv',
                    ['validate_v02.py', '--mode', 'live', '--output', str(path)]), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    main()
            self.assertEqual(exc.exception.code, 2)
            self.assertEqual(path.read_text(encoding='utf-8'), 'sentinel')

    def test_cannot_overwrite_baseline(self):
        before = (ROOT / 'data/tmdb_results.csv').read_bytes()
        with patch.object(sys, 'argv', ['validate_v02.py', '--output', str(ROOT / 'data/tmdb_results.csv')]), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main()
        self.assertEqual((ROOT / 'data/tmdb_results.csv').read_bytes(), before)

    def test_generated_artifacts_have_consistent_counts(self):
        rows = read_csv(ROOT / 'data/tmdb_revalidated_v0_2.csv')
        review = read_csv(ROOT / 'data/tmdb_revalidated_v0_2_review_required.csv')
        metrics = json.loads((ROOT / 'data/tmdb_revalidated_v0_2.metrics.json').read_text(encoding='utf-8'))
        self.assertEqual(len(rows), 30)
        self.assertEqual(len(review), metrics['review_required'])
        self.assertEqual(sum(r['match_status'] == 'identity_verified' for r in rows), metrics['identity_verified'])
        self.assertIsNone(metrics['accuracy_all_30'])

    def test_manual_queue_is_not_observations(self):
        queue = read_csv(ROOT / 'data/ott_manual_review_queue_v0_2.csv')
        self.assertEqual(len(queue), 90)
        self.assertTrue(all(r['verification_status'] == 'not_checked' and not r['source_url'] for r in queue))
        self.assertEqual(read_csv(ROOT / 'data/ott_upload_manual_v0_2.csv'), [])


class EpisodeTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(anime_id='1', season_id='1', ott_platform='Laftel', region='KR',
                        offer_type='subscription', availability_status='available',
                        latest_episode_number='12', available_episode_count='3',
                        available_episode_numbers='[1, 3, 12]', verification_status='verified',
                        source_url='https://laftel.net/item/test-fixture', verified_at='2020-01-01T00:00:00Z',
                        reviewer='test-fixture-only', source_method='official_manual',
                        evidence_reference='test-fixture-only', episode_numbering='ott_display', mapping_status='verified')

    def test_gapped_numbers_latest_is_not_count(self):
        validate_row(self.row)
        with self.assertRaises(ValueError):
            validate_row(dict(self.row, latest_episode_number='3'))

    def test_invalid_lists_counts_and_unknown_status(self):
        for changes in [dict(available_episode_numbers='[1,1,12]'), dict(available_episode_numbers='[true,3,12]'),
                        dict(available_episode_count='12'), dict(available_episode_numbers='[12,3,1]'),
                        dict(available_episode_numbers='[0,3,12]'), dict(verification_status='not_checked'),
                        dict(mapping_status='review_required'), dict(availability_status='unknown'),
                        dict(source_url='https://laftel.net.evil.example/item'), dict(reviewer=''),
                        dict(verified_at='2020-01-01'), dict(verified_at='2099-01-01T00:00:00Z')]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_row(dict(self.row, **changes))

    def test_unknown_does_not_mean_zero(self):
        row = dict(self.row, verification_status='not_checked', availability_status='unknown',
                   latest_episode_number='', available_episode_count='', available_episode_numbers='')
        validate_row(row)
        with self.assertRaises(ValueError):
            validate_row(dict(row, available_episode_count='0'))

    def test_verified_unavailable_requires_empty_list(self):
        row = dict(self.row, availability_status='unavailable', available_episode_count='0',
                   available_episode_numbers='[]', latest_episode_number='')
        validate_row(row)
        with self.assertRaises(ValueError):
            validate_row(dict(row, available_episode_numbers='[1]'))


if __name__ == '__main__':
    unittest.main()
