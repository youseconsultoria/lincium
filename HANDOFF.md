# HANDOFF — Lincium Hub
**Última atualização:** 2026-05-18
**Sessão:** React Hub MVP completo + deploy em produção Azure

---

## Objetivo

Construir o **Lincium Hub** — plataforma SaaS multi-tenant para escritórios de contabilidade. A PRIME é o piloto. O produto final será vendido como franquia.

---

## O que está 100% funcionando hoje

### Módulo de Conciliação (Jinja2 — legado, funcional)
- Interface em `localhost:8000` e no Azure — Auth0 autenticando, fila de revisão operando
- Autocomplete de conta com busca por substring (%termo%) no código e nome — lista de 10 resultados
- Ordenação do plano de contas pela hierarquia classificação (Ativo > Ativo Circulante > Caixa etc.)
- Taxa de automação: 85.3% (1608/1885 tx) — ALO EMBALAGENS jan/2026
- Testes: 70/70 passando

### Multi-tenancy (completo)
- Tabela `tenants`: PRIME com UUID fixo `00000000-0000-0000-0000-000000000001`
- `tenant_id UUID NOT NULL` em batches, transactions, learning
- Auth0 Action "Inject Tenant ID" (Node 22, Post Login): injeta `tenant_id` e `email` como custom claims no access token
- Claims: `https://lincium.com.br/tenant_id` e `https://lincium.com.br/email`

### React Hub — MVP em produção
- **Login**: tela com logo, "Lincium / Powered by EPrime", toggle dark/light, eslogan
- **Sidebar**: ícones + Home + seção CONTÁBIL > Lançamentos de extratos + user info + logout na base
- **Homepage**: fila de batches pendentes com cards (progresso, stats, "Ir para revisão"), histórico concluídos, botão "Nova conciliação"
- **Upload via web**: drag-and-drop multi-arquivo, detecção automática de tipo por nome do arquivo (Extrato Santander/BB/Sicoob, Comprovante Bradesco/Itaú, Plano de Contas .xlsx)
- **Período automático**: detectado pelo Counter das datas das transações do extrato (sem input manual)
- **Design system**: fonte Saira via `/static/fonts/Saira.ttf`, CSS custom properties, dark/light theme persistido em localStorage
- **URL produção**: `https://app-lincium-gse4ahbaetf0h8gs.brazilsouth-01.azurewebsites.net/app`

### API React (`/api/v1/*`)
- `GET /api/v1/me` — JWT Auth0 validado via python-jose + JWKS, retorna email + tenant_id + tenant_name
- `GET /api/v1/conciliacao/batches` — lista últimos 30 batches do tenant (para homepage)
- `POST /api/v1/conciliacao/upload` — recebe extrato PDF (obrigatório), comprovantes PDFs (opcional), plano .xlsx (opcional); detecta período automaticamente

### CI/CD
- `.github/workflows/deploy.yml`: inclui Node.js 20 + `npm ci && npm run build` antes do deploy Azure
- VITE env vars hardcoded no workflow (são públicas em SPAs de qualquer forma)
- Push para master → GitHub Actions → Azure App Service (automatico)

---

## PRÓXIMA SESSÃO — Começar aqui

### PASSO 1 — Corrigir o logo (15 min)
O PNG do logo (`src/review/static/logo.png`) tem fundo cinza — `filter: brightness(0) invert(1)` faz o fundo virar branco, tornando o ícone invisível no círculo laranja. Por isso aparece o fallback "L".

**Solução:** Obter o logo como SVG ou PNG com fundo transparente. Caminho do logo original: `C:\Users\youse\Projects\projeto-prime\lincium-ia\Logo Lincium.png`

Quando tiver o arquivo com fundo transparente, substituir em `src/review/static/logo.png`.

### PASSO 2 — "Escritório" no header
O usuário `goulart.matheust@gmail.com` já tem `app_metadata.tenant_id` correto no Auth0. Para o nome aparecer, precisa fazer **logout completo** (botão Sair no hub) + login de novo para regenerar o token com o claim tenant_id.

Se ainda não aparecer após logout/login, o bug está em `_get_tenant_name()` em `api.py` — verificar se a query ao PostgreSQL está retornando o nome da tabela `tenants`.

### PASSO 3 — Adicionar Fernando ao sistema
1. Auth0 → User Management → Users → Create User
   - Email: (email do Fernando)
   - Connection: Username-Password-Authentication
2. No perfil do usuário criado → aba Metadata → App Metadata:
   ```json
   {"tenant_id": "00000000-0000-0000-0000-000000000001"}
   ```
3. Compartilhar URL: `https://app-lincium-gse4ahbaetf0h8gs.brazilsouth-01.azurewebsites.net/app`

### PASSO 4 — Multi-cliente (maior gap do MVP)
Hoje tudo está hardcoded para ALO EMBALAGENS (`config_alo_embalagens.json`, `plano_contas_alo_embalagens.json`).

Para suportar múltiplos clientes:
- Upload deve ter campo de seleção de empresa (ou detectar pelo CNPJ/nome no extrato)
- Backend carrega o config/plano do cliente correto
- Tabela `clientes` ou campo na tabela `tenants` para mapear empresas por CNPJ

