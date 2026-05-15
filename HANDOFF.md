# HANDOFF — Lincium Hub
**Última atualização:** 2026-05-15
**Sessão:** Multi-tenancy completo (Slices A+B+C) + início do React hub

---

## Objetivo

Construir o **Lincium Hub** — plataforma SaaS multi-tenant para escritórios de contabilidade. A PRIME é o piloto. O produto final será vendido como franquia.

---

## O que está funcionando hoje (2026-05-15)

### Módulo de Conciliação
- Pipeline local: `python run.py` → PostgreSQL Azure + JSON local
- Taxa de automação: 85.3% (1.608/1.885 tx) — ALO EMBALAGENS jan/2026
- Interface de revisão: FastAPI + Jinja2 em `localhost:8000` e Azure
- Testes: 70/70 passando

### Multi-tenancy (100% concluído)
- Tabela `tenants`: PRIME com UUID fixo `00000000-0000-0000-0000-000000000001`
- `tenant_id UUID NOT NULL` em batches, transactions e learning
- 1.885 transações backfilladas; todas as queries filtram por tenant_id
- Auth0 Action "Inject Tenant ID" (Node 22, Post Login): injeta `app_metadata.tenant_id` como custom claim `https://lincium.com.br/tenant_id` no JWT
- `auth.py`: extrai o claim na sessão como `user["tenant_id"]`
- `app.py`: usa o valor da sessão (fallback para `PRIME_TENANT_ID` em dev sem Auth0 configurado)
- Validado localmente: `fallback: false`, UUID chegando do Auth0

### Infraestrutura
- Auth0: `lincium.us.auth0.com` — Regular Web App (session cookies) para Jinja2
- Azure App Service: `app-lincium-gse4ahbaetf0h8gs.brazilsouth-01.azurewebsites.net`
- PostgreSQL: `lincium-db.postgres.database.azure.com`
- Deploy: GitHub Actions → `azure/webapps-deploy@v3`

---

## React Hub — Estado atual e próximos passos

### O que foi feito (Slice R1)
- `frontend/` scaffoldado com Vite + JavaScript (não TypeScript)
- FastAPI serve o build em `/app` (Jinja2 permanece em `/`)
- `frontend/dist/` adicionado ao `.gitignore`; build gerado localmente antes do deploy

### Sequência de fatias restantes

**Slice R2 — Auth0 SPA Application (fazer ANTES de qualquer lógica React)**
1. No painel Auth0: criar nova Application → tipo **Single Page Application**
   - Nome: "Lincium Hub SPA"
   - Allowed Callback URLs: `http://localhost:5173, http://localhost:8000/app`
   - Allowed Logout URLs: mesmos
   - Allowed Web Origins: mesmos
2. Anotar o `Client ID` da SPA (não tem client_secret — é PKCE)
3. Instalar Auth0 SDK no frontend: `npm install @auth0/auth0-react`
4. Configurar `Auth0Provider` no `main.jsx` com domain + clientId
5. Validar: tela de login abre via Auth0, token chega no browser

**Slice R3 — Endpoint `/api/v1/me`**
1. FastAPI: novo router `src/review/api.py`
2. Endpoint `GET /api/v1/me`: valida Bearer JWT do Auth0 SPA, retorna `{email, tenant_id, tenant_name}`
3. Validar com curl/Postman antes de ligar ao React

**Slice R4 — React mínimo end-to-end**
1. React chama `/api/v1/me` com o token da sessão Auth0 SPA
2. Exibe: "Olá {nome} — {tenant}"
3. **Validar end-to-end antes de construir qualquer layout ou design**

**Slice R5 — Shell do hub (só após R4 validado)**
- Sidebar com módulos
- Routing interno (React Router v6)
- Design system: Saira, `#ee702f`, `#090d16`

---

## Decisões Arquiteturais Definitivas

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Frontend | React + Vite (JS, não TS) | SaaS multi-módulo precisa de SPA |
| Serving | `/app` no FastAPI serve o build React | Mesmo domínio = auth simples |
| Auth Jinja2 | Regular Web App (session cookies) | Já funcionando, não mexer |
| Auth React | SPA Application (PKCE, sem client_secret) | SPA não pode ter client_secret |
| Auth multi-tenant | `tenant_id` via Auth0 `app_metadata` + Action | Free tier, sem Organizations |
| DB | Row-level isolation com `tenant_id` | Simples, escalável |
| Linguagem frontend | JavaScript (não TypeScript) | Erros de TS difíceis de debugar |
| CSS | A decidir em R5 | — |
| UUID PRIME | `00000000-0000-0000-0000-000000000001` | Fixo, fácil de referenciar |
| Jinja2 | Mantém em `/` durante migração | Zero downtime |

---

## Armadilhas Conhecidas

- `.gitignore`: `/output/` com barra inicial — não mudar
- `frontend/dist/` no `.gitignore` — build gerado no deploy, não commitado
- Auth0 callback local: `http://localhost:8000/callback` (Jinja2) vs `http://localhost:5173` (React dev) — são apps Auth0 separadas
- PostgreSQL Azure: `sslmode=require` obrigatório
- `AZURE_PUBLISH_PROFILE` no GitHub Secrets: app principal, não slot
- ALO EMBALAGENS é apenas cliente de teste — não é o piloto real

---

## Como rodar

```powershell
# Servidor Jinja2 (interface de revisão atual)
python -m uvicorn src.review.app:app --host 127.0.0.1 --port 8000

# Pipeline completo + abre revisão
python run.py

# Frontend React (dev)
cd frontend && npm run dev   # porta 5173

# Build React para produção (FastAPI serve em /app)
cd frontend && npm run build
```

## Arquivos chave

| Arquivo | Função |
|---------|--------|
| `run.py` | CLI do pipeline |
| `src/review/app.py` | FastAPI — rotas Jinja2 + serve React em `/app` |
| `src/review/auth.py` | Auth0 session-based (Jinja2) |
| `src/db/repository.py` | PostgreSQL — todas as ops com tenant_id |
| `src/db/connection.py` | Conexão psycopg2 |
| `scripts/migrate_001_tenant_id.py` | Migração multi-tenancy (já rodada) |
| `frontend/` | React hub (Vite + JS) |
| `frontend/dist/` | Build (gitignored — gerado no deploy) |
