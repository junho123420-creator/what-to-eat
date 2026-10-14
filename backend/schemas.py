import re
from datetime import date, datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    model_validator,
)

Category = Literal["KOREAN", "CHINESE", "JAPANESE", "WESTERN", "SNACK", "ETC"]
PriceRange = Literal["LOW", "MID", "HIGH"]
VisitStatus = Literal["WANT", "VISITED"]

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_date(value):
    """YYYY-MM-DD 문자열만 날짜로 받는다. strict 모드에서도 JSON 문자열을 날짜로 바꾸기 위해 직접 변환한다."""
    if value is None or isinstance(value, date):
        return value
    if not isinstance(value, str) or not DATE_PATTERN.match(value):
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다.")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("존재하지 않는 날짜입니다.") from error


def check_map_url(value):
    """빈 문자열 또는 호스트가 있는 http·https 주소만 받는다(F07). 앞뒤 공백은 지운다."""
    if not isinstance(value, str):
        raise ValueError("지도 링크는 문자열이어야 합니다.")
    value = value.strip()
    if value == "":
        return value
    if len(value) > 500:
        raise ValueError("지도 링크는 500자 이하여야 합니다.")
    if re.search(r"\s", value):
        raise ValueError("지도 링크에 공백을 넣을 수 없습니다.")
    try:
        parts = urlsplit(value)
    except ValueError as error:
        raise ValueError("올바른 주소가 아닙니다.") from error
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        raise ValueError("지도 링크는 http:// 또는 https://로 시작하는 주소여야 합니다.")
    return value


# 앞뒤 공백을 지운 뒤 1~50자(F01)
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Rating = Annotated[int, Field(ge=1, le=5)]
VisitDate = Annotated[date, BeforeValidator(parse_date)]
LocationNote = Annotated[str, StringConstraints(max_length=100)]
MapUrl = Annotated[str, BeforeValidator(check_map_url)]
Memo = Annotated[str, StringConstraints(max_length=1000)]


def check_visit_record(data):
    """방문일은 오늘(서버 로컬 날짜) 이후일 수 없다. WANT이면 별점·방문일을 null로 저장한다(F06)."""
    if data.visit_status == "WANT":
        data.rating = None
        data.last_visited_on = None
    if data.last_visited_on is not None and data.last_visited_on > date.today():
        raise ValueError("마지막 방문일은 오늘 이후일 수 없습니다.")
    return data


class RestaurantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: Name
    category: Category = "ETC"
    price_range: PriceRange | None = None
    visit_status: VisitStatus = "WANT"
    rating: Rating | None = None
    last_visited_on: VisitDate | None = None
    location_note: LocationNote = ""
    map_url: MapUrl = ""
    memo: Memo = ""

    @model_validator(mode="after")
    def visit_record(self):
        return check_visit_record(self)


class RestaurantUpdate(BaseModel):
    """보낸 필드만 수정한다(F08). 형식 검사만 하고, 합친 결과는 RestaurantCreate 규칙으로 다시 검증한다."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: Name | None = None
    category: Category | None = None
    price_range: PriceRange | None = None
    visit_status: VisitStatus | None = None
    rating: Rating | None = None
    last_visited_on: VisitDate | None = None
    location_note: LocationNote | None = None
    map_url: MapUrl | None = None
    memo: Memo | None = None

    @model_validator(mode="after")
    def reject_null(self):
        not_nullable = ("name", "category", "visit_status", "location_note", "map_url", "memo")
        nulls = [field for field in not_nullable if field in self.model_fields_set and getattr(self, field) is None]
        if nulls:
            raise ValueError(f"null로 바꿀 수 없는 필드입니다: {', '.join(nulls)}")
        return self


class Restaurant(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: Category
    price_range: PriceRange | None
    visit_status: VisitStatus
    rating: int | None
    last_visited_on: date | None
    location_note: str
    map_url: str
    memo: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_utc(self, value: datetime) -> str:
        # DB에는 시간대 없는 UTC로 저장하므로 Z를 붙여 돌려준다.
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class Credentials(BaseModel):
    """회원가입·로그인 요청(F16, F17). 아이디는 자동 변환하지 않고, 비밀번호 앞뒤 공백도 그대로 쓴다."""

    model_config = ConfigDict(extra="forbid", strict=True)

    username: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]{3,30}$")]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_utc(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class Recommendation(BaseModel):
    exclude_days: int
    today: date
    candidates: list[Restaurant]
    picked: Restaurant | None
    reason: Literal["NO_RESTAURANTS", "ALL_RECENTLY_VISITED"] | None
