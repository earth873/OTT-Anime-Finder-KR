#!/usr/bin/env python3
"""v0.2: audited offline revalidation or authenticated TMDB refresh (stdlib)."""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from matching import assess_identity, choose_candidate
from validate_tmdb import HEADERS, ROOT, get

EXTRA = ['display_title_ko', 'previous_tmdb_id', 'previous_match_status',
         'identity_reason', 'identity_source_url', 'metadata_origin', 'metadata_status',
         'provider_verification_status', 'season_detail_status', 'season_mapping_status',
         'revalidated_at_utc', 'error_stage', 'error_type']
SEASON_HEADERS = ['query', 'tmdb_id', 'tmdb_season_id', 'tmdb_season_number',
                  'season_name', 'official_episode_count', 'air_date', 'source_url',
                  'checked_at_utc', 'scope', 'ott_mapping_status']


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, headers, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, headers)
        w.writeheader()
        w.writerows(rows)
    temporary.replace(path)


def revalidate_snapshot(baseline, rules, now):
    rows = []
    for old in baseline:
        row = {key: old.get(key, '') for key in HEADERS}
        row.update(dict.fromkeys(EXTRA, ''))
        rule = rules.get(old['query'])
        status, reason = assess_identity(old, rule)
        row.update(previous_tmdb_id=old['tmdb_id'], previous_match_status=old['match_status'],
                   match_status=status, identity_reason=reason, display_title_ko=old['query'],
                   identity_source_url=rule['source_url'] if rule else '',
                   metadata_origin='v0.1_snapshot', metadata_status='historical_not_refreshed',
                   provider_verification_status='historical_series_hint_not_current_verified',
                   season_detail_status='not_collected', season_mapping_status='review_required',
                   revalidated_at_utc=now, ott_latest_episode='', ott_episode_verification='NOT_CHECKED')
        if rule and rule.get('display_title_ko'):
            row['display_title_ko'] = rule['display_title_ko']
        # An independently researched replacement identity must not inherit another work's data.
        if old['query'] == '코노스바' and old['tmdb_id'] != str(rule['tmdb_id']):
            for key in ('first_air_date', 'season_count', 'official_episode_count',
                        'production_status', 'provider_source_url', 'checked_at_utc',
                        'providers_kr_subscription', 'providers_kr_rent', 'providers_kr_buy'):
                row[key] = ''
            row.update(tmdb_id=str(rule['tmdb_id']), matched_title=rule['display_title_ko'],
                       original_name=rule['original_names'][0],
                       match_status='identity_verified', identity_reason='wrong_spinoff_replaced_by_public_reference',
                       tmdb_url=f"https://www.themoviedb.org/tv/{rule['tmdb_id']}",
                       metadata_origin='public_identity_reference_only', metadata_status='not_collected',
                       provider_verification_status='not_checked', match_candidates='')
        rows.append(row)
    return rows


def refresh_live(samples, baseline, rules, token, delay):
    old_by_title = {r['query']: r for r in baseline}
    rows, seasons = [], []
    for sample in samples:
        ko, en = sample['title_ko'], sample['search_title_en']
        old = old_by_title.get(ko, {})
        rule = rules.get(ko)
        row = dict.fromkeys(HEADERS + EXTRA, '')
        row.update(query=ko, display_title_ko=(rule or {}).get('display_title_ko', ko),
                   previous_tmdb_id=old.get('tmdb_id', ''), previous_match_status=old.get('match_status', ''),
                   provider_scope='TV_SERIES_KR_NOT_EPISODE', ott_episode_verification='NOT_CHECKED',
                   metadata_origin='tmdb_live_api', metadata_status='not_collected',
                   provider_verification_status='not_checked', season_detail_status='not_collected',
                   season_mapping_status='review_required', identity_source_url=(rule or {}).get('source_url', ''),
                   revalidated_at_utc=datetime.now(timezone.utc).isoformat())
        stage = 'identity'
        try:
            if rule:
                candidate = get(f"/tv/{rule['tmdb_id']}", {'language': 'ko-KR'}, token)
                status, reason = assess_identity(candidate, rule)
            else:
                found = []
                for title, lang in ((en, 'en-US'), (ko, 'ko-KR')):
                    found.extend(get('/search/tv', {'query': title, 'language': lang,
                                     'include_adult': 'false'}, token).get('results', []))
                row['match_candidates'] = len({r['id'] for r in found})
                candidate, status, reason = choose_candidate(found, None, [en, ko])
                if candidate:
                    candidate = get(f"/tv/{candidate['id']}", {'language': 'ko-KR'}, token)
                    status, reason = assess_identity(candidate, None)
            row.update(match_status=status, identity_reason=reason)
            if candidate:
                cid = candidate['id']
                observed = datetime.now(timezone.utc).isoformat()
                row.update(tmdb_id=cid, matched_title=candidate.get('name', ''),
                           original_name=candidate.get('original_name', ''),
                           first_air_date=candidate.get('first_air_date', ''),
                           season_count=candidate.get('number_of_seasons', ''),
                           official_episode_count=candidate.get('number_of_episodes', ''),
                           production_status=candidate.get('status', ''),
                           tmdb_url=f'https://www.themoviedb.org/tv/{cid}',
                           checked_at_utc=observed, metadata_status='collected', season_detail_status='collected')
                for season in candidate.get('seasons', []):
                    seasons.append(dict(query=ko, tmdb_id=cid, tmdb_season_id=season['id'],
                                        tmdb_season_number=season['season_number'], season_name=season.get('name', ''),
                                        official_episode_count=season.get('episode_count', ''), air_date=season.get('air_date') or '',
                                        source_url=f"https://www.themoviedb.org/tv/{cid}/season/{season['season_number']}",
                                        checked_at_utc=observed, scope='TMDB_METADATA_NOT_OTT_UPLOAD', ott_mapping_status='review_required'))
                stage = 'providers'
                providers = get(f'/tv/{cid}/watch/providers', {}, token).get('results', {}).get('KR', {})
                row.update(provider_source_url=providers.get('link', ''),
                           provider_verification_status='series_hint_not_episode_verified')
                for field, source in [('providers_kr_subscription', 'flatrate'),
                                      ('providers_kr_rent', 'rent'), ('providers_kr_buy', 'buy')]:
                    row[field] = ' | '.join(sorted({p['provider_name'] for p in providers.get(source, [])}))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
            # Keep partial metadata, never emit request headers or exception messages containing secrets.
            row.update(error_stage=stage, error_type=type(exc).__name__)
            if stage == 'identity':
                row.update(match_status='review_required', identity_reason='api_identity_error', metadata_status='error')
            else:
                row['provider_verification_status'] = 'error'
        rows.append(row)
        print(f"{ko}: {row['match_status']} {row['error_type']}")
        time.sleep(delay)
    return rows, seasons


