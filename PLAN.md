# 오늘 뭐 먹지? PLAN
## 작업 원칙
한 번에 아래 작업 하나만 구현한다. 실제 확인 전에는 완료로 표시하지 않는다.
상태는 [ ] 미완료, [x] 확인 완료로 관리하고 확인 결과를 각 항목 아래 기록한다.
API 계약은 API-SPEC.md에 기록하고, 계약을 바꾸는 작업은 API-SPEC.md를 함께 고친다.
나중에 사용자 구분을 추가할 수 있도록 식당은 항상 고유 id로 다루고, 데이터 접근은 백엔드 한곳에 모은다.
## 1장: 백엔드와 DB 기반
- [x] R01: API-SPEC.md 작성. 식당 등록·목록·수정·삭제, 검색·필터, 추천 후보 조회 계약을 정한다. 코드 변경 없음.
  확인: PRD F01~F15가 API-SPEC 항목과 하나씩 대응한다. 입력 위반 응답(422)과 없는 id(404) 규칙이 적혀 있다.
  결정(2026-10-14): 추천은 서버가 후보 목록과 뽑은 식당을 함께 돌려주고, 화면은 그 후보로 슬롯을 돌려 뽑은 식당에서 멈춘다.
  WANT 식당에 별점·방문일이 오면 거절하지 않고 null로 저장한다(VISITED→WANT 수정 시 자동으로 지워짐).
  기록(2026-10-14): API-SPEC.md 작성(공통 규칙, Restaurant 객체, 목록·등록·수정·삭제·추천 API, PRD 대응표).
  포트는 flow-task(8000, Nginx 80)와 겹치지 않게 FastAPI 8010, Nginx 8080으로 정했다. "오늘"은 서버 로컬 날짜(Asia/Seoul).
  결과: PRD F01~F15가 대응표에 하나씩 대응, 422·404·503 규칙 명시. 코드 변경 없음.
- [x] R02: MariaDB 전용 DB·사용자 준비(사용자가 직접 생성), .env와 .env.example(가짜 값) 작성.
  확인: .env 정보로 mariadb 접속 성공, .env가 Git 제외 대상이다.
  기록(2026-10-14): .env.example(가짜 값), .gitignore(.env·.venv·node_modules·dist) 작성. DB·사용자 생성은 root 권한이 필요해 사용자 작업 대기.
  R03~R14는 임시 DB(스크래치 폴더의 MariaDB 11.8.6, 포트 3307)에서 먼저 확인하고, 실제 DB는 R16에서 다시 확인한다.
  기록(2026-10-14): 사용자가 sudo bash deploy/create-db.sh 실행 → what_to_eat DB, what_to_eat_app@localhost(DROP 권한 없음), .env(600) 생성.
  사용자가 .env 비밀번호를 바꿔 프로젝트 .env 접속이 1045 Access denied → deploy/sync-db-password.sh 추가(.env 값으로 ALTER USER, /opt .env 교체·재시작).
  사용자 요청으로 비밀번호 길이 제한(12자)은 뺐다. 결과: 프로젝트 .env 접속 성공, .env 소유자 wnsgh2929:wnsgh2929·600, SHOW GRANTS에 DROP 없음.
- [x] R03: backend 골격. requirements.txt, backend/main.py(/api/health), backend/database.py(.env 읽기, 엔진·세션).
  확인: curl로 /api/health 200과 status=ok, DB SELECT 1 성공.
  기록(2026-10-14): requirements.txt(fastapi 0.143.0, uvicorn 0.54.0, SQLAlchemy 2.1.4, PyMySQL 1.2.3), backend/__init__.py, database.py, main.py(health, DB 오류 503) 작성. Python 3.14.4 .venv.
  결과(임시 DB(스크래치 폴더의 MariaDB 11.8.6, 포트 3307)): /api/health 200 {"status":"ok"}, /docs 200, 없는 경로 404, SELECT 1 = 1(what_to_eat_app@localhost), 엔진 URL 출력 시 비밀번호 *** 표시.
