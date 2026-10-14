"""실행 중인 API에 실제 HTTP 요청을 보내 API-SPEC 계약을 확인한다.

기존 데이터는 지우지 않는다. 테스트가 만든 식당만 조회·수정·삭제한다.
실행: API_BASE=http://127.0.0.1:8010 python -m unittest tests.api_check -v
"""

import http.cookiejar
import json
import os
import time
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta
from urllib.parse import urlencode

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8010")
PASSWORD = "test-password-1"


class Client:
    """쿠키(로그인 세션)를 따로 가지는 HTTP 클라이언트. 사용자마다 하나씩 만든다."""

    def __init__(self):
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def call(self, method: str, path: str, body=None, query: dict | None = None):
        url = BASE + path + ("?" + urlencode(query) if query else "")
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(request) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            with error:
                raw = error.read()
            return error.code, json.loads(raw) if raw else None

    def signup_and_login(self, prefix="t"):
        username = f"{prefix}_{time.time_ns() % 10**12}"
        assert self.call("POST", "/api/auth/signup", {"username": username, "password": PASSWORD})[0] == 201
        assert self.call("POST", "/api/auth/login", {"username": username, "password": PASSWORD})[0] == 200
        return username


# 식당·추천 테스트는 로그인한 테스트 계정 하나로 실행한다.
default_client = Client()


def setUpModule():
    default_client.signup_and_login("api")


def call(method: str, path: str, body=None, query: dict | None = None):
    return default_client.call(method, path, body, query)


def create(**fields):
    status, body = call("POST", "/api/restaurants", {"name": "테스트식당", **fields})
    assert status == 201, (status, body)
    return body


class HealthTest(unittest.TestCase):
    def test_health(self):
        self.assertEqual(call("GET", "/api/health"), (200, {"status": "ok"}))


