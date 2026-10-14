import { useCallback, useEffect, useRef, useState } from 'react'

export const SLOT_STEPS = 24

// 슬롯에 차례로 보여 줄 이름 목록. 후보 이름만 쓰고 마지막은 뽑힌 식당이다(F14).
export function buildFrames(candidates, picked, steps = SLOT_STEPS, random = Math.random) {
  const names = candidates.map((candidate) => candidate.name)
  const frames = []
  for (let i = 0; i < steps - 1; i += 1) {
    let name = names[Math.floor(random() * names.length)]
    // 후보가 둘 이상이면 같은 이름이 연달아 나오지 않게 해 도는 느낌을 준다.
    if (names.length > 1 && name === frames[frames.length - 1]) {
      name = names[(names.indexOf(name) + 1) % names.length]
    }
    frames.push(name)
  }
  frames.push(picked.name)
  return frames
}

// 처음에는 빠르게, 끝으로 갈수록 느리게 바뀐다(전체 약 2.5초).
export function frameDelay(index, steps = SLOT_STEPS) {
  const progress = index / steps
  return Math.round(40 + progress * progress * 260)
}

// 운영체제의 "움직임 줄이기" 설정(F15)
export function prefersReducedMotion() {
  return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

// 입력칸에서 누른 Enter는 그 입력칸의 동작(폼 제출 등)으로 남겨 둔다.
function isTypingTarget(target) {
  return target instanceof Element && Boolean(target.closest('input, textarea, select, [contenteditable="true"]'))
}

// 추천 결과(result)가 바뀔 때마다 슬롯을 돌린다. phase: idle → spinning → done
// 움직임 줄이기 설정이면 돌리지 않고 바로 done, 도는 중 Enter를 누르면 바로 done(F15).
export function useSlotSpin(result) {
  const [phase, setPhase] = useState('idle')
  const [reelName, setReelName] = useState('')
  const timer = useRef(null)

  const stop = useCallback(() => {
    clearTimeout(timer.current)
    timer.current = null
  }, [])

  // 결과를 바로 보여 준다.
  const reveal = useCallback(() => {
    stop()
    if (result?.picked) {
      setReelName(result.picked.name)
      setPhase('done')
    }
  }, [result, stop])

  useEffect(() => {
    if (!result?.picked) {
      setPhase('idle')
      return undefined
    }
    if (prefersReducedMotion()) {
      setReelName(result.picked.name)
      setPhase('done')
      return undefined
    }
    const frames = buildFrames(result.candidates, result.picked)
    let index = 0
    setPhase('spinning')
    setReelName(frames[0])
    const tick = () => {
      index += 1
      setReelName(frames[index])
      if (index >= frames.length - 1) {
        timer.current = null
        setPhase('done')
        return
      }
      timer.current = setTimeout(tick, frameDelay(index))
    }
    timer.current = setTimeout(tick, frameDelay(0))
    return stop
  }, [result, stop])

  useEffect(() => {
    if (phase !== 'spinning') return undefined
    function handleKeyDown(event) {
      if (event.key !== 'Enter' || isTypingTarget(event.target)) return
      // 버튼에 포커스가 있어도 클릭(다시 요청)으로 이어지지 않게 막고 결과만 보여 준다.
      event.preventDefault()
      reveal()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [phase, reveal])

  return { phase, reelName, reveal }
}