- [x] R04: backend/models.py에 restaurants 테이블(PRD 데이터 항목 전체), backend/init_db.py(없는 테이블만 생성).
  확인: python -m backend.init_db 실행 후 SHOW CREATE TABLE로 열·기본값 확인. 재실행 시 변경 없음, 기존 행 유지.
  기록(2026-10-14): backend/models.py(RestaurantRow, ENUM·VARCHAR 길이·기본값, utf8mb4), init_db.py(없는 테이블만 생성) 작성. memo는 TEXT라 기본값을 앱이 넣는다.
  결과(임시 DB(스크래치 폴더의 MariaDB 11.8.6, 포트 3307)): SHOW CREATE TABLE에서 12개 열·기본값 확인, 재실행 시 "이미 있어 변경하지 않았습니다", 넣어 둔 행 유지.
- [x] R05: GET·POST /api/restaurants. 이름(F01)만 입력받고 나머지는 기본값으로 저장한다. 목록은 등록 순서(F02).
  확인: 등록 201, 같은 이름 두 번 등록, 빈 이름·공백 이름·51자 422, 50자 201, 목록 등록 순서, API 재시작 후 유지.
  기록(2026-10-14): backend/schemas.py(RestaurantCreate·Restaurant), store.py(RestaurantStore), main.py에 GET·POST /api/restaurants 추가.
  tests/api_check.py(표준 라이브러리 urllib로 실제 HTTP 요청, 테스트가 만든 행만 다룸) 작성.
  결과(임시 DB(스크래치 폴더의 MariaDB 11.8.6, 포트 3307), API 8011): api_check 7개 통과(기본값, 같은 이름, 경계값·null·숫자 422, id·created_at 등 422, HTML 글자 저장, id 순서). 재시작 전후 목록 8건 동일.
## 2장: React 화면
- [x] R06: frontend에 React 프로젝트 생성. 이름 입력·등록·목록 화면만 구현하고 /api로만 데이터를 요청한다.
  확인: 브라우저에서 두 식당 등록, 빈 이름 화면에서 거절, `<b>` 같은 입력이 글자로 표시, 새로고침·API 재시작 후 유지,
  API 중지 시 오류 표시. 프런트엔드 코드에 DB 접속 정보가 없다.
  기록(2026-10-14): frontend/(Vite 8.3.4, React 19.3.0, @vitejs/plugin-react 6.1.2) 작성. package.json packageManager npm@10.9.4.
  npm이 설치되어 있지 않아 corepack으로 실행한다(corepack npm@10.9.4 install). 개발 서버는 /api를 API_TARGET(기본 8010)으로 프록시.
  수정: 프록시가 API에 연결 못 하면 502가 와서 "(502)" 문구가 보여, 502·504는 "서버에 연결할 수 없습니다" 문구로 바꿈.
  결과(Playwright 헤드리스 Chromium 156, 스크래치 폴더에만 설치): 6개 통과(두 식당 등록·순서, 빈·공백·51자 화면 거절, HTML 글자 표시,
  새로고침·API 재시작 후 유지, API 중지 시 오류 문구, /api 외 요청 없음). frontend에서 DB_·password·3306 검색 결과 없음.
## 3장: 식당 관리 확장
- [x] R07: 음식 종류(F03)·가격대(F04)·방문 상태(F05)·별점·마지막 방문일(F06)을 API와 화면에 추가한다.
  확인: 기본값 ETC·null·WANT, 허용값 밖 422, 별점 0·6 422, 오늘 이후 방문일 422, WANT 식당은 별점·방문일 null.
  기록(2026-10-14): schemas.py에 category·price_range·visit_status·rating·last_visited_on 추가(YYYY-MM-DD 문자열만 날짜로 받음, WANT면 null로 바꾼 뒤 미래 날짜 검사).
  frontend: labels.js(한글 이름), RestaurantForm.jsx(등록·수정 공용 폼, VISITED일 때만 별점·방문일 칸), RestaurantItem.jsx(목록 항목) 추가.
  결과: api_check 11개 통과(허용값 전체, VISITED 기록, WANT면 null·미래 날짜도 무시, 위반 16종 422). 브라우저 5개 통과(기본값, 가본 식당 표시,
  WANT로 바꾸면 null 전송, 내일 날짜 화면 거절·오늘 허용(max=오늘), 화면 우회 요청 422). R06 회귀 6개 통과.
