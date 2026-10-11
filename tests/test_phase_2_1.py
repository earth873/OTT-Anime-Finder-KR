"""Mock HTTP regressions only. These tests never authenticate to TMDB."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_tmdb
from validate_tmdb import get
from validate_v02 import refresh_live, main


class LiveResponseTests(unittest.TestCase):
    def setUp(self):
        self.rules = json.loads((ROOT / 'data/identity_rules_v0_2.json').read_text(encoding='utf-8'))
        self.sample = dict(title_ko='최애의 아이', search_title_en='Oshi No Ko')
        self.details = dict(id=203737, name='【최애의 아이】', original_name='【推しの子】',
                            first_air_date='2023-04-12', number_of_seasons=1, number_of_episodes=35,
                            seasons=[dict(id=99, season_number=1, episode_count=35)])

    def run_mock(self, responses, samples=None):
        with patch('validate_v02.get', side_effect=responses), contextlib.redirect_stdout(io.StringIO()):
            return refresh_live(samples or [self.sample], [], self.rules, 'fake-token', 0)

    def test_no_kr_data_is_not_unavailable(self):
        rows, _ = self.run_mock([self.details, {'results': {}}])
        self.assertEqual(rows[0]['provider_verification_status'], 'no_kr_data_not_unavailable')
        self.assertEqual(rows[0]['providers_kr_subscription'], '')
        self.assertEqual(rows[0]['ott_latest_episode'], '')

    def test_missing_fields_and_seasons_are_explicit(self):
        incomplete = dict(self.details)
        del incomplete['number_of_episodes']
        del incomplete['seasons']
        rows, seasons = self.run_mock([incomplete, {'results': {}}])
        self.assertEqual(rows[0]['metadata_status'], 'incomplete')
        self.assertIn('number_of_episodes', rows[0]['missing_fields'])
        self.assertIn('seasons', rows[0]['missing_fields'])
        self.assertEqual(rows[0]['season_detail_status'], 'not_collected')
        self.assertEqual(seasons, [])

    def test_invalid_provider_payload_records_partial_failure(self):
        for malformed in (None, [], {'results': None}, {'results': {'KR': []}}):
            with self.subTest(malformed=malformed):
                rows, _ = self.run_mock([self.details, malformed])
                self.assertEqual(rows[0]['error_stage'], 'providers')
                self.assertEqual(rows[0]['provider_verification_status'], 'error')
                self.assertEqual(rows[0]['match_status'], 'identity_verified')

    def test_negative_or_boolean_counts_are_not_published(self):
        for count in (-1, True, '35'):
            with self.subTest(count=count):
                rows, _ = self.run_mock([dict(self.details, number_of_episodes=count), {'results': {}}])
                self.assertEqual(rows[0]['official_episode_count'], '')
                self.assertEqual(rows[0]['metadata_status'], 'incomplete')
                self.assertIn('number_of_episodes:invalid', rows[0]['missing_fields'])

    def test_invalid_seasons_type_has_correct_error_stage(self):
        rows, _ = self.run_mock([dict(self.details, seasons={})])
        self.assertEqual(rows[0]['error_stage'], 'seasons')
        self.assertEqual(rows[0]['season_detail_status'], 'error')

    def test_bad_season_and_error_continue_to_next_title(self):
        broken = dict(self.details, seasons=[{}])
        rows, _ = self.run_mock([broken, self.details, {'results': {}}], [self.sample, self.sample])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['error_stage'], 'seasons')
        self.assertEqual(rows[0]['season_detail_status'], 'error')
        self.assertFalse(rows[1]['error_type'])

    def test_http_error_messages_do_not_leak_tokens(self):
        secret = 'mock-sensitive-value'
        failure = urllib.error.HTTPError('https://example.org', 401, secret, {}, None)
        with patch('validate_v02.get', side_effect=failure), contextlib.redirect_stdout(io.StringIO()) as output:
            rows, _ = refresh_live([self.sample], [], self.rules, secret, 0)
        self.assertNotIn(secret, output.getvalue() + str(rows))
        self.assertEqual(rows[0]['error_type'], 'HTTPError')

    def test_json_decode_failure_is_reported(self):
        rows, _ = self.run_mock([json.JSONDecodeError('synthetic invalid JSON', '', 0)])
        self.assertEqual(rows[0]['metadata_status'], 'error')
        self.assertEqual(rows[0]['error_type'], 'JSONDecodeError')

    def test_cli_splits_errors_missing_and_review(self):
        from validate_v02 import revalidate_snapshot, read_csv
        baseline = read_csv(ROOT / 'data/tmdb_results.csv')[:1]
        rows = revalidate_snapshot(baseline, self.rules, '2026-10-11T00:00:00+00:00')
        rows[0].update(error_type='TimeoutError', error_stage='providers', missing_fields='seasons')
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / 'test.csv'
            with patch.object(sys, 'argv', ['validate_v02.py', '--limit', '1', '--output', str(output)]), \
                    patch('validate_v02.revalidate_snapshot', return_value=rows), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 1)
            self.assertEqual(len(read_csv(output.with_name('test_errors.csv'))), 1)
            self.assertEqual(len(read_csv(output.with_name('test_missing.csv'))), 1)
            self.assertEqual(len(read_csv(output.with_name('test_review_required.csv'))), 1)


class HttpRetryTests(unittest.TestCase):
    def test_retry_after_invalid_negative_or_nonfinite(self):
        for header in ('-1', 'nan', 'inf'):
            with self.subTest(header=header):
                error = urllib.error.HTTPError('https://example.org', 429, 'synthetic', {'Retry-After': header}, None)
                with patch('urllib.request.urlopen', side_effect=[error, io.BytesIO(b'{}')]), patch('time.sleep') as sleep:
                    self.assertEqual(get('/test', {}, 'fake'), {})
                sleep.assert_called_once_with(1)

    def test_server_error_retries_four_times_then_raises(self):
        error = urllib.error.HTTPError('https://example.org', 503, 'synthetic', {}, None)
        with patch('urllib.request.urlopen', side_effect=error) as request, patch('time.sleep') as sleep:
            with self.assertRaises(urllib.error.HTTPError):
                get('/test', {}, 'fake')
        self.assertEqual(request.call_count, 4)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2, 4])

    def test_connection_error_retries_four_times(self):
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('synthetic')) as request, patch('time.sleep'):
            with self.assertRaises(urllib.error.URLError):
                get('/test', {}, 'fake')
        self.assertEqual(request.call_count, 4)

    def test_legacy_cli_preserves_baseline(self):
        path = ROOT / 'data/tmdb_results.csv'
        before = path.read_bytes()
        with patch.object(sys, 'argv', ['validate_tmdb.py']), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as failure:
                validate_tmdb.main()
        self.assertEqual(failure.exception.code, 2)
        self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
