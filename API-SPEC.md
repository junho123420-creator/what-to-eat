# 오늘 뭐 먹지? API 명세

PRD.md의 요구사항을 API 계약으로 정리한다. 구현 순서는 PLAN.md를 따른다.

## 공통
- 기본 주소: `http://127.0.0.1:8010` (개발). 모든 경로는 `/api`로 시작한다.
- 화면은 Nginx(`http://localhost:8080`, R15)나 React 개발 서버를 통해 같은 주소의 `/api`로 요청한다. CORS는 허용하지 않는다.
- 요청·응답 본문은 JSON(UTF-8)이다.
- 날짜는 `YYYY-MM-DD`, 일시는 ISO 8601 UTC 문자열(예: `2026-10-14T05:12:30Z`)이다.
- "오늘"은 서버의 로컬 날짜(개발 서버 시간대 Asia/Seoul)이다. 화면도 브라우저 로컬 날짜를 쓴다.
- 오류 응답은 FastAPI 기본 형식 `{"detail": ...}`을 사용한다.
- 정의되지 않은 필드를 보내면 422로 거절한다.
- 사용자 입력은 받은 글자 그대로 저장하고, 화면은 HTML로 해석하지 않고 글자로 표시한다.

| 상태 코드 | 의미 |
|---|---|
| 200 | 조회·수정 성공 |
| 201 | 등록 성공 |
| 204 | 삭제 성공(본문 없음) |
| 404 | 대상 식당 없음. `{"detail": "식당을 찾을 수 없습니다."}` |
| 422 | 입력값 검증 실패 |
| 503 | DB 연결 실패 또는 DB 처리 오류. `{"detail": "DB에 연결할 수 없거나 처리 중 오류가 발생했습니다."}` |

## GET /api/health  (R03)
- 응답 200: `{"status": "ok"}`. DB 상태와 관계없이 API가 살아 있는지만 알려 준다.

## Restaurant 객체

| 필드 | 타입 | 규칙 | 기본값 | PRD |
|---|---|---|---|---|
| id | 정수 | 서버가 발급. 수정·삭제는 id로 한다 | - | 데이터 |
| name | 문자열 | 앞뒤 공백 제거 후 1~50자. 같은 이름 허용 | 필수 | F01 |
| category | 문자열 | `KOREAN` `CHINESE` `JAPANESE` `WESTERN` `SNACK` `ETC` | `ETC` | F03 |
| price_range | 문자열 또는 null | `LOW` `MID` `HIGH` 또는 null | null | F04 |
| visit_status | 문자열 | `WANT` `VISITED` | `WANT` | F05 |
| rating | 정수 또는 null | 1~5. `WANT`이면 항상 null | null | F06 |
| last_visited_on | 문자열 또는 null | `YYYY-MM-DD`, 오늘 이후 불가. `WANT`이면 항상 null | null | F06 |
| location_note | 문자열 | 최대 100자 | `""` | F07 |
| map_url | 문자열 | `""` 또는 `http://`·`https://`로 시작하고 호스트가 있는 주소, 앞뒤 공백 제거 후 최대 500자, 중간 공백 불가 | `""` | F07 |
| memo | 문자열 | 최대 1000자 | `""` | F07 |
| created_at | 문자열 | 등록 UTC 일시 | 서버 | 데이터 |
| updated_at | 문자열 | 마지막 수정 UTC 일시 | 서버 | 데이터 |

- 길이는 글자 수(유니코드 문자) 기준이다.
- `visit_status`가 `WANT`이면 보낸 `rating`·`last_visited_on`을 거절하지 않고 null로 저장한다(결정 2026-10-14).
- 타입이 다르거나(예: rating `"5"`, `4.5`) 허용값 밖이면 422이다.

```json
{
  "id": 1, "name": "김밥천국 역삼점", "category": "SNACK", "price_range": "LOW",
  "visit_status": "VISITED", "rating": 4, "last_visited_on": "2026-10-10",
  "location_note": "역삼역 3번 출구", "map_url": "https://map.example.com/123", "memo": "",
  "created_at": "2026-10-14T05:00:00Z", "updated_at": "2026-10-14T05:00:00Z"
}
```

