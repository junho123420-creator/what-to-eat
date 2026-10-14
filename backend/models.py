from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

CATEGORIES = ("KOREAN", "CHINESE", "JAPANESE", "WESTERN", "SNACK", "ETC")
PRICE_RANGES = ("LOW", "MID", "HIGH")
VISIT_STATUSES = ("WANT", "VISITED")


def utc_now() -> datetime:
    """DB에는 시간대 없는 UTC 일시로 저장한다."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


class RestaurantRow(Base):
    __tablename__ = "restaurants"
    __table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_general_ci"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(
        Enum(*CATEGORIES, name="category", native_enum=True), nullable=False, server_default="ETC"
    )
    price_range: Mapped[str | None] = mapped_column(Enum(*PRICE_RANGES, name="price_range"), nullable=True)
    visit_status: Mapped[str] = mapped_column(
        Enum(*VISIT_STATUSES, name="visit_status"), nullable=False, server_default="WANT"
    )
    rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    last_visited_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    location_note: Mapped[str] = mapped_column(String(100), nullable=False, server_default="")
    map_url: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    # TEXT 열은 MariaDB에서 기본값을 지정하지 않고, 앱이 빈 문자열을 넣는다.
    memo: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
