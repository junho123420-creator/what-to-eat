import { useEffect, useRef, useState } from 'react'
import { CATEGORIES, PRICE_RANGES, VISIT_STATUSES } from './labels.js'
import { EMPTY_FORM, localToday, toPayload, validateForm } from './validation.js'

// 식당 등록·수정 폼. idPrefix로 폼마다 다른 id를 써서 label과 입력칸을 연결한다.
export default function RestaurantForm({
  idPrefix, initialValues = EMPTY_FORM, submitLabel, onSubmit, onCancel, autoFocus = false,
}) {
  const [values, setValues] = useState(initialValues)
  const [errors, setErrors] = useState({})
  const [submitError, setSubmitError] = useState('')
  const [saving, setSaving] = useState(false)
  const today = localToday()
  const visited = values.visit_status === 'VISITED'
  const id = (field) => `${idPrefix}-${field}`
  const nameRef = useRef(null)

  useEffect(() => {
    if (autoFocus) nameRef.current?.focus()
  }, [autoFocus])

  // 수정 폼은 Esc로 취소한다.
  function handleKeyDown(event) {
    if (event.key === 'Escape' && onCancel) {
      event.preventDefault()
      onCancel()
    }
  }

  function update(field) {
    return (event) => setValues((current) => ({ ...current, [field]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const found = validateForm(values, today)
    setErrors(found)
    setSubmitError('')
    if (Object.keys(found).length > 0) return
    setSaving(true)
    try {
      await onSubmit(toPayload(values))
      if (!onCancel) setValues(EMPTY_FORM)
    } catch (error) {
      setSubmitError(error.message)
    } finally {
      setSaving(false)
    }
  }

  function errorProps(field) {
    return {
      'aria-invalid': errors[field] ? 'true' : 'false',
      'aria-describedby': errors[field] ? id(`${field}-error`) : undefined,
    }
  }

  function fieldError(field) {
    return errors[field] ? (
      <p id={id(`${field}-error`)} className="error field-error">{errors[field]}</p>
    ) : null
  }

  return (
    <form className="restaurant-form" onSubmit={handleSubmit} onKeyDown={handleKeyDown} noValidate>
      <div className="field wide">
        <label htmlFor={id('name')}>식당 이름</label>
        <input id={id('name')} ref={nameRef} value={values.name} onChange={update('name')} {...errorProps('name')} />
        {fieldError('name')}
      </div>

      <div className="field">
        <label htmlFor={id('category')}>음식 종류</label>
        <select id={id('category')} value={values.category} onChange={update('category')}>
          {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>

      <div className="field">
        <label htmlFor={id('price_range')}>가격대</label>
        <select id={id('price_range')} value={values.price_range} onChange={update('price_range')}>
          <option value="">선택 안 함</option>
          {PRICE_RANGES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>

      <div className="field">
        <label htmlFor={id('visit_status')}>방문 상태</label>
        <select id={id('visit_status')} value={values.visit_status} onChange={update('visit_status')}>
          {VISIT_STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>

      {visited && (
        <>
          <div className="field">
            <label htmlFor={id('rating')}>별점</label>
            <select id={id('rating')} value={values.rating} onChange={update('rating')}>
              <option value="">선택 안 함</option>
              {[5, 4, 3, 2, 1].map((n) => <option key={n} value={String(n)}>{n}점</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor={id('last_visited_on')}>마지막 방문일</label>
            <input
              id={id('last_visited_on')}
              type="date"
              max={today}
              value={values.last_visited_on}
              onChange={update('last_visited_on')}
              {...errorProps('last_visited_on')}
            />
            {fieldError('last_visited_on')}
          </div>
        </>
      )}

      <div className="field wide">
        <label htmlFor={id('location_note')}>위치 메모</label>
        <input id={id('location_note')} value={values.location_note} onChange={update('location_note')}
          placeholder="예: 역삼역 3번 출구" {...errorProps('location_note')} />
        {fieldError('location_note')}
      </div>

      <div className="field wide">
        <label htmlFor={id('map_url')}>지도 링크</label>
        <input id={id('map_url')} type="url" value={values.map_url} onChange={update('map_url')}
          placeholder="https://..." {...errorProps('map_url')} />
        {fieldError('map_url')}
      </div>

      <div className="field wide">
        <label htmlFor={id('memo')}>메모</label>
        <textarea id={id('memo')} rows={3} value={values.memo} onChange={update('memo')} {...errorProps('memo')} />
        {fieldError('memo')}
      </div>

      <div className="actions wide">
        <button type="submit" disabled={saving}>{submitLabel}</button>
        {onCancel && <button type="button" onClick={onCancel}>취소</button>}
      </div>
      <p className="error wide" role="alert">{submitError}</p>
    </form>
  )
}
