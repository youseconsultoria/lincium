"""
Serialização de batches de MatchResult para JSON — permite que o pipeline
salve resultados e o servidor de revisão os carregue sem re-processar os PDFs.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from ..matching.engine import MatchResult
from ..models import Transaction, Comprovante


def _serialize(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Not serializable: {type(obj)}")


def save_batch(results: list[MatchResult], path: str | Path) -> None:
    data = []
    for r in results:
        tx = r.transaction
        comp = r.matched_comprovante
        data.append({
            "tx": {
                "date": tx.date.isoformat(),
                "raw_description": tx.raw_description,
                "beneficiary": tx.beneficiary,
                "doc_number": tx.doc_number,
                "amount": str(tx.amount),
                "is_debit": tx.is_debit,
                "source": tx.source,
            },
            "comp": {
                "cnpj_beneficiary": comp.cnpj_beneficiary,
                "beneficiary_name": comp.beneficiary_name,
                "amount_total": str(comp.amount_total),
            } if comp else None,
            "cod_deb": r.cod_deb,
            "cod_cred": r.cod_cred,
            "historico": r.historico,
            "score": r.score,
            "match_type": r.match_type,
            "needs_review": r.needs_review,
            "review_reason": r.review_reason,
        })
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_batch(path: str | Path) -> list[MatchResult]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    results = []
    for item in raw:
        t = item["tx"]
        tx = Transaction(
            date=date.fromisoformat(t["date"]),
            raw_description=t["raw_description"],
            beneficiary=t.get("beneficiary"),
            doc_number=t.get("doc_number"),
            amount=Decimal(t["amount"]),
            is_debit=t["is_debit"],
            source=t.get("source", ""),
        )
        comp = None
        if item.get("comp"):
            c = item["comp"]
            comp = Comprovante(
                date=tx.date,
                type="boleto",
                cnpj_beneficiary=c["cnpj_beneficiary"],
                cnpj_final_beneficiary=None,
                beneficiary_name=c["beneficiary_name"],
                amount_principal=Decimal(c["amount_total"]),
                amount_juros=Decimal("0"),
                amount_multa=Decimal("0"),
                amount_total=Decimal(c["amount_total"]),
                doc_number=None,
                payer_cnpj="",
            )
        results.append(MatchResult(
            transaction=tx,
            matched_comprovante=comp,
            cod_deb=item.get("cod_deb"),
            cod_cred=item.get("cod_cred"),
            historico=item.get("historico", ""),
            score=item.get("score", 0),
            match_type=item.get("match_type", ""),
            needs_review=item.get("needs_review", True),
            review_reason=item.get("review_reason"),
        ))
    return results
