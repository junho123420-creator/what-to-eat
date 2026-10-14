import { useEffect, useRef, useState } from 'react'
import { currentUser, logout, onUnauthorized } from './api.js'
import { Landing, LoginPage, SignupPage } from './AuthPages.jsx'
import Home from './Home.jsx'

// 주소의 # 뒤를 화면 이름으로 쓴다: #/login, #/signup, 그 외는 시작 화면
function routeFromHash() {
  const route = window.location.hash.replace(/^#\/?/, '')
  return route === 'login' || route === 'signup' ? route : ''
}

export default function App() {
  const [user, setUser] = useState(undefined) // undefined: 확인 중, null: 로그인 안 함
  const [route, setRoute] = useState(routeFromHash)
  const [notice, setNotice] = useState('')
  const [lastUsername, setLastUsername] = useState('')
  const [error, setError] = useState('')
  // 로그아웃 직후 늦게 도착한 401로 "다시 로그인" 안내가 뜨지 않도록 현재 로그인 여부를 함께 본다.
  const loggedIn = useRef(false)
  loggedIn.current = Boolean(user)

  useEffect(() => {
    const handleHash = () => setRoute(routeFromHash())
    window.addEventListener('hashchange', handleHash)
    return () => window.removeEventListener('hashchange', handleHash)
  }, [])

  useEffect(() => {
    // 사용 중 로그인이 풀리면(세션 만료 등) 로그인 화면으로 보낸다(F18).
    onUnauthorized(() => {
      if (!loggedIn.current) return
      loggedIn.current = false
      setUser(null)
      setNotice('로그인이 필요합니다. 다시 로그인하세요.')
      window.location.hash = '#/login'
    })
    currentUser()
      .then(setUser)
      .catch((failure) => {
        setUser(null)
        setError(failure.message)
      })
    return () => onUnauthorized(null)
  }, [])

  function go(hash) {
    window.location.hash = hash
  }

  function handleLoggedIn(loggedIn) {
    setNotice('')
    setUser(loggedIn)
    go('#/')
  }

  function handleSignedUp(username) {
    setLastUsername(username)
    setNotice('가입했습니다. 로그인하세요.')
    go('#/login')
  }

  async function handleLogout() {
    loggedIn.current = false
    try {
      await logout()
    } finally {
      setUser(null)
      setNotice('로그아웃했습니다.')
      go('#/')
    }
  }

  if (user === undefined) return <p className="loading">불러오는 중...</p>
  if (user) return <Home user={user} onLogout={handleLogout} />
  if (route === 'login') {
    return <LoginPage key={lastUsername} initialUsername={lastUsername} notice={notice} onLoggedIn={handleLoggedIn} />
  }
  if (route === 'signup') return <SignupPage onSignedUp={handleSignedUp} />
  return <Landing notice={error || notice} />
}
