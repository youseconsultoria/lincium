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
| Auth0 Action (tenant_id + email claim) | ✅ | Post Login injeta ambos no access token via custom namespace |
| Auth0 SPA Application (PKCE) | ✅ | Client ID: YucQ5NSK3hmnHREZas7DkRdbxbyjGuVy |
| Auth0 API (Lincium API) | ✅ | Identifier: https://api.lincium.com.br — necessária para JWT access token |
| React frontend scaffold | ✅ | Vite + JS, servido pelo FastAPI em /app |
| CI/CD com build React | ✅ | deploy.yml inclui Node.js 20 + npm ci + npm run build |
| `/api/v1/me` endpoint JWT | ✅ | Valida JWT Auth0, retorna email + tenant_id + tenant_name |
| `/api/v1/conciliacao/batches` | ✅ | Lista 30 últimos batches do tenant |
| `/api/v1/conciliacao/upload` | ✅ | Pipeline roda no servidor, período detectado automaticamente |
| Hub shell (layout, navegação) | ✅ | Sidebar com ícones, header, dark/light theme |
| Homepage do hub | ✅ | Fila de pendentes, histórico, quick action |

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
| Autocomplete de conta (busca %termo%) | ✅ | Substituiu o select nativo — lista de 10, substring match |
| Ordenação do plano por hierarquia | ✅ | Ordenado por campo classif, não cod_reduzido |
| Lançamentos conciliados automaticamente (view) | 🔴 | Fernando precisa ver o que foi auto-classificado |
| **Upload de documentos via interface web** | ✅ | Drag-and-drop, detecção automática de tipo e período |
| Período automático | ✅ | Detectado pelo Counter de datas das transações |
| Pipeline salva no PostgreSQL | ✅ | `save_batch()` com tenant_id |
| App web lê do PostgreSQL | ✅ | `_load_session()` → DB first, sem cache |
| Tabela de aprendizado (learning) | ✅ | Schema criado, populated on confirm |
| Download .txt em memória (Azure) | ✅ | Sem depender de disco |
| **Multi-cliente no upload** | 🔴 | **Hardcoded para ALO EMBALAGENS — principal gap do MVP** |
| Multi-mês | 🔴 | Período detectado automaticamente, mas config ainda fixa |
| Parser plano de contas .xlsx | 🔴 | XLS do Domínio é OLE2 proprietário; precisa exportar .xlsx |
| Integração NF-e XML via SEFAZ | 🔴 | v2 — 3 certificados cobrem ~741 clientes |
| SQL Domínio para CNPJs fornecedores | 🔴 | Resolve ~241 boletos sem match |

---

## Módulo: React Hub

| Feature | Status | Notas |
|---------|--------|-------|
| Login screen (logo, eslogan, dark/light) | ✅ | "A única central que seu negócio precisa." |
| Logo no círculo laranja | 🔴 | PNG tem fundo cinza — precisa SVG/PNG transparente |
| Sidebar com ícones | ✅ | Home, Contábil > Lançamentos de extratos, user info base |
| Dark/light theme toggle | ✅ | Persistido em localStorage |
| Homepage com fila de pendentes | ✅ | Cards com batch_id, stats, "Ir para revisão" |
| Histórico de batches concluídos | ✅ | Compact list na homepage |
| Upload drag-and-drop | ✅ | Detecção de tipo por nome do arquivo |
| Detecção automática de período | ✅ | Sem seletores manuais |
| Tela de processamento (spinner) | ✅ | Animado, com mensagem contextual |
| Tela de resultado | ✅ | Stats, barra de progresso, links para revisão |
| Tenant name no header | 🔴 | Mostra "Escritório" — precisa logout completo + login para regenerar token |
| React Router v6 | 🔴 | Navegação via estado por agora; Router quando houver mais páginas |

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
| Dashboard geral do hub | ✅ Parcial (homepage cobre o essencial) |
