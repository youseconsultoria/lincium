import os
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from jose import JWTError, jwt

from ..db.connection import get_connection
from ..db.repository import PRIME_TENANT_ID

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "lincium.us.auth0.com")
AUDIENCE     = "https://api.lincium.com.br"
ISSUER       = f"https://{AUTH0_DOMAIN}/"
TENANT_CLAIM = "https://lincium.com.br/tenant_id"
EMAIL_CLAIM  = "https://lincium.com.br/email"
ALGORITHMS   = ["RS256"]

DATA_DIR = Path(__file__).parent.parent.parent / "data"

router = APIRouter(prefix="/api/v1")

_jwks_cache: dict | None = None


def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        resp = httpx.get(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json", timeout=5)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def _verify_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
        jwks = _get_jwks()
        rsa_key = next(
            (
                {"kty": k["kty"], "kid": k["kid"], "use": k["use"], "n": k["n"], "e": k["e"]}
                for k in jwks["keys"]
                if k["kid"] == header["kid"]
            ),
            None,
        )
        if not rsa_key:
            raise HTTPException(status_code=401, detail="Chave pública não encontrada")
        return jwt.decode(token, rsa_key, algorithms=ALGORITHMS, audience=AUDIENCE, issuer=ISSUER)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Token inválido: {exc}")


def _require_auth(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header ausente")
    return _verify_token(auth[7:])


def _get_tenant_name(tenant_id: str) -> str:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM tenants WHERE id = %s", (tenant_id,))
                row = cur.fetchone()
                return row['name'] if row else "Escritório"
    except Exception:
        return "Escritório"


@router.get("/me")
async def me(request: Request):
    payload   = _require_auth(request)
    email     = payload.get(EMAIL_CLAIM) or payload.get("email") or payload.get("sub", "")
    tenant_id = payload.get(TENANT_CLAIM, "")
    return {
        "email": email,
        "tenant_id": tenant_id,
        "tenant_name": _get_tenant_name(tenant_id) if tenant_id else "Escritório",
    }


@router.get("/conciliacao/batches")
async def list_batches(request: Request):
    payload   = _require_auth(request)
    tenant_id = payload.get(TENANT_CLAIM) or PRIME_TENANT_ID
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, client_name, period_year, period_month,
                           total_tx, auto_matched, needs_review_count, status, created_at
                    FROM batches WHERE tenant_id = %s ORDER BY created_at DESC LIMIT 30
                """, (tenant_id,))
                rows = cur.fetchall()
        return [
            {
                "batch_id":           str(r['id']),
                "client_name":        r['client_name'],
                "period_year":        r['period_year'],
                "period_month":       r['period_month'],
                "total_tx":           r['total_tx'],
                "auto_matched":       r['auto_matched'],
                "needs_review_count": r['needs_review_count'],
                "auto_rate":          round(r['auto_matched'] / r['total_tx'] * 100, 1) if r['total_tx'] else 0,
                "status":             r['status'],
                "created_at":         r['created_at'].isoformat() if r['created_at'] else None,
            }
            for r in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/conciliacao/upload")
async def upload_conciliacao(
    request: Request,
    extrato: UploadFile = File(...),
    comprovantes: list[UploadFile] = File(default=[]),
):
    payload   = _require_auth(request)
    tenant_id = payload.get(TENANT_CLAIM) or PRIME_TENANT_ID

    from ..parsers.detector import detect_and_parse
    from ..matching.engine import MatchEngine
    from ..matching.rules import EmpresaConfig
    from ..matching.plano_de_contas import PlanoDeContas
    from ..db import repository as db_repo

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        extrato_path = tmp / (extrato.filename or "extrato.pdf")
        extrato_path.write_bytes(await extrato.read())

        comp_paths = []
        for c in comprovantes:
            p = tmp / (c.filename or "comp.pdf")
            p.write_bytes(await c.read())
            comp_paths.append(p)

        try:
            # Ano estimado: tenta o ano atual; o parser vai refinar com as datas reais
            transactions = detect_and_parse(str(extrato_path), year=datetime.now().year)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Extrato não reconhecido: {exc}")

        # Detecta período predominante nas transações
        if transactions:
            (period_year, period_month), _ = Counter(
                (t.date.year, t.date.month) for t in transactions
            ).most_common(1)[0]
        else:
            now = datetime.now()
            period_year, period_month = now.year, now.month

        comp_objects = []
        for cp in comp_paths:
            try:
                comp_objects.extend(detect_and_parse(str(cp)))
            except ValueError:
                pass

        # MVP: configuração ALO EMBALAGENS — generalizar quando houver múltiplos clientes
        cfg_path   = DATA_DIR / "config_alo_embalagens.json"
        plano_path = DATA_DIR / "plano_contas_alo_embalagens.json"
        if not cfg_path.exists():
            raise HTTPException(status_code=500, detail="Configuração do cliente não encontrada")

        cfg   = EmpresaConfig.from_json(cfg_path)
        plano = PlanoDeContas.from_json(plano_path)

        engine  = MatchEngine(cfg, plano)
        results = engine.match_all(transactions, comprovantes=comp_objects)
        stats   = engine.summary(results)

        batch_id = db_repo.save_batch(
            results,
            tenant_id=tenant_id,
            client_cnpj=cfg.empresa_cnpj,
            client_name="ALO EMBALAGENS LTDA",
            period_year=period_year,
            period_month=period_month,
        )

    return {
        "batch_id": batch_id,
        "client_name": "ALO EMBALAGENS LTDA",
        "period_year": period_year,
        "period_month": period_month,
        "total": stats["total"],
        "auto_matched": stats["auto_matched"],
        "needs_review": stats["needs_review"],
        "auto_rate": stats["auto_rate"],
    }