### PASSO 5 — Plano de contas via .xlsx
O Domínio exporta o plano de contas em `.xls` (formato proprietário OLE2 — não parseable por xlrd, openpyxl ou pandas no Linux/Azure). Solução: pedir ao usuário que exporte como `.xlsx` (Excel moderno). O `openpyxl` já está disponível na stack.

Criar `src/parsers/plano_xlsx.py` que usa openpyxl para parsear as colunas:
- Coluna 8: `classif` (código hierárquico, ex: `1.1.1.02.002`)
- Colunas 12-16: nome (pegar primeira não-vazia)
- Coluna 4: tipo (S = sintética, em branco = analítica)
- Linha de início: 6 (as 5 primeiras são cabeçalho)

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
| CORS | Não necessário — tudo no mesmo domínio | |
| Plano de contas | XLS do Domínio não parseable → usar .xlsx | Formato OLE2 proprietário |
| Período do extrato | Detectado automaticamente via Counter de datas | Sem input manual do usuário |

---

## Armadilhas Conhecidas

- `frontend/.env.local` nunca commitar (`.gitignore` via `*.local`)
- `frontend/dist/` nunca commitar — o CI/CD builda no workflow
- Auth0 tem DUAS Applications: "lincium" (Regular Web App, Jinja2) e "Lincium Hub SPA" (SPA, React) — Client IDs diferentes
- Auth0 tem UMA API: "Lincium API" com identifier `https://api.lincium.com.br` — SPA precisa de "Grant Access" na aba APIs
- Auth0 Action "Inject Tenant ID" injeta claims em AMBAS as apps (Post Login é global)
- `RealDictCursor` do psycopg2 retorna dicionários — acessar por `r['coluna']`, NUNCA por `r[0]`
- `base: '/app/'` no Vite é essencial — sem isso os assets ficam em `/assets/*` e 404am
- AuthMiddleware libera `/api/`, `/app/assets/`, `/static`, `/login`, `/callback` — todo o resto requer sessão Jinja2
- XLS do Domínio usa formato OLE2 proprietário — não usar xlrd, openpyxl ou pandas. Único parser funcional é win32com (Windows) — inviável no Azure Linux
- PostgreSQL Azure: `sslmode=require` obrigatório
- `session["next"]` salva URL antes do redirect para login; callback lê e descarta

---

## Auth0 — IDs e configurações

| Item | Valor |
|------|-------|
| Tenant Auth0 | `lincium.us.auth0.com` |
| App Jinja2 (Regular Web App) | Client ID: `3mCGYGGMGe10lHUJ4f1Htsq9Q2k5kzUt` |
| App React (SPA) | Client ID: `YucQ5NSK3hmnHREZas7DkRdbxbyjGuVy` |
| API | Identifier: `https://api.lincium.com.br` (RS256) |
| Action | "Inject Tenant ID" — Login / Post Login — Node 22 |
| Callback URLs (SPA) | localhost:8000/app, azure/app |
| Logout URLs (SPA) | localhost:8000/app, azure/app |
| Web Origins (SPA) | localhost:8000, azure origin |

---

## Como Rodar

```powershell
# Servidor local (Jinja2 + React hub em /app)
python -m uvicorn src.review.app:app --host 127.0.0.1 --port 8000

# Build do frontend (necessário após qualquer mudança em frontend/src/)
cd frontend && npm run build

# Pipeline completo + abre revisão (legacy)
python run.py
```

## Arquivos-chave

| Arquivo | Função |
|---------|--------|
| `src/review/app.py` | FastAPI — Jinja2 + serve React em `/app` + routing |
| `src/review/api.py` | API REST para React: /me, /batches, /upload |
| `src/review/auth.py` | Auth0 session-based (Jinja2) + AuthMiddleware |
| `src/review/templates/queue.html` | Fila de revisão Jinja2 (autocomplete novo) |
| `src/db/repository.py` | PostgreSQL — todas as ops com tenant_id |
| `frontend/src/App.jsx` | App React completo: login, sidebar, homepage, upload |
| `frontend/src/index.css` | Design system: Saira, CSS variables dark/light |
| `frontend/src/main.jsx` | Entry point React — Auth0Provider com audience |
| `frontend/vite.config.js` | `base: '/app/'` — crítico |
| `frontend/.env.local` | Credenciais SPA (NÃO commitado — criar manualmente) |
| `.github/workflows/deploy.yml` | CI/CD → Azure (inclui build React) |
| `data/config_alo_embalagens.json` | Config cliente de teste |
| `data/plano_contas_alo_embalagens.json` | Plano de contas ALO (com campo classif) |

## Infraestrutura

| Serviço | URL / Identificador |
|---------|---------------------|
| React Hub (local) | `http://localhost:8000/app` |
| React Hub (Azure) | `https://app-lincium-gse4ahbaetf0h8gs.brazilsouth-01.azurewebsites.net/app` |
| Jinja2 (local) | `http://localhost:8000` |
| Auth0 tenant | `lincium.us.auth0.com` |
| Azure App Service | `app-lincium-gse4ahbaetf0h8gs.brazilsouth-01.azurewebsites.net` |
| PostgreSQL | `lincium-db.postgres.database.azure.com` — user: `lincium_admin` |
| GitHub | `https://github.com/youseconsultoria/lincium` |
| GitHub Actions | Deploy automático em push para master |
