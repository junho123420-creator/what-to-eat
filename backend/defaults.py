"""기본 맛집 목록(F22). 가입한 계정에 복사해 넣는 식당 데이터를 읽는다."""

import json
from pathlib import Path

from .models import RestaurantRow
from .schemas import RestaurantCreate

DEFAULTS_FILE = Path(__file__).with_name("default_restaurants.json")


def load_defaults() -> list[RestaurantCreate]:
    """목록 파일을 읽어 등록 규칙(RestaurantCreate)으로 검증한다. 규칙에 어긋나면 서버 시작 때 바로 실패한다."""
    items = [RestaurantCreate.model_validate(item) for item in json.loads(DEFAULTS_FILE.read_text(encoding="utf-8"))]
    names = [item.name for item in items]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"기본 맛집 목록에 같은 이름이 있습니다: {', '.join(duplicates)}")
    return items


DEFAULT_RESTAURANTS = load_defaults()


def default_rows(owner_id: int, skip_names: set[str] = frozenset()) -> list[RestaurantRow]:
    """owner_id 계정에 넣을 기본 맛집 행. skip_names에 있는 이름은 뺀다. 파일 순서대로 등록된다."""
    return [RestaurantRow(owner_id=owner_id, **item.model_dump())
            for item in DEFAULT_RESTAURANTS if item.name not in skip_names]
