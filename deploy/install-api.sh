#!/usr/bin/env bash
# R15: App 서버(FastAPI) 설치·업데이트. 테이블이 없으면 만들고 빠진 열만 추가한 뒤(기존 데이터 유지) systemd로 8010 포트에서 실행한다.
# 사용: 프로젝트 루트에서 sudo bash deploy/install-api.sh  (.env는 deploy/create-db.sh로 먼저 만든다)
# 커밋된 코드(HEAD)만 설치된다. 커밋하지 않은 변경은 포함되지 않는다.
# 서버 분리(R27): App 서버에서 sudo API_HOST=10.10.20.20 bash deploy/install-api.sh  (.env의 DB_HOST는 DB 서버 주소)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR=/opt/what-to-eat
SERVICE=what-to-eat-api.service
API_HOST="${API_HOST:-127.0.0.1}"   # API가 받는 주소. 기본은 같은 서버의 Nginx만 받는 127.0.0.1

if [[ $EUID -ne 0 ]]; then
  echo "sudo로 실행하세요: sudo bash deploy/install-api.sh" >&2
  exit 1
fi
if [[ ! -f "$REPO/.env" ]]; then
  echo "$REPO/.env 가 없습니다. sudo bash deploy/create-db.sh 를 먼저 실행하세요." >&2
  exit 1
fi
if [[ ! "$API_HOST" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "API_HOST는 IPv4 주소여야 합니다: $API_HOST" >&2
  exit 1
fi

echo "[1] 실행 계정"
id what-to-eat >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin what-to-eat

# 실행할 때마다 새 임시 파일을 쓴다(/tmp의 다른 사용자 파일은 root도 덮어쓸 수 없다: fs.protected_regular).
ARCHIVE="$(mktemp --suffix=.tar.gz)"
trap 'rm -f "$ARCHIVE"' EXIT

echo "[2] 코드 설치 → $APP_DIR (HEAD $(git -C "$REPO" -c safe.directory="$REPO" rev-parse --short HEAD): backend, requirements.txt)"
git -C "$REPO" -c safe.directory="$REPO" archive --format=tar.gz -o "$ARCHIVE" HEAD backend requirements.txt
mkdir -p "$APP_DIR"
rm -rf "$APP_DIR/backend"   # 업데이트 시 지워진 파일이 남지 않게 한다
tar -xzf "$ARCHIVE" -C "$APP_DIR"

echo "[3] 가상환경 (Python 3.10 이상)"
if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
  # Amazon Linux 2023 기본 python3는 3.9라서 python3.12·python3.11 패키지를 찾아 쓴다. PYTHON=경로 로 직접 지정할 수 있다.
  PY=""
  for c in ${PYTHON:-} python3 python3.13 python3.12 python3.11 python3.10; do
    if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then PY="$c"; break; fi
  done
  if [[ -z "$PY" ]]; then
    echo "Python 3.10 이상이 없습니다. Amazon Linux: sudo dnf install -y python3.12 / Ubuntu: sudo apt-get install -y python3-venv" >&2
    exit 1
  fi
  "$PY" -m venv "$APP_DIR/.venv" || {
    echo "가상환경을 만들 수 없습니다($PY). Ubuntu는 sudo apt-get install -y python3-venv 후 다시 실행하세요." >&2
    exit 1
  }
fi
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "[4] .env (권한 600)"
install -m 600 -o what-to-eat -g what-to-eat "$REPO/.env" "$APP_DIR/.env"

echo "[5] 테이블 확인 (없는 테이블 생성, 빠진 열만 추가)"
(cd "$APP_DIR" && runuser -u what-to-eat -- "$APP_DIR/.venv/bin/python" -m backend.init_db)

echo "[6] systemd 등록·재시작 (받는 주소 $API_HOST:8010)"
sed "s/--host 127\.0\.0\.1 /--host $API_HOST /" "$REPO/deploy/$SERVICE" > "/etc/systemd/system/$SERVICE"
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

echo "[7] 확인"
for _ in $(seq 20); do
  curl -fs http://$API_HOST:8010/api/health >/dev/null && break
  sleep 0.5
done
systemctl is-active "$SERVICE"
curl -s -w " %{http_code}\n" http://$API_HOST:8010/api/health
curl -s -o /dev/null -w "/api/restaurants %{http_code}\n" http://$API_HOST:8010/api/restaurants
