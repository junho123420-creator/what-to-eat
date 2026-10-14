"""추천 후보 계산 규칙(R12). DB·API 없이 실행한다.
실행: python -m unittest tests.test_recommend -v
"""

import random
import unittest
from collections import Counter
from datetime import date, datetime, timedelta

from backend.recommend import recommend
from backend.schemas import Restaurant

TODAY = date(2026, 10, 14)


def restaurant(rid, visited_days_ago=None, category="ETC"):
    last = None if visited_days_ago is None else TODAY - timedelta(days=visited_days_ago)
    now = datetime(2026, 10, 14)
    return Restaurant(id=rid, name=f"식당{rid}", category=category, price_range=None,
                      visit_status="WANT" if last is None else "VISITED", rating=None, last_visited_on=last,
                      location_note="", map_url="", memo="", created_at=now, updated_at=now)


class RecommendTest(unittest.TestCase):
    def ids(self, result):
        return [r.id for r in result.candidates]

    def test_exclude_boundaries(self):
        items = [restaurant(1, 0), restaurant(2, 2), restaurant(3, 3), restaurant(4, 6), restaurant(5, 7),
                 restaurant(6, 13), restaurant(7, 14), restaurant(8)]
        expected = {0: [1, 2, 3, 4, 5, 6, 7, 8], 3: [3, 4, 5, 6, 7, 8], 7: [5, 6, 7, 8], 14: [7, 8]}
        for days, ids in expected.items():
            with self.subTest(exclude_days=days):
                result = recommend(items, days, TODAY)
                self.assertEqual(self.ids(result), ids)
                self.assertIn(result.picked.id, ids)
                self.assertIsNone(result.reason)

    def test_no_restaurants(self):
        result = recommend([], 7, TODAY)
        self.assertEqual((result.candidates, result.picked, result.reason), ([], None, "NO_RESTAURANTS"))

    def test_all_recently_visited(self):
        result = recommend([restaurant(1, 0), restaurant(2, 6)], 7, TODAY)
        self.assertEqual((result.candidates, result.picked, result.reason), ([], None, "ALL_RECENTLY_VISITED"))
        self.assertEqual(recommend([restaurant(1, 0)], 0, TODAY).picked.id, 1)

    def test_uniform(self):
        items = [restaurant(1), restaurant(2), restaurant(3), restaurant(4, 0)]
        rng = random.Random(20261014)
        counts = Counter(recommend(items, 7, TODAY, rng=rng).picked.id for _ in range(6000))
        self.assertEqual(set(counts), {1, 2, 3})
        for rid in (1, 2, 3):
            self.assertAlmostEqual(counts[rid] / 6000, 1 / 3, delta=0.03)


class CategoryTest(unittest.TestCase):
    """R24: 음식 종류 조건(F21)"""

    items = [restaurant(1, category="KOREAN"), restaurant(2, 0, "KOREAN"), restaurant(3, category="CHINESE"),
             restaurant(4, 10, "KOREAN")]

    def test_category_and_exclude(self):
        result = recommend(self.items, 7, TODAY, "KOREAN")
        self.assertEqual(([r.id for r in result.candidates], result.category), ([1, 4], "KOREAN"))
        self.assertIn(result.picked.id, [1, 4])
        self.assertEqual([r.id for r in recommend(self.items, 0, TODAY, "KOREAN").candidates], [1, 2, 4])
        self.assertEqual([r.id for r in recommend(self.items, 7, TODAY).candidates], [1, 3, 4])

    def test_reasons(self):
        result = recommend(self.items, 7, TODAY, "JAPANESE")
        self.assertEqual((result.candidates, result.picked, result.reason), ([], None, "NO_CATEGORY_RESTAURANTS"))
        recent = [restaurant(1, 0, "KOREAN"), restaurant(2, category="CHINESE")]
        self.assertEqual(recommend(recent, 7, TODAY, "KOREAN").reason, "ALL_RECENTLY_VISITED")
        self.assertEqual(recommend([], 7, TODAY, "KOREAN").reason, "NO_RESTAURANTS")

    def test_uniform_in_category(self):
        rng = random.Random(7)
        counts = Counter(recommend(self.items, 7, TODAY, "KOREAN", rng).picked.id for _ in range(4000))
        self.assertEqual(set(counts), {1, 4})
        self.assertAlmostEqual(counts[1] / 4000, 0.5, delta=0.03)


if __name__ == "__main__":
    unittest.main()
