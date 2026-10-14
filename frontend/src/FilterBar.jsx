import { CATEGORIES, VISIT_STATUSES } from './labels.js'
import { NAME_MAX } from './validation.js'

// 이름 검색 → 음식 종류 → 방문 상태 순서로 놓아 Tab 키로 차례대로 이동한다(F10).
export default function FilterBar({ filters, onChange }) {
  function update(field) {
    return (event) => onChange({ ...filters, [field]: event.target.value })
  }

  return (
    <div className="filter-bar" role="search">
      <div className="field">
        <label htmlFor="filter-q">이름 검색</label>
        <input id="filter-q" type="search" maxLength={NAME_MAX} value={filters.q} onChange={update('q')} />
      </div>
      <div className="field">
        <label htmlFor="filter-category">음식 종류</label>
        <select id="filter-category" value={filters.category} onChange={update('category')}>
          <option value="">전체</option>
          {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>
      <div className="field">
        <label htmlFor="filter-visit-status">방문 상태</label>
        <select id="filter-visit-status" value={filters.visit_status} onChange={update('visit_status')}>
          <option value="">전체</option>
          {VISIT_STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>
    </div>
  )
}
