# CLAUDE.md — Lincium Hub

Leia este arquivo + `HANDOFF.md` + `FEATURES.md` antes de qualquer sessão.

---

## Contexto do Produto

**Lincium** é um hub SaaS multi-tenant para escritórios de contabilidade.
- **Piloto:** PRIME (escritório com ~69 funcionários, ~349 clientes externos)
- **Destino:** produto vendável como franquia para outros escritórios contábeis
- **Modelo:** módulos contratados separadamente ou em pacotes
- **Usuário principal:** Matheus — consultor líder, vibecoder, usa Claude Code como ferramenta principal

---

## Arquitetura Atual

```
lincium/
├── src/
│   ├── parsers/        ← leitura de PDFs bancários
│   ├── matching/       ← motor de classificação
│   ├── output/         ← geração arquivo Domínio + serialização batch
│   ├── review/         ← FastAPI app (Jinja2 — legado, migrar para React)
│   │   ├── app.py      ← rotas principais
│   │   └── auth.py     ← Auth0 session-based
│   └── db/             ← PostgreSQL (psycopg2 direto, sem ORM)
│       ├── connection.py
│       └── repository.py
├── frontend/           ← React hub (a criar)
├── data/               ← configs de clientes (config_*.json, plano_*.json)
├── run.py              ← CLI do pipeline (temporário — será substituído por upload)
└── tests/
```

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.13, FastAPI, psycopg2 |
| DB | PostgreSQL 16 (Azure Flexible Server) |
| Auth | Auth0 (Regular Web App para Jinja2, SPA para React) |
| Frontend legado | Jinja2 + HTML/CSS/JS |
| Frontend hub | React + Vite (JavaScript, não TypeScript) |
| Deploy | Azure App Service (backend + frontend build) |
| CI/CD | GitHub Actions |

---

## Regras de Comportamento

### Comunicação
- Matheus é vibecoder — prefere profundidade, não brevidade
- Explicar o "porquê" de decisões técnicas em linguagem acessível
- Nunca usar emojis
- Quando houver múltiplas opções, apresentar com recomendação clara

### Desenvolvimento
- **Fatias verticais:** nunca bundlar setup + auth + layout + design system numa sessão. Uma coisa de cada vez, validar que funciona antes de avançar
- **Multi-tenant primeiro:** qualquer nova tabela ou query deve ter `tenant_id` desde o início
- **Não TypeScript:** erros de TS são difíceis de debugar. Usar JavaScript puro no frontend
- Jinja2 permanece funcionando enquanto React não substituir — zero downtime

### Arquitetura
- React servido pelo FastAPI (mesmo domínio) — não usar Azure Static Web Apps
- Auth0 `app_metadata` para carregar `tenant_id` — não usar Auth0 Organizations (não está no free tier)
- psycopg2 direto (sem SQLAlchemy ORM) — queries SQL explícitas, mais fáceis de debugar
- Sem IA no fluxo principal de conciliação — custo variável inviabiliza escala

---

## Multi-tenancy

**Estado atual (2026-05-15):** tabelas sem `tenant_id` — migração pendente (próxima sessão).

**Modelo:**
- Cada escritório = 1 tenant (row em `tenants`)
- `tenant_id UUID` em todas as tabelas: `batches`, `transactions`, `learning`
- Todas as queries filtram por `tenant_id`
- Auth0 `app_metadata.tenant_id` carregado no login

**PRIME = tenant piloto** — ao criar a tabela `tenants`, PRIME é o primeiro registro e deve receber o `tenant_id` das 1.885 transações existentes via backfill.

---

## Design System

| Token | Valor |
|-------|-------|
| Cor primária | `#ee702f` (laranja) |
| Fundo principal | `#090d16` |
| Card | `#161e30` |
| Texto | `#e8edf5` |
| Fonte | Saira (variable, em `src/review/static/fonts/Saira.ttf`) |

---

## Variáveis de Ambiente (.env)

```
AUTH0_DOMAIN=lincium.us.auth0.com
AUTH0_CLIENT_ID=...
AUTH0_CLIENT_SECRET=...
AUTH0_CALLBACK_URL=http://localhost:8000/callback
SECRET_KEY=...
LINCIUM_DB_URL=postgresql://lincium_admin:...@lincium-db.postgres.database.azure.com:5432/postgres?sslmode=require
ENV=development
```

Nunca commitar `.env`. Arquivo `.env.example` está no repo como referência.

---

## Armadilhas Conhecidas

- `.gitignore` tem `/output/` com barra inicial — não mudar (protege `src/output/` módulo Python)
- `data/*.json` ignorado — exceções explícitas para `config_alo_embalagens.json` e `plano_contas_alo_embalagens.json`
- `AZURE_PUBLISH_PROFILE` no GitHub Secrets deve ser do app principal (não de slot)
- PostgreSQL precisa de `sslmode=require` na connection string
- Auth0 callback: `localhost:8000` — se mudar porta, atualizar `.env` E `src/review/auth.py`

---

## Como Rodar

```powershell
# Pipeline de conciliação + interface de revisão
cd C:\Users\youse\Projects\projeto-prime\lincium
python run.py

# Só pipeline sem abrir browser
python run.py --no-server
```

Interface: `http://localhost:8000`
Azure: `https://app-lincium-gse4ahbaetf0h8gs.brazilsouth-01.azurewebsites.net`
