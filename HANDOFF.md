# HANDOFF — Lincium Hub
**Última atualização:** 2026-05-15
**Sessão:** Multi-tenancy completo (Slices A e B)

---

## Objetivo

Construir o **Lincium Hub** — plataforma SaaS multi-tenant para escritórios de contabilidade. A PRIME é o piloto. O produto final será vendido como franquia.

Slogan provisório: "A única ferramenta que você precisa para o sucesso do seu escritório."

---

## O que está funcionando hoje (2026-05-15)

### Módulo de Conciliação (primeiro módulo do hub)
- **Pipeline local:** `python run.py` lê PDF do extrato → processa → salva no PostgreSQL Azure + JSON local
- **Taxa de automação:** 85.3% (1.608/1.885 tx) — dados de teste ALO EMBALAGENS jan/2026
- **Interface de revisão:** FastAPI + Jinja2 em `localhost:8000` e Azure
- **PostgreSQL Azure:** 4 tabelas (tenants, batches, transactions, learning) — multi-tenant
- **Azure App Service:** rodando, Auth0 autenticando, deploy automático via GitHub Actions
- **Testes:** 70/70 passando

### Multi-tenancy (concluído nesta sessão)
- Tabela `tenants` criada — PRIME registrada com UUID fixo `00000000-0000-0000-0000-000000000001`
- `tenant_id UUID NOT NULL` em batches, transactions e learning
- 1.885 transações existentes backfilladas com o tenant_id da PRIME
- UNIQUE constraints atualizadas para incluir tenant_id (garante isolamento entre tenants futuros)
- Foreign keys e índices criados
- `repository.py`: todas as funções recebem `tenant_id` como parâmetro
- `app.py`: usa `PRIME_TENANT_ID` hardcoded (temporário até Slice C — Auth0)

### Infraestrutura
- **Auth0:** `lincium.us.auth0.com` — Regular Web Application (session cookies)
- **Azure App Service:** `app-lincium-gse4ahbaetf0h8gs.brazilsouth-01.azurewebsites.net`
- **PostgreSQL:** `lincium-db.postgres.database.azure.com` — user: `lincium_admin`
- **Deploy:** GitHub Actions → `azure/webapps-deploy@v3` via publish profile do app principal

---

## Próxima Sessão — Começar aqui

### PASSO 1 — Slice C: tenant_id via Auth0 (fazer ANTES do React)

Hoje o `tenant_id` está hardcoded como `PRIME_TENANT_ID` em `app.py` e `run.py`.
O Slice C elimina esse hardcode: o tenant vem do login Auth0.

**O que fazer:**
1. No painel Auth0: criar uma **Action** (Login / Post Login) que adiciona `tenant_id` ao `app_metadata` do usuário e o injeta no JWT como custom claim (`https://lincium.com.br/tenant_id`)
2. Em `auth.py`: no `callback_route`, extrair `tenant_id` do `userinfo` e salvar em `request.session["user"]["tenant_id"]`
3. Em `app.py`: substituir `PRIME_TENANT_ID` por `request.session["user"]["tenant_id"]` (ou `_session["tenant_id"]`) carregado no callback
4. Testar localmente: login → sessão tem tenant_id → queries filtram pelo tenant correto

**Observação:** ainda não há segundo tenant, então o comportamento visível não muda — mas a arquitetura fica correta antes do hub.

### PASSO 2 — Hub React (depois do Slice C)

**Arquitetura decidida:**
- React (Vite + JavaScript, não TypeScript) servido PELO FastAPI (mesmo domínio, opção A)
- Não usar Azure Static Web Apps — mantém auth simples (session cookies, mesma app Auth0)
- React Router v6
- CSS: Tailwind ou plain CSS (decidir na sessão)
- Design system: fonte Saira, laranja `#ee702f`, fundo `#090d16`

