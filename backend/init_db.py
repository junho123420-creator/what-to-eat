"""테이블을 만든다. 이미 있는 테이블과 데이터는 변경하거나 삭제하지 않는다.

실행: python -m backend.init_db
"""

from sqlalchemy import inspect

from .database import Base, engine
from . import models  # noqa: F401  모든 테이블 정의를 Base.metadata에 등록한다.


def main() -> None:
    existing = set(inspect(engine).get_table_names())
    # create_all은 없는 테이블만 만든다.
    Base.metadata.create_all(engine)
    for table in Base.metadata.sorted_tables:
        if table.name in existing:
            print(f"{table.name} 테이블이 이미 있어 변경하지 않았습니다.")
        else:
            print(f"{table.name} 테이블을 만들었습니다.")


if __name__ == "__main__":
    main()
