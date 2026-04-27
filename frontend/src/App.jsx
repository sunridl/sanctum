import { useState, useEffect } from 'react'

function Dashboard({ token, role, userFirstName, userLastName, onLogout }) {
  const [clients, setClients] = useState([])
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')

  async function loadClients() {
    const r = await fetch('http://localhost:8000/clients/', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await r.json()
    setClients(data)
  }
  
  useEffect(() => { loadClients() }, [token])

  
  async function handleAddClient(e) {
    e.preventDefault()
    if (!firstName.trim() || !lastName.trim()) return
    const r = await fetch('http://localhost:8000/clients/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ first_name: firstName, last_name: lastName }),
    })
    if (!r.ok) return
    setFirstName('')
    setLastName('')
    await loadClients()
  }

  return (
    <div style={{ maxWidth: 600, margin: '100px auto', fontFamily: 'sans-serif' }}>
      <h1>🖤 Sanctum</h1>
      <p>
        Welcome
        {userFirstName && <span data-testid="user-name">, {userFirstName} {userLastName}</span>}
        {' '}(<strong data-testid="role-label">{role}</strong>){' '}
        <button onClick={onLogout}>Logout</button>
      </p>

      <h2>Clients</h2>
      <ul data-testid="client-list">
        {clients.map(c => (
          <li key={c.id} data-testid="client-row" data-client-id={c.id}>
            {c.first_name} {c.last_name}
          </li>
        ))}
      </ul>

      {role === 'therapist' && (
        <form onSubmit={handleAddClient} data-testid="add-client-form" style={{ marginTop: 24 }}>
          <h3>Add client</h3>
          <input
            data-testid="add-client-first-name"
            placeholder="First name"
            value={firstName}
            onChange={e => setFirstName(e.target.value)}
            style={{ padding: 8, marginRight: 8 }}
          />
          <input
            data-testid="add-client-last-name"
            placeholder="Last name"
            value={lastName}
            onChange={e => setLastName(e.target.value)}
            style={{ padding: 8, marginRight: 8 }}
          />
          <button data-testid="add-client-submit" type="submit" style={{ padding: 8 }}>
            Add
          </button>
        </form>
      )}

    </div>
  )
}

function App() {
  const [mode, setMode] = useState('login') // 'login' | 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [signupRole, setSignupRole] = useState('therapist')
  const [error, setError] = useState('')

  const [token, setToken] = useState(null)
  const [role, setRole] = useState(null)
  const [userFirstName, setUserFirstName] = useState('')
  const [userLastName, setUserLastName] = useState('')

  function applySession(data) {
    setToken(data.access_token)
    setRole(data.role)
    setUserFirstName(data.first_name || '')
    setUserLastName(data.last_name || '')
    setError('')
  }

  async function handleLogin(e) {
    e.preventDefault()
    setError('')
    const response = await fetch('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    if (!response.ok) {
      setError('Invalid email or password')
      return
    }
    applySession(await response.json())
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
    applySession(await response.json())
  }

  function switchMode(next) {
    setMode(next)
    setError('')
    setPassword('')
  }

  if (token) {
    return (
      <Dashboard
        token={token}
        role={role}
        userFirstName={userFirstName}
        userLastName={userLastName}
        onLogout={() => {
          setToken(null)
          setRole(null)
          setUserFirstName('')
          setUserLastName('')
          setEmail('')
          setPassword('')
          setFirstName('')
          setLastName('')
          setSignupRole('therapist')
          setError('')
          setMode('login')
        }}
      />
    )
  }

  const inputStyle = { width: '100%', padding: 8, marginBottom: 8 }

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
            <button
              data-testid="show-signup"
              type="button"
              onClick={() => switchMode('signup')}
              style={{ background: 'none', border: 'none', color: '#0066cc', cursor: 'pointer', padding: 0 }}
            >
              Create an account
            </button>
          </p>
        </form>
      ) : (
        <form onSubmit={handleSignup} data-testid="signup-form">
          <input
            data-testid="signup-first-name"
            placeholder="First name"
            value={firstName}
            onChange={e => setFirstName(e.target.value)}
            style={inputStyle}
          />
          <input
            data-testid="signup-last-name"
            placeholder="Last name"
            value={lastName}
            onChange={e => setLastName(e.target.value)}
            style={inputStyle}
          />
          <input
            data-testid="signup-email"
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            style={inputStyle}
          />
          <input
            data-testid="signup-password"
            type="password"
            placeholder="Password (min 8 chars)"
            value={password}
            onChange={e => setPassword(e.target.value)}
            style={inputStyle}
          />
          <select
            data-testid="signup-role"
            value={signupRole}
            onChange={e => setSignupRole(e.target.value)}
            style={inputStyle}
          >
            <option value="therapist">Therapist</option>
            <option value="psychiatrist">Psychiatrist</option>
          </select>
          <button data-testid="signup-submit" type="submit" style={{ width: '100%', padding: 8 }}>
            Sign up
          </button>
          <p style={{ marginTop: 12 }}>
            Already have an account?{' '}
            <button
              data-testid="show-login"
              type="button"
              onClick={() => switchMode('login')}
              style={{ background: 'none', border: 'none', color: '#0066cc', cursor: 'pointer', padding: 0 }}
            >
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

export default App