import logging
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from .auth import LOGIN_FAILED, SESSION_COOKIE, SESSION_MAX_AGE, USERNAME_TAKEN, auth_store, current_user
from .models import CATEGORIES
from .recommend import EXCLUDE_DAY_OPTIONS, recommend
from .schemas import (
    Category,
    Credentials,
    Recommendation,
    Restaurant,
    RestaurantCreate,
    RestaurantUpdate,
    User,
    VisitStatus,
)
from .store import RestaurantStore

app = FastAPI(title="오늘 뭐 먹지? API")
store = RestaurantStore()
logger = logging.getLogger(__name__)

DATABASE_ERROR = "DB에 연결할 수 없거나 처리 중 오류가 발생했습니다."
RESTAURANT_NOT_FOUND = "식당을 찾을 수 없습니다."
EXCLUDE_DAYS_INVALID = "최근 방문 제외 기간은 0, 3, 7, 14일 중 하나여야 합니다."
CATEGORY_INVALID = "음식 종류가 올바르지 않습니다."


@app.exception_handler(SQLAlchemyError)
def handle_database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
    """DB 오류는 내부 내용을 응답에 노출하지 않고 503으로 알린다. 자세한 내용은 서버 로그에 남긴다."""
    logger.error("DB 오류: %s %s: %s", request.method, request.url.path, error)
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": DATABASE_ERROR})


@app.get("/api/health")
def health() -> dict[str, str]:
    """API 서버가 요청을 처리할 수 있는지 확인한다."""
    return {"status": "ok"}


@app.post("/api/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(data: Credentials) -> User:
    """회원가입만 하고 로그인하지 않는다(세션 쿠키 없음, F16)."""
    user = auth_store.signup(data.username, data.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=USERNAME_TAKEN)
    return user


@app.post("/api/auth/login")
def login(data: Credentials, response: Response) -> User:
    """로그인하고 7일 동안 유지되는 세션 쿠키를 준다(F17). 실패 이유는 구분하지 않는다."""
    result = auth_store.login(data.username, data.password)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=LOGIN_FAILED)
    user, token = result
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax", path="/")
    return user


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    """세션을 지우고 쿠키를 삭제한다. 로그인하지 않았어도 204."""
    auth_store.logout(request.cookies.get(SESSION_COOKIE))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")
    return response


@app.get("/api/auth/me")
def me(request: Request) -> User | None:
    """로그인한 사용자(F20). 로그인하지 않았으면 null(브라우저 콘솔에 401 오류가 남지 않게 한다)."""
    return auth_store.user_for_token(request.cookies.get(SESSION_COOKIE))


@app.get("/api/restaurants")
def list_restaurants(
    user: Annotated[User, Depends(current_user)],
    q: Annotated[str, Query(max_length=50)] = "",
    category: Category | None = None,
    visit_status: VisitStatus | None = None,
) -> list[Restaurant]:
    """저장한 식당을 등록 순서로 돌려준다(F02). 이름 검색과 필터는 AND로 적용한다(F10)."""
    return store.list(user.id, q.strip(), category, visit_status)


@app.post("/api/restaurants", status_code=status.HTTP_201_CREATED)
def create_restaurant(data: RestaurantCreate, user: Annotated[User, Depends(current_user)]) -> Restaurant:
    """로그인한 사용자의 식당으로 등록한다(F01, F19)."""
    return store.create(user.id, data)


@app.patch("/api/restaurants/{restaurant_id}")
def update_restaurant(
    restaurant_id: int, data: RestaurantUpdate, user: Annotated[User, Depends(current_user)]
) -> Restaurant:
    """보낸 필드만 수정한다(F08). 결과가 WANT이면 별점·방문일을 지운다."""
    try:
        restaurant = store.update(user.id, restaurant_id, data)
    except ValidationError as error:
        # 합친 값이 규칙에 맞지 않으면(예: 기존 VISITED에 미래 방문일) 요청 검증 실패와 같은 422로 알린다.
        raise RequestValidationError(jsonable_encoder(error.errors(include_url=False), custom_encoder={ValueError: str}))
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RESTAURANT_NOT_FOUND)
    return restaurant


@app.delete("/api/restaurants/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_restaurant(restaurant_id: int, user: Annotated[User, Depends(current_user)]) -> Response:
    """식당을 삭제한다(F09). 삭제 확인은 화면에서 한다."""
    if not store.delete(user.id, restaurant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RESTAURANT_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/recommendation")
def get_recommendation(
    user: Annotated[User, Depends(current_user)], exclude_days: str = "7", category: str = ""
) -> Recommendation:
    """음식 종류(F21)와 최근 방문 제외(F12)에 맞는 후보 중 하나를 같은 확률로 추천한다(F11~F13). 결과는 저장하지 않는다."""
    # "7.0"·" 7" 같은 값도 거절하도록 쿼리 문자열을 그대로 비교한다.
    allowed = {str(days): days for days in EXCLUDE_DAY_OPTIONS}
    if exclude_days not in allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=EXCLUDE_DAYS_INVALID)
    # 빈 값은 전체. 그 외에는 음식 종류 값과 정확히 같아야 한다.
    if category and category not in CATEGORIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=CATEGORY_INVALID)
    return recommend(store.list(user.id), allowed[exclude_days], date.today(), category or None)
