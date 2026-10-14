import RestaurantDetails from './RestaurantDetails.jsx'

// 목록의 식당 한 개와 수정·삭제 버튼
export default function RestaurantItem({ restaurant, onEdit, onDelete, editButtonRef }) {
  return (
    <div className="restaurant">
      <RestaurantDetails restaurant={restaurant} />
      <div className="item-actions">
        <button type="button" ref={editButtonRef} onClick={onEdit} aria-label={`${restaurant.name} 수정`}>수정</button>
        <button type="button" className="danger" onClick={onDelete} aria-label={`${restaurant.name} 삭제`}>삭제</button>
      </div>
    </div>
  )
}
