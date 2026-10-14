#!/usr/bin/env bash
# .env의 DB_PASSWORD로 MariaDB 사용자 비밀번호를 바꾸고, 설치된 API(/opt/what-to-eat)의 .env도 맞춘 뒤 재시작한다.
# .env에서 비밀번호를 바꾼 뒤 실행한다. 비밀번호는 명령줄·화면·쉘 기록에 남기지 않는다.
# 사용: 프로젝트 루트에서 sudo bash deploy/sync-db-password.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$REPO/.env"
APP_DIR=/opt/what-to-eat
SERVICE=what-to-eat-api.service
OWNER="${SUDO_USER:-}"

if [[ $EUID -ne 0 || -z "$OWNER" ]]; then
  echo "일반 계정에서 sudo로 실행하세요: sudo bash deploy/sync-db-password.sh" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "$ENV_FILE 가 없습니다." >&2
  exit 1
fi

read_env() { grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'; }
DB_USER="$(read_env DB_USER)"
PASSWORD="$(read_env DB_PASSWORD)"
if [[ -z "$DB_USER" || -z "$PASSWORD" ]]; then
  echo ".env에 DB_USER와 DB_PASSWORD가 있어야 합니다." >&2
  exit 1
fi
if [[ ! "$DB_USER" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "DB_USER에는 영문·숫자·밑줄만 쓸 수 있습니다." >&2
  exit 1
fi

echo "[1] MariaDB 사용자 비밀번호 변경 ($DB_USER@localhost)"
# SQL 문자열 안의 \ 와 ' 를 이스케이프하고, 표준 입력으로 넘겨 프로세스 목록에 보이지 않게 한다.
ESCAPED="$(printf '%s' "$PASSWORD" | sed -e "s/\\\\/\\\\\\\\/g" -e "s/'/\\\\'/g")"
printf "ALTER USER '%s'@'localhost' IDENTIFIED BY '%s';\n" "$DB_USER" "$ESCAPED" | mariadb

echo "[2] 프로젝트 .env 권한 정리 (600, 소유자 $OWNER)"
chown "$OWNER:$(id -gn "$OWNER")" "$ENV_FILE"
chmod 600 "$ENV_FILE"

if [[ -d "$APP_DIR" ]]; then
  echo "[3] 설치된 API의 .env 교체·재시작"
  install -m 600 -o what-to-eat -g what-to-eat "$ENV_FILE" "$APP_DIR/.env"
  systemctl restart "$SERVICE"
  for _ in $(seq 20); do
    curl -fs http://127.0.0.1:8010/api/health >/dev/null && break
    sleep 0.5
  done
fi

echo "[4] 확인"
(cd "$REPO" && runuser -u "$OWNER" -- "$REPO/.venv/bin/python" -c "
from sqlalchemy import text
from backend.database import engine
with engine.connect() as c: print('프로젝트 .env 접속:', c.execute(text('SELECT CURRENT_USER()')).scalar())")
[[ -d "$APP_DIR" ]] && curl -s -o /dev/null -w "API /api/restaurants %{http_code}\n" http://127.0.0.1:8010/api/restaurants
ls -l "$ENV_FILE"
