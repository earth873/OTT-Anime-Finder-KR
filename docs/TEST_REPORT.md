# 테스트 보고

## Phase 2.1 실행 기록 — 2026-10-11

기준: `2ff7987`, 브랜치: `feature/phase-2-1-validation`. 각 Python 종료 코드를 `$LASTEXITCODE`로 확인했다.

| 실제 실행 | 결과 |
|---|---|
| `git fetch origin main`, SHA 비교 | 성공; main과 기준 일치, 시작 시 변경 없음 |
| 토큰 존재 여부 확인 | 현재 프로세스에 없음. 값은 출력/기록하지 않음 |
| `& C:\Python310-64\python.exe scripts\validate_v02.py --mode live --limit 30 --output .local\tmdb_live_v0_2_1.csv` | **종료 2**, 토큰 누락. API 조회/실시간 CSV 생성 없음 |
| `& C:\Python310-64\python.exe -m unittest discover -s tests -v` | 초기 31개, 최종 **33개 통과**, 종료 0; 기존 20+추가 13, API는 모의 테스트 |
| `& C:\Python310-64\python.exe -m compileall -q scripts tests` | 종료 0 |
| `& C:\Python310-64\python.exe scripts\validate_ott_episodes.py data\ott_upload_manual_v0_2.csv` | 종료 0; 관측 0/오류 0 |
| `& C:\Python310-64\python.exe scripts\validate_v02.py --mode offline --limit 30 --output .local\tmdb_offline_v0_2_1.csv` | 종료 0; 30개, 식별 3/검토 27; 과거 관측값 재검증 |
| PostgreSQL/psql/initdb/pg_ctl/Docker 탐색 | 실행 가능한 로컬 도구/테스트 DB를 확인하지 못함 |
| 원격 PostgreSQL 16 CI | 실행 전. 실제 결과 확인 후 보고서 갱신 예정 |
| 원본 SHA-256 및 `git diff --name-only main -- data` | 원본 해시 일치, data 변경 없음 |
| `git diff --check` | 종료 0 |

API 오류 검증 범위: 401 오류 메시지/토큰 비노출, 503/연결 실패 4회 시도 후 실패 기록, 비정상 Retry-After, JSON 파싱 실패, 잘못된 KR/시즌 응답, 필수 필드 누락, 다음 작품으로 처리 지속, 별도 errors/missing/review CSV, legacy 원본 덮어쓰기 거부. 실제 인증/API 성공을 의미하지 않는다.

SQL 검증 계획은 실제 PostgreSQL에서 v0.2 결함 2개를 먼저 재현하고 fixture를 rollback한 뒤, v0.2.1 수정으로 거부되는지 검사한다. SQL 실패가 발생하면 로그와 수정/재실행 결과를 남긴다. 아래는 이전 작업의 실제 기록을 보존한 것이다.

실행일: 2026-10-11 (Asia/Seoul). 실행 환경: Windows 11, `C:\Python310-64\python.exe` (3.10.1). 작업 브랜치: `feature/github-development-reporting`. 기준 커밋: `6c74d170ce2df47d64d6e43ac3477541a9546492`.

## 이번 작업에서 실제 실행한 검증

| 명령/검사 | 결과 | 종료 코드/주의 |
|---|---|---|
| `git status --short --branch` | 시작 시 main, 작업 파일 깨끗함 | 0 |
| `git remote -v` | 지정된 GitHub 저장소의 origin fetch/push 확인 | 0 |
| `git ls-remote --heads origin` | 최초 제한 환경에서 getaddrinfo() 실패 | 네트워크 실패; 원격 미연결로 단정하지 않음 |
| `git fetch origin main` | 허용된 네트워크 실행 환경에서 성공 | 0, 실패 후 복구 |
| `git rev-parse HEAD origin/main` / `git diff --stat HEAD origin/main` | 양쪽 모두 기준 SHA, 차이 없음 | 0, Phase 2 반영 확인 |
| `git ls-tree -r --name-only origin/main` | Phase 2 Python/CSV/SQL/보고서/테스트 포함 | 0 |
| `python -m unittest discover -s tests -v` | **20개 통과**, 0.116초 | Python 종료 0, 모의 API 포함 |
| `python -m compileall -q scripts tests` | Python 구문 검사 통과 | Python 종료 0 |
| `python scripts\validate_ott_episodes.py data\ott_upload_manual_v0_2.csv` | 관측 0건, 오류 0건 | Python 종료 0, 실제 데이터 확보 아님 |
| `python scripts\validate_v02.py --mode offline --limit 30 --output $env:TEMP\ott_anime_reporting_check.csv` | sandbox TEMP의 파일 원자 교체에 WinError 5 발생 | **Python 종료 1**, PermissionError |
| `python scripts\validate_v02.py --mode offline --limit 30 --output .local\tmdb_reporting_check.csv` | 쓰기 가능한 프로젝트 경로에서 재시도 성공 | Python 종료 0, 식별 검증 3/검토 27 |
| `git check-ignore` (아래 경로 목록) | 비밀/로컬 경로 모두 제외됨 | 0 |
| Python 표준 라이브러리로 업로드 대상의 토큰 형식/개인키/위험 파일명 검사 | 의심 항목 0건 | 종료 0, 모든 비밀 형식을 보장하는 검사는 아님 |
| `git diff --check` | 공백 오류 없음 | 0; Windows CRLF 변환 안내는 오류 아님 |
| `git diff --name-only origin/main -- data scripts sql tests research_report_v0_2.md CHANGELOG.md` | 출력 없음 | 기존 Phase 2 산출물 변경 없음 |
| `Get-FileHash data\tmdb_results.csv -Algorithm SHA256` | 기존 원본 해시와 일치 | 원본 보존 |
| `Get-Command psql,postgres,gh -ErrorAction SilentlyContinue` | 세 명령을 찾지 못함 | DB 실행 미지원, gh 미설치 |

