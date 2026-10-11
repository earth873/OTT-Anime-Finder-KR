"""Create a verification work queue, not fabricated availability observations."""
from validate_v02 import ROOT, read_csv, write_csv
from validate_ott_episodes import HEADERS


def main():
    template = ROOT / 'data/ott_upload_manual_v0_2.csv'
    if not template.exists():
        write_csv(template, HEADERS, [])
    rows = []
    for candidate in read_csv(ROOT / 'data/tmdb_revalidated_v0_2.csv'):
        for platform in ('Laftel', 'Netflix', 'TVING'):
            rows.append(dict(query=candidate['query'], candidate_tmdb_id=candidate['tmdb_id'],
                             identity_status=candidate['match_status'], ott_platform=platform,
                             verification_status='not_checked', source_url='', verified_at='',
                             note='작품/판본 확인 후 공식 화면의 시즌·회차를 검증. 이 행은 제공 여부 관측값이 아님.'))
    write_csv(ROOT / 'data/ott_manual_review_queue_v0_2.csv',
              ['query', 'candidate_tmdb_id', 'identity_status', 'ott_platform',
               'verification_status', 'source_url', 'verified_at', 'note'], rows)
    print(f'Manual queue: {len(rows)} tasks; template contains no invented observations.')


if __name__ == '__main__':
    main()
