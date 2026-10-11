# Phase 2.1 — 실제 동작 검증 보고서

검증일: 2026-10-11 (Asia/Seoul). 기준: main `2ff79874f78a08d6a360508a2310d2425363bcb5`.
작업 브랜치: `feature/phase-2-1-validation`. 기존 data 파일 및 과거 Phase 2 보고서를 보존한다.

## 실시간 TMDB와 모의 테스트 구분

현재 프로세스에서 `TMDB_READ_ACCESS_TOKEN`은 설정되지 않았다. 값 대신 존재 여부만 확인했다. `--mode live --limit 30 --output .local/tmdb_live_v0_2_1.csv`는 **종료 2**, 네트워크 요청/실시간 CSV 생성 없이 중단했다. **실제 API 인증과 30개 실시간 재조회는 미실행**이다. 환경변수를 실행 프로세스에 설정한 후 같은 명령을 재실행해야 한다. 토큰을 코드/파일/PR에 넣지 않는다.

기존 30개 데이터의 오프라인 재처리는 `.local/tmdb_offline_v0_2_1.csv`로 수행해 식별 3/검토 27을 확인했다. 이를 현재 ID/시즌/회차/한국 OTT 제공 정보의 API 성공으로 보고하지 않는다. 원본 SHA-256은 `8941d0cf153887f5269019579d7ff77126dd46e9e1912af65268b25b58761d5a`로 유지됐다.

최종 33개 Python 테스트(기존 20+추가 13)는 모두 통과했고 구문 검사도 종료 0이다. API 관련 테스트는 **모의 HTTP 응답/예외**다. 401·503·연결 실패·잘못된 JSON·KR 응답 누락·시즌 형식 오류·잘못된 Retry-After와 토큰/메시지 비노출·처리 지속을 검사했다. 음수/불리언/문자열 회차 집계는 공란으로 두고 invalid 누락 대상으로 기록한다.

보완한 수집기 결과는 오류 `_errors.csv`, 누락 `_missing.csv`, 검토 `_review_required.csv`를 분리한다. 목록은 서로 겹칠 수 있다. KR 데이터 없음은 미제공 확정이 아니다. 필수 필드/시즌 요약이 없으면 collected로 오인하지 않도록 `incomplete/missing_fields`를 기록한다. legacy 스크립트도 기존 baseline을 덮어쓰지 못하게 했고 README의 `py -3`를 실제 Python 경로로 교체했다.

## PostgreSQL 실제 검증 환경

로컬 psql/postgres/initdb/pg_ctl/Docker 및 사용할 수 있는 독립 테스트 DB를 확인하지 못했다. 운영 DB나 운영 서비스는 접근/변경하지 않았다. GitHub Actions에 **별도 Ubuntu runner + PostgreSQL 16 서비스**를 추가했다. 서비스 데이터는 작업 종료와 함께 폐기되며 실제 애니/OTT 정보를 수입하지 않는다. 인증은 격리된 테스트용 trust이며 운영용 구성이 아니다.

실행 순서:

1. `sql/schema.sql` → `sql/migration_v0_2.sql` → `tests/test_db_v02.sql`.
2. `tests/test_db_v021_baseline.sql`: 수정 전 v0.2에서 다른 작품 회차 매핑과 미래 verified_at 입력이 허용되는지 재현하고 rollback.
3. `sql/migration_v0_2_1.sql`: 추가 제약/트리거/공개 뷰 보완.
4. `tests/test_db_v02.sql` 재실행 → `tests/test_db_v021.sql`: 확장 실제 SQL assertion, fixture 모두 rollback.

