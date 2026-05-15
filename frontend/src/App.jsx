export default function App() {
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
      gap: '0.5rem',
    }}>
      <h1 style={{ color: '#ee702f', fontSize: '2rem', fontWeight: 700 }}>
        Lincium Hub
      </h1>
      <p style={{ color: '#8899aa' }}>React carregando via FastAPI — Slice R1 ok</p>
    </div>
  )
}
