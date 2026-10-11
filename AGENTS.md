# OTT Anime Finder KR 개발 규칙

## 작업 및 보존

- 작업 시작 시 `git status --short --branch`, remote와 현재 변경사항을 확인한다.
- main은 안정 기준이다. 새 개발은 `feature/<작업명>`에서 진행한다.
- main에 직접 개발 커밋하거나 자동 병합하지 않는다. force push를 하지 않는다.
- 다른 작업의 변경사항을 삭제·덮어쓰기·reset·clean하지 않는다. 기존 CSV는 보존하고 재처리는 별도 output을 사용한다.
- 다른 작업에서 기록한 과거 보고서는 당시 실행 기록이다. 현재 상태와 달라도 지우지 않고 최신 docs에서 시점을 구분한다.

## 검증

- 코드/설정 변경에 관련 검증을 실행한다. Python 기본 검증:
  `C:\Python310-64\python.exe -m unittest discover -s tests -v`
  및 `C:\Python310-64\python.exe -m compileall -q scripts tests`.
- SQL 변경은 별도 테스트 DB에서 `tests/test_db_v02.sql`을 실행한다. 도구나 DB가 없으면 미실행으로 기록한다.
- 실패·재시도·최종 결과·미실행을 `docs/TEST_REPORT.md`에 기록한다. 모의 API 성공을 실제 인증/API/OTT 관측 성공으로 보고하지 않는다.
- 기존 30개 전체 정확도는 독립 정답셋 없이 확정하지 않는다. 방송 회차와 OTT 업로드 회차를 혼동하지 않는다.
- 확인되지 않은 회차·제공 여부·판본은 추정으로 채우지 않는다. 라프텔은 공식 API/허가/계약 확인 전 자동 수집하지 않는다.

## 보안과 보고

- 토큰·.env·인증 파일을 저장소/출력/PR 본문에 노출하지 않는다. 커밋 전 ignore 규칙과 staged 내용을 점검한다.
- `docs/DEVELOPMENT_STATUS.md`, `docs/TEST_REPORT.md`, `docs/KNOWN_ISSUES.md`를 관련 변경에 맞게 갱신한다.
- 완료한 변경을 필요한 파일만 명시해 커밋하고 feature 브랜치에 push한다.
- 가능한 도구로 main 대상 PR을 생성한다. PR 생성 실패 시 원인과 브랜치 URL을 보고한다.
- 완료 보고에는 저장소 URL, 브랜치, SHA, PR URL, 변경 파일, 완료 내용, 테스트 결과, 미해결 문제와 다음 권장 작업을 포함한다.
- main 보호/required checks 설정은 문서 규칙이나 CI 추가만으로 활성화되지 않는다. 실제 적용 여부를 별도 확인한다.
