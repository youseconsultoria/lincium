import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from ..matching.plano_de_contas import PlanoDeContas
from ..matching.rules import EmpresaConfig
from ..output.batch import load_batch, save_batch
from ..output.dominio import generate
from .auth import AuthMiddleware, callback_route, login_route, logout_route
from .api import router as api_router
from ..db.repository import PRIME_TENANT_ID

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = Path(__file__).parent.parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

app = FastAPI(title="Lincium")

# SessionMiddleware primeiro (AuthMiddleware depende da sessão)
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "dev-only-change-in-prod"))

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# React hub — assets buildados pelo Vite em frontend/dist/assets/
if (FRONTEND_DIST / "assets").exists():
    app.mount(
        "/app/assets",
        StaticFiles(directory=str(FRONTEND_DIST / "assets")),
        name="react-assets",
    )

app.include_router(api_router)

# Rotas de autenticação
app.add_route("/login", login_route)
app.add_route("/callback", callback_route)
app.add_route("/logout", logout_route)


def _fmt_brl_filter(v) -> str:
    d = Decimal(str(v))
    s = f"{d:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

templates.env.filters["brl"] = _fmt_brl_filter

# Estado da sessão em memória (suficiente para uso single-user)
_session: dict = {}

_CONFIG_PATH = DATA_DIR / "config_alo_embalagens.json"
_PLANO_PATH  = DATA_DIR / "plano_contas_alo_embalagens.json"


def _load_session(tenant_id: str | None = None):
    _session.clear()

    # PRIME_TENANT_ID é fallback para dev local antes de Auth0 Action configurada.
    effective_tenant = tenant_id or PRIME_TENANT_ID

    # Tenta PostgreSQL primeiro
    if os.getenv("LINCIUM_DB_URL"):
        try:
            from ..db import repository as db_repo
            result = db_repo.load_latest_batch(effective_tenant)
            if result:
                batch_id, client_cnpj, client_name, period_label, results = result
                _session["batch_id"]    = batch_id
                _session["tenant_id"]   = effective_tenant
                _session["client_cnpj"] = client_cnpj
                _session["client_name"] = client_name
                _session["period"]      = period_label
                _session["results"]     = results
                _session["config"]      = EmpresaConfig.from_json(_CONFIG_PATH)
                _session["plano"]       = PlanoDeContas.from_json(_PLANO_PATH)
                _session["loaded"]      = True
                return
        except Exception:
            pass  # cai no fallback local

    # Fallback: JSON local (dev sem DB ou Azure sem dados ainda)
    batch_path = OUTPUT_DIR / "batch_latest.json"
    if not batch_path.exists():
        _session["error"] = "Nenhum batch encontrado. Rode o pipeline primeiro."
        _session["loaded"] = True
        return

    _session["results"]     = load_batch(batch_path)
    _session["client_name"] = "ALO EMBALAGENS LTDA"
    _session["period"]      = "Janeiro/2026"
    _session["config"]      = EmpresaConfig.from_json(_CONFIG_PATH)
    _session["plano"]       = PlanoDeContas.from_json(_PLANO_PATH)
    _session["loaded"]      = True


def _group_for_review(results) -> list[dict]:
    groups: dict[tuple, dict] = {}
    for r in results:
        if not r.needs_review:
            continue
        key = (r.transaction.raw_description, r.transaction.beneficiary or "")
        if key not in groups:
            groups[key] = {
                "key": f"{key[0]}|{key[1]}",
                "description": key[0],
                "beneficiary": key[1],
                "is_debit": r.transaction.is_debit,
                "transactions": [],
                "total": Decimal("0"),
                "cod_deb": r.cod_deb,
                "cod_cred": r.cod_cred,
                "review_reason": r.review_reason,
            }
        groups[key]["transactions"].append(r)
        groups[key]["total"] += r.transaction.amount

    return sorted(groups.values(), key=lambda g: -g["total"])


def _fmt_brl(v: Decimal) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _ctx(request: Request, extra: dict) -> dict:
    return {"user": request.session.get("user"), **extra}


