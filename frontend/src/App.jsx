import { useState, useEffect } from 'react'

function Dashboard({ token, role, onLogout }) {
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
      <p>Welcome, <strong data-testid="role-label">{role}</strong> <button onClick={onLogout}>Logout</button></p>

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
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState(null)
  const [role, setRole] = useState(null)

  async function handleLogin(e) {
    e.preventDefault()
    const response = await fetch('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    const data = await response.json()
    setToken(data.access_token)
    setRole(data.role)
  }

  if (token) {
    return <Dashboard token={token} role={role} onLogout={() => setToken(null)} />
  }

  return (
    <div style={{ maxWidth: 400, margin: '100px auto', fontFamily: 'sans-serif' }}>
      <h1>🖤 Sanctum</h1>
      <form onSubmit={handleLogin}>
        <input
          data-testid="login-email"
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          style={{ width: '100%', padding: 8, marginBottom: 8 }}
        />
        <input
          data-testid="login-password"
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          style={{ width: '100%', padding: 8, marginBottom: 8 }}
        />
        <button data-testid="login-submit" type="submit" style={{ width: '100%', padding: 8 }}>
          Login
        </button>
      </form>
    </div>
  )
}

export default App