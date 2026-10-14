import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
REQUIRED_SETTINGS = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")


def read_env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE 형식의 .env 파일을 읽는다. 빈 줄과 # 주석은 건너뛴다."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_settings() -> dict[str, str]:
    """DB 접속 정보를 읽는다. 환경변수가 .env 값보다 우선한다."""
    file_values = read_env_file(ENV_FILE)
    settings = {key: os.environ.get(key, file_values.get(key, "")) for key in REQUIRED_SETTINGS}
    missing = [key for key, value in settings.items() if not value]
    if missing:
        raise RuntimeError(
            f"DB 접속 정보가 없습니다: {', '.join(missing)}. "
            ".env.example을 참고해 .env 또는 환경변수를 설정하세요."
        )
    return settings


def build_url(settings: dict[str, str]) -> URL:
    # URL.create는 비밀번호의 특수문자를 안전하게 처리하고, 출력 시 비밀번호를 가린다.
    return URL.create(
        "mysql+pymysql",
        username=settings["DB_USER"],
        password=settings["DB_PASSWORD"],
        host=settings["DB_HOST"],
        port=int(settings["DB_PORT"]),
        database=settings["DB_NAME"],
        query={"charset": "utf8mb4"},
    )


engine = create_engine(build_url(load_settings()), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
