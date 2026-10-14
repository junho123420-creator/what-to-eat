"""이미 가입한 계정에 기본 맛집 목록(F22) 중 없는 것만 추가한다. 이름이 같은 식당이 있으면 건너뛴다.
기존 식당은 변경하거나 삭제하지 않으므로 여러 번 실행해도 같은 결과다.

실행: python -m backend.add_defaults 아이디
"""

import sys

from sqlalchemy import select

from .database import SessionLocal
from .defaults import DEFAULT_RESTAURANTS, default_rows
from .models import RestaurantRow, UserRow


def add_defaults(username: str) -> int:
    """추가한 식당 수. 없는 아이디면 LookupError."""
    with SessionLocal() as session:
        user_id = session.scalar(select(UserRow.id).where(UserRow.username == username))
        if user_id is None:
            raise LookupError(username)
        existing = set(session.scalars(select(RestaurantRow.name).where(RestaurantRow.owner_id == user_id)))
        rows = default_rows(user_id, skip_names=existing)
        session.add_all(rows)
        session.commit()
        return len(rows)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("사용법: python -m backend.add_defaults 아이디")
    try:
        added = add_defaults(sys.argv[1])
    except LookupError:
        sys.exit(f"'{sys.argv[1]}' 계정이 없습니다.")
    print(f"{sys.argv[1]} 계정에 기본 맛집 {added}곳을 추가했습니다(기본 목록 {len(DEFAULT_RESTAURANTS)}곳, 이미 있는 이름은 건너뜀).")


if __name__ == "__main__":
    main()
