#!/usr/bin/env bash
# R02: MariaDB에 what_to_eat DB와 전용 사용자를 만들고 프로젝트 루트에 .env(권한 600)를 쓴다.
# 사용: 프로젝트 루트에서 sudo bash deploy/create-db.sh
# 비밀번호는 무작위로 만들어 .env에만 저장하고 화면에 출력하지 않는다.
# 이미 .env가 있거나 같은 이름의 DB·사용자가 있으면 아무것도 바꾸지 않고 멈춘다(기존 데이터 보호).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DB_NAME=what_to_eat
DB_USER=what_to_eat_app
OWNER="${SUDO_USER:-}"

if [[ $EUID -ne 0 || -z "$OWNER" ]]; then
  echo "일반 계정에서 sudo로 실행하세요: sudo bash deploy/create-db.sh" >&2
  exit 1
fi
if [[ -e "$REPO/.env" ]]; then
  echo "$REPO/.env 가 이미 있어 멈춥니다. 다시 만들려면 내용을 확인한 뒤 직접 옮기세요." >&2
  exit 1
fi

EXISTS="$(mariadb -N -e "SELECT
  (SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='$DB_NAME') +
  (SELECT COUNT(*) FROM mysql.user WHERE User='$DB_USER')")"
if [[ "$EXISTS" != "0" ]]; then
  echo "$DB_NAME DB 또는 $DB_USER 사용자가 이미 있어 멈춥니다(기존 데이터 보호)." >&2
  exit 1
fi

PASSWORD="$(openssl rand -hex 24)"

echo "[1] DB·사용자 생성 (DROP 권한 없음)"
mariadb <<SQL
CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX ON $DB_NAME.* TO '$DB_USER'@'localhost';
SQL

echo "[2] .env 작성 (권한 600, 소유자 $OWNER)"
umask 077
cat > "$REPO/.env" <<ENV
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$PASSWORD
ENV
chown "$OWNER:" "$REPO/.env"
chmod 600 "$REPO/.env"

echo "[3] 확인"
mariadb -h127.0.0.1 -u"$DB_USER" -p"$PASSWORD" "$DB_NAME" -e "SELECT CURRENT_USER() AS user, DATABASE() AS db"
ls -l "$REPO/.env"
