import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function ClientPage() {
  const { clientId } = useParams()
  const { session } = useAuth()

  const [client, setClient] = useState(null)
  const [notFound, setNotFound] = useState(false)
  const [psychEmail, setPsychEmail] = useState('')
  const [shareError, setShareError] = useState('')

  async function loadClient() {
    const r = await fetch('http://localhost:8000/clients/', {
      headers: { Authorization: `Bearer ${session.token}` },
    })
    const list = await r.json()
    const found = list.find(c => String(c.id) === clientId)
    if (!found) {
      setNotFound(true)
      setClient(null)
      return
    }
    setClient(found)
    setNotFound(false)
  }

  useEffect(() => {
    loadClient()
  }, [clientId])

  async function handleShare(e) {
    e.preventDefault()
    setShareError('')
    if (!psychEmail.trim()) return
    const r = await fetch(`http://localhost:8000/clients/${clientId}/share`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${session.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ psychiatrist_email: psychEmail }),
    })
    if (!r.ok) {
      if (r.status === 404) setShareError('No psychiatrist registered with that email')
      else if (r.status === 409) setShareError('This client is already shared')
      else setShareError('Could not share — please try again')
      return
    }
    setPsychEmail('')
    await loadClient()
  }

  async function handleUnshare() {
    setShareError('')
    const r = await fetch(`http://localhost:8000/clients/${clientId}/share`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${session.token}` },
    })
    if (!r.ok) {
      setShareError('Could not unshare — please try again')
      return
    }
    await loadClient()
  }

  if (notFound) {
    return (
      <div style={{ maxWidth: 600, margin: '100px auto', fontFamily: 'sans-serif' }}>
        <p data-testid="client-not-found">Client not found.</p>
        <Link to="/dashboard">← Back to clients</Link>
      </div>
    )
  }

  if (!client) {
    return (
      <div style={{ maxWidth: 600, margin: '100px auto', fontFamily: 'sans-serif' }}>
        <p>Loading…</p>
      </div>
    )
  }

  const isTherapist = session.role === 'therapist'
  const isShared = Boolean(client.shared_with)

  return (
    <div style={{ maxWidth: 600, margin: '100px auto', fontFamily: 'sans-serif' }}>
      <p>
        <Link to="/dashboard" data-testid="back-to-dashboard">← Back to clients</Link>
      </p>
      <h1 data-testid="client-header">
        {client.first_name} {client.last_name}
      </h1>

      {isTherapist && (
        <section style={{ marginTop: 24 }} data-testid="share-section">
          <h2>Sharing</h2>

          {isShared ? (
            <div data-testid="shared-with-block">
              <p>
                Shared with{' '}
                <strong data-testid="shared-with-email">{client.shared_with}</strong>
              </p>
              <button data-testid="unshare-button" type="button" onClick={handleUnshare}>
                Unshare
              </button>
            </div>
          ) : (
            <form onSubmit={handleShare} data-testid="share-form">
              <input
                data-testid="share-email"
                type="email"
                placeholder="Psychiatrist email"
                value={psychEmail}
                onChange={e => setPsychEmail(e.target.value)}
                style={{ padding: 8, marginRight: 8, minWidth: 260 }}
              />
              <button data-testid="share-submit" type="submit" style={{ padding: 8 }}>
                Share
              </button>
            </form>
          )}

          {shareError && (
            <p data-testid="share-error" style={{ color: '#b00020', marginTop: 12 }}>
              {shareError}
            </p>
          )}
        </section>
      )}

      <section style={{ marginTop: 32 }}>
        <h2>Notes</h2>
        <p style={{ color: '#666' }}>(Notes UI coming next.)</p>
      </section>
    </div>
  )
}
