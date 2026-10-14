import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 개발 서버는 /api 요청을 FastAPI로 넘긴다. 화면 코드는 /api 주소만 알고 DB 정보는 모른다.
// API_TARGET 환경변수로 백엔드 주소를 바꿀 수 있다(기본 8010).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': process.env.API_TARGET || 'http://127.0.0.1:8010' },
  },
})
