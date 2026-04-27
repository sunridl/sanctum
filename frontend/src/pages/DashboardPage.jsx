import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function DashboardPage() {
  const { session, logout } = useAuth()
  const navigate = useNavigate()

  const [clients, setClients] = useState([])
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')

  async function loadClients() {
    const r = await fetch('http://localhost:8000/clients/', {
      headers: { Authorization: `Bearer ${session.token}` },
    })
    setClients(await r.json())
  }

  useEffect(() => {
    loadClients()
  }, [])

  async function handleAddClient(e) {
    e.preventDefault()
    if (!firstName.trim() || !lastName.trim()) return
    const r = await fetch('http://localhost:8000/clients/', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${session.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ first_name: firstName, last_name: lastName }),
    })
    if (!r.ok) return
    setFirstName('')
    setLastName('')
    await loadClients()
  }

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <div style={{ maxWidth: 600, margin: '100px auto', fontFamily: 'sans-serif' }}>
      <h1>🖤 Sanctum</h1>
      <p>
        Welcome
        {session.firstName && (
          <span data-testid="user-name">, {session.firstName} {session.lastName}</span>
        )}
        {' '}(<strong data-testid="role-label">{session.role}</strong>){' '}
        <button onClick={handleLogout}>Logout</button>
      </p>

      <h2>Clients</h2>
      <ul data-testid="client-list" style={{ listStyle: 'none', padding: 0 }}>
        {clients.map(c => (
          <li key={c.id} data-testid="client-row" data-client-id={c.id} style={{ padding: '6px 0' }}>
            <Link to={`/clients/${c.id}`} data-testid="client-link">
              {c.first_name} {c.last_name}
            </Link>
          </li>
        ))}
      </ul>

      {session.role === 'therapist' && (
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
