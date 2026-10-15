# 서버 3대 분리 배포 (R27, AWS EC2 Ubuntu)

| 계층 | 서버 | 주소 | 받는 포트 |
|---|---|---|---|
| Web (Nginx + React 빌드) | EC2 1 | 10.10.10.10, 공개 52.79.221.146 | 80 (모든 곳), 22 (내 IP) |
| App (FastAPI) | EC2 2 | 10.10.20.20 | 8010 (Web만), 22 (Web만) |
| DB (MariaDB) | EC2 3 | 10.10.30.30 | 3306 (App만), 22 (Web만) |

사용자는 `http://52.79.221.146`으로 접속한다. App·DB는 공개 주소 없이 프라이빗 주소로만 연결한다.
기존 WSL 한 대 배포(`install-api.sh`, `install-web.sh` 기본값)는 그대로 쓸 수 있다.

## 1. 보안 그룹
- Web: 인바운드 TCP 80 `0.0.0.0/0`, TCP 22 내 IP.
- App: 인바운드 TCP 8010 소스 `10.10.10.10/32`, TCP 22 소스 `10.10.10.10/32`.
- DB: 인바운드 TCP 3306 소스 `10.10.20.20/32`, TCP 22 소스 `10.10.10.10/32`.
- App·DB는 apt·pip 설치에 인터넷 아웃바운드가 필요하다(프라이빗 서브넷이면 NAT 게이트웨이).

App·DB 서버는 Web 서버를 거쳐 접속한다(키 파일은 각자 경로로 바꾼다).
```
ssh -i key.pem -J ubuntu@52.79.221.146 ubuntu@10.10.20.20
```

## 2. 코드 받기 (세 서버 모두)
```
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/junho123420-creator/what-to-eat.git && cd what-to-eat
```

## 3. DB 서버 (10.10.30.30)
WSL의 `.env`를 복사한다(비밀번호는 그대로 쓴다). WSL에서:
```
scp -J ubuntu@52.79.221.146 .env ubuntu@10.10.30.30:what-to-eat/.env
```
DB 서버에서:
```
chmod 600 .env
sudo bash deploy/setup-db-server.sh
```
확인: `10.10.30.30:3306` 대기, 사용자 `what_to_eat_app@10.10.20.20`.
설치 후 DB 서버의 `.env`는 더 필요 없으므로 지워도 된다(`rm .env`).

## 4. App 서버 (10.10.20.20)
WSL에서 `.env`를 복사하고, App 서버에서 `DB_HOST`만 DB 서버 주소로 바꾼다.
```
scp -J ubuntu@52.79.221.146 .env ubuntu@10.10.20.20:what-to-eat/.env
```
App 서버에서:
```
chmod 600 .env
sed -i 's/^DB_HOST=.*/DB_HOST=10.10.30.30/' .env
sudo apt-get install -y python3-venv
sudo API_HOST=10.10.20.20 bash deploy/install-api.sh
```
확인: 서비스 active, `http://10.10.20.20:8010/api/health` 200, `/api/restaurants` 401(로그인 전).

## 5. Web 서버 (10.10.10.10)
React 빌드는 Node가 있는 WSL에서 하고 결과만 복사한다. WSL에서:
```
cd frontend && corepack npm@10.9.4 run build && cd ..
scp -r frontend/dist ubuntu@52.79.221.146:what-to-eat/frontend/
```
Web 서버에서:
```
sudo WEB_MODE=split bash deploy/install-web.sh
```
확인: `/` 200, `/api/health` 200. 브라우저에서 `http://52.79.221.146` 접속 → 회원가입·로그인·식당 등록.

## 업데이트
- 백엔드: App 서버에서 `git pull` 후 `sudo API_HOST=10.10.20.20 bash deploy/install-api.sh`.
- 화면: WSL에서 다시 빌드·복사, Web 서버에서 `git pull` 후 `sudo WEB_MODE=split bash deploy/install-web.sh`.

## 참고
- 새 DB는 비어 있다. 회원가입하면 기본 맛집 40곳이 들어간다. WSL DB의 기존 계정·식당은 옮기지 않는다.
- 접속은 http다. 로그인 쿠키는 httponly이고 Secure 표시가 없어 http에서도 동작한다.
