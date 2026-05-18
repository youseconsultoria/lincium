# CLAUDE.md — Lincium Hub

Leia este arquivo + `HANDOFF.md` + `FEATURES.md` antes de qualquer sessão.

---

## Contexto do Produto

**Lincium** é um hub SaaS multi-tenant para escritórios de contabilidade.
- **Piloto:** PRIME (escritório com ~69 funcionários, ~349 clientes externos)
- **Destino:** produto vendável como franquia para outros escritórios contábeis
- **Modelo:** módulos contratados separadamente ou em pacotes
- **Usuário principal:** Matheus — consultor líder, vibecoder, usa Claude Code como ferramenta principal
- **Matheus tem experiência operacional contábil** — foi analista contábil por ~1 ano, conhece o processo tão bem quanto o Fernando (coordenador). Perguntar diretamente ao Matheus sobre regras de negócio contábeis.

---

## Arquitetura Atual

```
lincium/
├── src/
│   ├── parsers/        ← leitura de PDFs bancários (Santander, BB, Sicoob, Bradesco, Itaú)
│   ├── matching/       ← motor de classificação (keyword, CNPJ, fuzzy v2)
│   ├── output/         ← geração arquivo Domínio + serialização batch
│   ├── review/         ← FastAPI app
│   │   ├── app.py      ← rotas principais (Jinja2 + serve React em /app)
│   │   ├── api.py      ← API REST para React (/api/v1/*)
│   │   ├── auth.py     ← Auth0 session-based + AuthMiddleware
│   │   ├── templates/  ← Jinja2 HTML (queue.html, done.html, base.html, error.html)
│   │   └── static/     ← CSS, JS, fontes, logo.png
│   └── db/             ← PostgreSQL (psycopg2 direto, sem ORM)
│       ├── connection.py   ← get_connection() retorna RealDictCursor — acessar por nome, não por índice
│       └── repository.py
├── frontend/           ← React hub (Vite + JS)
│   ├── src/
│   │   ├── App.jsx     ← componente raiz completo (login, sidebar, homepage, upload, results)
│   │   ├── main.jsx    ← Auth0Provider com audience
│   │   └── index.css   ← design system: Saira, CSS vars dark/light
│   ├── vite.config.js  ← base: '/app/' — CRÍTICO, não alterar
│   ├── .env.local      ← NÃO commitado — criar manualmente (ver .env.example)
│   └── dist/           ← NÃO commitado — gerado pelo CI/CD
├── data/               ← configs de clientes (config_*.json, plano_*.json)
├── run.py              ← CLI do pipeline (legacy — substituído pelo upload web)
└── tests/
```

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.13, FastAPI, psycopg2 |
| DB | PostgreSQL 16 (Azure Flexible Server) |
| Auth Jinja2 | Auth0 Regular Web App (session cookies) |
| Auth React | Auth0 SPA (PKCE) + API audience `https://api.lincium.com.br` |
| Frontend legado | Jinja2 + HTML/CSS/JS |
| Frontend hub | React + Vite (JavaScript, não TypeScript) |
| Deploy | Azure App Service (Linux, Python 3.13) |
| CI/CD | GitHub Actions (build React + deploy Azure) |

---

## Regras de Comportamento

### Comunicação
- Matheus é vibecoder — prefere profundidade, não brevidade
- Explicar o "porquê" de decisões técnicas em linguagem acessível
- Nunca usar emojis
- Quando houver múltiplas opções, apresentar com recomendação clara
- Matheus tem background contábil operacional — pode responder dúvidas de processo diretamente

### Desenvolvimento
- **Fatias verticais:** nunca bundlar múltiplas features numa sessão. Uma coisa de cada vez, validar antes de avançar
- **Multi-tenant primeiro:** qualquer nova tabela ou query deve ter `tenant_id` desde o início
- **Não TypeScript:** erros de TS são difíceis de debugar. Usar JavaScript puro no frontend
- Jinja2 permanece funcionando enquanto React não substituir — zero downtime
- Após qualquer mudança em `frontend/src/`, rodar `cd frontend && npm run build` antes de testar

### Arquitetura
- React servido pelo FastAPI (mesmo domínio) — não usar Azure Static Web Apps
- Auth0 `app_metadata` para carregar `tenant_id` — não usar Auth0 Organizations (não está no free tier)
- psycopg2 direto (sem SQLAlchemy ORM) — queries SQL explícitas
- `RealDictCursor`: acessar colunas por nome (`r['id']`), NUNCA por índice (`r[0]`)
- Sem IA no fluxo principal de conciliação — custo variável inviabiliza escala
- `frontend/dist/` nunca commitado — CI/CD builda via `npm ci && npm run build`

---

## Multi-tenancy

**Estado atual (2026-05-18):** completo.

