#!/usr/bin/env bash
# R15: App 서버(FastAPI) 설치·업데이트. 테이블이 없으면 만들고(있으면 그대로 둠) systemd로 8010 포트에서 실행한다.
# 사용: 프로젝트 루트에서 sudo bash deploy/install-api.sh  (.env는 deploy/create-db.sh로 먼저 만든다)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR=/opt/what-to-eat
SERVICE=what-to-eat-api.service

if [[ $EUID -ne 0 ]]; then
  echo "sudo로 실행하세요: sudo bash deploy/install-api.sh" >&2
  exit 1
fi
if [[ ! -f "$REPO/.env" ]]; then
  echo "$REPO/.env 가 없습니다. sudo bash deploy/create-db.sh 를 먼저 실행하세요." >&2
  exit 1
fi

echo "[1] 실행 계정"
id what-to-eat >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin what-to-eat

echo "[2] 코드 복사 → $APP_DIR (backend, requirements.txt)"
mkdir -p "$APP_DIR"
rm -rf "$APP_DIR/backend"
cp -r "$REPO/backend" "$APP_DIR/backend"
find "$APP_DIR/backend" -name __pycache__ -prune -exec rm -rf {} +
cp "$REPO/requirements.txt" "$APP_DIR/requirements.txt"

echo "[3] 가상환경"
[[ -x "$APP_DIR/.venv/bin/python" ]] || python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "[4] .env (권한 600)"
install -m 600 -o what-to-eat -g what-to-eat "$REPO/.env" "$APP_DIR/.env"

echo "[5] 테이블 확인 (없는 테이블만 생성)"
(cd "$APP_DIR" && runuser -u what-to-eat -- "$APP_DIR/.venv/bin/python" -m backend.init_db)

echo "[6] systemd 등록·재시작"
cp "$REPO/deploy/$SERVICE" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

echo "[7] 확인"
for _ in $(seq 20); do
  curl -fs http://127.0.0.1:8010/api/health >/dev/null && break
  sleep 0.5
done
systemctl is-active "$SERVICE"
curl -s -w " %{http_code}\n" http://127.0.0.1:8010/api/health
curl -s -o /dev/null -w "/api/restaurants %{http_code}\n" http://127.0.0.1:8010/api/restaurants
