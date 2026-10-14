from sqlalchemy import select

from .database import SessionLocal
from .models import RestaurantRow, utc_now
from .schemas import Restaurant, RestaurantCreate, RestaurantUpdate

EDITABLE_FIELDS = tuple(RestaurantCreate.model_fields)


class RestaurantStore:
    """식당 데이터는 이 클래스로만 읽고 쓴다."""

    def list(self, q: str = "", category: str | None = None, visit_status: str | None = None) -> list[Restaurant]:
        """조건을 AND로 적용해 등록 순서로 돌려준다(F02, F10)."""
        query = select(RestaurantRow)
        if q:
            # %·_도 글자 그대로 찾는다. utf8mb4_general_ci라 대소문자를 구분하지 않는다.
            query = query.where(RestaurantRow.name.contains(q, autoescape=True))
        if category:
            query = query.where(RestaurantRow.category == category)
        if visit_status:
            query = query.where(RestaurantRow.visit_status == visit_status)
        with SessionLocal() as session:
            rows = session.scalars(query.order_by(RestaurantRow.id)).all()
            return [Restaurant.model_validate(row) for row in rows]

    def create(self, data: RestaurantCreate) -> Restaurant:
        with SessionLocal() as session:
            row = RestaurantRow(**data.model_dump())
            session.add(row)
            session.commit()
            session.refresh(row)
            return Restaurant.model_validate(row)

    def update(self, restaurant_id: int, data: RestaurantUpdate) -> Restaurant | None:
        """보낸 필드를 기존 값에 합친 뒤 등록과 같은 규칙으로 검증한다.
        규칙 위반은 pydantic.ValidationError, 없는 id는 None."""
        with SessionLocal() as session:
            row = session.get(RestaurantRow, restaurant_id)
            if row is None:
                return None
            changes = data.model_dump(exclude_unset=True)
            if not changes:
                return Restaurant.model_validate(row)
            merged = {field: getattr(row, field) for field in EDITABLE_FIELDS} | changes
            checked = RestaurantCreate.model_validate(merged)
            for field in EDITABLE_FIELDS:
                setattr(row, field, getattr(checked, field))
            row.updated_at = utc_now()
            session.commit()
            session.refresh(row)
            return Restaurant.model_validate(row)

    def delete(self, restaurant_id: int) -> bool:
        """식당 하나를 지운다. 없는 id면 False."""
        with SessionLocal() as session:
            row = session.get(RestaurantRow, restaurant_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True
