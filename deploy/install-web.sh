#!/usr/bin/env bash
# R15: Web 서버(Nginx) 설치·업데이트. React 빌드 결과를 /var/www/what-to-eat에 복사하고 8080 사이트를 켠다.
# frontend에 커밋하지 않은 변경이 있으면 멈춘다(커밋한 화면만 배포).
# 사용: 먼저 일반 계정으로 빌드한 뒤(cd frontend && corepack npm@10.9.4 run build) 프로젝트 루트에서
#       sudo bash deploy/install-web.sh
# 다른 사이트(default, flow-task)는 건드리지 않는다.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WEB_DIR=/var/www/what-to-eat
SITE=what-to-eat-web

if [[ $EUID -ne 0 ]]; then
  echo "sudo로 실행하세요: sudo bash deploy/install-web.sh" >&2
  exit 1
fi
if [[ ! -f "$REPO/frontend/dist/index.html" ]]; then
  echo "frontend/dist가 없습니다. 먼저 cd frontend && corepack npm@10.9.4 run build 를 실행하세요." >&2
  exit 1
fi

if [[ -n "$(git -C "$REPO" -c safe.directory="$REPO" status --porcelain -- frontend)" ]]; then
  echo "frontend에 커밋하지 않은 변경이 있습니다. 커밋한 뒤 다시 빌드하고 실행하세요." >&2
  exit 1
fi
if [[ -n "$(find "$REPO/frontend/src" "$REPO/frontend/index.html" -newer "$REPO/frontend/dist/index.html" -print -quit)" ]]; then
  echo "frontend/dist가 소스보다 오래됐습니다. 먼저 cd frontend && corepack npm@10.9.4 run build 를 실행하세요." >&2
  exit 1
fi

echo "[1] Nginx 확인"
command -v nginx >/dev/null || apt-get install -y nginx

echo "[2] 정적 파일 → $WEB_DIR"
rm -rf "$WEB_DIR"
mkdir -p "$WEB_DIR"
cp -r "$REPO/frontend/dist/." "$WEB_DIR/"

echo "[3] 사이트 설정"
cp "$REPO/deploy/$SITE.conf" "/etc/nginx/sites-available/$SITE"
ln -sf "/etc/nginx/sites-available/$SITE" "/etc/nginx/sites-enabled/$SITE"
nginx -t
systemctl enable nginx
systemctl reload nginx

echo "[4] 확인"
curl -s -o /dev/null -w "/ %{http_code}\n" http://127.0.0.1:8080/
curl -s -w " %{http_code}\n" http://127.0.0.1:8080/api/health
