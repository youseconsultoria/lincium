from datetime import date
from decimal import Decimal

from tests.conftest import TESTDATA_DIR
from src.parsers.sicoob import parse_file

PDF = TESTDATA_DIR / "SICOOB - 01.2026.pdf"


def test_parse_two_transactions():
    txs = parse_file(str(PDF), year=2026)
    assert len(txs) == 2, f"Esperado 2, obtido {len(txs)}: {txs}"


def test_all_debits():
    txs = parse_file(str(PDF), year=2026)
    for tx in txs:
        assert tx.is_debit, f"Esperado débito: {tx}"


def test_amounts():
    txs = parse_file(str(PDF), year=2026)
    for tx in txs:
        assert tx.amount == Decimal("128.30"), f"Valor incorreto: {tx}"


def test_dates():
    txs = parse_file(str(PDF), year=2026)
    assert txs[0].date == date(2026, 1, 16)
    assert txs[1].date == date(2026, 1, 30)


def test_description_is_pix():
    txs = parse_file(str(PDF), year=2026)
    for tx in txs:
        assert "PIX" in tx.raw_description.upper()


def test_source():
    txs = parse_file(str(PDF), year=2026)
    for tx in txs:
        assert tx.source == "sicoob"
