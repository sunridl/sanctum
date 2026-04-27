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

  const [notes, setNotes] = useState([])
  const [noteContent, setNoteContent] = useState('')
  const [noteIsShared, setNoteIsShared] = useState(false)
  const [noteError, setNoteError] = useState('')

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

  async function loadNotes() {
    const r = await fetch(`http://localhost:8000/clients/${clientId}/notes`, {
      headers: { Authorization: `Bearer ${session.token}` },
    })
    if (!r.ok) {
      setNotes([])
      return
    }
    setNotes(await r.json())
  }

  useEffect(() => {
    loadClient()
    loadNotes()
  }, [clientId])

  async function handleAddNote(e) {
    e.preventDefault()
    setNoteError('')
    if (!noteContent.trim()) return
    // The UI toggle expresses "shared" (the exception); the data model
    // expresses "is_private" (the default). Psychiatrists can't create
    // private notes at all, so we hardcode is_private=false for them.
    const isPrivate = isTherapist ? !noteIsShared : false
    const r = await fetch(`http://localhost:8000/clients/${clientId}/notes`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${session.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content: noteContent, is_private: isPrivate }),
    })
    if (!r.ok) {
      setNoteError('Could not save note — please try again')
      return
    }
    setNoteContent('')
    setNoteIsShared(false)
    await loadNotes()
  }

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

      <section style={{ marginTop: 32 }} data-testid="notes-section">
        <h2>Notes</h2>

        <ul data-testid="notes-list" style={{ listStyle: 'none', padding: 0 }}>
          {[...notes].reverse().map(n => (
            <li
              key={n.id}
              data-testid="note-row"
              data-note-id={n.id}
              style={{
                border: '1px solid #ddd',
                borderRadius: 6,
                padding: 12,
                marginBottom: 8,
              }}
            >
              <p data-testid="note-content" style={{ margin: '0 0 8px 0' }}>
                {n.content}
              </p>
              <small style={{ color: '#666' }}>
                {n.author_first_name && n.author_last_name ? (
                  <>
                    <span data-testid="note-author-name">
                      {n.author_first_name} {n.author_last_name}
                    </span>
                    {' '}(
                    <span data-testid="note-role">{n.role}</span>
                    , <span data-testid="note-author-email">{n.author}</span>)
                  </>
                ) : (
                  <>
                    <span data-testid="note-author-email">{n.author}</span>
                    {' '}(<span data-testid="note-role">{n.role}</span>)
                  </>
                )}
              </small>
              {isTherapist && !n.is_private && (
                <span
                  data-testid="note-shared-badge"
                  style={{
                    marginLeft: 8,
                    padding: '2px 6px',
                    background: '#d1ecf1',
                    border: '1px solid #bee5eb',
                    borderRadius: 4,
                    fontSize: '0.8em',
                  }}
                >
                  shared
                </span>
              )}
            </li>
          ))}
        </ul>

        <form onSubmit={handleAddNote} data-testid="add-note-form" style={{ marginTop: 16 }}>
          <textarea
            data-testid="add-note-content"
            placeholder="Write a note…"
            value={noteContent}
            onChange={e => setNoteContent(e.target.value)}
            rows={3}
            style={{ width: '100%', padding: 8, marginBottom: 8 }}
          />
          {isTherapist && (
            <label
              data-testid="add-note-shared-label"
              style={{ display: 'block', marginBottom: 8 }}
            >
              <input
                data-testid="add-note-shared-toggle"
                type="checkbox"
                checked={noteIsShared}
                onChange={e => setNoteIsShared(e.target.checked)}
              />{' '}
              Shared (visible to psychiatrist)
            </label>
          )}
          <button data-testid="add-note-submit" type="submit" style={{ padding: 8 }}>
            Add note
          </button>
        </form>

        {noteError && (
          <p data-testid="note-error" style={{ color: '#b00020', marginTop: 12 }}>
            {noteError}
          </p>
        )}
      </section>
    </div>
  )
}