## GET /api/restaurants  (R05, 필터는 R11)
- 응답 200: `Restaurant` 배열. 등록 순서(id 오름차순)로 정렬한다(F02).
- 쿼리(모두 선택, AND 조건, F10):
  - `q`: 이름에 포함된 글자(대소문자 무시). 앞뒤 공백 제거 후 빈 값이면 조건 없음. 최대 50자.
  - `category`: 음식 종류 하나.
  - `visit_status`: 방문 상태 하나.
- 허용값 밖 쿼리는 422.

## POST /api/restaurants  (R05, 필드 확장은 R07·R08)
- 요청: `name`만 필수, 나머지는 위 표의 기본값을 쓴다. `id`·`created_at`·`updated_at`은 보낼 수 없다.
```json
{ "name": "김밥천국 역삼점", "category": "SNACK" }
```
- 응답 201: 등록한 `Restaurant`.

## PATCH /api/restaurants/{id}  (R09)
- 보낸 필드만 바꾸고 보내지 않은 필드는 유지한다(F08). 빈 본문 `{}`은 아무것도 바꾸지 않고 200.
- `name` `category` `visit_status` `location_note` `map_url` `memo`는 null 불가(422).
  `price_range` `rating` `last_visited_on`은 null로 지울 수 있다.
- 바꾼 뒤의 상태가 `WANT`이면 `rating`·`last_visited_on`을 null로 저장한다(예: `{"visit_status": "WANT"}`만 보내도 지워짐).
- 응답 200: 수정한 `Restaurant`. 없는 id 404.

## DELETE /api/restaurants/{id}  (R10)
- 응답 204. 없는 id 404. 삭제 확인은 화면에서 한다(F09).

## GET /api/recommendation  (R12)
- 쿼리 `exclude_days`: `0`(제외 안 함), `3`, `7`, `14` 중 하나. 기본 `7`(F12).
  그 외 값(`7.0`, `-7` 포함)은 422 `{"detail": "최근 방문 제외 기간은 0, 3, 7, 14일 중 하나여야 합니다."}`.
- 후보: 저장한 식당 중 `last_visited_on`이 null이거나, 오늘과의 차이가 `exclude_days`일 이상인 식당.
  예: `exclude_days=7`, 오늘 10-14 → 10-08~10-14 방문은 제외, 10-07 이전 방문과 방문일 없음은 후보.
- 서버가 후보 중 하나를 같은 확률로 뽑는다(F11, 결정 2026-10-14). 결과는 저장하지 않는다.
- 응답 200:
```json
{ "exclude_days": 7, "today": "2026-10-14", "candidates": [Restaurant, ...], "picked": Restaurant, "reason": null }
```
- 후보가 없으면 `picked`는 null, `candidates`는 빈 배열이고 `reason`으로 이유를 알려 준다(F13):
  - `NO_RESTAURANTS`: 저장한 식당이 없음.
  - `ALL_RECENTLY_VISITED`: 식당은 있지만 모두 제외 기간 안에 방문함.
- 화면은 `candidates` 이름으로 슬롯머신을 돌리고 `picked`에서 멈춘다(F14, F15).

## PRD 대응표

| PRD | API |
|---|---|
| F01 | POST name 규칙(공백 제거 1~50자, 중복 허용) |
| F02 | GET /api/restaurants id 오름차순 |
| F03~F05 | Restaurant category·price_range·visit_status 허용값과 기본값 |
| F06 | rating·last_visited_on 규칙, WANT이면 null, 오늘 이후 422 |
| F07 | location_note·map_url·memo 길이와 http·https 규칙 |
| F08 | PATCH 부분 수정, 방문 기록 포함 |
| F09 | DELETE (확인은 화면) |
| F10 | GET 쿼리 q·category·visit_status AND (Tab 순서는 화면) |
| F11 | GET /api/recommendation 같은 확률 선택 |
| F12 | exclude_days 0·3·7·14, 기본 7, 오늘 포함 |
| F13 | picked null과 reason 두 가지 |
| F14·F15 | candidates·picked로 화면이 슬롯머신 표시 |
