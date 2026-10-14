"""테이블을 만들고, 기존 테이블에 빠진 열을 추가한다. 이미 있는 데이터는 변경하거나 삭제하지 않는다.

실행: python -m backend.init_db  (여러 번 실행해도 같은 결과)
"""

from sqlalchemy import inspect, text

from .database import Base, engine
from . import models  # noqa: F401  모든 테이블 정의를 Base.metadata에 등록한다.

# R18: 로그인 도입 전에 만든 restaurants 테이블에 작성자 열을 추가한다(NULL 허용이라 기존 행은 그대로).
# MariaDB의 ALTER는 트랜잭션으로 되돌릴 수 없으므로, 중간에 실패해도 다시 실행하면 빠진 단계만 하도록 하나씩 확인한다.
def add_owner_column() -> list[str]:
    """restaurants.owner_id 열·인덱스·외래키 중 없는 것만 추가하고, 추가한 항목 이름을 돌려준다."""
    added = []
    with engine.begin() as connection:
        table = inspect(connection)
        if "owner_id" not in {column["name"] for column in table.get_columns("restaurants")}:
            connection.execute(text("ALTER TABLE restaurants ADD COLUMN owner_id INT NULL AFTER id"))
            added.append("열")
        if not any(index["column_names"] == ["owner_id"] for index in table.get_indexes("restaurants")):
            connection.execute(text("ALTER TABLE restaurants ADD INDEX ix_restaurants_owner_id (owner_id)"))
            added.append("인덱스")
        if not any(fk["constrained_columns"] == ["owner_id"] for fk in table.get_foreign_keys("restaurants")):
            connection.execute(text(
                "ALTER TABLE restaurants ADD CONSTRAINT restaurants_ibfk_1 FOREIGN KEY (owner_id) REFERENCES users (id)"
            ))
            added.append("외래키")
    return added


def main() -> None:
    existing = set(inspect(engine).get_table_names())
    # create_all은 없는 테이블만 만든다.
    Base.metadata.create_all(engine)
    for table in Base.metadata.sorted_tables:
        if table.name in existing:
            print(f"{table.name} 테이블이 이미 있어 변경하지 않았습니다.")
        else:
            print(f"{table.name} 테이블을 만들었습니다.")
    if "restaurants" in existing:
        added = add_owner_column()
        if added:
            print(f"restaurants.owner_id {'·'.join(added)}을(를) 추가했습니다. 기존 행은 그대로입니다.")
        else:
            print("restaurants.owner_id 열·인덱스·외래키가 이미 있어 변경하지 않았습니다.")


if __name__ == "__main__":
    main()
