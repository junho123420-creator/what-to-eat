"""회원가입·로그인·세션(F16~F18). 비밀번호와 세션 토큰 원문은 저장하거나 기록하지 않는다."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from .database import SessionLocal
from .defaults import default_rows
from .models import RestaurantRow, SessionRow, UserRow, utc_now
from .schemas import User

SESSION_COOKIE = "what_to_eat_session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60  # 7일(초). 로그인 시점부터 고정, 사용해도 연장하지 않는다.

LOGIN_REQUIRED = "로그인이 필요합니다."
LOGIN_FAILED = "아이디 또는 비밀번호가 올바르지 않습니다."
USERNAME_TAKEN = "이미 사용 중인 아이디입니다."

# scrypt 설정. 해시 문자열에 함께 저장해 나중에 값을 바꿔도 기존 비밀번호를 확인할 수 있다.
SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_LEN = 2**14, 8, 1, 64


def hash_password(password: str, salt: bytes | None = None, n: int = SCRYPT_N, r: int = SCRYPT_R, p: int = SCRYPT_P) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=SCRYPT_LEN)
    return f"scrypt${n}${r}${p}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, digest = stored.split("$")
        expected = hash_password(password, bytes.fromhex(salt), int(n), int(r), int(p))
    except ValueError:
        return False
    return hmac.compare_digest(expected.split("$")[-1], digest)


# 없는 아이디로 로그인할 때도 같은 시간만큼 계산해, 응답 시간으로 아이디 존재 여부를 알 수 없게 한다.
DUMMY_HASH = hash_password(secrets.token_hex(16))


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthStore:
    def signup(self, username: str, password: str) -> User | None:
        """가입한 User, 아이디가 이미 있으면 None.
        처음 가입한 계정이면 작성자 없는 식당을 그 계정에 붙이고(F20), 그 밖의 계정에는 기본 맛집 목록을 넣는다(F22)."""
        with SessionLocal() as session:
            user = UserRow(username=username, password_hash=hash_password(password))
            session.add(user)
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
                return None
            claimed = 0
            first_id = session.scalar(select(func.min(UserRow.id)))
            if user.id == first_id:
                claimed = session.execute(
                    update(RestaurantRow).where(RestaurantRow.owner_id.is_(None)).values(owner_id=user.id)
                ).rowcount
            # 기존 식당을 받지 않은 계정에는 기본 맛집 목록을 넣는다(F22). 가입과 같은 트랜잭션이라 함께 저장된다.
            if not claimed:
                session.add_all(default_rows(user.id))
            session.commit()
            return User.model_validate(user)

    def login(self, username: str, password: str) -> tuple[User, str] | None:
        """(User, 세션 토큰 원문) 또는 실패 시 None. 토큰 원문은 쿠키로만 보내고 DB에는 해시만 저장한다."""
        with SessionLocal() as session:
            user = session.scalar(select(UserRow).where(UserRow.username == username))
            if not verify_password(password, user.password_hash if user else DUMMY_HASH) or user is None:
                return None
            now = utc_now()
            # 이 사용자의 만료된 세션은 로그인할 때 정리한다.
            session.execute(delete(SessionRow).where(SessionRow.user_id == user.id, SessionRow.expires_at <= now))
            token = secrets.token_urlsafe(32)
            session.add(SessionRow(token_hash=token_hash(token), user_id=user.id,
                                   expires_at=now + timedelta(seconds=SESSION_MAX_AGE)))
            session.commit()
            return User.model_validate(user), token

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with SessionLocal() as session:
            session.execute(delete(SessionRow).where(SessionRow.token_hash == token_hash(token)))
            session.commit()

    def user_for_token(self, token: str | None) -> User | None:
        if not token:
            return None
        with SessionLocal() as session:
            user = session.scalar(
                select(UserRow)
                .join(SessionRow, SessionRow.user_id == UserRow.id)
                .where(SessionRow.token_hash == token_hash(token), SessionRow.expires_at > utc_now())
            )
            return User.model_validate(user) if user else None


auth_store = AuthStore()


def current_user(request: Request) -> User:
    """로그인한 사용자. 세션이 없거나 만료됐으면 401(F18)."""
    user = auth_store.user_for_token(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=LOGIN_REQUIRED)
    return user
