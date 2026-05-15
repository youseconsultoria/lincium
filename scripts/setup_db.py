"""Cria o schema no PostgreSQL e faz upload do batch atual."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.db.connection import get_connection
from src.db.repository import _ensure_schema

conn = get_connection()
with conn:
    with conn.cursor() as cur:
        _ensure_schema(cur)
        cur.execute(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_schema = 'public' ORDER BY table_name"
        )
        tables = [r["table_name"] for r in cur.fetchall()]
        print("Tabelas:", tables)
conn.close()
print("Schema OK.")
