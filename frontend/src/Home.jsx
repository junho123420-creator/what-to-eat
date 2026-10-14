import { useEffect, useRef, useState } from 'react'
import { createRestaurant, deleteRestaurant, listRestaurants, updateRestaurant } from './api.js'
import FilterBar from './FilterBar.jsx'
import RecommendPanel from './RecommendPanel.jsx'
import RestaurantForm from './RestaurantForm.jsx'
import RestaurantItem from './RestaurantItem.jsx'
import { toFormValues } from './validation.js'

const EMPTY_FILTERS = { q: '', category: '', visit_status: '' }

export default function Home({ user, onLogout }) {
  const [restaurants, setRestaurants] = useState([])
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const filtersRef = useRef(filters)
  // 늦게 도착한 이전 검색 응답이 최신 결과를 덮어쓰지 않도록 요청 순번을 센다.
  const requestSeq = useRef(0)
  // 수정을 마치거나 취소하면 그 식당의 수정 버튼으로 포커스를 돌려준다.
  const editButtons = useRef(new Map())
  const focusAfterEdit = useRef(null)

  useEffect(() => {
    if (editingId === null && focusAfterEdit.current !== null) {
      editButtons.current.get(focusAfterEdit.current)?.focus()
      focusAfterEdit.current = null
    }
  }, [editingId, restaurants])

  async function reload(current = filtersRef.current) {
    const seq = ++requestSeq.current
    try {
      const data = await listRestaurants(current)
      if (seq !== requestSeq.current) return
      setRestaurants(data)
      setApiError('')
    } catch (error) {
      if (seq === requestSeq.current) setApiError(error.message)
    } finally {
      if (seq === requestSeq.current) setLoading(false)
    }
  }

  // 검색어 입력 중에는 잠깐 기다렸다가 한 번만 요청한다.
  useEffect(() => {
    filtersRef.current = filters
    const timer = setTimeout(() => reload(filters), 200)
    return () => clearTimeout(timer)
  }, [filters])

  const filtering = Boolean(filters.q.trim() || filters.category || filters.visit_status)

  async function handleCreate(payload) {
    await createRestaurant(payload)
    await reload()
  }

  function finishEdit(id) {
    focusAfterEdit.current = id
    setEditingId(null)
  }

  async function handleUpdate(id, payload) {
    await updateRestaurant(id, payload)
    await reload()
    finishEdit(id)
  }

  // 삭제 전 확인한다. 취소하면 아무 요청도 보내지 않는다(F09).
  async function handleDelete(restaurant) {
    if (!window.confirm(`'${restaurant.name}' 식당을 삭제할까요?`)) return
    try {
      await deleteRestaurant(restaurant.id)
    } catch (error) {
      setApiError(error.message)
      return
    }
    await reload()
  }

  return (
    <main className="app">
      <header className="app-header">
        <h1>오늘 뭐 먹지?</h1>
        <div className="account">
          <span className="account-name" data-testid="current-user">{user.username}</span>
          <button type="button" onClick={onLogout}>로그아웃</button>
        </div>
      </header>

      <RecommendPanel />

      <section aria-labelledby="add-title">
        <h2 id="add-title">식당 등록</h2>
        <RestaurantForm idPrefix="new" submitLabel="등록" onSubmit={handleCreate} />
      </section>

      <section aria-labelledby="list-title">
        <h2 id="list-title">저장한 식당</h2>
        <FilterBar filters={filters} onChange={setFilters} />
        {apiError && <p className="error" role="alert" data-testid="api-error">{apiError}</p>}
        {loading ? (
          <p>불러오는 중...</p>
        ) : restaurants.length === 0 ? (
          <p className="empty">{filtering ? '조건에 맞는 식당이 없습니다.' : '저장한 식당이 없습니다.'}</p>
        ) : (
          <>
            <p className="result-count" aria-live="polite">{restaurants.length}곳</p>
            <ul className="restaurant-list">
              {restaurants.map((restaurant) => (
                <li key={restaurant.id} data-id={restaurant.id} className={editingId === restaurant.id ? 'editing' : undefined}>
                  {editingId === restaurant.id ? (
                    <RestaurantForm
                      idPrefix={`edit-${restaurant.id}`}
                      initialValues={toFormValues(restaurant)}
                      submitLabel="저장"
                      autoFocus
                      onSubmit={(payload) => handleUpdate(restaurant.id, payload)}
                      onCancel={() => finishEdit(restaurant.id)}
                    />
                  ) : (
                    <RestaurantItem
                      restaurant={restaurant}
                      onEdit={() => setEditingId(restaurant.id)}
                      onDelete={() => handleDelete(restaurant)}
                      editButtonRef={(element) => {
                        if (element) editButtons.current.set(restaurant.id, element)
                        else editButtons.current.delete(restaurant.id)
                      }}
                    />
                  )}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </main>
  )
}
