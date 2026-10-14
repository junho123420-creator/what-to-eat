"""무작위 추천(F11~F13). DB와 분리해 후보 계산 규칙만 담는다."""

import random
from datetime import date

from .schemas import Recommendation, Restaurant

EXCLUDE_DAY_OPTIONS = (0, 3, 7, 14)


def is_recently_visited(restaurant: Restaurant, exclude_days: int, today: date) -> bool:
    """마지막 방문일이 오늘부터 exclude_days일 안(오늘 포함)이면 True. 방문일이 없으면 항상 후보."""
    if restaurant.last_visited_on is None:
        return False
    return (today - restaurant.last_visited_on).days < exclude_days


def recommend(restaurants: list[Restaurant], exclude_days: int, today: date, category: str | None = None,
              rng: random.Random | None = None) -> Recommendation:
    """음식 종류(F21)와 최근 방문 제외(F12)를 AND로 적용한 후보 중 하나를 같은 확률로 뽑는다. 후보가 없으면 이유를 알려 준다."""
    in_category = [r for r in restaurants if category is None or r.category == category]
    candidates = [r for r in in_category if not is_recently_visited(r, exclude_days, today)]
    reason = None
    if not restaurants:
        reason = "NO_RESTAURANTS"
    elif not in_category:
        reason = "NO_CATEGORY_RESTAURANTS"
    elif not candidates:
        reason = "ALL_RECENTLY_VISITED"
    picked = (rng or random).choice(candidates) if candidates else None
    return Recommendation(exclude_days=exclude_days, category=category, today=today, candidates=candidates,
                          picked=picked, reason=reason)