- Tabela `tenants`: PRIME com UUID fixo `00000000-0000-0000-0000-000000000001`
- `tenant_id UUID NOT NULL` em batches, transactions, learning
- Todas as queries filtram por `tenant_id`
- Auth0 Action "Inject Tenant ID" (Post Login): injeta `tenant_id` e `email` no access token com namespace `https://lincium.com.br/`
- `api.py`: extrai claims `https://lincium.com.br/tenant_id` e `https://lincium.com.br/email`
- Fallback para `PRIME_TENANT_ID` quando claim ausente (dev sem token Auth0)

---

## Design System

| Token | Valor |
|-------|-------|
| Cor primária | `#ee702f` (laranja) |
| Fundo dark | `#090d16` |
| Surface dark | `#0d1422` |
| Card dark | `#161e30` |
| Border dark | `#1e2a3a` |
| Texto dark | `#e8edf5` |
| Muted dark | `#6b7f96` |
| Fundo light | `#f5f7fa` |
| Card light | `#ffffff` |
| Texto light | `#0f172a` |
| Fonte | Saira (em `src/review/static/fonts/Saira.ttf`, referenciada como `/static/fonts/Saira.ttf`) |
| Logo | `src/review/static/logo.png` (PNG com fundo cinza — precisa SVG/transparente) |

Todos os tokens estão em CSS custom properties em `frontend/src/index.css`. O tema dark/light alterna via `[data-theme="light"]` no `<html>`.

---

## Auth0 — IDs Definitivos

| Item | Valor |
|------|-------|
| Tenant | `lincium.us.auth0.com` |
| App Jinja2 (Regular Web App) | Client ID: `3mCGYGGMGe10lHUJ4f1Htsq9Q2k5kzUt` |
| App React (SPA) | Client ID: `YucQ5NSK3hmnHREZas7DkRdbxbyjGuVy` |
| API audience | `https://api.lincium.com.br` |
| Namespace claims | `https://lincium.com.br/tenant_id` e `https://lincium.com.br/email` |
| Action | "Inject Tenant ID" — Login / Post Login — Node 22 |

---

## Variáveis de Ambiente

### Local (`.env` — nunca commitar)
```
AUTH0_DOMAIN=lincium.us.auth0.com
AUTH0_CLIENT_ID=3mCGYGGMGe10lHUJ4f1Htsq9Q2k5kzUt
AUTH0_CLIENT_SECRET=...
AUTH0_CALLBACK_URL=http://localhost:8000/callback
SECRET_KEY=...
LINCIUM_DB_URL=postgresql://lincium_admin:...@lincium-db.postgres.database.azure.com:5432/postgres?sslmode=require
ENV=development
```

### Frontend (`.env.local` — nunca commitar)
```
VITE_AUTH0_DOMAIN=lincium.us.auth0.com
VITE_AUTH0_CLIENT_ID=YucQ5NSK3hmnHREZas7DkRdbxbyjGuVy
VITE_AUTH0_CALLBACK_URL=http://localhost:8000/app
```

### Azure (configurado no App Service)
- Mesmas vars do `.env` com `AUTH0_CALLBACK_URL=https://app-lincium-gse4ahbaetf0h8gs.brazilsouth-01.azurewebsites.net/callback`
- VITE_* são passadas no workflow do CI/CD (não precisam estar no App Service)

---

## Armadilhas Conhecidas

- `.gitignore` tem `/output/` com barra inicial — não mudar (protege `src/output/` módulo Python)
- `data/*.json` ignorado — exceções explícitas para os arquivos da ALO EMBALAGENS
- `RealDictCursor`: rows são dicts — usar `r['coluna']`, nunca `r[0]`
- `AZURE_PUBLISH_PROFILE` no GitHub Secrets deve ser do app principal (não de slot)
- PostgreSQL precisa de `sslmode=require` na connection string
- XLS do Domínio usa OLE2 proprietário — xlrd, openpyxl e pandas falham. Só win32com funciona (Windows). Inviável no Azure Linux. Solução: exportar como .xlsx do Domínio
- `base: '/app/'` no Vite é essencial — assets ficam em `/app/assets/*`
- AuthMiddleware libera: `/login`, `/callback`, `/static*`, `/app/assets*`, `/api/*`
- Auth0 Action injeta claims em AMBAS as apps (Post Login é global)
- Dois sistemas de auth coexistem: session cookie (Jinja2 em `/`) e Bearer JWT (React em `/api/*`)
- `_load_session()` em `app.py` chama `_session.clear()` em toda requisição — sem cache (correto para refletir novos batches)

---

## Como Rodar

```powershell
# Servidor local
python -m uvicorn src.review.app:app --host 127.0.0.1 --port 8000

# Build do frontend (necessário após qualquer mudança em frontend/src/)
cd frontend && npm run build && cd ..

# Pipeline completo (legacy)
python run.py
```

Local: `http://localhost:8000` (Jinja2) e `http://localhost:8000/app` (React)
Azure: `https://app-lincium-gse4ahbaetf0h8gs.brazilsouth-01.azurewebsites.net/app`