- [x] R08: 위치 메모·지도 링크·메모(F07)를 API와 화면에 추가한다.
  확인: 최대 길이 경계값, javascript: 등 http·https 외 주소 422, 화면 지도 링크는 http·https만 열린다.
  기록(2026-10-14): schemas.py에 location_note(100)·map_url(공백 제거, http·https와 호스트 필수, 500)·memo(1000) 추가.
  frontend: 폼 입력칸, 목록에 위치 메모·"지도 보기" 링크(rel="noopener noreferrer", 새 탭)·메모(줄바꿈 유지) 표시.
  결과: api_check 15개 통과(100·500·1000자와 이모지 경계값, javascript:·data:·ftp·호스트 없음·공백·501자·null 422). 브라우저 4개 통과(저장·글자 표시,
  잘못된 링크 화면 거절, 101·1001자 거절, DB에 직접 넣은 javascript: 주소는 링크로 만들지 않음). R07 회귀 5개 통과.
- [x] R09: PATCH /api/restaurants/{id}와 수정 화면(F08). 방문 기록도 여기서 바꾼다.
  확인: 보내지 않은 필드 유지, 다른 식당 변경 없음, VISITED→WANT 시 별점·방문일 null, 없는 id 404.
  기록(2026-10-14): schemas.py RestaurantUpdate(보낸 필드만, null 불가 필드 422), store.update(기존 값에 합친 뒤 등록 규칙으로 다시 검증, updated_at 갱신),
  main.py PATCH(합친 값 위반도 422). 화면: 목록 항목 "수정" 버튼 → 같은 자리 수정 폼(기존 값 채움, 이름 칸 포커스), 저장·취소·Esc 후 수정 버튼으로 포커스 복귀.
  api.js가 서버 한글 검증 문구(ctx.error)를 보여 주도록 수정.
  결과: api_check 20개 통과(부분 수정 시 나머지·다른 식당 유지, 별점만 null, WANT로 바꾸면 기록 삭제, {} 200, 위반 13종 422·변경 없음, 없는 id 404).
  브라우저 5개 통과(기존 값·저장·포커스 복귀, 가봄→가보고 싶음, 취소·Esc, 빈 이름·미래 날짜 거절, 404 문구).
- [x] R10: DELETE /api/restaurants/{id}와 삭제 확인(F09).
  확인: 취소 시 유지, 삭제 시 해당 식당만 삭제 204, 재삭제 404.
  기록(2026-10-14): store.delete, main.py DELETE(204·404). 화면: "삭제" 버튼과 확인 창(window.confirm, 식당 이름 표시), 취소하면 요청을 보내지 않는다.
  결과: api_check 22개 통과(해당 식당만 삭제, 재삭제·삭제 후 수정 404, 없는 id 404). 브라우저 3개 통과(취소 시 DELETE 요청 없음·새로고침 후 유지,
  확인 시 해당 식당만 삭제, 확인 창에 HTML 이름 글자 그대로). R06~R09 회귀 통과.
- [x] R11: 이름 검색, 음식 종류·방문 상태 필터 AND 적용(F10).
  확인: 필터 조합 결과, 필터 중 수정·삭제가 정확한 식당에 적용, Tab 키로 검색창→음식 종류→방문 상태 순서 이동.
  기록(2026-10-14): GET /api/restaurants에 q(공백 제거, 최대 50자, %·_ 글자 그대로, 대소문자 무시)·category·visit_status 추가.
  화면: FilterBar.jsx(검색창→음식 종류→방문 상태), 검색어 200ms 대기 후 요청, 늦게 온 이전 응답 무시, 결과 수·"조건에 맞는 식당이 없습니다" 표시.
  결과: api_check 24개 통과(AND 조합, 대소문자, %·_ 이스케이프, 잘못된 쿼리·51자 422). 브라우저 4개 통과(AND 필터, 필터 중 수정·삭제가 해당 식당에만 적용·필터 유지,
  Tab·Shift+Tab 순서와 키보드 선택, 빠른 입력 시 마지막 결과). R06~R10 회귀 통과.
