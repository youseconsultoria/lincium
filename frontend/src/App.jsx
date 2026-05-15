import { useAuth0 } from '@auth0/auth0-react'

export default function App() {
  const { isLoading, isAuthenticated, loginWithRedirect, user } = useAuth0()

  if (isLoading) {
    return <Screen><p style={{ color: '#8899aa' }}>Carregando...</p></Screen>
  }

  if (!isAuthenticated) {
    return (
      <Screen>
        <h1>Lincium Hub</h1>
        <button onClick={() => loginWithRedirect()} style={btnStyle}>
          Entrar
        </button>
      </Screen>
    )
  }

  return (
    <Screen>
      <h1>Lincium Hub</h1>
      <p style={{ color: '#8899aa' }}>Olá, {user.email}</p>
      <p style={{ color: '#556', fontSize: '0.85rem' }}>Auth0 SPA OK — Slice R2</p>
    </Screen>
  )
}

function Screen({ children }) {
  return (
    <div style={{
      background: '#090d16',
      color: '#e8edf5',
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif',
      gap: '1rem',
    }}>
      {children}
    </div>
  )
}

const btnStyle = {
  background: '#ee702f',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  padding: '0.6rem 1.6rem',
  fontSize: '1rem',
  cursor: 'pointer',
  fontWeight: 600,
}
