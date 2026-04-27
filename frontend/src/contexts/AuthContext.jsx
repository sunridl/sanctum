import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)
const STORAGE_KEY = 'sanctum.session'

// NOTE: storing the JWT in sessionStorage is a deliberate portfolio-stage
// tradeoff. It's cleared on tab close (less risky than localStorage) but is
// still readable by JS, so it carries XSS exposure. Production should move
// auth to HTTP-only cookies; that's noted in the README as future work.
function readStoredSession() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readStoredSession)

  function login(data) {
    const next = {
      token: data.access_token,
      role: data.role,
      firstName: data.first_name || '',
      lastName: data.last_name || '',
    }
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    setSession(next)
  }

  function logout() {
    sessionStorage.removeItem(STORAGE_KEY)
    setSession(null)
  }

  return (
    <AuthContext.Provider value={{ session, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