## 4장: 무작위 추천
- [x] R12: 최근 방문 제외 기간(제외 안 함·3·7·14일, 기본 7일) 선택과 후보 계산, 같은 확률 추천(F11~F13).
  확인: 7일 기준 오늘·6일 전 방문 제외, 7일 전 방문·방문일 없음 포함. 식당 없음과 모두 최근 방문의 이유 문구가 다르다.
  기록(2026-10-14): backend/recommend.py(후보 계산·같은 확률 선택, DB와 분리), schemas.py Recommendation, main.py GET /api/recommendation.
  수정: exclude_days를 Literal 정수로 받으니 쿼리 "3"도 422가 되고, int로 받으니 "7.0"이 통과해 쿼리 문자열을 0·3·7·14와 그대로 비교하도록 변경.
  화면: RecommendPanel.jsx(제외 기간 기본 7일, 추천 받기, 이유 문구), RestaurantDetails.jsx(목록·결과 공용 정보 표시)로 분리.
  결과: tests/test_recommend.py 4개 통과(DB 없이 실행, 0·3·7·14일 경계값, 이유 2종, 6000번 뽑기 각 1/3±0.03). api_check 27개 통과
  (오늘·6일 전 제외, 7일 전·방문일 없음 포함, 0일이면 모두 후보, 1·5·-7·abc·7.0 422, 추천 후 목록 변화 없음).
  브라우저 5개 통과(기본 7일, 선택 기간으로 요청·결과 이름, 이유 문구 2종(응답 모의), 결과 정보 표시·메모 숨김, 502 문구).
- [x] R13: 슬롯머신 결과 공개와 결과 식당 정보 표시, 다시 돌리기(F14).
  확인: 후보 이름만 돌고 멈춘 이름과 표시 정보가 일치, 다시 돌리기 동작, 사용자 입력은 글자로 표시.
  기록(2026-10-14): src/slot.js(buildFrames: 후보 이름 23개 + 마지막 뽑힌 식당, 점점 느려지는 간격 약 2.5초, useSlotSpin 훅), 슬롯 창(aria-hidden)과 멈춘 뒤 결과 카드(aria-live).
  결과: 브라우저 4개 통과(22번 바뀌며 2.8초, 후보 이름만 표시·뽑힌 식당에서 멈춤·멈춘 뒤에만 결과 카드, 다시 돌리기, 후보 1개, 실제 API 결과).
- [x] R14: 도는 중 Enter로 건너뛰기, 움직임 줄이기 설정 시 애니메이션 없이 결과 표시(F15).
  확인: Enter 즉시 결과, 브라우저·OS 움직임 줄이기 설정에서 바로 결과.
  기록(2026-10-14): 도는 중 window keydown Enter → 바로 결과(입력칸의 Enter는 가로채지 않음), 같은 버튼이 "바로 보기"로 바뀌고 안내 문구 표시.
  prefers-reduced-motion이면 돌리지 않고 결과 표시, CSS 애니메이션도 끔.
  수정: 요청 중 버튼을 disabled로 만들면 키보드 포커스가 사라져, disabled 대신 요청 중 클릭을 무시하도록 변경.
  결과: 브라우저 4개 통과(Enter 후 0.01초 결과·추가 요청 없음·포커스 유지, 멈춘 뒤 Enter는 다시 돌리기, 입력칸 Enter는 폼 동작 유지,
  reduced_motion=reduce에서 0.28초 결과·animation none). R06~R13 회귀, vite build 성공, 390px 너비 가로 스크롤 없음.
## 5장: 역할 분리와 최종 확인
- [x] R15: Nginx가 React 빌드 결과를 제공하고 /api를 FastAPI로 프록시한다. FastAPI·MariaDB는 각자 실행한다.
  확인: Nginx 주소로 등록·조회, FastAPI 재시작 후 데이터 유지, DB 접속 정보가 백엔드에만 있다.
  기록(2026-10-14, 진행 중): deploy/create-db.sh(R02용, 무작위 비밀번호를 .env에만 저장, 기존 DB·사용자·.env가 있으면 멈춤, DROP 권한 없음),
  install-api.sh·what-to-eat-api.service(/opt/what-to-eat, 계정 what-to-eat, 127.0.0.1:8010, 없는 테이블만 생성),
  install-web.sh·what-to-eat-web.conf(/var/www/what-to-eat, 8080, /api/ → 8010, default·flow-task 사이트는 건드리지 않음) 작성.
  사전 확인(sudo 없이 내 계정으로 같은 server 블록을 127.0.0.1:18080에 띄움, API는 임시 DB의 8011): nginx -t 성공, / ·깊은 경로 200(index.html),
  /api/health·restaurants·recommendation 200, 없는 API 404 JSON, /assets/ 30일 캐시. 빌드 결과로 R06~R14 브라우저 테스트 40개 모두 통과.
  임시 DB를 끄면 /api/restaurants 503 한글 문구, health 200, 로그에 비밀번호 없음, DB 재시작 후 200.
  설치(사용자 실행): install-api.sh(restaurants 테이블 생성, 서비스 active·enabled, 8010 health·restaurants 200), install-web.sh(nginx -t 성공, 8080 / 200, /api/health 200).
  결과: 8080(실제 Nginx→8010→실제 DB)에서 등록·조회, SQL COUNT와 API 목록 수 일치(58건). 8010은 127.0.0.1에서만 받음(WSL IP로 접근 불가).
  /var/www/what-to-eat에 DB 정보 없음, /opt/what-to-eat/.env는 what-to-eat 계정 600(다른 계정 읽기 거부). flow-task(80, task-flow-api) 정상 유지.
  API 재시작 후 유지: systemd 서비스 재시작은 sudo가 필요해, 같은 실제 DB에 연결한 별도 API(8011)를 끄고 다시 켜 확인했다(R16의 R06 테스트).