class CreateAndListTest(unittest.TestCase):
    """R05: 등록·목록(F01, F02)"""

    def test_defaults(self):
        body = create(name="  기본값 확인  ")
        self.assertEqual(body["name"], "기본값 확인")
        expected = {
            "category": "ETC", "price_range": None, "visit_status": "WANT", "rating": None,
            "last_visited_on": None, "location_note": "", "map_url": "", "memo": "",
        }
        self.assertEqual({key: body[key] for key in expected}, expected)
        self.assertRegex(body["created_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_same_name_allowed(self):
        first, second = create(name="같은 이름"), create(name="같은 이름")
        self.assertNotEqual(first["id"], second["id"])

    def test_name_boundaries(self):
        self.assertEqual(len(create(name="가" * 50)["name"]), 50)
        for bad in ["", "   ", "가" * 51, None, 123]:
            with self.subTest(name=bad):
                self.assertEqual(call("POST", "/api/restaurants", {"name": bad})[0], 422)
        self.assertEqual(call("POST", "/api/restaurants", {})[0], 422)

    def test_unknown_or_server_fields_rejected(self):
        for extra in [{"id": 99}, {"created_at": "2026-01-01T00:00:00Z"}, {"unknown": 1}]:
            with self.subTest(extra=extra):
                self.assertEqual(call("POST", "/api/restaurants", {"name": "x", **extra})[0], 422)

    def test_html_kept_as_text(self):
        self.assertEqual(create(name="<b>굵게</b>")["name"], "<b>굵게</b>")

    def test_list_in_created_order(self):
        a, b = create(name="순서A"), create(name="순서B")
        status, items = call("GET", "/api/restaurants")
        self.assertEqual(status, 200)
        ids = [item["id"] for item in items]
        self.assertEqual(ids, sorted(ids))
        self.assertLess(ids.index(a["id"]), ids.index(b["id"]))


class VisitFieldsTest(unittest.TestCase):
    """R07: 음식 종류·가격대·방문 상태·별점·마지막 방문일(F03~F06)"""

    def test_all_values_accepted(self):
        for category in ["KOREAN", "CHINESE", "JAPANESE", "WESTERN", "SNACK", "ETC"]:
            self.assertEqual(create(category=category)["category"], category)
        for price in ["LOW", "MID", "HIGH", None]:
            self.assertEqual(create(price_range=price)["price_range"], price)

    def test_visited_record(self):
        today = date.today().isoformat()
        body = create(visit_status="VISITED", rating=5, last_visited_on=today)
        self.assertEqual((body["visit_status"], body["rating"], body["last_visited_on"]), ("VISITED", 5, today))
        body = create(visit_status="VISITED")
        self.assertEqual((body["rating"], body["last_visited_on"]), (None, None))

    def test_want_clears_record(self):
        body = create(visit_status="WANT", rating=4, last_visited_on="2026-01-01")
        self.assertEqual((body["rating"], body["last_visited_on"]), (None, None))
        future = (date.today() + timedelta(days=1)).isoformat()
        body = create(visit_status="WANT", last_visited_on=future)
        self.assertIsNone(body["last_visited_on"])

    def test_invalid_values(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        cases = [
            {"category": "FAST"}, {"category": None}, {"category": "korean"},
            {"price_range": "CHEAP"}, {"visit_status": "DONE"}, {"visit_status": None},
            {"visit_status": "VISITED", "rating": 0}, {"visit_status": "VISITED", "rating": 6},
            {"visit_status": "VISITED", "rating": "5"}, {"visit_status": "VISITED", "rating": 4.5},
            {"visit_status": "VISITED", "rating": True},
            {"visit_status": "VISITED", "last_visited_on": tomorrow},
            {"visit_status": "VISITED", "last_visited_on": "2026-02-30"},
            {"visit_status": "VISITED", "last_visited_on": "2026/10/01"},
            {"visit_status": "VISITED", "last_visited_on": "2026-10-01T00:00:00"},
            {"visit_status": "VISITED", "last_visited_on": 20261001},
        ]
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(call("POST", "/api/restaurants", {"name": "x", **case})[0], 422)


class NoteFieldsTest(unittest.TestCase):
    """R08: 위치 메모·지도 링크·메모(F07)"""

    def test_boundaries_accepted(self):
        body = create(location_note="가" * 100, map_url="https://m.example.com/" + "a" * 478, memo="메" * 1000)
        self.assertEqual((len(body["location_note"]), len(body["map_url"]), len(body["memo"])), (100, 500, 1000))
        self.assertEqual(create(location_note="😀" * 100)["location_note"], "😀" * 100)

    def test_map_url(self):
        self.assertEqual(create(map_url="  http://map.example.com/a?b=1  ")["map_url"], "http://map.example.com/a?b=1")
        self.assertEqual(create(map_url="HTTPS://Map.example.com")["map_url"], "HTTPS://Map.example.com")
        self.assertEqual(create(map_url="   ")["map_url"], "")
        bad = ["javascript:alert(1)", "JavaScript://x.com/%0aalert(1)", "data:text/html,hi", "ftp://x.com",
               "map.example.com", "https://", "http:///path", "https://a b.com", "//example.com",
               "https://x.com/" + "a" * 487, None, 1]
        for url in bad:
            with self.subTest(url=url):
                self.assertEqual(call("POST", "/api/restaurants", {"name": "x", "map_url": url})[0], 422)

    def test_too_long(self):
        for field, size in [("location_note", 101), ("memo", 1001)]:
            with self.subTest(field=field):
                self.assertEqual(call("POST", "/api/restaurants", {"name": "x", field: "가" * size})[0], 422)
            with self.subTest(field=field, value=None):
                self.assertEqual(call("POST", "/api/restaurants", {"name": "x", field: None})[0], 422)

    def test_memo_keeps_text(self):
        memo = "첫 줄\n<script>alert(1)</script>\n  들여쓰기"
        self.assertEqual(create(memo=memo)["memo"], memo)


class UpdateTest(unittest.TestCase):
    """R09: 부분 수정(F08)"""

    def patch(self, restaurant_id, body):
        return call("PATCH", f"/api/restaurants/{restaurant_id}", body)

    def test_partial_update_keeps_others(self):
        target = create(name="수정 전", category="KOREAN", price_range="LOW", memo="메모 유지", map_url="https://a.com")
        other = create(name="다른 식당")
        status, body = self.patch(target["id"], {"name": "  수정 후  ", "price_range": None})
        self.assertEqual(status, 200)
        self.assertEqual((body["name"], body["price_range"], body["category"], body["memo"], body["map_url"]),
                         ("수정 후", None, "KOREAN", "메모 유지", "https://a.com"))
        self.assertEqual(body["created_at"], target["created_at"])
        _, items = call("GET", "/api/restaurants")
        self.assertIn(other, items)

    def test_visit_record(self):
        target = create()
        status, body = self.patch(target["id"], {"visit_status": "VISITED", "rating": 3, "last_visited_on": "2026-10-01"})
        self.assertEqual((status, body["rating"], body["last_visited_on"]), (200, 3, "2026-10-01"))
        status, body = self.patch(target["id"], {"rating": None})
        self.assertEqual((body["rating"], body["last_visited_on"]), (None, "2026-10-01"))
        status, body = self.patch(target["id"], {"visit_status": "WANT"})
        self.assertEqual((status, body["rating"], body["last_visited_on"]), (200, None, None))
        status, body = self.patch(target["id"], {"rating": 5})  # WANT 상태에서 별점만 보내도 null
        self.assertEqual((status, body["rating"]), (200, None))

    def test_empty_body(self):
        target = create()
        self.assertEqual(self.patch(target["id"], {}), (200, target))

    def test_invalid(self):
        target = create(visit_status="VISITED")
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        cases = [{"name": None}, {"name": " "}, {"category": None}, {"visit_status": None}, {"memo": None},
                 {"location_note": None}, {"map_url": None}, {"map_url": "javascript:alert(1)"}, {"rating": 0},
                 {"last_visited_on": tomorrow}, {"id": 5}, {"created_at": "2026-01-01T00:00:00Z"}, {"x": 1}]
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(self.patch(target["id"], case)[0], 422)
        _, items = call("GET", "/api/restaurants")
        self.assertIn(target, items)  # 거절된 요청은 아무것도 바꾸지 않는다

    def test_not_found(self):
        self.assertEqual(self.patch(999999999, {"name": "x"})[0], 404)
        self.assertEqual(self.patch("abc", {"name": "x"})[0], 422)


class DeleteTest(unittest.TestCase):
    """R10: 삭제(F09)"""

    def test_delete_only_target(self):
        target, other = create(name="삭제 대상"), create(name="남을 식당")
        self.assertEqual(call("DELETE", f"/api/restaurants/{target['id']}"), (204, None))
        ids = [item["id"] for item in call("GET", "/api/restaurants")[1]]
        self.assertNotIn(target["id"], ids)
        self.assertIn(other["id"], ids)
        self.assertEqual(call("DELETE", f"/api/restaurants/{target['id']}")[0], 404)
        self.assertEqual(call("PATCH", f"/api/restaurants/{target['id']}", {"name": "x"})[0], 404)

    def test_not_found(self):
        self.assertEqual(call("DELETE", "/api/restaurants/999999999")[0], 404)
        self.assertEqual(call("DELETE", "/api/restaurants/abc")[0], 422)


class FilterTest(unittest.TestCase):
    """R11: 이름 검색, 음식 종류·방문 상태 필터 AND(F10)"""

    def names(self, **query):
        status, items = call("GET", "/api/restaurants", query=query)
        self.assertEqual(status, 200)
        return [item["name"] for item in items]

    def test_and_filters(self):
        tag = str(time.time_ns())[-9:]
        create(name=f"필터{tag} Kim 한식가봄", category="KOREAN", visit_status="VISITED")
        create(name=f"필터{tag} kim 한식가고싶음", category="KOREAN")
        create(name=f"필터{tag} 중식가봄", category="CHINESE", visit_status="VISITED")
        create(name=f"필터{tag} 100%_특가", category="SNACK")
        self.assertEqual(len(self.names(q=f"필터{tag}")), 4)
        self.assertEqual(self.names(q=f"  필터{tag} KIM  "), [f"필터{tag} Kim 한식가봄", f"필터{tag} kim 한식가고싶음"])
        self.assertEqual(self.names(q=f"필터{tag}", category="KOREAN", visit_status="VISITED"), [f"필터{tag} Kim 한식가봄"])
        self.assertEqual(self.names(q=f"필터{tag}", visit_status="VISITED"), [f"필터{tag} Kim 한식가봄", f"필터{tag} 중식가봄"])
        self.assertEqual(self.names(q=f"필터{tag} 100%_"), [f"필터{tag} 100%_특가"])
        self.assertEqual(self.names(q=f"필터{tag} 1%"), [])
        self.assertEqual(self.names(q=f"필터{tag}_"), [])
        self.assertEqual(self.names(q=f"필터{tag}", category="WESTERN"), [])
        self.assertEqual(len(self.names(q="   ")), len(self.names()))

    def test_invalid_query(self):
        for query in [{"category": "FAST"}, {"visit_status": "want"}, {"q": "가" * 51}]:
            with self.subTest(query=query):
                self.assertEqual(call("GET", "/api/restaurants", query=query)[0], 422)
        self.assertEqual(call("GET", "/api/restaurants", query={"q": "가" * 50})[0], 200)


class RecommendationApiTest(unittest.TestCase):
    """R12: 추천 API(F11~F13). 기존 데이터가 있으므로 테스트가 만든 식당의 후보 여부만 확인한다."""

    def test_exclude_days(self):
        today = date.today()
        made = {
            days: create(visit_status="VISITED", last_visited_on=(today - timedelta(days=days)).isoformat())["id"]
            for days in (0, 6, 7)
        }
        never = create()["id"]
        status, body = call("GET", "/api/recommendation")
        self.assertEqual(status, 200)
        self.assertEqual((body["exclude_days"], body["today"], body["reason"]), (7, today.isoformat(), None))
        ids = [item["id"] for item in body["candidates"]]
        self.assertNotIn(made[0], ids)
        self.assertNotIn(made[6], ids)
        self.assertIn(made[7], ids)
        self.assertIn(never, ids)
        self.assertIn(body["picked"], body["candidates"])
        ids = [item["id"] for item in call("GET", "/api/recommendation", query={"exclude_days": 0})[1]["candidates"]]
        self.assertTrue({made[0], made[6], made[7], never} <= set(ids))

    def test_invalid_exclude_days(self):
        for value in ["1", "5", "-7", "abc", "7.0"]:
            with self.subTest(value=value):
                self.assertEqual(call("GET", "/api/recommendation", query={"exclude_days": value})[0], 422)

    def test_not_saved(self):
        before = call("GET", "/api/restaurants")[1]
        call("GET", "/api/recommendation")
        self.assertEqual(call("GET", "/api/restaurants")[1], before)


class AuthTest(unittest.TestCase):
    """R19: 회원가입·로그인·로그아웃·내 정보(F16~F18)"""

    def username(self):
        return f"auth_{time.time_ns() % 10**12}"

    def test_signup_login_logout(self):
        client, name = Client(), self.username()
        status, body = client.call("POST", "/api/auth/signup", {"username": name, "password": PASSWORD})
        self.assertEqual(status, 201)
        self.assertEqual(set(body), {"id", "username", "created_at"})
        self.assertEqual(len(client.cookies), 0)  # 자동 로그인 없음
        self.assertEqual(client.call("GET", "/api/auth/me"), (401, {"detail": "로그인이 필요합니다."}))
        status, body = client.call("POST", "/api/auth/login", {"username": name, "password": PASSWORD})
        self.assertEqual((status, body["username"]), (200, name))
        cookie = next(iter(client.cookies))
        self.assertEqual(cookie.name, "what_to_eat_session")
        self.assertTrue(cookie.has_nonstandard_attr("HttpOnly"))
        self.assertGreater(cookie.expires - time.time(), 7 * 86400 - 120)
        self.assertEqual(client.call("GET", "/api/auth/me")[1]["username"], name)
        self.assertEqual(client.call("POST", "/api/auth/logout"), (204, None))
        self.assertEqual(client.call("GET", "/api/auth/me")[0], 401)
        self.assertEqual(Client().call("POST", "/api/auth/logout"), (204, None))  # 로그인 안 해도 204

    def test_logout_ends_old_token(self):
        client, name = Client(), self.username()
        client.call("POST", "/api/auth/signup", {"username": name, "password": PASSWORD})
        client.call("POST", "/api/auth/login", {"username": name, "password": PASSWORD})
        stolen = Client()
        for cookie in client.cookies:
            stolen.cookies.set_cookie(cookie)
        self.assertEqual(stolen.call("GET", "/api/auth/me")[0], 200)
        client.call("POST", "/api/auth/logout")
        self.assertEqual(stolen.call("GET", "/api/auth/me")[0], 401)  # 서버에서 세션이 지워짐

    def test_duplicate_and_invalid(self):
        name = self.username()
        self.assertEqual(Client().call("POST", "/api/auth/signup", {"username": name, "password": PASSWORD})[0], 201)
        self.assertEqual(Client().call("POST", "/api/auth/signup", {"username": name, "password": PASSWORD}),
                         (409, {"detail": "이미 사용 중인 아이디입니다."}))
        cases = [{"username": "ab"}, {"username": "a" * 31}, {"username": "Abc"}, {"username": "ab c"},
                 {"username": "가나다"}, {"password": "1234567"}, {"password": "x" * 129}, {"password": 12345678},
                 {"extra": 1}]
        for case in cases:
            with self.subTest(case=case):
                body = {"username": self.username(), "password": PASSWORD, **case}
                self.assertEqual(Client().call("POST", "/api/auth/signup", body)[0], 422)
        self.assertEqual(Client().call("POST", "/api/auth/signup",
                                       {"username": "a_" + str(time.time_ns())[-28:], "password": " " * 8})[0], 201)

    def test_login_failures_same_message(self):
        name = self.username()
        Client().call("POST", "/api/auth/signup", {"username": name, "password": PASSWORD})
        wrong = Client().call("POST", "/api/auth/login", {"username": name, "password": PASSWORD + "x"})
        missing = Client().call("POST", "/api/auth/login", {"username": name + "_none", "password": PASSWORD})
        spaced = Client().call("POST", "/api/auth/login", {"username": name, "password": " " + PASSWORD})
        expected = (401, {"detail": "아이디 또는 비밀번호가 올바르지 않습니다."})
        self.assertEqual((wrong, missing, spaced), (expected, expected, expected))


class OwnerTest(unittest.TestCase):
    """R20: 로그인 필요, 사용자별 식당(F18, F19)"""

    def test_login_required(self):
        anonymous = Client()
        cases = [("GET", "/api/restaurants", None), ("POST", "/api/restaurants", {"name": "x"}),
                 ("POST", "/api/restaurants", {"bad": 1}), ("PATCH", "/api/restaurants/1", {"name": "x"}),
                 ("DELETE", "/api/restaurants/1", None), ("GET", "/api/recommendation", None)]
        for method, path, body in cases:
            with self.subTest(method=method, path=path):
                self.assertEqual(anonymous.call(method, path, body), (401, {"detail": "로그인이 필요합니다."}))
        self.assertEqual(anonymous.call("GET", "/api/health")[0], 200)

    def test_users_are_isolated(self):
        a, b = Client(), Client()
        a.signup_and_login("a")
        b.signup_and_login("b")
        self.assertEqual(b.call("GET", "/api/restaurants"), (200, []))
        self.assertEqual(b.call("GET", "/api/recommendation")[1]["reason"], "NO_RESTAURANTS")
        mine = a.call("POST", "/api/restaurants", {"name": "같은이름", "memo": "A의 메모"})[1]
        theirs = b.call("POST", "/api/restaurants", {"name": "같은이름", "memo": "B의 메모"})[1]
        self.assertEqual([r["id"] for r in a.call("GET", "/api/restaurants")[1]], [mine["id"]])
        self.assertEqual([r["id"] for r in b.call("GET", "/api/restaurants", query={"q": "같은"})[1]], [theirs["id"]])
        rec = b.call("GET", "/api/recommendation", query={"exclude_days": 0})[1]
        self.assertEqual([r["id"] for r in rec["candidates"]], [theirs["id"]])
        self.assertNotIn("owner_id", theirs)
        # 다른 사용자의 식당은 없는 식당과 같은 404이고 바뀌지 않는다.
        not_found = (404, {"detail": "식당을 찾을 수 없습니다."})
        self.assertEqual(b.call("PATCH", f"/api/restaurants/{mine['id']}", {"memo": "B가 바꿈"}), not_found)
        self.assertEqual(b.call("DELETE", f"/api/restaurants/{mine['id']}"), not_found)
        self.assertEqual(a.call("GET", "/api/restaurants")[1], [mine])
        self.assertEqual(a.call("DELETE", f"/api/restaurants/{mine['id']}")[0], 204)
        self.assertEqual(b.call("GET", "/api/restaurants")[1], [theirs])

    def test_logout_blocks_restaurants(self):
        client = Client()
        client.signup_and_login("lo")
        self.assertEqual(client.call("GET", "/api/restaurants")[0], 200)
        client.call("POST", "/api/auth/logout")
        self.assertEqual(client.call("GET", "/api/restaurants")[0], 401)


if __name__ == "__main__":
    unittest.main()
