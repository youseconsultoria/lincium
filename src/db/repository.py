"""
Operações de banco de dados do Lincium.

Tabelas:
  batches      — um registro por run do pipeline (cliente × mês × banco)
  transactions — um registro por MatchResult dentro do batch
  learning     — decisões humanas acumuladas para melhorar o matching futuro
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from psycopg2.extras import execute_values

from ..matching.engine import MatchResult
from ..models import Comprovante, Transaction
from .connection import get_connection


_SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    id              UUID        PRIMARY KEY,
    client_cnpj     VARCHAR(18) NOT NULL,
    client_name     VARCHAR(200) NOT NULL,
    bank            VARCHAR(50) NOT NULL DEFAULT 'santander',
    period_year     SMALLINT    NOT NULL,
    period_month    SMALLINT    NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_tx        INTEGER     NOT NULL DEFAULT 0,
    auto_matched    INTEGER     NOT NULL DEFAULT 0,
    needs_review_count INTEGER  NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending_review',
    UNIQUE (client_cnpj, period_year, period_month, bank)
);

CREATE TABLE IF NOT EXISTS transactions (
    id              BIGSERIAL   PRIMARY KEY,
    batch_id        UUID        NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
    tx_date         DATE        NOT NULL,
    raw_description TEXT        NOT NULL,
    beneficiary     TEXT,
    doc_number      TEXT,
    amount          NUMERIC(15,2) NOT NULL,
    is_debit        BOOLEAN     NOT NULL,
    source          VARCHAR(50),
    comp_cnpj       VARCHAR(18),
    comp_name       TEXT,
    comp_amount     NUMERIC(15,2),
    cod_deb         VARCHAR(20),
    cod_cred        VARCHAR(20),
    historico       TEXT,
    score           SMALLINT    NOT NULL DEFAULT 0,
    match_type      VARCHAR(30) NOT NULL DEFAULT 'unmatched',
    needs_review    BOOLEAN     NOT NULL DEFAULT TRUE,
    review_reason   TEXT,
    reviewed_at     TIMESTAMPTZ,
    reviewed_by     TEXT
);

CREATE INDEX IF NOT EXISTS idx_tx_batch    ON transactions(batch_id);
CREATE INDEX IF NOT EXISTS idx_tx_review   ON transactions(batch_id, needs_review);

CREATE TABLE IF NOT EXISTS learning (
    id              BIGSERIAL   PRIMARY KEY,
    client_cnpj     VARCHAR(18) NOT NULL,
    raw_description TEXT        NOT NULL,
    beneficiary     TEXT        NOT NULL DEFAULT '',
    cod_deb         VARCHAR(20) NOT NULL,
    cod_cred        VARCHAR(20) NOT NULL,
    decision_count  INTEGER     NOT NULL DEFAULT 1,
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (client_cnpj, raw_description, beneficiary)
);
"""


def _ensure_schema(cur) -> None:
    cur.execute(_SCHEMA)


# ---------------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------------

def save_batch(
    results: list[MatchResult],
    client_cnpj: str,
    client_name: str,
    period_year: int,
    period_month: int,
    bank: str = "santander",
) -> str:
    """
    Persiste um batch no PostgreSQL, substituindo qualquer batch anterior
    do mesmo cliente/período/banco. Retorna o batch_id (UUID).
    """
    batch_id = str(uuid.uuid4())
    auto_matched = sum(1 for r in results if not r.needs_review)
    needs_review_count = len(results) - auto_matched
    status = "completed" if needs_review_count == 0 else "pending_review"

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                _ensure_schema(cur)

                # Substitui batch existente para o mesmo cliente/período/banco
                cur.execute(
                    "DELETE FROM batches WHERE client_cnpj = %s AND period_year = %s"
                    " AND period_month = %s AND bank = %s",
                    (client_cnpj, period_year, period_month, bank),
                )

                cur.execute(
                    """INSERT INTO batches
                       (id, client_cnpj, client_name, bank, period_year, period_month,
                        total_tx, auto_matched, needs_review_count, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (batch_id, client_cnpj, client_name, bank,
                     period_year, period_month,
                     len(results), auto_matched, needs_review_count, status),
                )

                rows = []
                for r in results:
                    tx = r.transaction
                    comp = r.matched_comprovante
                    rows.append((
                        batch_id,
                        tx.date,
                        tx.raw_description,
                        tx.beneficiary,
                        tx.doc_number,
                        float(tx.amount),
                        tx.is_debit,
                        tx.source,
                        comp.cnpj_beneficiary if comp else None,
                        comp.beneficiary_name if comp else None,
                        float(comp.amount_total) if comp else None,
                        r.cod_deb,
                        r.cod_cred,
                        r.historico,
                        r.score,
                        r.match_type,
                        r.needs_review,
                        r.review_reason,
                    ))

                execute_values(cur, """
                    INSERT INTO transactions (
                        batch_id, tx_date, raw_description, beneficiary, doc_number,
                        amount, is_debit, source,
                        comp_cnpj, comp_name, comp_amount,
                        cod_deb, cod_cred, historico, score, match_type,
                        needs_review, review_reason
                    ) VALUES %s
                """, rows)

    finally:
        conn.close()

    return batch_id


def update_reviewed(
    batch_id: str,
    confirmed: dict[str, dict],
    reviewed_by: str | None = None,
) -> int:
    """
    Marca transações como revisadas no DB e atualiza seus códigos contábeis.
    `confirmed` mapeia group_key → {cod_deb, cod_cred}.
    Retorna o número de linhas atualizadas.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                now = datetime.now(timezone.utc)
                updated = 0

                for group_key, codes in confirmed.items():
                    parts = group_key.split("|", 1)
                    raw_desc = parts[0]
                    beneficiary = parts[1] if len(parts) > 1 else ""

                    cur.execute("""
                        UPDATE transactions
                        SET needs_review = FALSE,
                            cod_deb      = %s,
                            cod_cred     = %s,
                            match_type   = 'human_review',
                            reviewed_at  = %s,
                            reviewed_by  = %s
                        WHERE batch_id        = %s
                          AND raw_description = %s
                          AND COALESCE(beneficiary, '') = %s
                          AND needs_review    = TRUE
                    """, (
                        codes["cod_deb"], codes["cod_cred"],
                        now, reviewed_by,
                        batch_id, raw_desc, beneficiary,
                    ))
                    updated += cur.rowcount

                # Fecha o batch se não há mais pendências
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM transactions"
                    " WHERE batch_id = %s AND needs_review = TRUE",
                    (batch_id,),
                )
                if cur.fetchone()["cnt"] == 0:
                    cur.execute(
                        "UPDATE batches SET status = 'completed' WHERE id = %s",
                        (batch_id,),
                    )

                return updated
    finally:
        conn.close()