- [x] R16: PRD 완료 기준 전체 점검.
  확인: PRD 완료 기준 각 문장을 Nginx 주소에서 하나씩 확인하고 결과를 기록한다.
  기록(2026-10-14): 실제 DB가 빈 상태에서 추천 → NO_RESTAURANTS, 오늘 방문 식당 1개만 두고 7·3일 → ALL_RECENTLY_VISITED, 0일 → 추천됨(확인 후 그 식당 삭제).
  api_check 27개(8080 경유)·test_recommend 4개 통과. 브라우저: R07~R14 35개는 실제 Nginx 8080, R06 6개는 실제 DB에 연결한 8011 API+임시 Nginx 18080(재시작·중지 확인용)으로 모두 통과.
  PRD 완료 기준 대응: 등록·빈 이름 거절(R05·R06), 수정·삭제 취소·필터 중 정확한 수정(R09~R11), 가본 식당 기록·가보고 싶음 미기록(R07·R09),
  제외 기간 후보와 이유(R12·위 실제 확인), 슬롯머신·Enter·움직임 줄이기(R13·R14), Tab 순서(R11), 재시작 후 유지(R06), HTML 글자 표시·http/https 링크만(R06·R08).
  남은 일: 테스트가 실제 DB에 만든 식당 58건(id 2 이후, 테스트 전 0건)은 일괄 삭제가 권한 확인에서 막혀 남아 있다. 사용자 확인 후 정리한다.
## 6장: 로그인과 사용자별 목록 (PRD F16~F20)
결정(2026-10-14, 사용자): 로그인만 넣고 목록은 사용자별 개인 목록(팀 공유 없음). 기존 식당은 처음 가입한 계정에 붙인다.
화면은 로그인 전 시작 화면을 만들고, 다크 모드가 아닌 새 디자인으로 바꾼다. 세부 규칙은 flow-task(F10~F12)와 같게 맞춘다.
- [x] R17: API-SPEC.md에 인증 API와 식당·추천 API 변경(로그인 필요, 본인 식당만) 작성. 코드 변경 없음.
  확인: PRD F16~F20이 API-SPEC 항목과 하나씩 대응한다.
  기록(2026-10-14): PRD에 계정 요구사항 F16~F20 추가(제외 기능에서 로그인·회원가입 제거, 팀 공유는 계속 제외), 데이터·완료 기준 갱신.
  API-SPEC.md에 세션 쿠키(what_to_eat_session, HttpOnly·SameSite=Lax·7일 고정), 로그인 불필요 경로, User 객체, signup·login·logout·me,
  식당·추천 API의 사용자 범위, 401·409 상태 코드 추가. 결과: 대응표에 F16~F20 행 존재. 코드 변경 없음.
- [x] R18: users·sessions 테이블 추가, restaurants에 owner_id(NULL 허용, 외래키·인덱스) 추가. 기존 테이블은 ALTER로 열만 추가한다.
  확인: SHOW CREATE TABLE로 새 열·외래키·인덱스·유일 제약 확인, 기존 행 수 유지, 스크립트 재실행 시 변경 없음.
  기록(2026-10-14): models.py에 UserRow(username UNIQUE)·SessionRow(token_hash CHAR(64) PK, user_id FK·인덱스, expires_at), RestaurantRow.owner_id(NULL, FK·인덱스).
  init_db.py가 없는 테이블을 만들고, 기존 restaurants에는 owner_id 열·인덱스·외래키 중 없는 것만 ALTER로 추가(MariaDB DDL은 되돌릴 수 없어 단계별 확인).
  결과(임시 DB, 실제 DB와 같은 권한·예전 구조·564건): 1회차 users·sessions 생성과 열·인덱스·외래키 추가, 2회차 변경 없음, 564건 유지.
  외래키만 지운 상태(중간 실패 흉내)에서 외래키만 다시 추가, 빈 새 DB는 create_all로 같은 구조 생성.