def metrics(baseline, rows, mode):
    platforms = {'Netflix': {'Netflix', 'Netflix Standard with Ads'}, 'TVING': {'TVING'},
                 'Laftel': {'Laftel', '라프텔'}}
    def counts(records):
        return {platform: sum(bool(names.intersection(
            p.strip() for p in r.get('providers_kr_subscription', '').split('|'))) for r in records)
                for platform, names in platforms.items()}
    return dict(mode=mode, total=len(rows),
                baseline_title_candidates=sum(r['match_status'] == 'exact_title_candidate' for r in baseline),
                baseline_review_required=sum(r['match_status'] == 'review_required' for r in baseline),
                identity_verified=sum(r['match_status'] == 'identity_verified' for r in rows),
                review_required=sum(r['match_status'] == 'review_required' for r in rows),
                not_found=sum(r['match_status'] == 'not_found' for r in rows),
                baseline_subscription_hints=counts(baseline), subscription_hints=counts(rows),
                metadata_count_fields=sum(bool(r['season_count'] and r['official_episode_count']) for r in rows),
                season_details=sum(r['season_detail_status'] == 'collected' for r in rows),
                api_errors=sum(bool(r['error_type']) for r in rows),
                actual_ott_episode_verified=0,
                accuracy_all_30=None,
                accuracy_note='No independent reference labels for all 30; identity coverage is not accuracy.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=['offline', 'live'], default='offline')
    p.add_argument('--input', default=str(ROOT / 'data/tmdb_results.csv'))
    p.add_argument('--output', default=str(ROOT / 'data/tmdb_revalidated_v0_2.csv'))
    p.add_argument('--limit', type=int, default=30)
    p.add_argument('--delay', type=float, default=.3)
    args = p.parse_args()
    if not 1 <= args.limit <= 30 or args.delay < 0:
        p.error('--limit must be 1..30; --delay must be nonnegative')
    source, output = Path(args.input), Path(args.output)
    if source.resolve() == output.resolve():
        p.error('v0.1 input cannot be overwritten')
    token = os.environ.get('TMDB_READ_ACCESS_TOKEN', '').strip()
    if args.mode == 'live' and not token:
        p.error('TMDB_READ_ACCESS_TOKEN is missing. No output was written.')
    baseline = read_csv(source)[:args.limit]
    samples = read_csv(ROOT / 'data/sample_titles_30.csv')[:args.limit]
    if [r['query'] for r in baseline] != [r['title_ko'] for r in samples]:
        p.error('baseline/sample titles or ordering differ')
    rules = json.loads((ROOT / 'data/identity_rules_v0_2.json').read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc).isoformat()
    if args.mode == 'offline':
        rows, seasons = revalidate_snapshot(baseline, rules, now), []
    else:
        rows, seasons = refresh_live(samples, baseline, rules, token, args.delay)
    write_csv(output, HEADERS + EXTRA, rows)
    write_csv(output.with_name(output.stem + '_seasons.csv'), SEASON_HEADERS, seasons)
    review_headers = ['query', 'tmdb_id', 'matched_title', 'original_name', 'first_air_date',
                      'identity_reason', 'identity_source_url']
    write_csv(output.with_name(output.stem + '_review_required.csv'), review_headers,
              [{key: row[key] for key in review_headers} for row in rows
               if row['match_status'] != 'identity_verified'])
    summary = metrics(baseline, rows, args.mode)
    summary.update(revalidated_at_utc=now, input_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    output.with_suffix('.metrics.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary['api_errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
