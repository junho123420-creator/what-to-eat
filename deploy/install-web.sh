#!/usr/bin/env bash
# R15: Web 서버(Nginx) 설치·업데이트. React 빌드 결과를 /var/www/what-to-eat에 복사하고 사이트를 켠다(8080, 80번의 eat.localhost).
# frontend에 커밋하지 않은 변경이 있으면 멈춘다(커밋한 화면만 배포).
# 사용: 먼저 일반 계정으로 빌드한 뒤(cd frontend && corepack npm@10.9.4 run build) 프로젝트 루트에서
#       sudo bash deploy/install-web.sh
# 다른 사이트(default, flow-task)는 건드리지 않는다.
# 서버 분리(R27): Web 서버에서 sudo WEB_MODE=split bash deploy/install-web.sh
#   what-to-eat-web-split.conf(80번 기본 사이트, /api/ → 10.10.20.20:8010)를 쓰고, Nginx 기본 환영 페이지(sites-enabled/default)는 끈다.
#   Amazon Linux(dnf, sites-available 없음)에서는 /etc/nginx/conf.d/what-to-eat-web.conf로 설치한다.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WEB_DIR=/var/www/what-to-eat
SITE=what-to-eat-web
WEB_MODE="${WEB_MODE:-single}"
case "$WEB_MODE" in
  single) CONF=what-to-eat-web.conf ;;
  split) CONF=what-to-eat-web-split.conf ;;
  *) echo "WEB_MODE는 single 또는 split입니다: $WEB_MODE" >&2; exit 1 ;;
esac

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
if ! command -v nginx >/dev/null; then
  if command -v dnf >/dev/null; then dnf install -y nginx; else apt-get update -q && apt-get install -y nginx; fi
fi

echo "[2] 정적 파일 → $WEB_DIR"
rm -rf "$WEB_DIR"
mkdir -p "$WEB_DIR"
cp -r "$REPO/frontend/dist/." "$WEB_DIR/"

echo "[3] 사이트 설정 ($CONF)"
if [[ -d /etc/nginx/sites-available ]]; then
  cp "$REPO/deploy/$CONF" "/etc/nginx/sites-available/$SITE"
  # split: 이 서버 전용이라 80번 기본 사이트를 쓴다. 패키지 기본 사이트(링크만)를 끄고, 원본은 sites-available에 남긴다.
  [[ "$WEB_MODE" == split && -L /etc/nginx/sites-enabled/default ]] && rm /etc/nginx/sites-enabled/default
  ln -sf "/etc/nginx/sites-available/$SITE" "/etc/nginx/sites-enabled/$SITE"
else
  # Amazon Linux: nginx.conf가 conf.d/*.conf를 읽는다. nginx.conf의 환영 페이지 server에 default_server가 있으면 이 사이트와 겹친다.
  if grep -Eq "^[^#]*listen[^;]*\b80\b[^;]*default_server" /etc/nginx/nginx.conf; then
    echo "/etc/nginx/nginx.conf의 80번 server에 default_server가 있습니다. 그 단어를 지운 뒤 다시 실행하세요." >&2
    exit 1
  fi
  cp "$REPO/deploy/$CONF" "/etc/nginx/conf.d/$SITE.conf"
fi
nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "[4] 확인"
if [[ "$WEB_MODE" == split ]]; then
  curl -s -o /dev/null -w "/ %{http_code}\n" http://127.0.0.1/
  curl -s -w " %{http_code}\n" http://127.0.0.1/api/health
  exit 0
fi
curl -s -o /dev/null -w "/ %{http_code}\n" http://127.0.0.1:8080/
curl -s -w " %{http_code}\n" http://127.0.0.1:8080/api/health
curl -s -o /dev/null -H "Host: eat.localhost" -w "eat.localhost(80) / %{http_code}\n" http://127.0.0.1/
curl -s -o /dev/null -w "localhost(80, flow-task) / %{http_code}\n" http://127.0.0.1/