위 표의 python 명령은 모두 `& C:\Python310-64\python.exe`로 실행했으며, 출력 인코딩은 `PYTHONIOENCODING=utf-8`로 지정했다. 여러 명령을 묶은 PowerShell의 전체 종료 상태와 별개로 `$LASTEXITCODE`를 출력해 각 Python 종료 코드를 확인했다.

ignore 확인 경로: `.env`, `.env.production`, `.aws/credentials`, `.ssh/id_rsa`, `credentials.json`, `client_secret_demo.json`, `token.json`, `private.pem`, `.local/tmdb_reporting_check.csv`. 검사만 했으며 실제 인증 파일이나 테스트용 비밀을 생성하지 않았다. `.env.example`은 값 없는 예시만 추적 가능하다.

내용 점검은 Git 추적 파일과 새 보고/설정 파일을 읽되 매칭 문자열을 출력하지 않고 의심 파일 경로만 출력했다. PEM 개인키, GitHub 토큰, JWT 형태, AWS access-key 형태 및 실행 환경 TMDB 토큰이 파일에 존재하는지 확인했다. 실제 토큰 값은 보고서/로그/PR에 저장하지 않았다. 커밋 대상 파일은 별도로 명시하고 최종 staged 차이도 검사한다.

원본 SHA-256: `8941d0cf153887f5269019579d7ff77126dd46e9e1912af65268b25b58761d5a`.

## 테스트가 확인한 내용

20개 기존 테스트는 ID/원제/연도 충돌, 한국어 괄호·× 정규화, 헌터 판본 불확실성, 코노스바 스핀오프 값 제거, 첫 검색 결과 자동 선택 금지, API 오류 표시/재시도/인증 실패, 원본 덮어쓰기 방지, 토큰 누락 시 출력 보존, CSV 통계/수동 큐 일관성, 회차 누락·중복·최신과 개수의 구분·출처·시각을 확인했다.

출력의 `TimeoutError`는 의도적으로 주입한 모의 API 오류 테스트다. 실패 테스트나 실제 API 요청 실패를 감추는 출력이 아니다. 실제 API를 호출하지 않고 오류가 결과에 기록되는지 확인한다.

## 미실행 / 검증 범위 밖

- 실시간 TMDB 인증 및 최신 데이터 재조회: 이번 GitHub 보고체계 작업에서는 실행하지 않았다. Phase 2의 토큰 누락 실패 기록은 기존 보고서에 보존했다.
- PostgreSQL schema/migration/SQL 테스트: psql/postgres가 없어 미실행. Python 테스트 성공을 DB 검증 성공으로 해석하지 않는다.
- 실제 라프텔/Netflix/TVING 업로드 회차: 이번 작업 관측 0건. 오프라인 CSV 및 빈 관측 양식 통과는 현재 회차 확인이 아니다.
- 자동 테스트는 `.github/workflows/python-validation.yml`에 추가했다. 원격 실행의 실제 결과는 GitHub Actions에서 확인하며 로컬 성공과 구분한다.

## GitHub 리뷰 기준

main 대상 PR에서 변경 파일과 위 결과를 리뷰한다. Phase 2 데이터/코드/SQL은 유지하고 보고/설정 파일만 추가·갱신한다. main 자동 병합과 force push를 하지 않는다. required reviews/status checks의 저장소 보호 설정은 별도 후속 작업이다.
