import { useState, useEffect } from 'react'

function Dashboard({ token, role, onLogout }) {
  const [clients, setClients] = useState([])

  useEffect(() => {
    fetch('http://localhost:8000/clients/', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(data => setClients(data))
  }, [token])

  return (
    <div style={{ maxWidth: 600, margin: '100px auto', fontFamily: 'sans-serif' }}>
      <h1>🖤 Sanctum</h1>
      <p>Welcome, <strong>{role}</strong> <button onClick={onLogout}>Logout</button></p>
      <h2>Clients</h2>
        <ul data-testid="client-list">
          {clients.map(c => (
    <     li key={c.id} data-testid="client-row" data-client-id={c.id}>
            {c.first_name} {c.last_name}
          </li>
          ))}
        </ul>
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
        <div>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            style={{ width: '100%', padding: 8, marginBottom: 8 }}
          />
        </div>
        <div>
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            style={{ width: '100%', padding: 8, marginBottom: 8 }}
          />
        </div>
        <button type="submit" style={{ width: '100%', padding: 8 }}>
          Login
        </button>
      </form>
    </div>
  )
}

export default App