**Sequência de construção (fatias verticais — não bundlar tudo de uma vez):**
1. Scaffold React em `lincium/frontend/`
2. FastAPI serve o build do React em `/app` (ou `/`)
3. Auth0 SPA Application (segundo app no Auth0, tipo SPA, PKCE)
4. Um endpoint `/api/v1/me` que valida JWT e retorna `{user, tenant}`
5. React mínimo: login → chama `/api/v1/me` → mostra "Olá {nome} — {tenant}"
6. **Validar end-to-end antes de construir layout, navegação, design system**
7. Depois: shell do hub (sidebar, módulos, routing)

**Módulos planejados:**
```
Lincium Hub
├── Dashboard          ← visão geral
├── Conciliação        ← módulo atual (migrar da Jinja2 para React)
├── IA Lincium         ← segundo módulo (outro chat)
├── [Fiscal]           ← futuro
├── [Dep. Pessoal]     ← futuro
├── [Societário]       ← futuro
└── Administração      ← usuários, clientes, módulos contratados
```

---

## Decisões Arquiteturais Definitivas

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Frontend | React + Vite (JS, não TS) | SaaS multi-módulo precisa de SPA |
| Serving | React build servido pelo FastAPI | Mesmo domínio = auth simples, zero config extra |
| Auth multi-tenant | `tenant_id` em `app_metadata` do Auth0 | Auth0 Organizations não está no free tier |
| Multi-tenancy DB | Row-level isolation (`tenant_id` em todas as tabelas) | Simples, escalável para franquia |
| Auth0 para React | Nova Application tipo SPA (PKCE, sem client_secret) | SPA não pode ter client_secret |
| Linguagem frontend | JavaScript (não TypeScript) | Erros de TS são difíceis de debugar no vibecoder |
| CSS | A decidir na próxima sessão | — |
| Domínio | `lincium.com.br` — registrar no Registro.br (R$40/ano) | Ainda não registrado — não bloqueia dev |
| Jinja2 atual | Mantém funcionando durante migração | Zero downtime na transição |
| UUID PRIME | `00000000-0000-0000-0000-000000000001` (fixo) | Mais fácil de referenciar no código e testes |

---

## Armadilhas Conhecidas

- `.gitignore` tem `/output/` (com barra inicial) — não mudar para `output/` (quebraria `src/output/`)
- `AZURE_PUBLISH_PROFILE` no GitHub Actions deve ser do app principal, não de slot
- Auth0 callback URL local: `http://localhost:8000/callback` — se mudar porta, atualizar `.env` E `src/review/auth.py`
- `data/*.json` está no `.gitignore` com exceções explícitas para `config_alo_embalagens.json` e `plano_contas_alo_embalagens.json`
- PostgreSQL Azure requer `sslmode=require` na connection string
- Cliente piloto real ainda não definido — ALO EMBALAGENS foi usado só para desenvolvimento/testes
- `PRIME_TENANT_ID` está em `src/db/repository.py` e é importado por `app.py`; `run.py` também o importa de lá

---

## Como rodar localmente

```powershell
cd C:\Users\youse\Projects\projeto-prime\lincium
python run.py        # pipeline + abre revisão em localhost:8000
python run.py --no-server   # só pipeline, sem abrir browser
```

## Arquivos chave

| Arquivo | Função |
|---------|--------|
| `run.py` | CLI do pipeline (entrada principal) |
| `src/review/app.py` | FastAPI — rotas da interface de revisão |
| `src/review/auth.py` | Auth0 session-based |
| `src/db/repository.py` | Todas as operações no PostgreSQL (tenant_id em tudo) |
| `src/db/connection.py` | Conexão psycopg2 via LINCIUM_DB_URL |
| `src/matching/engine.py` | Motor de matching (3 camadas) |
| `scripts/migrate_001_tenant_id.py` | Migração multi-tenancy (já rodada em produção) |
| `data/config_alo_embalagens.json` | Config do cliente de teste |
| `data/plano_contas_alo_embalagens.json` | 750 contas analíticas |
| `.env` | Credenciais locais (nunca commitar) |
| `.github/workflows/deploy.yml` | CI/CD → Azure |
