# HANDOFF — Lincium Hub
**Última atualização:** 2026-05-15
**Sessão:** Multi-tenancy (A+B+C) + React hub Slice R1 + Slice R2 parcial

---

## Objetivo

Construir o **Lincium Hub** — plataforma SaaS multi-tenant para escritórios de contabilidade. A PRIME é o piloto. O produto final será vendido como franquia.

---

## O que está 100% funcionando hoje

### Módulo de Conciliação (Jinja2)
- Interface em `localhost:8000` e no Azure — Auth0 autenticando, fila de revisão operando
- Pipeline: `python run.py` → PostgreSQL Azure + JSON local
- Taxa de automação: 85.3% (1.608/1.885 tx) — ALO EMBALAGENS jan/2026
- Testes: 70/70 passando

### Multi-tenancy (completo)
- Tabela `tenants`: PRIME com UUID fixo `00000000-0000-0000-0000-000000000001`
- `tenant_id UUID NOT NULL` em batches, transactions, learning
- Todas as queries filtram por `tenant_id`
- Auth0 Action "Inject Tenant ID" (Node 22, Post Login): injeta `app_metadata.tenant_id` como custom claim `https://lincium.com.br/tenant_id`
- `auth.py`: extrai o claim na sessão como `user["tenant_id"]`; redireciona para URL original após login (`session["next"]`)
- Validado: `fallback: false`, UUID chegando do Auth0

### React Hub — Slice R1 (completo)
- `frontend/` scaffoldado com create-vite (React, JS, Vite 8, Node 24)
- `vite.config.js`: `base: '/app/'` — assets referenciam `/app/assets/*`
- FastAPI serve o build em `/app` (Jinja2 permanece em `/` — zero downtime)
- `AuthMiddleware`: `/app/assets/*` liberado de auth (arquivos estáticos)
- Validado: `localhost:8000/app` → tela "Lincium Hub" em laranja sobre fundo escuro

---

## PRÓXIMA SESSÃO — Começar aqui

### PASSO 1 — Finalizar Slice R2: Auth0 SPA + build (30 min)

O código já está pronto. Falta só o Client ID e buildar.

**1a. Criar o `frontend/.env.local`** (já tem o `.env.example` como referência):
```
VITE_AUTH0_DOMAIN=lincium.us.auth0.com
VITE_AUTH0_CLIENT_ID=<client_id_da_SPA_aqui>
VITE_AUTH0_CALLBACK_URL=http://localhost:8000/app
```

O Client ID vem da Application "Lincium Hub SPA" no Auth0 → Settings.
Se a Application ainda não foi criada no Auth0:
- Applications → Create Application → Single Page Application → "Lincium Hub SPA"
- Allowed Callback URLs: `http://localhost:8000/app`
- Allowed Logout URLs: `http://localhost:8000/app`
- Allowed Web Origins: `http://localhost:8000`
- Salvar → copiar o Client ID

**1b. Buildar e testar:**
```powershell
cd frontend
npm run build
cd ..
python -m uvicorn src.review.app:app --host 127.0.0.1 --port 8000
```

Acessa `localhost:8000/app`. Deve aparecer botão "Entrar".
Clica → Auth0 → volta para `/app` → aparece "Olá, {email} — Auth0 SPA OK — Slice R2".

**O que o código já faz (commitado):**
- `main.jsx`: `Auth0Provider` com domain/clientId via VITE_* env vars
- `App.jsx`: três estados — `isLoading`, `!isAuthenticated` (botão Entrar), `isAuthenticated` (mostra email)

### PASSO 2 — Slice R3: endpoint `/api/v1/me`

Só após Slice R2 validado.

Criar `src/review/api.py` com:
```
GET /api/v1/me
Authorization: Bearer <token Auth0 SPA>
→ { email, tenant_id, tenant_name }
```

A validação do JWT Auth0 no FastAPI usa `python-jose` + JWKS público do Auth0.
Não usar a sessão Jinja2 — são sistemas de auth separados.

### PASSO 3 — Slice R4: React chama `/api/v1/me`

Só após Slice R3 validado.

`App.jsx`: após login, pega o access token (`getAccessTokenSilently()`),
chama `/api/v1/me`, exibe: "Olá {nome} — {tenant_name}".
Validar end-to-end antes de qualquer layout ou design system.

