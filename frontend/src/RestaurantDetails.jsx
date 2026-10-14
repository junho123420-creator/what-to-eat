import { CATEGORY_ICONS, categoryLabel, priceLabel, stars, visitLabel } from './labels.js'
import { safeMapUrl } from './validation.js'

// 식당 정보 표시(목록·추천 결과 공용). 사용자 입력은 모두 React 텍스트로 넣어 HTML로 해석되지 않는다.
export default function RestaurantDetails({ restaurant, showMemo = true, nameAs: NameTag = 'span' }) {
  const visited = restaurant.visit_status === 'VISITED'
  const mapUrl = safeMapUrl(restaurant.map_url)
  return (
    <>
      <div className="restaurant-head">
        <NameTag className="name">{restaurant.name}</NameTag>
        <span className={`badge status-${restaurant.visit_status.toLowerCase()}`}>{visitLabel(restaurant.visit_status)}</span>
      </div>
      <div className="meta">
        <span className="chip">
          <span aria-hidden="true">{CATEGORY_ICONS[restaurant.category]} </span>
          {categoryLabel(restaurant.category)}
        </span>
        {restaurant.price_range && <span className="chip">{priceLabel(restaurant.price_range)}</span>}
        {visited && restaurant.rating && (
          <span className="stars" aria-label={`별점 ${restaurant.rating}점`}>{stars(restaurant.rating)}</span>
        )}
        {visited && restaurant.last_visited_on && <span>마지막 방문 {restaurant.last_visited_on}</span>}
      </div>
      {(restaurant.location_note || mapUrl) && (
        <div className="meta">
          {restaurant.location_note && <span className="location">📍 {restaurant.location_note}</span>}
          {mapUrl && <a href={mapUrl} target="_blank" rel="noopener noreferrer">지도 보기</a>}
        </div>
      )}
      {showMemo && restaurant.memo && <p className="memo">{restaurant.memo}</p>}
    </>
  )
}