@app.get("/", response_class=HTMLResponse)
async def queue(request: Request):
    tenant_id = request.session.get("user", {}).get("tenant_id")
    _load_session(tenant_id)
    if _session.get("error"):
        return templates.TemplateResponse(request, "error.html", _ctx(request, {
            "message": _session["error"],
        }))

    results = _session["results"]
    groups = _group_for_review(results)
    plano = _session["plano"]

    auto = sum(1 for r in results if not r.needs_review)
    total = len(results)
    def _classif_key(e):
        parts = (e.classif or '9.9.9.9.9').split('.')
        return [int(x) if x.isdigit() else 0 for x in parts] + [0] * (8 - len(parts))
    contas_all = sorted(plano._by_cod.values(), key=_classif_key)

    return templates.TemplateResponse(request, "queue.html", _ctx(request, {
        "groups": groups,
        "contas": contas_all,
        "auto_count": auto,
        "review_count": len(groups),
        "total_count": total,
        "empresa": _session.get("client_name", "ALO EMBALAGENS LTDA"),
        "periodo": _session.get("period", "Janeiro/2026"),
    }))


@app.post("/confirm")
async def confirm(request: Request):
    form = await request.form()
    results = _session["results"]

    confirmed = {}
    for k, v in form.items():
        if k.startswith("group_"):
            group_key = k[6:]
            parts = str(v).split(":")
            if len(parts) == 2:
                confirmed[group_key] = {"cod_deb": parts[0], "cod_cred": parts[1]}

    updated = 0
    for r in results:
        if not r.needs_review:
            continue
        key = f"{r.transaction.raw_description}|{r.transaction.beneficiary or ''}"
        if key in confirmed:
            r.cod_deb = confirmed[key]["cod_deb"]
            r.cod_cred = confirmed[key]["cod_cred"]
            r.needs_review = False
            r.match_type = "human_review"
            updated += 1

    # Persiste no DB se disponível
    batch_id = _session.get("batch_id")
    if batch_id and confirmed:
        try:
            from ..db import repository as db_repo
            user_email = request.session.get("user", {}).get("email")
            db_repo.update_reviewed(batch_id, confirmed, reviewed_by=user_email)
            db_repo.save_learning(_session["tenant_id"], _session["config"].empresa_cnpj, confirmed)
        except Exception:
            pass  # DB indisponível não bloqueia o fluxo

    # Salva localmente (fallback e dev)
    try:
        save_batch(results, OUTPUT_DIR / "batch_latest.json")
    except Exception:
        pass

    _session["loaded"] = False

    config = _session["config"]
    out_path = OUTPUT_DIR / "alo_embalagens_01_2026_importacao.txt"
    try:
        generate(results, config.empresa_cnpj, output_path=str(out_path))
    except Exception:
        pass

    total_auto = sum(1 for r in results if not r.needs_review)
    remaining = sum(1 for r in results if r.needs_review)

    return templates.TemplateResponse(request, "done.html", _ctx(request, {
        "updated": updated,
        "total_auto": total_auto,
        "remaining": remaining,
        "download_ready": True,
        "empresa": _session.get("client_name", "ALO EMBALAGENS LTDA"),
        "periodo": _session.get("period", "Janeiro/2026"),
    }))


@app.get("/download")
async def download():
    results = _session.get("results")
    config  = _session.get("config")
    if not results or not config:
        return HTMLResponse("Sem dados para download. Rode o pipeline primeiro.", status_code=404)

    # Tenta servir o arquivo já gerado em disco
    path = OUTPUT_DIR / "alo_embalagens_01_2026_importacao.txt"
    if path.exists():
        return FileResponse(
            path=str(path),
            filename="alo_embalagens_01_2026_importacao.txt",
            media_type="text/plain",
        )

    # Fallback: gera em memória (necessário no Azure onde o disco é efêmero)
    content = generate(results, config.empresa_cnpj)
    return Response(
        content=content.encode("latin-1"),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=importacao.txt"},
    )


# ---------------------------------------------------------------------------
# React Hub — SPA catch-all (deve ser o último bloco de rotas)
# Retorna index.html para qualquer /app/* — o React Router resolve internamente.
# Os assets (/app/assets/*) são servidos pelo mount acima e chegam aqui
# apenas se o mount ainda não existir (build ausente).
# ---------------------------------------------------------------------------

async def _react_hub(request: Request, full_path: str = ""):
    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return HTMLResponse(
        "<p style='font-family:monospace;padding:2rem'>"
        "Frontend não buildado. Execute: <code>cd frontend && npm install && npm run build</code>"
        "</p>",
        status_code=503,
    )

app.add_api_route("/app", _react_hub, response_class=HTMLResponse)
app.add_api_route("/app/{full_path:path}", _react_hub, response_class=HTMLResponse)