### PASSO 4 — Slice R5: shell do hub (só após R4)
- Sidebar com módulos
- React Router v6
- Design system: Saira, `#ee702f`, `#090d16`

---

## Decisões Arquiteturais Definitivas

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Frontend | React + Vite (JS, não TS) | SaaS multi-módulo precisa de SPA |
| Serving | FastAPI serve build em `/app` | Mesmo domínio = auth simples |
| Auth Jinja2 | Regular Web App (session cookies) | Já funcionando |
| Auth React | SPA Application (PKCE, sem client_secret) | SPA não pode ter client_secret |
| Auth multi-tenant | `tenant_id` via Auth0 `app_metadata` + Action | Free tier, sem Organizations |
| DB | Row-level isolation com `tenant_id` | Simples, escalável |
| Linguagem frontend | JavaScript (não TypeScript) | Erros TS difíceis de debugar |
| UUID PRIME | `00000000-0000-0000-0000-000000000001` | Fixo, fácil de referenciar |
| Jinja2 | Mantém em `/` durante migração | Zero downtime |
| CORS | Não necessário agora — tudo no mesmo domínio | |

---

## Armadilhas Conhecidas

- `frontend/.env.local` nunca commitar (já no `.gitignore` via `*.local`)
- `frontend/dist/` nunca commitar (no `.gitignore`)
- Auth0 tem duas Applications: "lincium" (Regular Web App, Jinja2) e "Lincium Hub SPA" (SPA, React) — Client IDs diferentes
- A Auth0 Action injeta `tenant_id` em AMBAS as apps (Post Login é global) — comportamento correto
- `base: '/app/'` no Vite é essencial — sem isso os assets referenciam `/assets/*` e 404am
- AuthMiddleware libera `/app/assets/*` (estáticos) mas protege `/app` e `/app/*` (SPA) — correto
- `session["next"]` salva a URL antes do redirect para login; callback lê e descarta
- PostgreSQL Azure: `sslmode=require` obrigatório
- `.gitignore` raiz: `/output/` com barra inicial — não mudar

---

## Como rodar

```powershell
# Servidor (interface de revisão Jinja2 + hub React em /app)
python -m uvicorn src.review.app:app --host 127.0.0.1 --port 8000

# Pipeline completo + abre revisão
python run.py

# Build do frontend (necessário após qualquer mudança em frontend/src/)
cd frontend && npm run build

# Dev frontend com HMR (apenas para desenvolvimento de componentes)
cd frontend && npm run dev   # porta 5173 — auth não funciona aqui ainda
```

## Arquivos chave

| Arquivo | Função |
|---------|--------|
| `run.py` | CLI do pipeline |
| `src/review/app.py` | FastAPI — Jinja2 + serve React em `/app` |
| `src/review/auth.py` | Auth0 session-based (Jinja2) + redirect pós-login |
| `src/db/repository.py` | PostgreSQL — todas as ops com `tenant_id` |
| `scripts/migrate_001_tenant_id.py` | Migração multi-tenancy (já rodada) |
| `frontend/src/main.jsx` | Entry point React — `Auth0Provider` |
| `frontend/src/App.jsx` | Componente raiz — estados de auth |
| `frontend/vite.config.js` | `base: '/app/'` — crítico |
| `frontend/.env.local` | Credenciais da SPA (NÃO commitado — criar manualmente) |
| `frontend/.env.example` | Template do `.env.local` |
| `data/config_alo_embalagens.json` | Config do cliente de teste |
| `.github/workflows/deploy.yml` | CI/CD → Azure |

## Infraestrutura

| Serviço | URL / Identificador |
|---------|---------------------|
| Auth0 tenant | `lincium.us.auth0.com` |
| Auth0 App (Jinja2) | Regular Web Application — "lincium" |
| Auth0 App (React) | Single Page Application — "Lincium Hub SPA" |
| Auth0 Action | "Inject Tenant ID" — Login / Post Login — Node 22 |
| Azure App Service | `app-lincium-gse4ahbaetf0h8gs.brazilsouth-01.azurewebsites.net` |
| PostgreSQL | `lincium-db.postgres.database.azure.com` — user: `lincium_admin` |
| GitHub Actions | Deploy automático em push para master |
