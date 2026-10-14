import logging
from datetime import date
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from .recommend import EXCLUDE_DAY_OPTIONS, recommend
from .schemas import Category, Recommendation, Restaurant, RestaurantCreate, RestaurantUpdate, VisitStatus
from .store import RestaurantStore

app = FastAPI(title="오늘 뭐 먹지? API")
store = RestaurantStore()
logger = logging.getLogger(__name__)

DATABASE_ERROR = "DB에 연결할 수 없거나 처리 중 오류가 발생했습니다."
RESTAURANT_NOT_FOUND = "식당을 찾을 수 없습니다."
EXCLUDE_DAYS_INVALID = "최근 방문 제외 기간은 0, 3, 7, 14일 중 하나여야 합니다."


@app.exception_handler(SQLAlchemyError)
def handle_database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
    """DB 오류는 내부 내용을 응답에 노출하지 않고 503으로 알린다. 자세한 내용은 서버 로그에 남긴다."""
    logger.error("DB 오류: %s %s: %s", request.method, request.url.path, error)
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": DATABASE_ERROR})


@app.get("/api/health")
def health() -> dict[str, str]:
    """API 서버가 요청을 처리할 수 있는지 확인한다."""
    return {"status": "ok"}


@app.get("/api/restaurants")
def list_restaurants(
    q: Annotated[str, Query(max_length=50)] = "",
    category: Category | None = None,
    visit_status: VisitStatus | None = None,
) -> list[Restaurant]:
    """저장한 식당을 등록 순서로 돌려준다(F02). 이름 검색과 필터는 AND로 적용한다(F10)."""
    return store.list(q.strip(), category, visit_status)


@app.post("/api/restaurants", status_code=status.HTTP_201_CREATED)
def create_restaurant(data: RestaurantCreate) -> Restaurant:
    """식당을 등록한다(F01)."""
    return store.create(data)


@app.patch("/api/restaurants/{restaurant_id}")
def update_restaurant(restaurant_id: int, data: RestaurantUpdate) -> Restaurant:
    """보낸 필드만 수정한다(F08). 결과가 WANT이면 별점·방문일을 지운다."""
    try:
        restaurant = store.update(restaurant_id, data)
    except ValidationError as error:
        # 합친 값이 규칙에 맞지 않으면(예: 기존 VISITED에 미래 방문일) 요청 검증 실패와 같은 422로 알린다.
        raise RequestValidationError(jsonable_encoder(error.errors(include_url=False), custom_encoder={ValueError: str}))
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RESTAURANT_NOT_FOUND)
    return restaurant


@app.delete("/api/restaurants/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_restaurant(restaurant_id: int) -> Response:
    """식당을 삭제한다(F09). 삭제 확인은 화면에서 한다."""
    if not store.delete(restaurant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RESTAURANT_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/recommendation")
def get_recommendation(exclude_days: str = "7") -> Recommendation:
    """최근 방문한 곳을 뺀 후보 중 하나를 같은 확률로 추천한다(F11~F13). 결과는 저장하지 않는다."""
    # "7.0"·" 7" 같은 값도 거절하도록 쿼리 문자열을 그대로 비교한다.
    allowed = {str(days): days for days in EXCLUDE_DAY_OPTIONS}
    if exclude_days not in allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=EXCLUDE_DAYS_INVALID)
    return recommend(store.list(), allowed[exclude_days], date.today())
