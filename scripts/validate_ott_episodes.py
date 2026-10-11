#!/usr/bin/env python3
"""Validate manual OTT observations. Never derive uploaded episodes from TMDB counts."""
import argparse
import csv
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

HEADERS = ['anime_id', 'season_id', 'ott_platform', 'region', 'offer_type',
           'availability_status', 'latest_episode_number', 'available_episode_count',
           'available_episode_numbers', 'verification_status', 'source_url', 'verified_at',
           'reviewer', 'source_method', 'evidence_reference', 'ott_season_label',
           'episode_numbering', 'mapping_status', 'notes']


def integer(value, name, minimum=0):
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise ValueError(f'{name}: expected integer')
    number = int(value)
    if number < minimum:
        raise ValueError(f'{name}: too small')
    return number


def validate_row(row):
    integer(row.get('anime_id', ''), 'anime_id', 1)
    integer(row.get('season_id', ''), 'season_id', 1)
    if row.get('ott_platform') not in {'Laftel', 'Netflix', 'TVING'}:
        raise ValueError('unsupported ott_platform')
    if row.get('region') != 'KR':
        raise ValueError('region must be KR for this evaluation')
    if row.get('offer_type') not in {'subscription', 'rental', 'purchase', 'free', 'unknown'}:
        raise ValueError('invalid offer_type')
    status = row.get('verification_status')
    availability = row.get('availability_status')
    mapping = row.get('mapping_status')
    if availability not in {'available', 'unavailable', 'unknown'}:
        raise ValueError('invalid availability_status')
    if status not in {'not_checked', 'review_required', 'verified', 'stale'}:
        raise ValueError('invalid verification_status')
    if mapping not in {'not_checked', 'review_required', 'verified'}:
        raise ValueError('invalid mapping_status')
    episode_fields = ('latest_episode_number', 'available_episode_count', 'available_episode_numbers')
    if status != 'verified':
        if any(row.get(key, '') != '' for key in episode_fields):
            raise ValueError('unverified/stale observations must not publish episode values')
        return
    if availability == 'unknown' or mapping != 'verified':
        raise ValueError('verified episodes need known availability and verified season mapping')
    if row.get('offer_type') == 'unknown':
        raise ValueError('verified observation needs offer_type')
    if row.get('episode_numbering') != 'ott_display':
        raise ValueError('episode numbers must use observed OTT display numbering')
    url = urlparse(row.get('source_url', ''))
    hosts = {'Laftel': ('laftel.net',), 'Netflix': ('netflix.com',), 'TVING': ('tving.com',)}
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise ValueError('source_url must be HTTPS without credentials')
    official = any(url.hostname == h or url.hostname.endswith('.' + h) for h in hosts[row['ott_platform']])
    method = row.get('source_method')
    if method not in {'official_manual', 'official_api', 'licensed_feed'}:
        raise ValueError('invalid verified source_method')
    if method != 'licensed_feed' and not official:
        raise ValueError('official observations need the matching platform domain')
    if not row.get('reviewer', '').strip() or not row.get('evidence_reference', '').strip():
        raise ValueError('reviewer and evidence_reference are required')
    checked = datetime.fromisoformat(row.get('verified_at', '').replace('Z', '+00:00'))
    if checked.tzinfo is None or checked > datetime.now(timezone.utc):
        raise ValueError('verified_at must have timezone and cannot be in future')
    numbers = json.loads(row.get('available_episode_numbers', ''))
    if not isinstance(numbers, list) or any(type(n) is not int or n < 1 for n in numbers):
        raise ValueError('available_episode_numbers must be JSON array of positive integers')
    if numbers != sorted(set(numbers)):
        raise ValueError('episode numbers must be sorted and unique; gaps are allowed')
    count = integer(row.get('available_episode_count', ''), 'available_episode_count')
    if count != len(numbers):
        raise ValueError('count differs from observed list length')
    latest = row.get('latest_episode_number', '')
    if availability == 'unavailable':
        if numbers or count or latest:
            raise ValueError('unavailable needs [] / 0 / blank latest')
    elif not numbers or integer(latest, 'latest_episode_number', 1) != max(numbers):
        raise ValueError('latest must equal max observed episode, not count')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input')
    args = p.parse_args()
    errors, checked = [], 0
    with open(args.input, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != HEADERS:
            p.error('CSV headers differ from v0.2 manual template')
        for line, row in enumerate(reader, 2):
            checked += 1
            try:
                validate_row(row)
            except (ValueError, TypeError) as exc:
                errors.append(f'line {line}: {exc}')
    for error in errors:
        print(error)
    print(f'Validated {checked} observations; {len(errors)} errors. Empty template is not data coverage.')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
