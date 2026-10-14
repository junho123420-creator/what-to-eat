// 화면 입력값 검증. 서버(API-SPEC)와 같은 규칙을 쓰며, 서버도 다시 검증한다.

export const NAME_MAX = 50
export const LOCATION_NOTE_MAX = 100
export const MAP_URL_MAX = 500
export const MEMO_MAX = 1000

// 글자 수는 유니코드 문자 기준으로 센다(서버와 같음).
export function charLength(value) {
  return [...value].length
}

// 브라우저 로컬 날짜(YYYY-MM-DD)
export function localToday(now = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

export function validateName(name) {
  const trimmed = name.trim()
  if (trimmed === '') return '식당 이름을 입력하세요.'
  if (charLength(trimmed) > NAME_MAX) return `식당 이름은 ${NAME_MAX}자 이하로 입력하세요.`
  return null
}

// http·https 주소만 링크로 연다(F07). 다른 주소는 null.
export function safeMapUrl(value) {
  const trimmed = (value ?? '').trim()
  if (!trimmed || /\s/.test(trimmed)) return null
  try {
    const url = new URL(trimmed)
    return (url.protocol === 'http:' || url.protocol === 'https:') && url.host ? trimmed : null
  } catch {
    return null
  }
}

// 폼 값 전체를 검증해 { 필드: 오류 문구 } 를 돌려준다. 오류가 없으면 빈 객체.
export function validateForm(values, today = localToday()) {
  const errors = {}
  const nameError = validateName(values.name)
  if (nameError) errors.name = nameError
  if (values.visit_status === 'VISITED' && values.last_visited_on) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(values.last_visited_on)) {
      errors.last_visited_on = '날짜를 YYYY-MM-DD 형식으로 입력하세요.'
    } else if (values.last_visited_on > today) {
      errors.last_visited_on = '마지막 방문일은 오늘 이후일 수 없습니다.'
    }
  }
  if (charLength(values.location_note) > LOCATION_NOTE_MAX) {
    errors.location_note = `위치 메모는 ${LOCATION_NOTE_MAX}자 이하로 입력하세요.`
  }
  const mapUrl = values.map_url.trim()
  if (charLength(mapUrl) > MAP_URL_MAX) {
    errors.map_url = `지도 링크는 ${MAP_URL_MAX}자 이하로 입력하세요.`
  } else if (mapUrl && !safeMapUrl(mapUrl)) {
    errors.map_url = '지도 링크는 http:// 또는 https://로 시작하는 주소여야 합니다.'
  }
  if (charLength(values.memo) > MEMO_MAX) errors.memo = `메모는 ${MEMO_MAX}자 이하로 입력하세요.`
  return errors
}

// 폼 값을 API 요청 본문으로 바꾼다. WANT이면 별점·방문일을 보내지 않는다(null).
export function toPayload(values) {
  const visited = values.visit_status === 'VISITED'
  return {
    name: values.name.trim(),
    category: values.category,
    price_range: values.price_range || null,
    visit_status: values.visit_status,
    rating: visited && values.rating ? Number(values.rating) : null,
    last_visited_on: visited && values.last_visited_on ? values.last_visited_on : null,
    location_note: values.location_note,
    map_url: values.map_url.trim(),
    memo: values.memo,
  }
}

export const EMPTY_FORM = {
  name: '',
  category: 'ETC',
  price_range: '',
  visit_status: 'WANT',
  rating: '',
  last_visited_on: '',
  location_note: '',
  map_url: '',
  memo: '',
}

// 저장된 식당을 폼 값으로 바꾼다(수정 화면).
export function toFormValues(restaurant) {
  return {
    name: restaurant.name,
    category: restaurant.category,
    price_range: restaurant.price_range ?? '',
    visit_status: restaurant.visit_status,
    rating: restaurant.rating ? String(restaurant.rating) : '',
    last_visited_on: restaurant.last_visited_on ?? '',
    location_note: restaurant.location_note,
    map_url: restaurant.map_url,
    memo: restaurant.memo,
  }
}
