# FEATURES — Lincium Hub

Rastreamento de features por módulo. Status: ✅ Pronto | 🟡 Em andamento | 🔴 Pendente | 💡 Planejado

---

## Infraestrutura / Base

| Feature | Status | Notas |
|---------|--------|-------|
| FastAPI + Jinja2 (conciliação) | ✅ | Mantido durante migração para React |
| Auth0 — Regular Web App (session) | ✅ | `lincium.us.auth0.com` |
| Azure App Service deploy | ✅ | GitHub Actions automático |
| PostgreSQL Azure | ✅ | `lincium-db` — tabelas: batches, transactions, learning |
| Multi-tenancy (tenant_id) | ✅ | DB migrado, tenant_id em todas as tabelas, PRIME como piloto |
| Auth0 SPA Application (PKCE) | 🔴 | Necessário para React hub |
| React frontend scaffold | 🔴 | Vite + JS, servido pelo FastAPI |
| `/api/v1/me` endpoint JWT | 🔴 | Primeira fatia do hub |
| Hub shell (layout, navegação) | 🔴 | Só após validar auth end-to-end |

---

## Módulo: Conciliação Contábil

| Feature | Status | Notas |
|---------|--------|-------|
| Parser Santander | ✅ | 1.885 tx, diff R$0,00 |
| Parser Banco do Brasil | ✅ | |
| Parser Sicoob | ✅ | |
| Parser comprovante Bradesco | ✅ | |
| Parser comprovante Itaú | ✅ | |
| Auto-detecção de banco (detector.py) | ✅ | |
| Motor de matching — keyword | ✅ | |
| Motor de matching — comprovante/CNPJ | ✅ | |
| Motor de matching — fuzzy | 🔴 | v2 |
| Plano de contas (JSON + stub SQL) | ✅ | 750 contas |
| Geração arquivo Domínio (.txt) | ✅ | Tipo X e C validados |
| Interface de revisão (fila) | ✅ | Jinja2, será migrada para React |
| Lançamentos conciliados automaticamente (view) | 🔴 | Necessário — Fernando precisa conferir |
| **Upload de documentos via interface** | 🔴 | **Substitui o run.py local** |
| Pipeline salva no PostgreSQL | ✅ | `run.py` → `save_batch()` |
| App web lê do PostgreSQL | ✅ | `_load_session()` → DB first |
| Tabela de aprendizado (learning) | ✅ | Schema criado, populated on confirm |
| Download .txt em memória (Azure) | ✅ | Sem depender de disco |
| Multi-cliente no run.py | 🔴 | Hardcoded para ALO EMBALAGENS |
| Multi-mês no run.py | 🔴 | Hardcoded para jan/2026 |
| Integração NF-e XML via SEFAZ | 🔴 | v2 — 3 certificados cobrem ~741 clientes |
| SQL Domínio para CNPJs fornecedores | 🔴 | Resolve ~241 boletos sem match |
| Script .bat para Windows | 🔴 | Substituído pela interface de upload |

---

## Módulo: IA Lincium

| Feature | Status | Notas |
|---------|--------|-------|
| Chat com Ollama (Lyra/Vega) | ✅ | Tratado em outro chat — porta 3000 |
| Upload PDF/Excel/CSV/imagem | ✅ | Tratado em outro chat |
| Integração no hub | 🔴 | Entrar no hub quando pronto |

---

## Módulo: Gestão de Carteira (futuro)

| Feature | Status | Notas |
|---------|--------|-------|
| CRM clientes do escritório | 💡 | Sendo desenvolvido por outra colaboradora |
| Contratos e módulos contratados | 💡 | |
| Integração no hub | 💡 | |

---

## Módulos Futuros

| Módulo | Status |
|--------|--------|
| Fiscal | 💡 |
| Departamento Pessoal | 💡 |
| Societário | 💡 |
| Administração (usuários, tenants) | 🔴 Planejado |
| Dashboard geral do hub | 🔴 Planejado |
