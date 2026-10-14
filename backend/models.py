from datetime import date, datetime, timezone

from sqlalchemy import CHAR, Date, DateTime, Enum, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

CATEGORIES = ("KOREAN", "CHINESE", "JAPANESE", "WESTERN", "SNACK", "ETC")
PRICE_RANGES = ("LOW", "MID", "HIGH")
VISIT_STATUSES = ("WANT", "VISITED")


def utc_now() -> datetime:
    """DB에는 시간대 없는 UTC 일시로 저장한다."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


TABLE_ARGS = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_general_ci"}


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = TABLE_ARGS

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    # scrypt 해시와 솔트·설정값을 함께 담은 문자열. 비밀번호 원문은 저장하지 않는다.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class SessionRow(Base):
    __tablename__ = "sessions"
    __table_args__ = TABLE_ARGS

    # 토큰 원문이 아닌 SHA-256 해시(16진수 64자)만 저장한다.
    token_hash: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class RestaurantRow(Base):
    __tablename__ = "restaurants"
    __table_args__ = TABLE_ARGS

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 등록한 사용자. 로그인 도입 전 데이터는 NULL이며 처음 가입한 계정에 연결된다(F20).
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
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
