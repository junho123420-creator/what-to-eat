import { useRef, useState } from 'react'
import { getRecommendation } from './api.js'
import RestaurantDetails from './RestaurantDetails.jsx'
import { useSlotSpin } from './slot.js'

export const EXCLUDE_OPTIONS = [
  ['0', '제외 안 함'],
  ['3', '3일'],
  ['7', '7일'],
  ['14', '14일'],
]

// 후보가 없을 때 이유(F13)
export function reasonMessage(reason, excludeDays) {
  if (reason === 'NO_RESTAURANTS') return '저장한 식당이 없습니다. 먼저 식당을 등록하세요.'
  if (reason === 'ALL_RECENTLY_VISITED') {
    return `저장한 식당을 모두 최근 ${excludeDays}일 안에 방문했습니다. 제외 기간을 줄여 보세요.`
  }
  return ''
}

export default function RecommendPanel() {
  const [excludeDays, setExcludeDays] = useState('7')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const requesting = useRef(false)
  const { phase, reelName, reveal } = useSlotSpin(result)
  const spinning = phase === 'spinning'

  async function handleRecommend() {
    // 버튼을 disabled로 만들면 키보드 포커스가 사라지므로, 요청 중 클릭은 무시만 한다.
    if (requesting.current) return
    requesting.current = true
    setLoading(true)
    setError('')
    try {
      setResult(await getRecommendation(excludeDays))
    } catch (failure) {
      setResult(null)
      setError(failure.message)
    } finally {
      requesting.current = false
      setLoading(false)
    }
  }

  return (
    <section aria-labelledby="recommend-title" className="recommend">
      <h2 id="recommend-title">어디서 먹을까?</h2>
      <div className="recommend-controls">
        <div className="field">
          <label htmlFor="exclude-days">최근 방문한 곳 제외</label>
          <select id="exclude-days" value={excludeDays} onChange={(event) => setExcludeDays(event.target.value)}>
            {EXCLUDE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
        {/* 도는 중에는 같은 버튼이 "바로 보기"가 되어 포커스를 잃지 않는다. */}
        <button type="button" className="primary" onClick={spinning ? reveal : handleRecommend} aria-busy={loading}>
          {spinning ? '바로 보기' : result?.picked ? '다시 돌리기' : '추천 받기'}
        </button>
        {spinning && <span className="hint">Enter 키를 누르면 바로 결과를 봅니다.</span>}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {result?.picked && (
        // 도는 동안의 이름은 화면 읽기 프로그램에 읽히지 않게 하고, 멈춘 뒤 결과만 알린다.
        <div className="slot-frame" aria-hidden="true">
          <div className={`slot ${spinning ? 'spinning' : 'stopped'}`} data-testid="slot-reel">
            <span key={reelName} className="slot-name">{reelName}</span>
          </div>
        </div>
      )}
      <div aria-live="polite" data-testid="recommend-result">
        {result && !result.picked && <p className="notice">{reasonMessage(result.reason, result.exclude_days)}</p>}
        {result?.picked && phase === 'done' && (
          <div className="result-card">
            <p className="result-label">오늘은 여기!</p>
            <RestaurantDetails restaurant={result.picked} showMemo={false} nameAs="strong" />
          </div>
        )}
      </div>
    </section>
  )
}
