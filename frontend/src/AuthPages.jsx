import { useEffect, useRef, useState } from 'react'
import { login, signup } from './api.js'
import { validateLogin, validateSignup } from './validation.js'

const LOGIN_FAILED = '아이디 또는 비밀번호가 올바르지 않습니다.'

// 로그인 전 시작 화면(F18)
export function Landing({ notice }) {
  return (
    <main className="landing">
      <section className="hero" aria-labelledby="landing-title">
        <p className="eyebrow">점심 메뉴 고민 끝</p>
        <h1 id="landing-title">오늘 뭐 먹지?</h1>
        <p className="lead">자주 가는 식당과 가보고 싶은 식당을 모아 두고, 고민될 때 슬롯머신으로 한 곳을 골라 드려요.</p>
        {notice && <p className="notice" role="status">{notice}</p>}
        <div className="hero-actions">
          <a className="button primary" href="#/login">로그인</a>
          <a className="button" href="#/signup">회원가입</a>
        </div>
      </section>
      <ul className="features">
        <li><strong>식당 저장</strong><span>음식 종류·가격대·방문 기록·지도 링크를 한곳에</span></li>
        <li><strong>최근 방문 제외</strong><span>며칠 안에 간 곳은 빼고 추천</span></li>
        <li><strong>슬롯머신 추천</strong><span>후보 중 한 곳을 같은 확률로</span></li>
      </ul>
    </main>
  )
}

function AuthForm({ title, fields, submitLabel, validate, onSubmit, initialUsername = '', notice, footer }) {
  const [values, setValues] = useState({ username: initialUsername, password: '', passwordConfirm: '' })
  const [errors, setErrors] = useState({})
  const [submitError, setSubmitError] = useState('')
  const [saving, setSaving] = useState(false)
  const firstInput = useRef(null)
  const passwordInput = useRef(null)

  useEffect(() => {
    // 아이디가 미리 채워져 있으면 비밀번호 칸부터 입력한다.
    ;(initialUsername ? passwordInput : firstInput).current?.focus()
  }, [initialUsername])

  function update(field) {
    return (event) => setValues((current) => ({ ...current, [field]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const found = validate(values)
    setErrors(found)
    setSubmitError('')
    if (Object.keys(found).length > 0) return
    setSaving(true)
    try {
      await onSubmit(values)
    } catch (error) {
      setSubmitError(error.message)
      setSaving(false)
    }
  }

  return (
    <main className="auth">
      <form className="auth-card" onSubmit={handleSubmit} noValidate aria-labelledby="auth-title">
        <a className="brand" href="#/">오늘 뭐 먹지?</a>
        <h1 id="auth-title">{title}</h1>
        {notice && <p className="notice" role="status">{notice}</p>}
        {fields.map(({ name, label, type, autoComplete, hint }) => (
          <div className="field" key={name}>
            <label htmlFor={`auth-${name}`}>{label}</label>
            <input
              id={`auth-${name}`}
              ref={name === 'username' ? firstInput : name === 'password' ? passwordInput : undefined}
              type={type}
              autoComplete={autoComplete}
              autoCapitalize="none"
              spellCheck="false"
              value={values[name]}
              onChange={update(name)}
              aria-invalid={errors[name] ? 'true' : 'false'}
              aria-describedby={errors[name] ? `auth-${name}-error` : hint ? `auth-${name}-hint` : undefined}
            />
            {hint && !errors[name] && <p id={`auth-${name}-hint`} className="hint">{hint}</p>}
            {errors[name] && <p id={`auth-${name}-error`} className="error field-error">{errors[name]}</p>}
          </div>
        ))}
        <p className="error" role="alert">{submitError}</p>
        <button type="submit" className="primary wide-button" disabled={saving}>{submitLabel}</button>
        <p className="auth-footer">{footer}</p>
      </form>
    </main>
  )
}

export function LoginPage({ initialUsername, notice, onLoggedIn }) {
  async function handleLogin({ username, password }) {
    try {
      onLoggedIn(await login(username, password))
    } catch (error) {
      // 형식 오류(422)도 같은 문구로 알려 무엇이 틀렸는지 드러내지 않는다.
      if (error.status === 401 || error.status === 422) throw new Error(LOGIN_FAILED)
      throw error
    }
  }

  return (
    <AuthForm
      title="로그인"
      submitLabel="로그인"
      initialUsername={initialUsername}
      notice={notice}
      validate={validateLogin}
      onSubmit={handleLogin}
      fields={[
        { name: 'username', label: '아이디', type: 'text', autoComplete: 'username' },
        { name: 'password', label: '비밀번호', type: 'password', autoComplete: 'current-password' },
      ]}
      footer={<>계정이 없나요? <a href="#/signup">회원가입</a></>}
    />
  )
}

export function SignupPage({ onSignedUp }) {
  async function handleSignup({ username, password }) {
    await signup(username, password)
    onSignedUp(username)
  }

  return (
    <AuthForm
      title="회원가입"
      submitLabel="가입하기"
      validate={validateSignup}
      onSubmit={handleSignup}
      fields={[
        { name: 'username', label: '아이디', type: 'text', autoComplete: 'username', hint: '영문 소문자·숫자·밑줄(_) 3~30자' },
        { name: 'password', label: '비밀번호', type: 'password', autoComplete: 'new-password', hint: '8~128자' },
        { name: 'passwordConfirm', label: '비밀번호 확인', type: 'password', autoComplete: 'new-password' },
      ]}
      footer={<>이미 계정이 있나요? <a href="#/login">로그인</a></>}
    />
  )
}