**원격 실제 PostgreSQL 검증 성공.** [GitHub Actions run 38143396065](https://github.com/earth873/OTT-Anime-Finder-KR/actions/runs/38143396065)은 Python/DB job 모두 success다. 검증 코드 커밋은 `d7d02a01d44706282ac2e7fa14dd5ae739ddf463`, DB job은 `114481671598`이다. 서버 로그의 PostgreSQL 버전은 **16.15**이며 각 psql 명령과 SQL 결과를 확인했다. 기존 v0.2 SQL 테스트는 수정 전·후 모두 통과했고, 기준 버전 결함 2개가 재현됐으며, 확장 실제 SQL assertion **22개 모두 통과**했다. fixture는 모두 rollback했고 테스트 컨테이너는 CI 종료 시 폐기됐다. 실제 API 조회를 대신한 결과가 아니다.

로그 핵심:

```text
REPRODUCED 2 baseline gaps: cross-anime mapping and future verified_at accepted
passed_assertions
22
(22 rows)
ROLLBACK
```

SQL 문법/제약/트리거/뷰 실행 오류는 이 CI에서 발생하지 않았다. 발견한 무결성 결함은 '오류를 throw하지 않고 잘못된 관계를 허용'하는 문제였으며, 수정 전 허용/수정 후 차단을 별도 검사했다. 로컬 DB 실행은 도구가 없어 미실행이고 운영 DB는 그대로다.

## 무결성 검사 항목

| 요구 | 구현/SQL assertion |
|---|---|
| 방송과 OTT 회차 분리 | 공식 episodes에는 2개 fixture만 있고 OTT에는 [1,3,12]; 공식 행 자동 채움 없음 |
| 미확인 회차 NULL | 기본 관측의 latest/count/list 모두 NULL, 0 입력 거부 |
| 작품-시즌 관계 | snapshot 복합 FK 검사, 다른 작품 시즌 연결 거부 |
| 중복/회차 계산 | 중복 배열/매핑 PK 거부, 개수는 배열 길이, 최신은 배열 최대값 |
| OTT별 회차 차이 | 같은 작품·시즌에 플랫폼 A=[1,3,12], B=[1,3]를 별도 저장 |
| 시즌·파트 매핑 | 다른 작품 매핑 거부, 같은 작품의 정규 시즌 여러 개에 걸친 파트는 허용 |
| 부모 변경 | 이미 매핑된 episode의 시즌/season의 작품 변경 및 관측 목록 제거로 매핑을 깨뜨리는 update 거부 |
| 오래된 결과 제한 | 8일 된 검증, 식별 미검증, 최신 unknown 뒤 과거 verified의 공개를 차단 |
| 미래 시각 | verified_at이 관측 생성 시각 이후면 거부, 뷰에도 현재 시각 상한 추가 |

트리거는 행 연결과 관측 번호 포함 여부를 검사한다. 실제 파트 대응 의미나 화면 확인의 진실성은 DB만으로 증명할 수 없다. 기존 invalid mapping은 추가 migration에서 중단하며 임의 삭제/자동 교정하지 않는다. 동시 쓰기 경합/백업 복원/실제 운영 데이터 업그레이드는 별도 검증이 필요하다.

## 로컬 독립 환경 구축 방법 (이번 작업에서 실행하지 않음)

Docker가 설치된 별도 개발 PC에서 다음을 실행할 수 있다. 운영 DB 연결 문자열이나 운영 볼륨을 사용하지 않는다. 아래 컨테이너만 사용하는 새 테스트 DB다.

```powershell
docker run --rm --name ott-anime-phase21 -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_DB=ott_anime_test -p 127.0.0.1:55432:5432 -d postgres:16
docker exec ott-anime-phase21 pg_isready -U postgres -d ott_anime_test
docker cp sql ott-anime-phase21:/tmp/sql
docker cp tests ott-anime-phase21:/tmp/tests
docker exec ott-anime-phase21 psql -X -U postgres -d ott_anime_test -v ON_ERROR_STOP=1 -f /tmp/sql/schema.sql
docker exec ott-anime-phase21 psql -X -U postgres -d ott_anime_test -v ON_ERROR_STOP=1 -f /tmp/sql/migration_v0_2.sql
docker exec ott-anime-phase21 psql -X -U postgres -d ott_anime_test -v ON_ERROR_STOP=1 -f /tmp/tests/test_db_v02.sql
docker exec ott-anime-phase21 psql -X -U postgres -d ott_anime_test -v ON_ERROR_STOP=1 -f /tmp/tests/test_db_v021_baseline.sql
docker exec ott-anime-phase21 psql -X -U postgres -d ott_anime_test -v ON_ERROR_STOP=1 -f /tmp/sql/migration_v0_2_1.sql
docker exec ott-anime-phase21 psql -X -U postgres -d ott_anime_test -v ON_ERROR_STOP=1 -f /tmp/tests/test_db_v021.sql
docker stop ott-anime-phase21
```

pg_isready가 준비 완료를 표시한 뒤 SQL을 실행하고 각 명령이 실패하면 다음 단계로 넘어가지 않는다. 마지막 stop은 위에서 만든 테스트 컨테이너만 종료한다. Docker 설치·서비스 변경은 이번 작업에서 수행하지 않았다.

## 참고 문서

- [PostgreSQL CHECK/외래키 제약](https://www.postgresql.org/docs/current/ddl-constraints.html): CHECK만으로 다른 행/테이블의 연결 무결성을 보장하지 않으므로 연결 검증에 FK와 트리거를 사용했다.
- [PostgreSQL trigger 함수](https://www.postgresql.org/docs/current/plpgsql-trigger.html): INSERT/UPDATE의 NEW/OLD 검사.
- [GitHub PostgreSQL 서비스 컨테이너](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers): 별도 runner 서비스와 health check 구성.

## 남은 문제

토큰 설정 후 실제 TMDB 30개 조회, 27개 독립 작품 검토/헌터 판본 결정, 현재 OTT 회차 관측, 라프텔 데이터 허가, 실제 파트 의미 검토, DB 적재/RLS, main 보호 설정은 남아 있다. PostgreSQL 실제 CI는 성공했으나 동시 쓰기/운영 데이터 업그레이드/로컬 DB 실행은 미검증이다. main 자동 병합/force push는 하지 않는다.

## GitHub 리뷰 및 변경 범위

[PR #2](https://github.com/earth873/OTT-Anime-Finder-KR/pull/2), 브랜치 `feature/phase-2-1-validation` → main. 기존 data 차이 없음, 원본 해시 유지, 비밀정보 검사 의심 항목 0건. 변경 12개 파일: README, Python 수집기 2개, 추가 migration, Python 추가 테스트, SQL 재현/확장 테스트 2개, CI workflow, 개발 상태/테스트/알려진 문제/본 보고서 4개. 최종 보고서는 이 검증 코드 커밋 위에 문서 결과 기록 커밋으로 추가한다.
