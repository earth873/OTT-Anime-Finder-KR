# v0.2 실행 기록

2026-10-11, C:\ott_anime_validation_v0_1, C:\Python310-64\python.exe (3.10.1).

| 실행 | 결과 |
|---|---|
| `scripts\validate_v02.py --mode offline --limit 30` | 성공, 30개/identity_verified 3/review_required 27 |
| `scripts\validate_v02.py --mode live --limit 30` | 토큰 환경변수 없음; argparse 오류로 중단, 출력 변경 없음 |
| `scripts\prepare_manual_queue.py` | 성공, 90개 작업, 실제 관측값을 생성하지 않음 |
| `scripts\validate_ott_episodes.py data\ott_upload_manual_v0_2.csv` | 성공, 관측 0건/오류 0건 |
| `-m unittest discover -s tests -v` | 최종 20 tests, OK, 종료 0 |
| `-m compileall -q scripts tests` | 성공, 종료 0 |
| `Get-Command psql,postgres -ErrorAction SilentlyContinue` | 실행 도구를 찾지 못함; DB 테스트 미실행 |
| `git status --short` | Git 저장소 아님 |
| `Get-FileHash data\tmdb_results.csv -Algorithm SHA256` | 원본 보존, 8941D0CF153887F5269019579D7FF77126DD46E9E1912AF65268B25B58761D5A |

실시간 실패는 환경 준비 미완료이며 테스트 통과로 감추지 않았다. API 인증 성공/30개 최신 재수집/실제 PostgreSQL 제약 검증/실제 OTT 회차 확인은 이번 실행의 성공 항목이 아니다.