- [x] R19: 회원가입·로그인·로그아웃·내 정보 API. 비밀번호는 hashlib.scrypt, 세션 토큰은 secrets로 발급하고 해시만 저장.
  첫 가입 계정에 작성자 없는 식당을 붙인다.
  확인: 가입 201(자동 로그인 없음), 중복 409, 형식 위반 422, 틀린 비밀번호·없는 아이디 같은 401, 로그인 후 me 200,
  로그아웃 후 401, 만료 세션 401, DB에 비밀번호·토큰 원문 없음, 첫 가입자만 기존 식당을 받는다.
  기록(2026-10-14): backend/auth.py(scrypt n=2^14·r=8·p=1 해시 문자열, 없는 아이디도 같은 계산, secrets 토큰·SHA-256 해시 저장, 7일 고정 만료,
  로그인 시 그 사용자의 만료 세션 정리, current_user 의존성), schemas.py Credentials·User, main.py signup·login·logout·me. 새 패키지 없음(표준 라이브러리).
  tests/api_check.py를 사용자별 쿠키 클라이언트로 바꾸고 AuthTest 추가.
  결과: api_check 31개 통과(가입 201·쿠키 없음, 로그인 쿠키 HttpOnly·7일, me·로그아웃, 로그아웃한 토큰 재사용 401, 중복 409, 형식 위반 9종 422,
  틀린 비밀번호·없는 아이디·앞 공백 비밀번호 같은 401). DB: 비밀번호 원문 0건, 해시 scrypt$…, token_hash 64자, 만료시각을 과거로 바꾸면 me 401,
  기존 564건이 첫 가입 계정(id 1)에 연결, API 로그에 비밀번호·토큰 없음.
- [x] R20: 식당·추천 API에 로그인·소유자 적용. 로그인 없으면 401, 등록 시 owner_id=로그인 사용자.
  확인: 두 계정(A·B)으로 서로의 식당이 목록·검색·추천에 없고 수정·삭제는 404, 같은 이름도 각자 등록 가능.
  기록(2026-10-14): store.py 모든 메서드에 owner_id 범위(다른 사용자 식당은 None → 404), main.py 식당·추천 API에 current_user 적용.
  결과: api_check 38개(+test_recommend) 통과. 로그인 없이 식당·추천 6종 401(잘못된 본문도 401 먼저), health 200.
  A·B 계정: B 목록 빈 배열·NO_RESTAURANTS, 같은 이름 각자 등록, 목록·검색·추천에 자기 식당만, B가 A 식당 PATCH·DELETE 404·변경 없음, 로그아웃 후 401.
