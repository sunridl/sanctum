import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const { session, login } = useAuth()
  const navigate = useNavigate()

  const [mode, setMode] = useState('login') // 'login' | 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [signupRole, setSignupRole] = useState('therapist')
  const [error, setError] = useState('')

  if (session) return <Navigate to="/dashboard" replace />

  async function handleLogin(e) {
    e.preventDefault()
    setError('')
    const response = await fetch('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!response.ok) {
      setError('Invalid email or password')
      return
    }
    login(await response.json())
    navigate('/dashboard')
  }

  async function handleSignup(e) {
    e.preventDefault()
    setError('')
    const response = await fetch('http://localhost:8000/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        password,
        first_name: firstName,
        last_name: lastName,
        role: signupRole,
      }),
    })
    if (!response.ok) {
      if (response.status === 409) setError('That email is already registered')
      else if (response.status === 422) setError('Please check your inputs (email format, password ≥ 8 chars)')
      else setError('Could not sign up — please try again')
      return
    }
    login(await response.json())
    navigate('/dashboard')
  }

  function switchMode(next) {
    setMode(next)
    setError('')
    setPassword('')
  }

  const inputStyle = { width: '100%', padding: 8, marginBottom: 8 }
  const linkStyle = { background: 'none', border: 'none', color: '#0066cc', cursor: 'pointer', padding: 0 }

  return (
    <div style={{ maxWidth: 400, margin: '100px auto', fontFamily: 'sans-serif' }}>
      <h1>🖤 Sanctum</h1>

      {mode === 'login' ? (
        <form onSubmit={handleLogin} data-testid="login-form">
          <input
            data-testid="login-email"
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            style={inputStyle}
          />
          <input
            data-testid="login-password"
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            style={inputStyle}
          />
          <button data-testid="login-submit" type="submit" style={{ width: '100%', padding: 8 }}>
            Login
          </button>
          <p style={{ marginTop: 12 }}>
            New here?{' '}
            <button data-testid="show-signup" type="button" onClick={() => switchMode('signup')} style={linkStyle}>
              Create an account
            </button>
          </p>
        </form>
      ) : (
        <form onSubmit={handleSignup} data-testid="signup-form">
          <input data-testid="signup-first-name" placeholder="First name" value={firstName} onChange={e => setFirstName(e.target.value)} style={inputStyle} />
          <input data-testid="signup-last-name" placeholder="Last name" value={lastName} onChange={e => setLastName(e.target.value)} style={inputStyle} />
          <input data-testid="signup-email" type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} style={inputStyle} />
          <input data-testid="signup-password" type="password" placeholder="Password (min 8 chars)" value={password} onChange={e => setPassword(e.target.value)} style={inputStyle} />
          <select data-testid="signup-role" value={signupRole} onChange={e => setSignupRole(e.target.value)} style={inputStyle}>
            <option value="therapist">Therapist</option>
            <option value="psychiatrist">Psychiatrist</option>
          </select>
          <button data-testid="signup-submit" type="submit" style={{ width: '100%', padding: 8 }}>
            Sign up
          </button>
          <p style={{ marginTop: 12 }}>
            Already have an account?{' '}
            <button data-testid="show-login" type="button" onClick={() => switchMode('login')} style={linkStyle}>
              Log in
            </button>
          </p>
        </form>
      )}

      {error && (
        <p data-testid="auth-error" style={{ color: '#b00020', marginTop: 12 }}>
          {error}
        </p>
      )}
    </div>
  )
}
