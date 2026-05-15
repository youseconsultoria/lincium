"""
Migração 001 — Multi-tenancy: adiciona tenant_id às tabelas existentes.

Cria a tabela `tenants`, insere PRIME como tenant piloto e migra as colunas
`batches`, `transactions` e `learning` com tenant_id, backfill e constraints.

Idempotente: pode ser rodado mais de uma vez sem efeito colateral.

Rodar: python scripts/migrate_001_tenant_id.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.db.connection import get_connection

PRIME_UUID = "00000000-0000-0000-0000-000000000001"
PRIME_NAME = "PRIME Contabilidade"


def _step(label: str, cur, sql: str, params=None) -> int:
    print(f"  {label}...", end=" ", flush=True)
    cur.execute(sql, params)
    n = cur.rowcount if cur.rowcount >= 0 else 0
    print("ok" if n == 0 else f"ok ({n} linhas)")
    return n


def run():
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:

                # ------------------------------------------------------------------
                # 1. Tabela tenants
                # ------------------------------------------------------------------
                print("\n[1] Criando tabela tenants")
                _step("CREATE TABLE IF NOT EXISTS tenants", cur, """
                    CREATE TABLE IF NOT EXISTS tenants (
                        id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                        name        VARCHAR(200) NOT NULL,
                        cnpj        VARCHAR(18),
                        created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                        active      BOOLEAN      NOT NULL DEFAULT TRUE
                    )
                """)

                # ------------------------------------------------------------------
                # 2. Registro PRIME
                # ------------------------------------------------------------------
                print("\n[2] Inserindo PRIME como tenant piloto")
                _step(f"INSERT PRIME uuid={PRIME_UUID}", cur, """
                    INSERT INTO tenants (id, name, cnpj)
                    VALUES (%s, %s, NULL)
                    ON CONFLICT (id) DO NOTHING
                """, (PRIME_UUID, PRIME_NAME))

                # ------------------------------------------------------------------
                # 3. Adiciona colunas tenant_id (nullable para permitir backfill)
                # ------------------------------------------------------------------
                print("\n[3] Adicionando coluna tenant_id (nullable)")
                _step("batches.tenant_id",      cur, "ALTER TABLE batches      ADD COLUMN IF NOT EXISTS tenant_id UUID")
                _step("transactions.tenant_id", cur, "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS tenant_id UUID")
                _step("learning.tenant_id",     cur, "ALTER TABLE learning     ADD COLUMN IF NOT EXISTS tenant_id UUID")

                # ------------------------------------------------------------------
                # 4. Backfill — todas as linhas existentes pertencem à PRIME
                # ------------------------------------------------------------------
                print("\n[4] Backfill tenant_id = PRIME")
                n = _step("batches",      cur, "UPDATE batches      SET tenant_id = %s WHERE tenant_id IS NULL", (PRIME_UUID,))
                n = _step("transactions", cur, "UPDATE transactions SET tenant_id = %s WHERE tenant_id IS NULL", (PRIME_UUID,))
                n = _step("learning",     cur, "UPDATE learning     SET tenant_id = %s WHERE tenant_id IS NULL", (PRIME_UUID,))

                # ------------------------------------------------------------------
                # 5. NOT NULL após backfill
                # ------------------------------------------------------------------
                print("\n[5] Aplicando NOT NULL")
                _step("batches.tenant_id",      cur, "ALTER TABLE batches      ALTER COLUMN tenant_id SET NOT NULL")
                _step("transactions.tenant_id", cur, "ALTER TABLE transactions ALTER COLUMN tenant_id SET NOT NULL")
                _step("learning.tenant_id",     cur, "ALTER TABLE learning     ALTER COLUMN tenant_id SET NOT NULL")

                # ------------------------------------------------------------------
                # 6. Foreign keys (idempotente via DO block)
                # ------------------------------------------------------------------
                print("\n[6] Foreign keys → tenants(id)")
                for table, constraint in [
                    ("batches",      "batches_tenant_fk"),
                    ("transactions", "transactions_tenant_fk"),
                    ("learning",     "learning_tenant_fk"),
                ]:
                    _step(f"{table} FK", cur, f"""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.table_constraints
                                WHERE constraint_name = '{constraint}'
                                  AND table_name      = '{table}'
                            ) THEN
                                ALTER TABLE {table}
                                    ADD CONSTRAINT {constraint}
                                    FOREIGN KEY (tenant_id) REFERENCES tenants(id);
                            END IF;
                        END $$
                    """)

                # ------------------------------------------------------------------
                # 7. UNIQUE constraints — adiciona tenant_id
                #    Dropa a constraint antiga (sem tenant_id) e cria nova.
                # ------------------------------------------------------------------
                print("\n[7] Atualizando UNIQUE constraints (adicionando tenant_id)")

                # batches
                _step("batches: drop old unique", cur, """
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM information_schema.table_constraints
                            WHERE constraint_name = 'batches_client_cnpj_period_year_period_month_bank_key'
                              AND table_name      = 'batches'
                        ) THEN
                            ALTER TABLE batches DROP CONSTRAINT
                                batches_client_cnpj_period_year_period_month_bank_key;
                        END IF;
                    END $$
                """)
                _step("batches: add new unique (tenant_id + cliente + período)", cur, """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints
                            WHERE constraint_name = 'batches_unique_per_tenant'
                              AND table_name      = 'batches'
                        ) THEN
                            ALTER TABLE batches ADD CONSTRAINT batches_unique_per_tenant
                                UNIQUE (tenant_id, client_cnpj, period_year, period_month, bank);
                        END IF;
                    END $$
                """)

                # learning
                _step("learning: drop old unique", cur, """
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM information_schema.table_constraints
                            WHERE constraint_name = 'learning_client_cnpj_raw_description_beneficiary_key'
                              AND table_name      = 'learning'
                        ) THEN
                            ALTER TABLE learning DROP CONSTRAINT
                                learning_client_cnpj_raw_description_beneficiary_key;
                        END IF;
                    END $$
                """)
                _step("learning: add new unique (tenant_id + cliente + descrição)", cur, """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints
                            WHERE constraint_name = 'learning_unique_per_tenant'
                              AND table_name      = 'learning'
                        ) THEN
                            ALTER TABLE learning ADD CONSTRAINT learning_unique_per_tenant
                                UNIQUE (tenant_id, client_cnpj, raw_description, beneficiary);
                        END IF;
                    END $$
                """)

                # ------------------------------------------------------------------
                # 8. Índices em tenant_id (para queries filtradas por tenant)
                # ------------------------------------------------------------------
                print("\n[8] Criando índices em tenant_id")
                _step("idx_batch_tenant",    cur, "CREATE INDEX IF NOT EXISTS idx_batch_tenant    ON batches(tenant_id)")
                _step("idx_tx_tenant",       cur, "CREATE INDEX IF NOT EXISTS idx_tx_tenant       ON transactions(tenant_id)")
                _step("idx_learning_tenant", cur, "CREATE INDEX IF NOT EXISTS idx_learning_tenant ON learning(tenant_id)")

                # ------------------------------------------------------------------
                # 9. Sanity checks (dentro da transação — consistente)
                # ------------------------------------------------------------------
                print("\n[9] Sanity checks")

                checks = [
                    ("tenants (esperado: 1)",             "SELECT COUNT(*) AS n FROM tenants",                               1),
                    ("batches sem tenant_id (esperado: 0)", "SELECT COUNT(*) AS n FROM batches WHERE tenant_id IS NULL",    0),
                    ("transactions sem tenant_id (esperado: 0)", "SELECT COUNT(*) AS n FROM transactions WHERE tenant_id IS NULL", 0),
                    ("learning sem tenant_id (esperado: 0)",  "SELECT COUNT(*) AS n FROM learning WHERE tenant_id IS NULL", 0),
                    ("total transactions (esperado: 1885)", "SELECT COUNT(*) AS n FROM transactions",                        1885),
                ]

                all_ok = True
                for label, sql, expected in checks:
                    cur.execute(sql)
                    actual = cur.fetchone()["n"]
                    status = "OK" if actual == expected else f"FALHOU (esperado {expected}, obtido {actual})"
                    if actual != expected:
                        all_ok = False
                    print(f"  {label}: {actual} — {status}")

                if not all_ok:
                    raise RuntimeError("Sanity checks falharam — rollback automático.")

        print("\nMigracao 001 concluida com sucesso.")

    except Exception as e:
        print(f"\nERRO: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