- [x] R21: 프런트엔드 시작 화면(로그인 전), 로그인·회원가입 화면, 로그인 아이디·로그아웃 버튼, 401 응답 시 시작 화면 전환.
  확인: 브라우저에서 가입·로그인·로그아웃·새로고침 후 로그인 유지, 잘못된 로그인 문구, 아이디 글자 표시, 키보드로 조작.
  기록(2026-10-14): App.jsx를 로그인 확인·화면 선택(#/ 시작, #/login, #/signup)으로 바꾸고 기존 메인 화면은 Home.jsx로 옮김(상단에 아이디·로그아웃).
  AuthPages.jsx(시작 화면, 로그인, 회원가입 — 비밀번호 확인 칸, 가입 후 아이디 채운 로그인 화면), api.js(인증 함수, 사용 중 401이면 로그인 화면으로),
  validation.js(가입 규칙, 로그인은 빈 칸만 확인하고 형식 오류도 같은 실패 문구).
  수정: 로그아웃 직후 늦게 온 401이 "다시 로그인" 안내로 덮어쓰지 않도록 로그인 상태일 때만 전환.
  결과(임시 DB): 브라우저 9개 통과(시작 화면·Tab, 가입 검증 3종, 가입 후 자동 로그인 없음·아이디 채움·비밀번호 포커스, 중복 문구,
  로그인 실패 3종 같은 문구·빈 칸 문구, HttpOnly·SameSite=Lax 쿠키·document.cookie 빈 값·새로고침·새 탭 유지, 내 식당만,
  DB에서 세션을 지우면 다음 요청 때 로그인 화면·안내, 로그아웃 후 401·뒤로 가기에도 목록 없음). R06~R14 회귀 40개 통과(테스트마다 새 계정으로 로그인).
- [x] R22: 화면 디자인 변경(다크 모드 아님). 기능·접근성(포커스 표시, Tab 순서, 움직임 줄이기)은 유지한다.
  확인: 데스크톱·390px 화면 확인, 가로 스크롤 없음, R06~R21 화면 테스트 회귀.
  기록(2026-10-14): App.css 새로 작성(크림색 바탕·토마토 주황 강조·둥근 카드, 색은 :root 변수, 밝은 테마 하나). 넓은 화면(960px 이상)은 왼쪽 추천·등록, 오른쪽 목록 2단.
  시작 화면(소개·로그인·회원가입·기능 3개), 로그인 카드, 상단 고정 헤더(아이디·로그아웃), 전구 테두리 슬롯머신, 음식 종류 그림 문자(aria-hidden)와 칩.
  화면 순서(DOM)와 테스트가 쓰는 클래스는 유지, 움직임 줄이기 시 애니메이션·전환 끔.
  결과: 1280px·390px 스크린샷(스크래치 폴더에 Noto Sans KR을 받아 테스트 브라우저에서만 사용) 확인, 두 크기 모두 가로 스크롤 없음.
  색 대비 12쌍 모두 4.5:1 이상(가장 낮은 것 가봄 배지 4.63). 브라우저 회귀 R06~R14·R21 49개, api_check·test_recommend 통과.
  참고: 테스트 브라우저에는 이모지 글꼴이 없어 그림 문자가 네모로 보였다(Windows 브라우저에서는 정상 표시 예상).
- [ ] R23: 배포 반영(설치 스크립트가 R18 변경을 실제 DB에 적용)과 실제 환경 통합 확인.
  확인: 기존 20곳이 첫 가입 계정에 붙음, 8080에서 가입·로그인·추천, API 재시작 후 로그인·데이터 유지.
  기록(2026-10-14, 진행 중): install-api.sh를 git archive(HEAD의 backend·requirements.txt)로 설치하도록 변경, install-web.sh는 frontend 미커밋 변경·오래된 빌드면 멈춤.
  사전 확인: 빌드 결과를 임시 Nginx(18080)+임시 API(8011)로 R21·R13·R06 19개 통과.
  배포(사용자 실행, 16:20): install-api.sh·install-web.sh. 결과: /opt/what-to-eat·/var/www/what-to-eat가 커밋 b954787(R24 포함)과 같음,
  8080에서 로그인 없이 /api/auth/me·/api/restaurants 401. 사용자가 먼저 가입한 wnsgh2929(id 1)에 기존 20곳이 모두 연결, 다른 계정 없음.
  남은 확인: 실제 DB에는 테스트 계정을 만들지 않기로 해, 실제 환경에서 API 재시작 후 로그인 유지는 사용자 확인 대기
  (임시 DB에서는 R21 테스트로 확인). flow-task(80) 정상.
## 7장: 추천 조건 (PRD F21)
결정(2026-10-14, 사용자 요청): 추천에 음식 종류 선택을 추가한다. 기본값 전체, 최근 방문 제외와 AND. 가격대·방문 상태 조건은 계속 제외.
- [x] R24: GET /api/recommendation에 category 조건과 이유 NO_CATEGORY_RESTAURANTS 추가, 추천 화면에 음식 종류 선택 칸 추가.
  확인: 한식을 고르면 한식만 후보·결과, 제외 기간과 AND, 이유 3종 문구, 잘못된 값 422, 전체는 기존과 같음, Tab 순서, R12~R14 회귀.
  기록(2026-10-14): PRD F21 추가(F13 이유에 "고른 음식 종류의 식당 없음", 제외 기능에서 음식 종류 조건 제거), API-SPEC category 쿼리·응답·이유 추가.
  recommend.py에 category 조건(전체→종류→최근 방문 순으로 걸러 이유 구분), main.py category 검사(빈 값=전체, 그 외 정확히 일치), 응답에 category.
  화면: 추천 영역에 음식 종류 선택(전체+6종, 제외 기간 앞), 이유 문구에 종류 이름 표시.
  결과: test_recommend 7개(종류·제외 AND, 이유 3종, 종류 안에서 같은 확률), api_check 43개 통과(KOREAN만 후보, 0일과 AND, 빈 값=전체, JAPANESE 없음 이유,
  모두 최근 방문 이유, korean·FAST·" KOREAN"·1 422). 브라우저 4개 통과(기본 전체·선택지 7개·Tab 순서, 한식 3회 모두 슬롯·결과 한식만,
  이유 문구 2종·제외 안 함과 AND, 전체로 돌아가면 category 없이 요청). R06~R14·R21 회귀 통과.
  수정(테스트): R13 테스트의 결과 카드 중복 확인이 카드가 막 나타난 순간 실패하는 경쟁 조건이라 중복 확인 제거(3회 연속 통과).
## 8장: 기본 맛집 목록 (PRD F22)
결정(2026-10-14, 사용자 요청): 가입하면 기본 맛집 목록을 그 계정의 식당으로 복사한다(사용자별 복사본이라 각자 수정·삭제). 맛집을 더 찾아 목록을 늘리고 기존 계정에도 추가한다.
- [x] R25: backend/default_restaurants.json(기존 20곳)과 가입 시 복사, 기존 계정에 빠진 기본 맛집만 추가하는 명령(python -m backend.add_defaults).
  확인: 새 가입자 목록에 기본 맛집이 등록 순서대로, 수정·삭제가 다른 계정에 영향 없음, 첫 가입자(기존 식당 받음)는 복사 안 함, 명령 재실행 시 중복 없음.
  기록(2026-10-14): PRD F22 추가. backend/default_restaurants.json(기존 20곳), defaults.py(서버 시작 때 등록 규칙·이름 중복 검사), auth.py 가입 시
  기존 식당을 받지 않은 계정에 같은 트랜잭션으로 복사, add_defaults.py(이름이 같은 식당은 건너뛰고 추가, 없는 아이디는 종료 코드 1).
  테스트 계정은 가입 직후 기본 맛집을 지우고 시작하도록 tests/api_check.py·화면 테스트 도구 수정.
  결과: api_check 44개 통과(새 계정에 20곳 파일 순서·값 동일·WANT, 추천 후보 20곳, A의 수정·삭제가 B에 영향 없음, 직접 등록 201).
  새 임시 DB: 기존 식당 2곳을 받은 첫 가입자는 2곳만, 두 번째 가입자 20곳, 빈 DB 첫 가입자 20곳. add_defaults는 이름 겹친 1곳을 건너뛰고 19곳 추가,
  재실행 0곳, 없는 아이디 종료 코드 1. 브라우저 R06~R14·R21·R24 회귀 통과(R21은 가입 직후 기본 맛집 20곳 표시 확인으로 변경).
  수정(테스트): R13의 마지막 슬롯 이름 확인을 결과 카드가 뜬 뒤 다시 읽도록 바꿈(5회 연속 통과).
- [x] R26: 맛집 추가 조사(웹 검색)로 기본 목록 확장, 실제 계정(wnsgh2929)에 새 맛집 추가.
  확인: 목록 항목 모두 등록 규칙 통과, 이름 중복 없음, 출처 기록, 실제 계정 식당 수 증가·기존 20곳 그대로.
  기록(2026-10-14): 웹 검색(내일신문, 뽈레, 식신, 핫플레이스헌터 후기)으로 20곳 추가 → 기본 목록 40곳(한식 11, 중식 6, 일식 6, 양식 7, 분식 2, 기타 8).
  다른 동네(압구정 루비떡볶이, 논현역 도셰프 등)·폐점 표시(감성타코, 봄베이 브로이, 수엠부 등)는 제외. 멕시칸·인도·태국은 기타(ETC)로 분류.
  가격대는 근거 있는 곳만(엉터리생고기 LOW), 지도 링크는 네이버 지도 검색 주소, 메모에 "방문 전 영업 여부 확인 필요". 이도곰탕 주소(논현로94길 29-5)를 기본 목록에만 반영.
  결과: defaults.py 검증 40곳 통과, DefaultRestaurantsTest·OwnerTest 통과. 실제 DB: python -m backend.add_defaults wnsgh2929 → 20곳 추가(20→40), 계정별 이름 중복 0.
  남은 일: 새 가입자가 40곳을 받으려면 sudo bash deploy/install-api.sh로 서버 반영(화면 변경 없음).
