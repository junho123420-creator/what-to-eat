// API 값과 화면에 보여 줄 한글 이름(PRD F03~F05)

export const CATEGORIES = [
  ['KOREAN', '한식'],
  ['CHINESE', '중식'],
  ['JAPANESE', '일식'],
  ['WESTERN', '양식'],
  ['SNACK', '분식'],
  ['ETC', '기타'],
]

export const PRICE_RANGES = [
  ['LOW', '1만원 이하'],
  ['MID', '1만~2만원'],
  ['HIGH', '2만원 이상'],
]

export const VISIT_STATUSES = [
  ['WANT', '가보고 싶음'],
  ['VISITED', '가봄'],
]

// 목록에서 음식 종류를 한눈에 알아보도록 붙이는 그림 문자(장식용, 화면 읽기 프로그램에서는 숨김)
export const CATEGORY_ICONS = {
  KOREAN: '🍚',
  CHINESE: '🥟',
  JAPANESE: '🍣',
  WESTERN: '🍝',
  SNACK: '🍢',
  ETC: '🍽️',
}

function labelOf(pairs, value) {
  return pairs.find(([key]) => key === value)?.[1] ?? ''
}

export const categoryLabel = (value) => labelOf(CATEGORIES, value)
export const priceLabel = (value) => labelOf(PRICE_RANGES, value)
export const visitLabel = (value) => labelOf(VISIT_STATUSES, value)

export function stars(rating) {
  return rating ? '★'.repeat(rating) + '☆'.repeat(5 - rating) : ''
}