def save_learning(
    client_cnpj: str,
    confirmed: dict[str, dict],
) -> None:
    """
    Faz upsert das decisões humanas na tabela de aprendizado.
    Cada confirmação incrementa decision_count — usada futuramente para
    melhorar o matching automático.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                now = datetime.now(timezone.utc)
                for group_key, codes in confirmed.items():
                    parts = group_key.split("|", 1)
                    raw_desc = parts[0]
                    beneficiary = parts[1] if len(parts) > 1 else ""

                    cur.execute("""
                        INSERT INTO learning
                            (client_cnpj, raw_description, beneficiary,
                             cod_deb, cod_cred, last_seen)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (client_cnpj, raw_description, beneficiary)
                        DO UPDATE SET
                            cod_deb        = EXCLUDED.cod_deb,
                            cod_cred       = EXCLUDED.cod_cred,
                            decision_count = learning.decision_count + 1,
                            last_seen      = EXCLUDED.last_seen
                    """, (
                        client_cnpj, raw_desc, beneficiary,
                        codes["cod_deb"], codes["cod_cred"], now,
                    ))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------

_PT_MONTHS = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def load_latest_batch() -> tuple[str, str, str, str, list[MatchResult]] | None:
    """
    Carrega o batch mais recente do PostgreSQL.
    Retorna (batch_id, client_cnpj, client_name, period_label, results)
    ou None se não houver nenhum batch.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ensure_schema(cur)

            cur.execute(
                "SELECT * FROM batches ORDER BY created_at DESC LIMIT 1"
            )
            batch = cur.fetchone()
            if not batch:
                return None

            batch_id = str(batch["id"])
            client_cnpj = batch["client_cnpj"]
            client_name = batch["client_name"]
            period_label = (
                f"{_PT_MONTHS[batch['period_month']]}/{batch['period_year']}"
            )

            cur.execute(
                "SELECT * FROM transactions WHERE batch_id = %s ORDER BY id",
                (batch_id,),
            )
            rows = cur.fetchall()

        results = []
        for row in rows:
            tx = Transaction(
                date=row["tx_date"],
                raw_description=row["raw_description"],
                beneficiary=row["beneficiary"],
                doc_number=row["doc_number"],
                amount=Decimal(str(row["amount"])),
                is_debit=row["is_debit"],
                source=row["source"] or "",
            )
            comp = None
            if row["comp_cnpj"]:
                amt = Decimal(str(row["comp_amount"]))
                comp = Comprovante(
                    date=tx.date,
                    type="boleto",
                    cnpj_beneficiary=row["comp_cnpj"],
                    cnpj_final_beneficiary=None,
                    beneficiary_name=row["comp_name"] or "",
                    amount_principal=amt,
                    amount_juros=Decimal("0"),
                    amount_multa=Decimal("0"),
                    amount_total=amt,
                    doc_number=None,
                    payer_cnpj="",
                )
            results.append(MatchResult(
                transaction=tx,
                matched_comprovante=comp,
                cod_deb=row["cod_deb"],
                cod_cred=row["cod_cred"],
                historico=row["historico"] or "",
                score=row["score"],
                match_type=row["match_type"],
                needs_review=row["needs_review"],
                review_reason=row["review_reason"],
            ))

        return batch_id, client_cnpj, client_name, period_label, results

    finally:
        conn.close()
