# 개발 상태

## Phase 2.1 현재 검증

기준 main: `2ff79874f78a08d6a360508a2310d2425363bcb5`, 작업: `feature/phase-2-1-validation` (2026-10-11).
최신 main과 기준 커밋이 일치하며 기존 데이터는 변경하지 않았다. Python 최종 33개 테스트와 구문 검사를 로컬에서 통과했다. 신규 13개 테스트는 실제 HTTP 요청 없이 오류/누락/비정상 회차 값/분리 출력/원본 보존을 확인한다.

현재 프로세스의 TMDB 토큰이 없어 live 조회는 종료 2로 중단했다. 실시간 CSV를 생성하지 않았으며 기존 30개 오프라인 재처리만 별도 `.local` 경로에서 실행했다(식별 3/검토 27). 실제 OTT 관측은 계속 0건이다.

로컬 PostgreSQL/Docker는 없다. 독립 GitHub Actions PostgreSQL 16 서비스를 추가해 v0.2 스키마/기존 SQL 테스트/기준 버전 결함 재현/추가 마이그레이션/확장 SQL 테스트를 **실제 실행해 통과**했다. 기준 버전 결함 2개 재현, 수정 후 확장 assertion **22개 통과**를 로그에서 확인했다. [CI run 38143396065](https://github.com/earth873/OTT-Anime-Finder-KR/actions/runs/38143396065)은 Python/DB 두 job 모두 success이며 검증 코드 커밋은 `d7d02a01d44706282ac2e7fa14dd5ae739ddf463`다. 운영 DB는 접근하지 않았다.

보완: KR 응답 없음과 미제공 구분, 누락 필드와 오류/검토 CSV 분리, 비정상 Retry-After 처리, legacy 원본 보호, 다른 작품으로 회차 매핑하는 오류/부모 변경 차단, 미래 검증 시각/공개 제한. 새 최종 서비스 기능이나 임의 회차 데이터는 추가하지 않았다.

자세한 실행 결과와 독립 DB 절차: [PHASE_2_1_REPORT.md](PHASE_2_1_REPORT.md). 아래는 Phase 2 및 GitHub 보고체계 도입 당시 기록이다.

기준일: 2026-10-11 (Asia/Seoul). 프로젝트: OTT Anime Finder KR v0.2.

## 저장소 및 기준 버전

- 저장소: https://github.com/earth873/OTT-Anime-Finder-KR
- 안정 기준 브랜치: main
- 이번 작업 브랜치: feature/github-development-reporting
- Phase 2 기준 커밋: `6c74d170ce2df47d64d6e43ac3477541a9546492`
- 원격 main을 fetch한 뒤 로컬 HEAD와 원격 SHA가 같음을 확인했다. main에 Phase 2의 코드·CSV·SQL·보고서·테스트가 이미 포함되어 있다. 작업 시작 시 미커밋 변경사항은 없었다.
- 이전 `research_report_v0_2.md` 및 `data/validation_run_v0_2.md`의 'Git 저장소 아님'은 Phase 2 당시 기록이다. 현재는 GitHub 원격이 연결되어 있다.

## 구현 완료

| 영역 | 상태 | 근거 |
|---|---|---|
| TMDB 조회 경로 | 구현 | 환경변수 토큰, 재시도, 오류 단계 기록. 실제 인증 조회는 별도 필요 |
| 작품 식별 | 구현 | ID·원제·연도/근거 비교, 불확실성 유지 |
| 우선 작품 검토 | 조사/일부 교정 | 코노스바 본편 교정, 최애의 아이 별칭, 코드 기아스 본편, 헌터 판본/원피스 매핑 검토 |
| 30개 재검증 | 오프라인 완료 | 식별 검증 3 / 수동 검토 27 |
| OTT 회차 구조 | SQL 설계 완료 | 공식 방송 회차와 업로드 관측 분리, 실제 DB 검증 미실행 |
| 수동 회차 검증 | 구현 | 빈 관측 양식 및 90개 확인 작업, 관측 0건 |
| 라프텔 접근 조사 | 조사 완료 | 공개 API/재사용 허가 확인 못함, 자동 수집 미구현 |
| Python 테스트 | 재실행 통과 | 20개, 자세한 결과는 TEST_REPORT.md |
| GitHub 보고 체계 | 추가 | 개발 상태/테스트/알려진 문제, AGENTS.md, PR 양식, 자동 Python 검증 |

## 아직 구현/검증하지 않은 항목

실제 TMDB 인증 재조회, 개별 회차 상세 수집, PostgreSQL 적용/SQL 실행, DB 적재기/권한/RLS, 현재 OTT 회차 관측, 라프텔 계약형 데이터 연동, 최종 검색 사이트, 주기적 재검증 및 30개 독립 정답셋은 미완료다.

이번 작업은 GitHub 관리와 보고 체계를 추가한다. Phase 2 데이터·Python 코드·SQL 및 당시 보고서를 변경하지 않는다. 오프라인 재실행 결과는 별도 로컬 검사 경로에 쓰며 기존 CSV의 조회/검증 시각을 변경하지 않는다.

## 개발·리뷰 운영

feature 브랜치 → 관련 테스트 → 세 문서 갱신 → 비밀정보/차이 검사 → 커밋 → push → main 대상 PR → 외부 리뷰 순서로 진행한다. main 자동 병합과 force push를 하지 않는다. GitHub CLI가 없으면 연결된 GitHub 도구로 PR을 생성한다.

GitHub Actions는 Python 3.10의 단위 테스트·구문·수동 양식·오프라인 검증을 실행한다. 실제 API/OTT/DB 검증은 포함하지 않는다. CI 결과는 GitHub Actions 화면에서 별도 확인한다. 저장소 보호 규칙/required reviews/required status checks의 서버 설정은 이번 작업에서 적용하지 않았으므로 권장 후속 설정이다.
