// 백엔드 API 호출. 화면은 /api 주소로만 데이터를 요청한다.

const NETWORK_ERROR = '서버에 연결할 수 없습니다. API 서버가 실행 중인지 확인하세요.'
// Nginx·개발 서버가 API에 연결하지 못하면 502·504를 돌려준다.
const PROXY_ERRORS = [502, 504]

// 로그인이 풀렸을 때(401) 화면을 시작 화면으로 돌리는 함수. App이 등록한다.
let unauthorizedHandler = null
export function onUnauthorized(handler) {
  unauthorizedHandler = handler
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

// FastAPI 오류 응답({"detail": ...})을 사용자에게 보여 줄 문장으로 바꾼다.
function errorMessage(status, body) {
  if (typeof body?.detail === 'string') return body.detail
  // 서버가 직접 만든 한글 검증 문구(ctx.error)가 있으면 보여 준다.
  const serverMessage = Array.isArray(body?.detail) && body.detail.find((item) => typeof item?.ctx?.error === 'string')
  if (serverMessage) return serverMessage.ctx.error
  if (PROXY_ERRORS.includes(status)) return NETWORK_ERROR
  if (status === 422) return '입력값을 확인하세요.'
  return `요청을 처리하지 못했습니다. (${status})`
}

async function request(method, path, body) {
  let response
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(NETWORK_ERROR, 0)
  }
  const text = await response.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    // Nginx·개발 서버가 API 대신 HTML 오류를 돌려준 경우
    data = null
  }
  if (response.ok && data === null && text) throw new ApiError(NETWORK_ERROR, response.status)
  if (response.status === 401 && !path.startsWith('/api/auth/')) unauthorizedHandler?.()
  if (!response.ok) throw new ApiError(errorMessage(response.status, data), response.status)
  return data
}

// filters: { q, category, visit_status }. 빈 값은 보내지 않는다.
export function listRestaurants(filters = {}) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    const text = (value ?? '').trim()
    if (text) params.set(key, text)
  }
  const query = params.toString()
  return request('GET', `/api/restaurants${query ? `?${query}` : ''}`)
}

export function createRestaurant(data) {
  return request('POST', '/api/restaurants', data)
}

export function updateRestaurant(id, data) {
  return request('PATCH', `/api/restaurants/${encodeURIComponent(id)}`, data)
}

export function deleteRestaurant(id) {
  return request('DELETE', `/api/restaurants/${encodeURIComponent(id)}`)
}

// category가 빈 값이면 전체(F21)
export function getRecommendation(excludeDays, category = '') {
  const params = new URLSearchParams({ exclude_days: excludeDays })
  if (category) params.set('category', category)
  return request('GET', `/api/recommendation?${params}`)
}

export function signup(username, password) {
  return request('POST', '/api/auth/signup', { username, password })
}

export function login(username, password) {
  return request('POST', '/api/auth/login', { username, password })
}

export function logout() {
  return request('POST', '/api/auth/logout')
}

// 로그인했으면 User, 아니면 null
export async function currentUser() {
  try {
    return await request('GET', '/api/auth/me')
  } catch (error) {
    if (error.status === 401) return null
    throw error
  }
}
