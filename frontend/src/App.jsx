import { useAuth0 } from '@auth0/auth0-react'
import { useCallback, useEffect, useRef, useState } from 'react'

const AUDIENCE = 'https://api.lincium.com.br'
const MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
               'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

// ─── Theme ────────────────────────────────────────────────────────────────────

function useTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem('lincium-theme') || 'dark')
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('lincium-theme', theme)
  }, [theme])
  return [theme, () => setTheme(t => t === 'dark' ? 'light' : 'dark')]
}

// ─── Icons ────────────────────────────────────────────────────────────────────

const ic = (d, extra = '') => ({ size = 16, color, style: st } = {}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color || 'currentColor'}
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={st} {...extra && {}}>
    <path d={d} />
  </svg>
)

const IconHome     = ({ size = 16 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
const IconLayers   = ({ size = 16 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
const IconUpload   = ({ size = 36 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>
const IconSun      = ({ size = 15 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
const IconMoon     = ({ size = 15 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
const IconCheck    = ({ size = 16 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
const IconX        = ({ size = 13 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
const IconFile     = ({ size = 14 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
const IconLogout   = ({ size = 15 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
const IconChevron  = ({ open, size = 12 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }}><polyline points="9 18 15 12 9 6"/></svg>
const IconClock    = ({ size = 16 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>

// ─── Spinner ──────────────────────────────────────────────────────────────────

function Spinner({ size = 36 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 50 50" style={{ animation: 'lspin 0.85s linear infinite' }}>
      <style>{`@keyframes lspin{to{transform:rotate(360deg)}}`}</style>
      <circle cx="25" cy="25" r="20" fill="none" stroke="var(--border-hi)" strokeWidth="4"/>
      <circle cx="25" cy="25" r="20" fill="none" stroke="var(--primary)" strokeWidth="4" strokeDasharray="42 88" strokeLinecap="round"/>
    </svg>
  )
}

// ─── Logo ─────────────────────────────────────────────────────────────────────

function LogoMark({ size = 32 }) {
  const [err, setErr] = useState(false)
  return (
    <div style={{ width: size, height: size, borderRadius: '50%', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', flexShrink: 0, boxShadow: '0 0 0 2px rgba(238,112,47,0.2)' }}>
      {err
        ? <span style={{ color: '#fff', fontWeight: 900, fontSize: size * 0.42, lineHeight: 1 }}>L</span>
        : <img src="/static/logo.png" alt="" onError={() => setErr(true)} style={{ width: '74%', height: '74%', objectFit: 'contain', filter: 'brightness(0) invert(1)' }} />
      }
    </div>
  )
}

// ─── Login ────────────────────────────────────────────────────────────────────

function LoginScreen({ onLogin, theme, onToggleTheme }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', padding: '2rem', position: 'relative' }}>
      <button onClick={onToggleTheme} style={{ ...s.iconBtn, position: 'absolute', top: '1.5rem', right: '1.5rem' }}>
        {theme === 'dark' ? <IconSun /> : <IconMoon />}
      </button>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', maxWidth: 340, width: '100%' }}>
        <LogoMark size={76} />
        <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
          <h1 style={{ fontSize: '2.1rem', fontWeight: 800, letterSpacing: '-0.5px', color: 'var(--text)', lineHeight: 1 }}>Lincium</h1>
          <p style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.45rem', letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 500 }}>Powered by EPrime</p>
        </div>
        <button onClick={onLogin} style={{ ...s.btnPrimary, width: '100%', padding: '0.9rem', fontSize: '1rem', fontWeight: 700, marginTop: '2.75rem' }}>Entrar</button>
        <p style={{ marginTop: '1.25rem', fontSize: '0.72rem', color: 'var(--dim)', textAlign: 'center', lineHeight: 1.7 }}>
          Acesso restrito a colaboradores autorizados.<br />Autenticação segura via Auth0.
        </p>
      </div>
      <p style={{ position: 'absolute', bottom: '2rem', fontSize: '0.75rem', color: 'var(--dim)', fontStyle: 'italic' }}>
        "A única central que seu negócio precisa."
      </p>
    </div>
  )
}

// ─── Header ───────────────────────────────────────────────────────────────────

function AppHeader({ theme, onToggleTheme }) {
  return (
    <header style={{ position: 'sticky', top: 0, zIndex: 100, height: 52, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 1.5rem', background: theme === 'dark' ? 'rgba(9,13,22,0.92)' : 'rgba(245,247,250,0.92)', backdropFilter: 'blur(14px)', borderBottom: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <LogoMark size={26} />
        <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text)', letterSpacing: '-0.2px' }}>Lincium</span>
        <span style={{ color: 'var(--dim)', margin: '0 0.1rem' }}>·</span>
        <span style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>EPrime</span>
      </div>
      <button onClick={onToggleTheme} style={s.iconBtn} title="Alternar tema">
        {theme === 'dark' ? <IconSun /> : <IconMoon />}
      </button>
    </header>
  )
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { id: 'home',     label: 'Home',                    Icon: IconHome,   section: null },
  { id: '_sep1',    label: 'Contábil',                Icon: null,       section: 'CONTÁBIL' },
  { id: 'extratos', label: 'Lançamentos de extratos', Icon: IconLayers, section: 'CONTÁBIL' },
]

function Sidebar({ page, onNavigate, me, onLogout }) {
  const initials = me?.email?.[0]?.toUpperCase() || '?'

  return (
    <aside style={{ width: 228, flexShrink: 0, background: 'var(--surface)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
      <nav style={{ flex: 1, padding: '0.5rem 0.5rem 0' }}>
        {NAV_ITEMS.map(item => {
          if (item.section && !item.Icon) {
            return (
              <p key={item.id} style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--dim)', letterSpacing: '0.1em', textTransform: 'uppercase', padding: '1rem 0.75rem 0.3rem' }}>
                {item.label}
              </p>
            )
          }
          const active = page === item.id
          return (
            <button key={item.id} onClick={() => onNavigate(item.id)} style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: '0.65rem',
              padding: '0.52rem 0.75rem', borderRadius: 7, marginBottom: 2,
              background: active ? 'var(--primary-dim)' : 'transparent',
              color: active ? 'var(--primary)' : 'var(--muted)',
              border: 'none', fontSize: '0.84rem', fontWeight: active ? 600 : 400,
              cursor: 'pointer', transition: 'all 0.12s', textAlign: 'left',
            }}>
              <span style={{ flexShrink: 0, opacity: active ? 1 : 0.7 }}>
                <item.Icon size={15} />
              </span>
              {item.label}
            </button>
          )
        })}
      </nav>

      {/* User info at bottom */}
      <div style={{ padding: '0.75rem', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <div style={{ width: 30, height: 30, borderRadius: '50%', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: '0.75rem', fontWeight: 800, color: '#fff' }}>
          {initials}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{me?.tenant_name || '...'}</p>
          <p style={{ fontSize: '0.68rem', color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{me?.email || ''}</p>
        </div>
        <button onClick={onLogout} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', padding: 4, display: 'flex', flexShrink: 0 }} title="Sair">
          <IconLogout size={14} />
        </button>
      </div>
    </aside>
  )
}

// ─── Homepage ─────────────────────────────────────────────────────────────────

function BatchCard({ batch, onNovo }) {
  const pct = batch.auto_rate
  const periodo = batch.period_month
    ? `${MESES[batch.period_month - 1]}/${batch.period_year}`
    : String(batch.period_year)
  const isPending = batch.status === 'pending_review'

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
      <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
          <div>
            <p style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text)' }}>{batch.client_name}</p>
            <p style={{ fontSize: '0.78rem', color: 'var(--muted)', marginTop: '0.15rem' }}>{periodo}</p>
          </div>
          {isPending
            ? <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#f59e0b', background: 'rgba(245,158,11,0.12)', padding: '0.2rem 0.55rem', borderRadius: 4, letterSpacing: '0.04em', textTransform: 'uppercase' }}>Revisão pendente</span>
            : <span style={{ fontSize: '0.66rem', fontWeight: 700, color: 'var(--success)', background: 'rgba(45,212,191,0.1)', padding: '0.2rem 0.55rem', borderRadius: 4, letterSpacing: '0.04em', textTransform: 'uppercase' }}>Concluído</span>
          }
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Automação</span>
          <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--primary)' }}>{pct}%</span>
        </div>
        <div style={{ height: 4, background: 'var(--surface)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg,var(--primary),#f5924e)', borderRadius: 2 }} />
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', borderBottom: '1px solid var(--border)' }}>
        {[
          { l: 'Total', v: batch.total_tx, c: 'var(--text)' },
          { l: 'Automáticas', v: batch.auto_matched, c: 'var(--success)' },
          { l: 'A revisar', v: batch.needs_review_count, c: batch.needs_review_count > 0 ? '#f59e0b' : 'var(--success)' },
        ].map(({ l, v, c }, i) => (
          <div key={i} style={{ padding: '0.75rem', textAlign: 'center', borderRight: i < 2 ? '1px solid var(--border)' : 'none' }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: c, letterSpacing: '-0.5px' }}>{v}</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--muted)', marginTop: '0.2rem', fontWeight: 500 }}>{l}</div>
          </div>
        ))}
      </div>
      {isPending && (
        <div style={{ padding: '0.75rem 1.25rem' }}>
          <a href="/" style={{ ...s.btnPrimary, display: 'block', textAlign: 'center', textDecoration: 'none', padding: '0.6rem', fontSize: '0.85rem' }}>
            Ir para revisão →
          </a>
        </div>
      )}
    </div>
  )
}

// ─── Home ─────────────────────────────────────────────────────────────────────

const MODULES = [
  {
    id: 'extratos',
    label: 'Conciliação Contábil',
    desc: 'Extrato bancário → matching automático → plano de contas → Domínio',
    status: 'active',
  },
  {
    id: null,
    label: 'Departamento Pessoal',
    desc: 'Folha de pagamento, dissídios, convenções coletivas, conferência automática',
    status: 'dev',
  },
  {
    id: null,
    label: 'Fiscal',
    desc: 'SPED, NF-e, obrigações acessórias, monitoramento SEFAZ',
    status: 'dev',
  },
  {
    id: null,
    label: 'Societário',
    desc: 'Alterações contratuais, atos societários, registro de sócios',
    status: 'dev',
  },
  {
    id: null,
    label: 'IA Lincium',
    desc: 'Assistente inteligente para análise de documentos e consultas contábeis',
    status: 'dev',
  },
]

function HomePage({ me, onNavigate }) {
  const name = me?.email?.split('@')[0] || ''
  return (
    <div style={{ maxWidth: 760, margin: '0 auto', padding: '2.5rem 2rem' }}>
      <div style={{ marginBottom: '2.5rem' }}>
        <p style={{ fontSize: '0.7rem', color: 'var(--dim)', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.35rem' }}>Hub</p>
        <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.3px' }}>
          Olá{name ? `, ${name}` : ''}
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--muted)', marginTop: '0.3rem' }}>
          {me?.tenant_name || 'PRIME Contabilidade'} — selecione um módulo para começar
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '0.85rem' }}>
        {MODULES.map(mod => (
          <div
            key={mod.label}
            onClick={() => mod.id && onNavigate(mod.id)}
            style={{
              background: 'var(--card)',
              border: `1px solid ${mod.status === 'active' ? 'var(--border)' : 'var(--border)'}`,
              borderRadius: 10,
              padding: '1.25rem 1.4rem',
              cursor: mod.status === 'active' ? 'pointer' : 'default',
              transition: 'border-color 0.15s, box-shadow 0.15s',
              position: 'relative',
              ...(mod.status === 'active' ? {} : { opacity: 0.6 }),
            }}
            onMouseEnter={e => { if (mod.id) { e.currentTarget.style.borderColor = 'var(--primary)'; e.currentTarget.style.boxShadow = '0 0 0 1px var(--primary-dim)' } }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.6rem' }}>
              <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text)' }}>{mod.label}</h3>
              {mod.status === 'active'
                ? <span style={{ fontSize: '0.62rem', fontWeight: 700, color: 'var(--success)', background: 'rgba(45,212,191,0.1)', padding: '0.2rem 0.55rem', borderRadius: 4, letterSpacing: '0.06em', flexShrink: 0, marginLeft: '0.5rem' }}>ATIVO</span>
                : <span style={{ fontSize: '0.62rem', fontWeight: 700, color: 'var(--dim)', background: 'var(--surface)', padding: '0.2rem 0.55rem', borderRadius: 4, letterSpacing: '0.06em', flexShrink: 0, marginLeft: '0.5rem' }}>EM DESENVOLVIMENTO</span>
              }
            </div>
            <p style={{ fontSize: '0.81rem', color: 'var(--muted)', lineHeight: 1.55 }}>{mod.desc}</p>
            {mod.status === 'active' && (
              <p style={{ fontSize: '0.75rem', color: 'var(--primary)', marginTop: '0.75rem', fontWeight: 600 }}>Acessar →</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Overview (extratos) ──────────────────────────────────────────────────────

function OverviewView({ token, onNovo }) {
  const [batches, setBatches] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    fetch('/api/v1/conciliacao/batches', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(data => { setBatches(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [token])

  const pending   = batches?.filter(b => b.status === 'pending_review') ?? []
  const completed = batches?.filter(b => b.status !== 'pending_review') ?? []

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '2.5rem 2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem' }}>
        <div>
          <p style={{ fontSize: '0.7rem', color: 'var(--dim)', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.3rem' }}>Contábil · Extratos</p>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.3px' }}>Lançamentos de Extratos</h2>
        </div>
        <button onClick={onNovo} style={{ ...s.btnPrimary, padding: '0.65rem 1.1rem', fontSize: '0.88rem' }}>
          + Nova conciliação
        </button>
      </div>

      {loading && <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}><Spinner size={32} /></div>}

      {!loading && pending.length === 0 && completed.length === 0 && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted)', border: '1px dashed var(--border)', borderRadius: 10 }}>
          <p style={{ fontSize: '0.9rem' }}>Nenhum processamento encontrado.</p>
          <p style={{ fontSize: '0.8rem', marginTop: '0.3rem' }}>Clique em "Nova conciliação" para começar.</p>
        </div>
      )}

      {!loading && pending.length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.85rem' }}>
            <span style={{ color: '#f59e0b' }}><IconClock size={14} /></span>
            <h3 style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Aguardando revisão</h3>
            <span style={{ fontSize: '0.68rem', background: 'rgba(245,158,11,0.12)', color: '#f59e0b', padding: '0.15rem 0.5rem', borderRadius: 4, fontWeight: 700 }}>{pending.length}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {pending.map(b => <BatchCard key={b.batch_id} batch={b} />)}
          </div>
        </section>
      )}

      {!loading && completed.length > 0 && (
        <section>
          <h3 style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.75rem' }}>Histórico</h3>
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
            {completed.slice(0, 8).map((b, i) => {
              const periodo = b.period_month ? `${MESES[b.period_month - 1]}/${b.period_year}` : String(b.period_year)
              return (
                <div key={b.batch_id} style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1.1rem', borderBottom: i < Math.min(completed.length, 8) - 1 ? '1px solid var(--border)' : 'none' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: '0.83rem', fontWeight: 600, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{b.client_name}</p>
                    <p style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: '0.1rem' }}>{periodo}</p>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <p style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--primary)' }}>{b.auto_rate}%</p>
                    <p style={{ fontSize: '0.68rem', color: 'var(--muted)' }}>{b.total_tx} tx</p>
                  </div>
                  <span style={{ fontSize: '0.66rem', fontWeight: 700, color: 'var(--success)', background: 'rgba(45,212,191,0.1)', padding: '0.2rem 0.5rem', borderRadius: 4, flexShrink: 0 }}>OK</span>
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}

// ─── File detection + DropZone ────────────────────────────────────────────────

const FILE_TYPES = {
  extrato: { label: 'Extrato Bancário', color: '#60a5fa' },
  comp:    { label: 'Comprovante',      color: '#a78bfa' },
  plano:   { label: 'Plano de Contas',  color: '#ee702f' },
  pdf:     { label: 'PDF',              color: '#6b7f96' },
  unknown: { label: 'Não suportado',    color: '#e05050' },
}

function classifyFile(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  const up  = file.name.toUpperCase()
  if (['xlsx', 'xls'].includes(ext)) return 'plano'
  if (ext !== 'pdf') return 'unknown'
  if (up.includes('SANTANDER') || up.includes('SICOOB') || up.includes('SISBR') || up.includes('BRASIL') || up.includes('EXTRATO')) return 'extrato'
  if (up.includes('COMPROVANTE') || up.includes('BRADESCO') || up.includes('ITAU')) return 'comp'
  return 'pdf'
}

const fmtSize = b => b < 1048576 ? (b / 1024).toFixed(0) + ' KB' : (b / 1048576).toFixed(1) + ' MB'

function DropZone({ items, onAdd, onRemove }) {
  const [drag, setDrag] = useState(false)
  const ref = useRef()

  const addFiles = useCallback(list => {
    const next = Array.from(list)
      .filter(f => !items.find(i => i.file.name === f.name))
      .map(f => ({ id: Math.random().toString(36).slice(2), file: f, role: classifyFile(f) }))
    if (next.length) onAdd(next)
  }, [items, onAdd])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
      <div
        onClick={() => ref.current.click()}
        onDragOver={e => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={e => { e.preventDefault(); setDrag(false); addFiles(e.dataTransfer.files) }}
        style={{ border: `2px dashed ${drag ? 'var(--primary)' : 'var(--border-hi)'}`, borderRadius: 12, padding: '2.25rem 2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.6rem', cursor: 'pointer', userSelect: 'none', background: drag ? 'var(--primary-dim)' : 'var(--surface)', color: drag ? 'var(--primary)' : 'var(--dim)', transition: 'all 0.14s ease', transform: drag ? 'scale(1.015)' : 'scale(1)' }}
      >
        <IconUpload size={36} />
        <div style={{ textAlign: 'center' }}>
          <p style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text)' }}>Arraste os documentos aqui</p>
          <p style={{ fontSize: '0.8rem', color: 'var(--muted)', marginTop: '0.2rem' }}>ou <span style={{ color: 'var(--primary)' }}>clique para selecionar</span></p>
        </div>
        <p style={{ fontSize: '0.72rem', color: 'var(--dim)', textAlign: 'center', lineHeight: 1.6 }}>
          Extratos bancários (PDF) · Comprovantes (PDF) · Plano de Contas (.xlsx)
        </p>
      </div>
      <input ref={ref} type="file" multiple accept=".pdf,.xlsx,.xls" style={{ display: 'none' }} onChange={e => { addFiles(e.target.files); e.target.value = '' }} />
      {items.map(item => {
        const t = FILE_TYPES[item.role]
        return (
          <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', padding: '0.55rem 0.85rem', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
            <span style={{ color: 'var(--muted)', flexShrink: 0 }}><IconFile size={14} /></span>
            <span style={{ flex: 1, fontSize: '0.83rem', color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.file.name}</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--muted)', flexShrink: 0 }}>{fmtSize(item.file.size)}</span>
            <span style={{ fontSize: '0.66rem', fontWeight: 700, letterSpacing: '0.05em', color: t.color, background: t.color + '18', padding: '0.18rem 0.5rem', borderRadius: 4, flexShrink: 0, textTransform: 'uppercase' }}>{t.label}</span>
            <button onClick={() => onRemove(item.id)} style={{ background: 'none', border: 'none', color: 'var(--muted)', display: 'flex', flexShrink: 0, padding: '2px', cursor: 'pointer' }}><IconX size={13} /></button>
          </div>
        )
      })}
    </div>
  )
}

// ─── Upload View ──────────────────────────────────────────────────────────────

function UploadView({ onProcess, error }) {
  const [items, setItems] = useState([])
  const addItems   = useCallback(n => setItems(p => [...p, ...n]), [])
  const removeItem = useCallback(id => setItems(p => p.filter(i => i.id !== id)), [])

  function submit() {
    const ext  = items.filter(i => i.role === 'extrato' || i.role === 'pdf')
    const comp = items.filter(i => i.role === 'comp')
    const plan = items.find(i => i.role === 'plano')
    if (!ext.length) { onProcess(null, 'Adicione pelo menos um extrato bancário (PDF).'); return }
    onProcess({ extrato: ext[0].file, comprovantes: comp.map(c => c.file), plano: plan?.file })
  }

  return (
    <div style={{ maxWidth: 660, margin: '0 auto', padding: '2.5rem 2rem' }}>
      <div style={{ marginBottom: '1.75rem' }}>
        <p style={{ fontSize: '0.7rem', color: 'var(--dim)', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.3rem' }}>Contábil · Extratos</p>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.3px' }}>Nova Conciliação</h2>
        <p style={{ fontSize: '0.83rem', color: 'var(--muted)', marginTop: '0.3rem' }}>Importe os documentos — o sistema detecta banco, período e classifica automaticamente.</p>
      </div>
      <DropZone items={items} onAdd={addItems} onRemove={removeItem} />
      {error && <p style={{ marginTop: '1rem', fontSize: '0.83rem', color: 'var(--danger)', padding: '0.7rem 1rem', background: 'rgba(224,80,80,0.07)', borderRadius: 8, border: '1px solid rgba(224,80,80,0.18)' }}>{error}</p>}
      <button onClick={submit} disabled={!items.length} style={{ ...s.btnPrimary, width: '100%', padding: '0.85rem', marginTop: '1.25rem', fontSize: '0.93rem', opacity: items.length ? 1 : 0.4, cursor: items.length ? 'pointer' : 'not-allowed' }}>
        Processar documentos →
      </button>
    </div>
  )
}

// ─── Processing View ──────────────────────────────────────────────────────────

function ProcessingView() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 360, gap: '1.25rem' }}>
      <Spinner size={44} />
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontWeight: 600, color: 'var(--text)', fontSize: '1rem' }}>Processando documentos</p>
        <p style={{ fontSize: '0.82rem', color: 'var(--muted)', marginTop: '0.3rem' }}>Detectando banco, período e classificando transações...</p>
      </div>
    </div>
  )
}

// ─── Results View ─────────────────────────────────────────────────────────────

function ResultsView({ result, onNovo, onHome }) {
  const pct = result.auto_rate
  const periodo = result.period_month ? `${MESES[result.period_month - 1]}/${result.period_year}` : String(result.period_year)
  return (
    <div style={{ maxWidth: 580, margin: '0 auto', padding: '2.5rem 2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
        <div style={{ width: 30, height: 30, borderRadius: '50%', background: 'rgba(45,212,191,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--success)', flexShrink: 0 }}><IconCheck size={16} /></div>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.2px' }}>Processamento concluído</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--muted)', marginTop: '0.1rem' }}>{result.client_name} · {periodo}</p>
        </div>
      </div>
      <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden', marginBottom: '1.5rem', boxShadow: 'var(--shadow-sm)' }}>
        <div style={{ padding: '1.1rem 1.4rem', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.6rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Taxa de automação</span>
            <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--primary)' }}>{pct}%</span>
          </div>
          <div style={{ height: 5, background: 'var(--surface)', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg,var(--primary),#f5924e)', borderRadius: 3, transition: 'width 0.7s ease' }} />
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr' }}>
          {[{ l:'Total', v:result.total, c:'var(--text)'}, {l:'Automáticas', v:result.auto_matched, c:'var(--success)'}, {l:'Para revisar', v:result.needs_review, c:result.needs_review>0?'#f59e0b':'var(--success)'}].map(({l,v,c},i) => (
            <div key={i} style={{ padding:'1.1rem', textAlign:'center', borderRight:i<2?'1px solid var(--border)':'none'}}>
              <div style={{fontSize:'1.65rem',fontWeight:800,color:c,letterSpacing:'-0.5px',lineHeight:1}}>{v}</div>
              <div style={{fontSize:'0.72rem',color:'var(--muted)',marginTop:'0.3rem',fontWeight:500}}>{l}</div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <a href="/" style={{ ...s.btnPrimary, flex: 1, textAlign: 'center', textDecoration: 'none', padding: '0.8rem', display: 'block', minWidth: 160 }}>Ver fila de revisão →</a>
        <button onClick={onNovo} style={{ ...s.btnOutline, padding: '0.8rem 1rem' }}>Nova</button>
        <button onClick={onHome} style={{ ...s.btnOutline, padding: '0.8rem 1rem' }}>Home</button>
      </div>
    </div>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const { isLoading, isAuthenticated, loginWithRedirect, logout, getAccessTokenSilently } = useAuth0()
  const [theme, toggleTheme] = useTheme()
  const [me,     setMe]    = useState(null)
  const [token,  setToken] = useState(null)
  const [page,   setPage]  = useState('home')
  const [view,   setView]  = useState('overview')
  const [result, setResult] = useState(null)
  const [error,  setError]  = useState(null)

  useEffect(() => {
    if (!isAuthenticated) return
    getAccessTokenSilently({ authorizationParams: { audience: AUDIENCE } })
      .then(t => { setToken(t); return fetch('/api/v1/me', { headers: { Authorization: `Bearer ${t}` } }) })
      .then(r => r.json()).then(setMe).catch(console.error)
  }, [isAuthenticated])

  if (isLoading || (isAuthenticated && !me)) {
    return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}><Spinner size={40} /></div>
  }

  if (!isAuthenticated) {
    return <LoginScreen onLogin={() => loginWithRedirect()} theme={theme} onToggleTheme={toggleTheme} />
  }

  async function handleProcess({ extrato, comprovantes, plano }) {
    setError(null); setView('processing')
    try {
      const t = await getAccessTokenSilently({ authorizationParams: { audience: AUDIENCE } })
      const form = new FormData()
      form.append('extrato', extrato)
      for (const c of comprovantes) form.append('comprovantes', c)
      if (plano) form.append('plano_contas', plano)
      const res = await fetch('/api/v1/conciliacao/upload', { method: 'POST', headers: { Authorization: `Bearer ${t}` }, body: form })
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Erro no processamento') }
      setResult(await res.json()); setView('done')
    } catch (err) { setError(err.message); setView('upload') }
  }

  function navigate(p) { setPage(p); setView('overview'); setResult(null); setError(null) }

  const extratosContent =
    view === 'overview'   ? <OverviewView token={token} onNovo={() => setView('upload')} /> :
    view === 'upload'     ? <UploadView onProcess={handleProcess} error={error} /> :
    view === 'processing' ? <ProcessingView /> :
    <ResultsView result={result}
      onNovo={() => { setView('upload'); setResult(null); setError(null) }}
      onHome={() => { setView('overview'); setResult(null); setError(null) }} />

  return (
    <div style={{ height: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <AppHeader theme={theme} onToggleTheme={toggleTheme} />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar page={page} onNavigate={navigate} me={me} onLogout={() => logout({ logoutParams: { returnTo: window.location.origin + '/app' } })} />
        <main style={{ flex: 1, overflowY: 'auto' }}>
          {page === 'home'     && <HomePage me={me} onNavigate={navigate} />}
          {page === 'extratos' && extratosContent}
        </main>
      </div>
    </div>
  )
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const s = {
  btnPrimary:  { background: 'var(--primary)', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700, fontSize: '0.88rem', cursor: 'pointer', transition: 'background 0.14s', display: 'inline-block' },
  btnGhost:    { background: 'transparent', color: 'var(--muted)', border: 'none', fontSize: '0.82rem', fontWeight: 500, cursor: 'pointer', padding: '0.35rem 0.5rem', borderRadius: 6 },
  btnOutline:  { background: 'transparent', color: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 8, fontSize: '0.85rem', fontWeight: 500, cursor: 'pointer' },
  iconBtn:     { background: 'transparent', border: '1px solid var(--border)', color: 'var(--muted)', width: 30, height: 30, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', flexShrink: 0 },
}
