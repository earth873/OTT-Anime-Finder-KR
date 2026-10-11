# OTT Anime Finder KR — 데이터 검증 v0.2

v0.2는 기존 30개 결과를 보존하며 작품 식별과 실제 OTT 회차 검증을 분리합니다. 현재 실행에서는 TMDB 토큰이 없어 **오프라인 재검증만 완료**했습니다. 식별 근거 일치 3개, 수동 검토 27개, 실제 OTT 회차 관측 0건입니다. 자세한 결과·제한·조사 출처는 [research_report_v0_2.md](research_report_v0_2.md)를 확인하세요.

## GitHub 개발 및 보고

저장소: [earth873/OTT-Anime-Finder-KR](https://github.com/earth873/OTT-Anime-Finder-KR). Phase 2 결과는 main의 `6c74d170ce2df47d64d6e43ac3477541a9546492`에 반영되어 있습니다. 이후 작업은 feature 브랜치에서 테스트·문서화한 뒤 push하고, main을 대상으로 PR을 열어 리뷰합니다. main 직접 작업·자동 병합·force push는 하지 않습니다.

- [개발 상태](docs/DEVELOPMENT_STATUS.md): 구현 항목과 미구현 항목.
- [테스트 보고](docs/TEST_REPORT.md): 실제 실행 명령·종료 코드·실패 및 미실행 사유.
- [알려진 문제](docs/KNOWN_ISSUES.md): 미해결 문제와 다음 단계.
- [개발 작업 규칙](AGENTS.md): 브랜치·기존 파일 보존·검증·보고 규칙.

GitHub Actions의 `Python validation`은 push/PR에서 Python 3.10 단위 테스트·구문 검사·수동 양식 검사·오프라인 재처리와, 별도 PostgreSQL 서비스의 실제 SQL 검증을 실행합니다. API 토큰을 사용하지 않으며 실제 OTT 회차를 확인하지 않습니다. required checks 및 main 보호 규칙은 저장소 설정에서 별도로 적용해야 합니다.

새 작업의 기본 순서:

```powershell
git status --short --branch
git fetch origin
# 작업 폴더 변경을 먼저 확인하고, 깨끗한 main에서 feature 브랜치를 만듭니다.
git switch main
git pull --ff-only origin main
git switch -c feature/<작업명>
& C:\Python310-64\python.exe -m unittest discover -s tests -v
& C:\Python310-64\python.exe -m compileall -q scripts tests
# 문서 갱신과 비밀정보/변경내용 확인 후 필요한 파일만 명시적으로 add/commit합니다.
git push -u origin feature/<작업명>
```

GitHub CLI가 있으면 `gh pr create --base main --head feature/<작업명>`을 사용합니다. 없으면 연결된 GitHub 도구 또는 GitHub 화면으로 PR을 생성합니다. PR을 만들지 못하면 실패 이유와 브랜치 URL을 보고합니다. 리뷰 후 사람이 병합 여부를 결정합니다.

`.env`, 인증 JSON, 개인키, 로컬 검사 결과는 `.gitignore`에서 제외합니다. `.env.example`은 기존 규칙에 따라 추적할 수 있으므로 **값 없는 예시만** 넣습니다. 이미 추적된 파일은 ignore 규칙으로 제거되지 않으므로 커밋 전 staged 파일과 내용도 확인해야 합니다. 토큰은 실행 프로세스 환경변수로만 전달합니다.

## v0.2 실행

Phase 2.1 검증 상태와 실제/모의 실행 구분은 [PHASE_2_1_REPORT.md](docs/PHASE_2_1_REPORT.md)를 확인하세요. 현재 프로세스의 TMDB 토큰은 없으므로 실시간 조회는 미실행입니다. 조회할 때는 기존 CSV와 다른 경로를 지정합니다.

```powershell
& C:\Python310-64\python.exe scripts\validate_v02.py --mode live --limit 30 --output .local\tmdb_live_v0_2_1.csv
```

결과 외에 `_errors.csv`, `_missing.csv`, `_review_required.csv`를 분리합니다. KR 제공 데이터가 없으면 `no_kr_data_not_unavailable`이며 미제공을 뜻하지 않습니다. API 응답에 필수 상세 필드/시즌 요약이 없으면 `incomplete` 및 `missing_fields`에 기록합니다. legacy 조회도 기존 `data/tmdb_results.csv` 덮어쓰기를 거부하므로 `--output`을 지정해야 합니다.

```powershell
Set-Location C:\ott_anime_validation_v0_1
& C:\Python310-64\python.exe scripts\validate_v02.py --mode offline --limit 30
& C:\Python310-64\python.exe -m unittest discover -s tests -v
& C:\Python310-64\python.exe scripts\prepare_manual_queue.py
& C:\Python310-64\python.exe scripts\validate_ott_episodes.py data\ott_upload_manual_v0_2.csv
```

환경변수 `TMDB_READ_ACCESS_TOKEN`이 실행 프로세스에 설정된 경우:

```powershell
& C:\Python310-64\python.exe scripts\validate_v02.py --mode live --limit 30 --output data\tmdb_live_v0_2.csv
```

실시간 경로는 TMDB 작품 상세의 시즌 요약 및 작품 단위 KR 제공 정보를 수집합니다. 개별 회차 상세 또는 OTT 업로드 회차 수집은 하지 않습니다. 토큰이 없으면 출력 파일을 쓰지 않습니다. 일부 API 오류가 나면 부분 결과와 `error_stage/error_type`을 기록하고 종료 코드 1을 반환합니다. 결과에 오류가 있다는 사실을 숨기지 않습니다. 토큰은 파일·명령 출력·Git에 저장하지 마세요.

- `data/tmdb_revalidated_v0_2.csv`: 30개 재검증. `identity_verified`는 작품 식별 상태이며 현재 OTT 제공 확인이 아닙니다.
- `data/tmdb_revalidated_v0_2_review_required.csv`: 수동 검토 대상과 사유.
- `data/tmdb_revalidated_v0_2_seasons.csv`: 공식 메타데이터 시즌 상세; 오프라인 실행에서는 헤더만 있습니다.
- `data/tmdb_revalidated_v0_2.metrics.json`: 비교 통계·실행 모드·원본 해시. 전체 정확도는 독립 정답셋이 없어 null입니다.
- `data/identity_rules_v0_2.json`: 5개 우선 작품의 ID/원제/제작연도/근거. 다른 25개는 제목만으로 확정하지 않습니다.
- `data/ott_manual_review_queue_v0_2.csv`: 90개 확인 작업 목록; 관측 데이터가 아닙니다.
- `data/ott_upload_manual_v0_2.csv`: 빈 수동 관측 양식. 내부 anime/season ID, 출처·시간·검토자·증거와 확인한 전체 회차 목록을 입력하세요.

수동 양식에서 미확인 회차는 공란, verified일 때 회차는 정렬된 JSON 배열입니다. `[1,3,12]`면 최신 12, 제공 수 3입니다. 실제 제공을 확인하지 못하면 0이나 unavailable로 채우지 마세요. 시즌 매핑도 확인해야 합니다. 검증기는 형식/일관성을 검사하며 관측값의 진실성이나 내부 DB ID의 실존은 검토자/DB에서 확인해야 합니다.

## DB 스키마

기존 DB는 `sql/migration_v0_2.sql`을 한 번 적용합니다. 새 PostgreSQL DB는 `sql/schema.sql` → `sql/migration_v0_2.sql` 순서입니다. 미확인 데이터는 공개용 뷰에 표시하지 않으며, 공개용 회차는 최근 7일 확인 정책을 적용합니다. 마이그레이션은 재실행용이 아닙니다.

Phase 2.1 테스트 DB에는 이어서 `sql/migration_v0_2_1.sql`을 적용해 다른 작품의 회차 매핑과 매핑을 깨뜨리는 부모 변경을 차단합니다. 같은 작품의 여러 정규 시즌에 걸친 OTT 파트는 허용합니다. 운영 DB 적용은 이번 작업 범위가 아닙니다. GitHub Actions의 별도 PostgreSQL 16 서비스에서 SQL을 실제 실행하며, 로컬 독립 환경 구축 절차는 Phase 2.1 보고서에 있습니다.

```powershell
# PostgreSQL 도구/별도 테스트 DB를 준비한 뒤 실행 (이번 작업에서는 미실행)
psql -v ON_ERROR_STOP=1 -d ott_anime_test -f sql\schema.sql
psql -v ON_ERROR_STOP=1 -d ott_anime_test -f sql\migration_v0_2.sql
psql -v ON_ERROR_STOP=1 -d ott_anime_test -f tests\test_db_v02.sql
psql -v ON_ERROR_STOP=1 -d ott_anime_test -f sql\migration_v0_2_1.sql
psql -v ON_ERROR_STOP=1 -d ott_anime_test -f tests\test_db_v021.sql
```

운영 DB 연결/적용·권한/RLS·데이터 적재·최종 사이트는 아직 구현하지 않았습니다. 독립 PostgreSQL CI에서 실제 SQL 검증은 Phase 2.1에서 통과했습니다. 라프텔 자동 수집도 공식 허가/API를 확인하지 못해 추가하지 않았습니다.

## 보존된 v0.1 조회 기능

## 범위와 결과 상태

- **기존 결과:** `data/tmdb_results.csv`에 v0.1의 30개 API 조회 결과가 있습니다.
- **이번 실행:** 토큰 누락으로 실시간 재조회 미실행; v0.2 오프라인 재검증 완료.
- **미확인:** 넷플릭스/라프텔/티빙의 작품별 실제 업로드 회차.
- **중요:** TMDB의 `number_of_episodes`는 작품 전체 정보이지 특정 OTT가 제공하는 회차가 아님.

## Windows PowerShell 실행

1. TMDB 계정에서 API Read Access Token을 발급받습니다.
2. PowerShell에서 프로젝트 폴더로 이동해 실행합니다.

```powershell
$env:TMDB_READ_ACCESS_TOKEN = '여기에_읽기_토큰'
& C:\Python310-64\python.exe scripts/validate_tmdb.py --limit 5 --output .local\tmdb_legacy_check.csv
& C:\Python310-64\python.exe scripts/validate_tmdb.py --limit 30 --output .local\tmdb_legacy_check_30.csv
```

파이썬 표준 라이브러리만 사용하므로 pip 설치가 필요 없습니다. 결과는 `data/tmdb_results.csv`에 저장됩니다. 엑셀에서 UTF-8(BOM)으로 열 수 있습니다. `match_status=review_required`는 사람이 실제 작품을 확인해야 합니다. 수집값이 있다고 해서 OTT의 현재 시청 가능 에피소드까지 확정된 것은 아닙니다.

## CSV 해석

- `providers_kr_subscription`: 한국 지역 기준 제공 플랫폼 목록 (작품 단위)
- `provider_scope`: 항상 `TV_SERIES_KR_NOT_EPISODE`
- `official_episode_count`: TMDB에 등록된 공식 전체 회차 수. OTT별 시청 회차 아님
- `ott_latest_episode`: 검증 전 공란으로 유지
- `ott_episode_verification`: 검증 전 `NOT_CHECKED`
- `match_status`: v0.1 CSV의 `exact_title_candidate`는 확정이 아닙니다. 수정된 실행 코드는 제목만으로 확정하지 않고 `review_required`로 표시합니다.

## 다음 검증

1. 애니 30개부터 한국 OTT의 제공 현황이 얼마나 매칭되는지 측정.
2. 인기 애니 100개로 확장 (본 스크립트의 표본은 30개이며 100개 수집은 별도 표본 확대 필요).
3. 각 OTT 회차 정보의 정식/허가된 접근 경로 조사 및 일부 작품 수동 대조.
4. `data/ott_episode_manual_verification.csv`에 직접 확인한 회차만 입력.
5. 검증 데이터만 사이트에 공개하고 미확인 상태와 마지막 확인일을 표시.

## 라이선스 주의

TMDB 비상업적 개발 및 평가와 광고 수익이 발생하는 상업적 서비스는 이용조건이 다릅니다. 광고가 붙는 검색 사이트에 TMDB 자료를 활용하려면 별도 상업적 계약이 필요할 수 있습니다. TMDB 및 JustWatch 저작자 표시 정책을 확인해야 하며, 포스터 이용권도 검토해야 합니다. TMDB 응답을 무기한 보관하지 마세요.

- https://www.themoviedb.org/api-terms-of-use
- https://developer.themoviedb.org/reference/tv-series-watch-providers
- https://developer.themoviedb.org/docs/faq
- https://apis.justwatch.com/docs/content_partner/

## 데이터 주의

`ott_episode_manual_verification.csv`의 `availability_status`는 `available`, `unavailable`, `unknown`만 사용합니다. `unknown`은 미제공이 아니며 단순히 확인하지 않은 상태입니다. 회차는 시즌 번호와 함께 표시합니다. 스트리밍 사이트를 무단으로 크롤링하는 코드는 포함하지 않았습니다.
