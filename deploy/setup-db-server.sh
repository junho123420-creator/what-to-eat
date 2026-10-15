#!/usr/bin/env bash
# R27: DB 서버(10.10.30.30)에 MariaDB를 설치하고, App 서버(10.10.20.20)에서만 접속할 수 있는 DB·사용자를 만든다.
# Amazon Linux 2023(dnf)과 Ubuntu(apt)에서 동작한다.
# 사용: DB 서버의 프로젝트 루트에 기존 .env(DB_NAME·DB_USER·DB_PASSWORD)를 복사한 뒤 sudo bash deploy/setup-db-server.sh
#       비밀번호는 .env 값을 그대로 쓰고 화면·명령줄에 출력하지 않는다.
# 같은 이름의 DB·사용자가 이미 있으면 아무것도 만들지 않고 멈춘다(기존 데이터 보호). DROP 권한은 주지 않는다.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$REPO/.env"
DB_BIND="${DB_BIND:-10.10.30.30}"   # MariaDB가 받는 주소(이 서버의 프라이빗 IP)
APP_HOST="${APP_HOST:-10.10.20.20}" # 접속을 허용할 App 서버 주소

if [[ $EUID -ne 0 ]]; then
  echo "sudo로 실행하세요: sudo bash deploy/setup-db-server.sh" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "$ENV_FILE 가 없습니다. 기존 .env를 이 서버의 프로젝트 루트에 복사하세요(권한 600)." >&2
  exit 1
fi
for ip in "$DB_BIND" "$APP_HOST"; do
  if [[ ! "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "IPv4 주소가 아닙니다: $ip" >&2
    exit 1
  fi
done
if ! ip -4 addr show | grep -qF "inet $DB_BIND/"; then
  echo "이 서버에 $DB_BIND 주소가 없습니다. DB 서버에서 실행하는지 확인하세요." >&2
  exit 1
fi

read_env() { grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'; }
DB_NAME="$(read_env DB_NAME)"
DB_USER="$(read_env DB_USER)"
PASSWORD="$(read_env DB_PASSWORD)"
if [[ -z "$DB_NAME" || -z "$DB_USER" || -z "$PASSWORD" ]]; then
  echo ".env에 DB_NAME, DB_USER, DB_PASSWORD가 있어야 합니다." >&2
  exit 1
fi
if [[ ! "$DB_NAME" =~ ^[A-Za-z0-9_]+$ || ! "$DB_USER" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "DB_NAME, DB_USER에는 영문·숫자·밑줄만 쓸 수 있습니다." >&2
  exit 1
fi

echo "[1] MariaDB 설치 확인"
if ! systemctl list-unit-files mariadb.service | grep -q mariadb; then
  if command -v dnf >/dev/null; then dnf install -y mariadb105-server
  else apt-get update -q && apt-get install -y mariadb-server; fi
fi
systemctl enable --now mariadb
SQL_CLI="$(command -v mariadb || command -v mysql)"
# 설정 파일은 이름순으로 읽혀 뒤 파일이 이긴다. zz-로 시작해 배포판 기본 설정(bind-address 등)보다 뒤에 읽히게 한다.
if [[ -d /etc/my.cnf.d ]]; then CNF=/etc/my.cnf.d/zz-what-to-eat.cnf
else CNF=/etc/mysql/mariadb.conf.d/zz-what-to-eat.cnf; fi

echo "[2] 받는 주소 $DB_BIND:3306 ($CNF)"
cat > "$CNF" <<CNF
# R27: App 서버($APP_HOST)가 프라이빗 주소로 접속한다. 공개 주소로는 받지 않는다.
[mysqld]
bind-address = $DB_BIND
CNF
systemctl restart mariadb

echo "[3] DB·사용자 생성 ('$DB_USER'@'$APP_HOST', DROP 권한 없음)"
EXISTS="$("$SQL_CLI" -N -e "SELECT
  (SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='$DB_NAME') +
  (SELECT COUNT(*) FROM mysql.user WHERE User='$DB_USER')")"
if [[ "$EXISTS" != "0" ]]; then
  echo "$DB_NAME DB 또는 $DB_USER 사용자가 이미 있어 만들지 않습니다(기존 데이터 보호)."
else
  # SQL 문자열 안의 \ 와 ' 를 이스케이프하고, 표준 입력으로 넘겨 프로세스 목록에 보이지 않게 한다.
  ESCAPED="$(printf '%s' "$PASSWORD" | sed -e "s/\\\\/\\\\\\\\/g" -e "s/'/\\\\'/g")"
  "$SQL_CLI" <<SQL
CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER '$DB_USER'@'$APP_HOST' IDENTIFIED BY '$ESCAPED';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX ON $DB_NAME.* TO '$DB_USER'@'$APP_HOST';
SQL
fi

echo "[4] 확인"
ss -ltn | grep -E ":3306 " || echo "3306 포트가 열려 있지 않습니다."
"$SQL_CLI" -N -e "SELECT CONCAT(User, '@', Host) FROM mysql.user WHERE User='$DB_USER'"
